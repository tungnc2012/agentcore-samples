# Deploying Exam Mockup Agent to AWS

This guide covers two deployment options:
1. **Flask Web App on ECS/EC2** — the full web UI with question navigator, scoring, and AI explanations
2. **AgentCore API** — headless agent deployed to Amazon Bedrock AgentCore

---

## Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Docker installed and running
- An AWS account with access to:
  - Amazon ECR (Elastic Container Registry)
  - Amazon ECS (Elastic Container Service) or EC2
  - Amazon Bedrock (Claude model enabled in your region)
- Bedrock model access enabled for `us.anthropic.claude-sonnet-4-20250514` in `us-east-1`

---

## Option 1: Deploy Flask Web App to ECS Fargate

### Step 1: Update the Dockerfile for Flask

Create a production Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exam_mockup_agent/ ./exam_mockup_agent/
COPY templates/ ./templates/

EXPOSE 5000

ENV FLASK_SECRET_KEY=change-this-to-a-random-string

CMD ["python", "exam_mockup_agent/flask_app.py"]
```

### Step 2: Build and push Docker image to ECR

```bash
# Set variables
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REPO_NAME=exam-mockup-agent
IMAGE_TAG=latest

# Create ECR repository (first time only)
aws ecr create-repository --repository-name $REPO_NAME --region $REGION

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build and tag
docker build -t $REPO_NAME:$IMAGE_TAG .
docker tag $REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG

# Push
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
```

### Step 3: Create ECS Task Definition

Create `task-definition.json`:

```json
{
  "family": "exam-mockup-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "exam-mockup-agent",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/exam-mockup-agent:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "FLASK_SECRET_KEY", "value": "your-production-secret-key"},
        {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/exam-mockup-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Step 4: Create IAM Task Role

The task role needs Bedrock access for AI explanations:

```bash
# Create the role
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach Bedrock policy
aws iam put-role-policy \
  --role-name ecsTaskRole \
  --policy-name BedrockAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-20250514"
    }]
  }'
```

### Step 5: Create ECS Cluster and Service

```bash
# Create cluster
aws ecs create-cluster --cluster-name exam-prep-cluster

# Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/exam-mockup-agent

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service (requires a VPC with public subnets and security group allowing port 5000)
aws ecs create-service \
  --cluster exam-prep-cluster \
  --service-name exam-mockup-agent \
  --task-definition exam-mockup-agent \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

### Step 6: Access the app

Once the task is running, find the public IP:

```bash
TASK_ARN=$(aws ecs list-tasks --cluster exam-prep-cluster --service-name exam-mockup-agent --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster exam-prep-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "App available at: http://$PUBLIC_IP:5000"
```

---

## Option 2: Deploy to Amazon Bedrock AgentCore

This deploys the agent as a headless API (no web UI) that can be invoked programmatically.

### Step 1: Install AgentCore CLI

```bash
pip install bedrock-agentcore
```

### Step 2: Build the Docker image

```bash
docker build -t exam-mockup-agent:latest .
```

### Step 3: Configure and launch

```bash
# Configure the agent
agentcore configure \
  --name exam-mockup-agent \
  --image exam-mockup-agent:latest \
  --region us-east-1

# Deploy
agentcore launch --name exam-mockup-agent
```

### Step 4: Invoke the agent

```python
import boto3
import json

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# Example: Upload questions
response = client.invoke_agent(
    agentId="your-agent-id",
    sessionId="session-123",
    inputText=json.dumps({
        "action": "start_session",
        "mode": "practice",
        "questions": [...]  # your parsed questions
    })
)
```

---

## Option 3: Quick Deploy to EC2 (simplest)

For a quick single-instance deployment:

```bash
# SSH into your EC2 instance
ssh ec2-user@your-instance-ip

# Clone the repo
git clone <your-repo-url>
cd agentcore-samples
git checkout flask-frontend

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install flask openpyxl boto3 flask-session

# Set environment variables
export FLASK_SECRET_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Run with gunicorn for production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "exam_mockup_agent.flask_app:app"
```

Make sure the EC2 instance has an IAM role with Bedrock `InvokeModel` permission.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for session encryption | `dev-secret-key-change-in-prod` |
| `AWS_DEFAULT_REGION` | AWS region for Bedrock calls | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials (if not using IAM role) | — |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials (if not using IAM role) | — |

---

## Security Considerations

- Always set a strong `FLASK_SECRET_KEY` in production
- Use IAM roles (not access keys) when running on AWS
- Put an ALB or CloudFront in front for HTTPS
- Restrict the security group to only allow traffic from your network
- Consider adding authentication (e.g. Cognito) for multi-user access
