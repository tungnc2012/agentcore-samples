# Quick Deploy Reference

Quick command reference for deploying the Customer Support agent.

## Option A: S3 Zip Deployment (Fastest)

```bash
# Setup
cd agentcore-samples/00-getting-started/CustomerSupport
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="agentcore-artifacts-${ACCOUNT_ID}"
REGION="us-east-1"
ROLE_NAME="AgentCoreCustomerSupportRole"

# Package
cd app/CustomerSupport && uv sync && cd ../..
zip -r agent-package.zip app/CustomerSupport -x "*.pyc" -x "*__pycache__*" -x "*.venv/*"

# Upload
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}
aws s3 cp agent-package.zip s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip

# IAM Role
cat > trust-policy.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock-agentcore.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name ${ROLE_NAME} --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text)
sleep 15

# Deploy
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name CustomerSupport \
  --execution-role-arn "${ROLE_ARN}" \
  --code-location "s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip" \
  --runtime-version PYTHON_3_14 \
  --protocol HTTP \
  --network-mode PUBLIC \
  --region ${REGION}

# Get Runtime ARN
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes --region ${REGION} \
  --query "agentRuntimeSummaries[?agentRuntimeName=='CustomerSupport'].agentRuntimeArn | [0]" --output text)
RUNTIME_ID=$(echo ${RUNTIME_ARN} | cut -d'/' -f2)

# Wait for READY
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id ${RUNTIME_ID} --region ${REGION} --query 'agentRuntime.status' --output text)
  echo "Status: ${STATUS}"
  [ "${STATUS}" = "READY" ] && break
  sleep 10
done

# Test
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "What products do you have?"}' \
  --region ${REGION}
```

---

## Option B: ECR Container Deployment (Production)

```bash
# Setup
cd agentcore-samples/00-getting-started/CustomerSupport
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
REPO_NAME="customer-support-agent"
ROLE_NAME="AgentCoreCustomerSupportRole"

# Build
docker build -t customer-support-agent:latest .

# ECR Setup
aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION}
REPO_URI=$(aws ecr describe-repositories --repository-names ${REPO_NAME} --region ${REGION} \
  --query 'repositories[0].repositoryUri' --output text)

# Push
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
docker tag customer-support-agent:latest ${REPO_URI}:latest
docker push ${REPO_URI}:latest

# IAM Role
cat > trust-policy.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock-agentcore.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name ${ROLE_NAME} --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text)
sleep 15

# Deploy
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name CustomerSupport \
  --execution-role-arn "${ROLE_ARN}" \
  --image-uri "${REPO_URI}:latest" \
  --runtime-version PYTHON_3_14 \
  --protocol HTTP \
  --network-mode PUBLIC \
  --region ${REGION}

# Get Runtime ARN
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes --region ${REGION} \
  --query "agentRuntimeSummaries[?agentRuntimeName=='CustomerSupport'].agentRuntimeArn | [0]" --output text)
RUNTIME_ID=$(echo ${RUNTIME_ARN} | cut -d'/' -f2)

# Wait for READY
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id ${RUNTIME_ID} --region ${REGION} --query 'agentRuntime.status' --output text)
  echo "Status: ${STATUS}"
  [ "${STATUS}" = "READY" ] && break
  sleep 10
done

# Test
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "What products do you have?"}' \
  --region ${REGION}
```

---

## Quick Update

### S3 Update
```bash
zip -r agent-package.zip app/CustomerSupport -x "*.pyc" -x "*__pycache__*" -x "*.venv/*"
aws s3 cp agent-package.zip s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip
aws bedrock-agentcore-control update-agent-runtime --agent-runtime-id ${RUNTIME_ID} \
  --code-location "s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip" --region ${REGION}
```

### ECR Update
```bash
docker build -t customer-support-agent:latest .
docker tag customer-support-agent:latest ${REPO_URI}:v1.1
docker push ${REPO_URI}:v1.1
docker tag customer-support-agent:latest ${REPO_URI}:latest
docker push ${REPO_URI}:latest
aws bedrock-agentcore-control update-agent-runtime --agent-runtime-id ${RUNTIME_ID} \
  --image-uri "${REPO_URI}:latest" --region ${REGION}
```

---

## Quick Cleanup

```bash
# Delete Runtime
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id ${RUNTIME_ID} --region ${REGION}

# S3 Cleanup
aws s3 rm s3://${BUCKET_NAME} --recursive
aws s3 rb s3://${BUCKET_NAME}

# ECR Cleanup
aws ecr delete-repository --repository-name ${REPO_NAME} --region ${REGION} --force

# IAM Cleanup
aws iam detach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam detach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam detach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly 2>/dev/null || true
aws iam delete-role --role-name ${ROLE_NAME}
```
