import json
import os
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import boto3


dynamodb = boto3.resource("dynamodb")
incident_table = dynamodb.Table(os.environ["LOG_TABLE_NAME"])
notification_table = dynamodb.Table(os.environ["NOTIFICATION_TABLE_NAME"])

sns = boto3.client("sns")
lambda_client = boto3.client("lambda")

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
REMEDIATION_FUNCTION_NAME = os.environ["REMEDIATION_FUNCTION_NAME"]

NOTIFICATION_COOLDOWN_MINUTES = 10


def classify_incident(alarm_name: str, state_value: str) -> tuple[str, str, str]:
    if state_value != "ALARM":
        return "UNKNOWN", "NO_ACTION", "Alarm state is not ALARM"

    if "HighCPU" in alarm_name:
        return "HIGH_CPU", "SCALE_UP", "Alarm name matched HighCPU pattern"
    if "StatusCheck" in alarm_name:
        return "STATUS_CHECK_FAILED", "REBOOT_INSTANCE", "Alarm name matched StatusCheck pattern"
    if "LowUtilization" in alarm_name:
        return "LOW_UTILIZATION", "STOP_INSTANCE", "Alarm name matched LowUtilization pattern"
    if "Health" in alarm_name or "Scheduled" in alarm_name:
        return "SCHEDULED_HEALTH_EVALUATION", "CHECK_ALL_INSTANCES", "Alarm name matched health evaluation pattern"

    return "UNKNOWN", "NO_ACTION", "No known alarm pattern matched"


def should_send_notification(instance_id: str, action: str, alarm_name: str) -> tuple[bool, str]:
    notification_key = f"{instance_id}#{action}#{alarm_name}"
    existing = notification_table.get_item(Key={"notification_key": notification_key})
    item = existing.get("Item")
    now = datetime.now(timezone.utc)

    if item:
        last_sent_time = datetime.fromisoformat(item["last_sent_time"])
        if now - last_sent_time < timedelta(minutes=NOTIFICATION_COOLDOWN_MINUTES):
            return False, (
                f"Notification suppressed. Same incident notified within "
                f"{NOTIFICATION_COOLDOWN_MINUTES} minutes."
            )

    notification_table.put_item(
        Item={
            "notification_key": notification_key,
            "instance_id": instance_id,
            "action": action,
            "alarm_name": alarm_name,
            "last_sent_time": now.isoformat(),
        }
    )

    return True, "Notification allowed. No recent duplicate notification found."


def lambda_handler(event, context):
    print("Received event:", event)

    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "")
    state_value = detail.get("state", {}).get("value", "")
    resources = event.get("resources", [])

    instance_id = resources[0] if resources else "UNKNOWN"

    incident_type, action, decision_reason = classify_incident(alarm_name, state_value)

    log_item = {
        "log_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_type": incident_type,
        "action": action,
        "instance_id": instance_id,
        "alarm_name": alarm_name,
        "alarm_state": state_value,
        "decision_reason": decision_reason,
    }

    incident_table.put_item(Item=log_item)

    print(
        f"Decision made | incident_type={incident_type} | action={action} | "
        f"instance_id={instance_id} | reason={decision_reason}"
    )

    if action != "NO_ACTION" and instance_id != "UNKNOWN":
        remediation_payload = {
            "instance_id": instance_id,
            "incident_type": incident_type,
            "action": action,
            "alarm_name": alarm_name,
        }

        lambda_client.invoke(
            FunctionName=REMEDIATION_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(remediation_payload),
        )

        print(
            f"Remediation invocation sent | function={REMEDIATION_FUNCTION_NAME} | "
            f"payload={remediation_payload}"
        )

    should_notify, notification_reason = should_send_notification(instance_id, action, alarm_name)

    print(
        f"Notification decision | should_notify={should_notify} | "
        f"reason={notification_reason}"
    )

    if should_notify:
        message = {
            "timestamp": log_item["timestamp"],
            "incident_type": incident_type,
            "action": action,
            "instance_id": instance_id,
            "alarm_name": alarm_name,
            "alarm_state": state_value,
            "decision_reason": decision_reason,
            "notification_reason": notification_reason,
        }

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Incident Detected: {incident_type}",
            Message=json.dumps(message, indent=2),
        )

        print("SNS notification sent")
    else:
        print("SNS notification skipped due to cooldown")

    return {
        "statusCode": 200,
        "body": log_item
    }