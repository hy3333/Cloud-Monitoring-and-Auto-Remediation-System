import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

table = dynamodb.Table(os.environ["LOG_TABLE_NAME"])
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def send_notification(subject: str, message: str) -> None:
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message
    )


def log_incident(instance_id, alarm_name, alarm_state, incident_type, action, details, result_message, status):
    table.put_item(
        Item={
            "log_id": str(uuid4()),
            "instance_id": instance_id or "UNKNOWN",
            "alarm_name": alarm_name or "UNKNOWN",
            "alarm_state": alarm_state or "UNKNOWN",
            "incident_type": incident_type or "UNKNOWN",
            "action": action or "NO_ACTION",
            "status": status,
            "result_message": result_message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    instance_id = event.get("instance_id")
    alarm_name = event.get("alarm_name")
    alarm_state = event.get("alarm_state")
    incident_type = event.get("incident_type", "UNKNOWN")
    action = event.get("action", "NO_ACTION")
    details = event.get("details", {})

    result_message = ""
    status = "SUCCESS"

    try:
        if not instance_id and action in ["REBOOT", "STOP"]:
            raise ValueError("instance_id is required for REBOOT or STOP action")

        if action == "REBOOT":
            ec2.reboot_instances(InstanceIds=[instance_id])
            result_message = f"Reboot triggered for instance {instance_id}"

        elif action == "STOP":
            ec2.stop_instances(InstanceIds=[instance_id])
            result_message = f"Stop triggered for instance {instance_id}"

        else:
            result_message = f"No remediation action taken for incident type {incident_type}"

    except Exception as e:
        status = "FAILED"
        result_message = f"Remediation failed: {str(e)}"
        print("Remediation error:", result_message)

    log_incident(
        instance_id=instance_id,
        alarm_name=alarm_name,
        alarm_state=alarm_state,
        incident_type=incident_type,
        action=action,
        details=details,
        result_message=result_message,
        status=status
    )

    send_notification(
        subject=f"[Cloud Monitoring] {incident_type} - {action} - {status}",
        message=(
            f"Alarm Name: {alarm_name}\n"
            f"Alarm State: {alarm_state}\n"
            f"Instance ID: {instance_id}\n"
            f"Incident Type: {incident_type}\n"
            f"Action: {action}\n"
            f"Status: {status}\n"
            f"Result: {result_message}\n"
            f"Details: {json.dumps(details)}"
        )
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": result_message,
                "status": status,
                "instance_id": instance_id,
                "incident_type": incident_type,
                "action": action
            }
        )
    }