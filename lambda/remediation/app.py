import boto3


ec2 = boto3.client("ec2")


def lambda_handler(event, context):
    print("Received event:", event)

    instance_id = event.get("instance_id")
    action = event.get("action")

    if not instance_id or not action:
        return {
            "statusCode": 400,
            "body": "Missing instance_id or action"
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

    print(result)

    return {
        "statusCode": 200,
        "body": result
    }