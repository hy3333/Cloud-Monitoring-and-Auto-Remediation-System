import os
from datetime import datetime, timezone, timedelta

import boto3


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")
cooldown_table = dynamodb.Table(os.environ["COOLDOWN_TABLE_NAME"])

COOLDOWN_MINUTES = 10


def lambda_handler(event, context):
    print("Received event:", event)

    instance_id = event.get("instance_id")
    action = event.get("action")
    incident_type = event.get("incident_type", "UNKNOWN")
    alarm_name = event.get("alarm_name", "UNKNOWN")

    if not instance_id or not action:
        return {
            "statusCode": 400,
            "body": "Missing instance_id or action"
        }

    cooldown_key = f"{instance_id}#{action}"
    now = datetime.now(timezone.utc)

    existing = cooldown_table.get_item(Key={"cooldown_key": cooldown_key})
    item = existing.get("Item")

    if item:
        last_action_time = datetime.fromisoformat(item["last_action_time"])
        if now - last_action_time < timedelta(minutes=COOLDOWN_MINUTES):
            result = (
                f"Suppressed action {action} for {instance_id}. "
                f"Cooldown active for {COOLDOWN_MINUTES} minutes."
            )
            print(
                f"{result} | incident_type={incident_type} | alarm_name={alarm_name}"
            )

            return {
                "statusCode": 200,
                "body": result
            }

    if action == "REBOOT_INSTANCE":
        ec2.reboot_instances(InstanceIds=[instance_id])
        result = f"Reboot triggered for {instance_id}"

    elif action == "STOP_INSTANCE":
        ec2.stop_instances(InstanceIds=[instance_id])
        result = f"Stop triggered for {instance_id}"

    elif action == "SCALE_UP":
        result = f"No scale action implemented for {instance_id}"

    elif action == "CHECK_ALL_INSTANCES":
        response = ec2.describe_instances()
        result = f"Checked instances. Reservations count: {len(response.get('Reservations', []))}"

    else:
        result = f"No valid remediation mapped for action {action}"

    cooldown_table.put_item(
        Item={
            "cooldown_key": cooldown_key,
            "instance_id": instance_id,
            "action": action,
            "incident_type": incident_type,
            "alarm_name": alarm_name,
            "last_action_time": now.isoformat(),
        }
    )

    print(
        f"Remediation executed | result={result} | incident_type={incident_type} | "
        f"alarm_name={alarm_name}"
    )

    return {
        "statusCode": 200,
        "body": result
    }