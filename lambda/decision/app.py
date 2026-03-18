def lambda_handler(event, context):
    print("Received event:", event)

    alarm_name = event.get("detail", {}).get("alarmName")
    instance_id = None
    resources = event.get("resources", [])

    if resources:
        instance_id = resources[0]

    incident_type = "UNKNOWN"
    action = "NO_ACTION"

    if alarm_name == "high-cpu-alarm":
        incident_type = "HIGH_CPU"
        action = "SCALE_UP"

    elif alarm_name == "status-check-failed-alarm":
        incident_type = "STATUS_CHECK_FAILED"
        action = "REBOOT_INSTANCE"

    elif alarm_name == "low-utilization-alarm":
        incident_type = "LOW_UTILIZATION"
        action = "STOP_INSTANCE"

    elif event.get("detail-type") == "Scheduled Event":
        incident_type = "SCHEDULED_HEALTH_EVALUATION"
        action = "CHECK_ALL_INSTANCES"

    response = {
        "incident_type": incident_type,
        "action": action,
        "instance_id": instance_id
    }

    print("Decision response:", response)

    return {
        "statusCode": 200,
        "body": str(response)
    }