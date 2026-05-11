#!/bin/bash
# Deployment script for Exam Mockup Agent on Amazon Bedrock AgentCore
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed and running
#   - agentcore CLI installed (pip install bedrock-agentcore)
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -e

APP_NAME="exam-mockup-agent"
REGION="${AWS_REGION:-us-east-1}"

echo "=== Building Docker image ==="
docker build -t "${APP_NAME}:latest" .

echo "=== Configuring AgentCore deployment ==="
agentcore configure \
    --name "${APP_NAME}" \
    --image "${APP_NAME}:latest" \
    --region "${REGION}"

echo "=== Launching on AgentCore ==="
agentcore launch --name "${APP_NAME}"

echo "=== Deployment complete ==="
echo "Agent '${APP_NAME}' is now running on Amazon Bedrock AgentCore."
