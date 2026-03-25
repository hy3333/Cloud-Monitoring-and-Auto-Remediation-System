# Cloud Monitoring & Auto-Remediation System

## 📌 Overview

This project implements a production-grade cloud monitoring and auto-remediation system on AWS using Infrastructure as Code (IaC).

It monitors EC2 instances running in an Auto Scaling Group (ASG), detects incidents using CloudWatch alarms, and triggers automated decision-making and remediation workflows using Lambda.

---

## 🚀 Key Features

- Fully deployed using AWS SAM (IaC)
- Auto Scaling Group (ASG) for dynamic scaling
- Application Load Balancer (ALB)
- CloudWatch alarms for monitoring
- EventBridge for event-driven flow
- Lambda-based decision engine
- Automated remediation (reboot/stop)
- SNS notifications with cooldown logic
- DynamoDB logging system
- CloudWatch dashboard

---

## 🧠 Architecture Flow

CloudWatch Alarm → EventBridge → Decision Lambda →  
→ (Reboot/Stop if needed) → Remediation Lambda → EC2  
→ Logs → DynamoDB  
→ Notification → SNS  

---

## 📊 Incident Handling Logic

| Incident Type         | Action                     | Reason |
|----------------------|---------------------------|--------|
| HIGH_CPU             | SCALE_MANAGED_BY_ASG      | Scaling handled by ASG |
| STATUS_CHECK_FAILED  | REBOOT                    | Instance unhealthy |
| LOW_UTILIZATION      | STOP                      | Cost optimization |

---

## ⚙️ Tech Stack

- AWS SAM (CloudFormation)
- AWS Lambda (Python)
- Amazon EC2
- Auto Scaling Group
- Application Load Balancer
- CloudWatch (Alarms + Dashboard)
- EventBridge
- DynamoDB
- SNS

---

## 🏗️ Infrastructure Components

### Compute
- EC2 instances
- Launch Template
- Auto Scaling Group

### Networking
- Application Load Balancer
- Security Groups

### Monitoring
- CloudWatch Alarms
- CloudWatch Dashboard

### Serverless
- Decision Lambda
- Remediation Lambda

### Storage
- DynamoDB (logs + cooldown tracking)

### Notifications
- SNS (email alerts)

---

## 🧠 Architecture Diagram

![Architecture Diagram](docs/architectureflow.png)



## 📁 Project Structure

.
├── template.yaml  
├── samconfig.toml  
├── README.md  
├── docs/  
│   └── architecture.png  
├── lambda/  
│   ├── decision/  
│   │   ├── app.py  
│   │   └── requirements.txt  
│   └── remediation/  
│       ├── app.py  
│       └── requirements.txt  
├── test_events/  
│   ├── high_cpu_alarm.json  
│   ├── status_check_failed_alarm.json  
│   ├── low_utilization_alarm.json  
│   ├── normal_state_event.json  
│   ├── unknown_alarm.json  
│   └── sample_event.json  

---

## 🚀 Deployment

### Build

sam build
sam deploy --guided


