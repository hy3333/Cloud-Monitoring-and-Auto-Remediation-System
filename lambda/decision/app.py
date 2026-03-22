import json
import os
from uuid import uuid4
from datetime import datetime, timezone

import boto3


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["LOG_TABLE_NAME"])

sns = boto3.client("sns")
lambda_client = boto3.client("lambda")

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
REMEDIATION_FUNCTION_NAME = os.environ["REMEDIATION_FUNCTION_NAME"]


def lambda_handler(event, context):
    print("Received event:", event)

    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "")
    state_value = detail.get("state", {}).get("value", "")
    resources = event.get("resources", [])

    instance_id = "UNKNOWN"
    if resources:
        instance_id = resources[0]

    incident_type = "UNKNOWN"
    action = "NO_ACTION"

    if state_value == "ALARM":
        if "HighCPU" in alarm_name:
            incident_type = "HIGH_CPU"
            action = "SCALE_UP"
        elif "StatusCheck" in alarm_name:
            incident_type = "STATUS_CHECK_FAILED"
            action = "REBOOT_INSTANCE"
        elif "LowUtilization" in alarm_name:
            incident_type = "LOW_UTILIZATION"
            action = "STOP_INSTANCE"
        elif "Health" in alarm_name or "Scheduled" in alarm_name:
            incident_type = "SCHEDULED_HEALTH_EVALUATION"
            action = "CHECK_ALL_INSTANCES"

    item = {
        "log_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_type": incident_type,
        "action": action,
        "instance_id": instance_id,
        "alarm_name": alarm_name,
        "alarm_state": state_value,
    }

    table.put_item(Item=item)

    if action != "NO_ACTION" and instance_id != "UNKNOWN":
        remediation_payload = {
            "instance_id": instance_id,
            "incident_type": incident_type,
            "action": action,
        }

        lambda_client.invoke(
            FunctionName=REMEDIATION_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(remediation_payload),
        )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Incident Detected",
        Message=str(item)
    )

    return {
        "statusCode": 200,
        "body": item
    }