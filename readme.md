# Cloud Monitoring & Auto-Remediation System (AWS)

## Overview
Production-grade cloud monitoring system built using AWS services and Infrastructure as Code (AWS SAM).  
It detects incidents on EC2 instances running in an Auto Scaling Group (ASG) and triggers automated decision-making and remediation.

---

## Key Highlights
- Event-driven architecture using CloudWatch + EventBridge
- Automated remediation using AWS Lambda
- Intelligent decision engine (incident classification + cooldown logic)
- Auto Scaling integration (separation of scaling vs remediation)
- DynamoDB logging + notification tracking
- SNS alerts with duplicate suppression
- Fully deployed using AWS SAM (IaC)

---

## Architecture Diagram
![Architecture Diagram](docs/architectureflow.png)

---

## CloudWatch Dashboard
![Dashboard](docs/CLOUD-MONITORING-DASHBOARD.png)

---

## Tech Stack
- AWS SAM (CloudFormation)
- AWS Lambda (Python)
- Amazon EC2 + Auto Scaling Group
- Application Load Balancer (ALB)
- CloudWatch (Alarms + Dashboard)
- EventBridge
- DynamoDB
- SNS

---

## System Flow
CloudWatch Alarm → EventBridge → Decision Lambda →  
→ Remediation Lambda (if needed) → EC2 Action  
→ DynamoDB Logs → SNS Notification  

---

## Incident Handling Logic

| Incident Type        | Action                    | Description |
|---------------------|---------------------------|-------------|
| HIGH_CPU            | SCALE_MANAGED_BY_ASG     | Load handled by ASG scaling |
| STATUS_CHECK_FAILED | REBOOT                   | Instance unhealthy |
| LOW_UTILIZATION     | STOP                     | Cost optimization |

---

## Core Design Decisions

### Scaling vs Remediation
- Scaling handled by ASG policies
- Remediation handled by Lambda

### Cooldown Mechanism
- Prevents repeated alerts and actions
- Ensures system stability under repeated alarms

### Instance Resolution
- Dynamically identifies correct EC2 instance from ASG
- Avoids hardcoding

---

## Deployment

### Build
```
sam build
```

### First Deploy
```
sam deploy --guided
```

### Subsequent Deploy
```
sam deploy
```

---

## Testing

Use test events:
- high_cpu_alarm.json
- status_check_failed_alarm.json

### Expected Behavior
- High CPU → No reboot, ASG scales
- Status failure → Instance reboot
- Duplicate events → Suppressed via cooldown

---

## Real-World Value
- Reduces manual intervention in cloud operations
- Improves system reliability
- Demonstrates production-level architecture design

---

## Future Improvements
- Multi-region deployment
- Slack/Webhook alerts
- Predictive scaling
- Advanced analytics

---

## Author
    Himanshu Yadav
