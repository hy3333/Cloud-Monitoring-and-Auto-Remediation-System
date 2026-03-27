import json
import os
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import boto3


lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")
asg_client = boto3.client("autoscaling")

REMEDIATION_LAMBDA_NAME = os.environ["REMEDIATION_LAMBDA_NAME"]
LOG_TABLE_NAME = os.environ["LOG_TABLE_NAME"]
NOTIFICATION_TABLE_NAME = os.environ["NOTIFICATION_TABLE_NAME"]
AUTO_SCALING_GROUP_NAME = os.environ["AUTO_SCALING_GROUP_NAME"]

incident_table = dynamodb.Table(LOG_TABLE_NAME)
notification_table = dynamodb.Table(NOTIFICATION_TABLE_NAME)

NOTIFICATION_COOLDOWN_MINUTES = 10


def classify_incident(alarm_name: str, state_value: str) -> tuple[str, str, str]:
    if state_value != "ALARM":
        return "UNKNOWN", "NO_ACTION", "Alarm state is not ALARM"

    alarm_name_lower = alarm_name.lower()

    if "cpu" in alarm_name_lower:
        return "HIGH_CPU", "SCALE_MANAGED_BY_ASG", "Alarm name matched CPU pattern"

    if "status-check" in alarm_name_lower or "statuscheck" in alarm_name_lower:
        return "STATUS_CHECK_FAILED", "REBOOT", "Alarm name matched status check pattern"

    if "lowutilization" in alarm_name_lower or "low-utilization" in alarm_name_lower:
        return "LOW_UTILIZATION", "STOP", "Alarm name matched low utilization pattern"

    return "UNKNOWN", "NO_ACTION", "No known alarm pattern matched"


def resolve_instance_id(event: dict, incident_type: str) -> tuple[str, str]:
    resources = event.get("resources", [])

    for resource in resources:
        if isinstance(resource, str) and ":instance/" in resource:
            return resource.split("/")[-1], "Resolved from EC2 instance ARN in event resources"

    if incident_type == "STATUS_CHECK_FAILED":
        try:
            response = asg_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[AUTO_SCALING_GROUP_NAME]
            )
            groups = response.get("AutoScalingGroups", [])

            if not groups:
                return "UNKNOWN", "ASG not found"

            instances = groups[0].get("Instances", [])

            if not instances:
                return "UNKNOWN", "No instances in ASG"

            for inst in instances:
                if inst.get("HealthStatus") == "Unhealthy":
                    return inst["InstanceId"], "Resolved UNHEALTHY instance from ASG"

            for inst in instances:
                if inst.get("LifecycleState") == "InService":
                    return inst["InstanceId"], "Fallback to InService instance (no unhealthy found)"

            return instances[0]["InstanceId"], "Fallback to first instance in ASG"

        except Exception as e:
            return "UNKNOWN", f"ASG lookup failed: {str(e)}"

    return "UNKNOWN", "Instance resolution not required for this incident type"


def evaluate_cooldown(instance_id: str, action: str, alarm_name: str) -> tuple[bool, bool, str]:
    """
    Returns:
    - should_notify
    - should_remediate
    - reason
    """
    notification_key = f"{instance_id}#{action}#{alarm_name}"
    existing = notification_table.get_item(Key={"notification_key": notification_key})
    item = existing.get("Item")
    now = datetime.now(timezone.utc)

    if item:
        last_sent_time = datetime.fromisoformat(item["last_sent_time"])
        if now - last_sent_time < timedelta(minutes=NOTIFICATION_COOLDOWN_MINUTES):
            return (
                False,
                False,
                f"Cooldown active. Same incident already processed within {NOTIFICATION_COOLDOWN_MINUTES} minutes."
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

    return (
        True,
        True,
        "Cooldown clear. Notification and remediation allowed."
    )


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "")
    state_value = detail.get("state", {}).get("value", "")

    incident_type, action, decision_reason = classify_incident(alarm_name, state_value)
    instance_id, instance_resolution_reason = resolve_instance_id(event, incident_type)

    should_notify = False
    should_remediate = False
    cooldown_reason = "Cooldown not evaluated"

    if action in ["REBOOT", "STOP"]:
        should_notify, should_remediate, cooldown_reason = evaluate_cooldown(
            instance_id=instance_id,
            action=action,
            alarm_name=alarm_name
        )
    elif action == "SCALE_MANAGED_BY_ASG":
        should_notify = False
        should_remediate = False
        cooldown_reason = "Scaling expected to be handled by ASG; no direct remediation or notification."
    else:
        should_notify = False
        should_remediate = False
        cooldown_reason = "No action required for this incident."

    log_item = {
        "log_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_type": incident_type,
        "action": action,
        "instance_id": instance_id,
        "alarm_name": alarm_name,
        "alarm_state": state_value,
        "decision_reason": decision_reason,
        "instance_resolution_reason": instance_resolution_reason,
        "should_notify": should_notify,
        "should_remediate": should_remediate,
        "cooldown_reason": cooldown_reason,
        "source": "decision-handler"
    }

    incident_table.put_item(Item=log_item)

    print(
        f"Decision made | incident_type={incident_type} | action={action} | "
        f"instance_id={instance_id} | reason={decision_reason} | "
        f"instance_resolution_reason={instance_resolution_reason} | "
        f"should_notify={should_notify} | should_remediate={should_remediate} | "
        f"cooldown_reason={cooldown_reason}"
    )

    remediation_invoked = False

    if action in ["REBOOT", "STOP"] and should_remediate and instance_id != "UNKNOWN":
        remediation_payload = {
            "instance_id": instance_id,
            "incident_type": incident_type,
            "action": action,
            "alarm_name": alarm_name,
            "alarm_state": state_value,
            "details": event,
            "should_notify": should_notify,
            "cooldown_reason": cooldown_reason
        }

        lambda_client.invoke(
            FunctionName=REMEDIATION_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(remediation_payload),
        )

        remediation_invoked = True
        print(
            f"Remediation invocation sent | function={REMEDIATION_LAMBDA_NAME} | "
            f"payload={json.dumps(remediation_payload)}"
        )
    else:
        print("Remediation invocation skipped")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                **log_item,
                "remediation_invoked": remediation_invoked
            }
        )
    }