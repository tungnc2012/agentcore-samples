# Manual Deployment Guide for AgentCore Customer Support Agent

This guide walks you through deploying the Customer Support agent to AWS **without** using `agentcore deploy`. You'll use AWS CLI commands directly to understand each deployment step.

## Deployment Options

This guide covers **two deployment methods**:

1. **[Option A: S3 Zip Package](#option-a-deploy-via-s3-zip-package)** — Simpler, faster for small agents
2. **[Option B: ECR Container](#option-b-deploy-via-ecr-container)** — More flexible, better for complex dependencies

Choose the method that best fits your needs. Both result in the same runtime behavior.

## Prerequisites

Before starting, ensure you have:

- ✅ AWS CLI v2 installed and configured
- ✅ Valid AWS credentials with appropriate permissions
- ✅ Completed the agent development (Steps 1-3 from README.md)
- ✅ Your agent tested locally with `agentcore dev`

**Additional for Option B (ECR):**
- ✅ Docker installed and running
- ✅ Docker daemon accessible

Verify your setup:

```bash
aws --version  # Should show AWS CLI 2.x
aws sts get-caller-identity  # Should return your AWS account info

# For Option B only:
docker --version  # Should show Docker 20.x or later
docker ps  # Should connect to Docker daemon
```

## Required IAM Permissions

Your IAM user/role needs these permissions:

- `s3:CreateBucket`, `s3:PutObject`, `s3:GetObject`
- `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:GetRole`
- `bedrock-agentcore-control:CreateAgentRuntime`, `bedrock-agentcore-control:GetAgentRuntime`
- `bedrock-agentcore:InvokeAgentRuntime`
- `bedrock:InvokeModel` (for the LLM calls)

---

## Option A: Deploy via S3 Zip Package

This method packages your agent as a zip file and uploads it to S3. It's simpler and faster for straightforward agents.

### Step A1: Package Your Agent Code

Navigate to your project root and create a deployment package:

```bash
cd agentcore-samples/00-getting-started/CustomerSupport
```

Create the zip package:

```bash
cd app/CustomerSupport

# Ensure dependencies are installed
uv sync

# Return to project root
cd ../..

# Create deployment package (excludes unnecessary files)
zip -r agent-package.zip app/CustomerSupport \
  -x "*.pyc" \
  -x "*__pycache__*" \
  -x "*.venv/*" \
  -x "*.git/*" \
  -x "*.pytest_cache/*"
```

Verify the package was created:

```bash
ls -lh agent-package.zip
# Should show a file around 1-5 MB
```

---

### Step A2: Create S3 Bucket and Upload Package

Create a unique S3 bucket for your deployment artifacts:

```bash
# Generate a unique bucket name using your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="agentcore-artifacts-${ACCOUNT_ID}"
REGION="us-east-1"

echo "Bucket name: ${BUCKET_NAME}"

# Create the bucket
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}
```

Upload your agent package:

```bash
aws s3 cp agent-package.zip \
  s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip
```

Verify the upload:

```bash
aws s3 ls s3://${BUCKET_NAME}/CustomerSupport/
# Should show agent-package.zip with timestamp
```

---

### Step A3: Create IAM Execution Role

Your agent needs an IAM role to execute with proper permissions.

#### A3.1 Create Trust Policy

Create a trust policy document that allows AgentCore to assume the role:

```bash
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

#### A3.2 Create the IAM Role

```bash
ROLE_NAME="AgentCoreCustomerSupportRole"

aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://trust-policy.json \
  --description "Execution role for AgentCore Customer Support Agent"
```

#### A3.3 Attach Required Policies

Attach Amazon Bedrock permissions:

```bash
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

Attach CloudWatch Logs permissions:

```bash
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

#### A3.4 Get the Role ARN

Save the role ARN for the next step:

```bash
ROLE_ARN=$(aws iam get-role \
  --role-name ${ROLE_NAME} \
  --query 'Role.Arn' \
  --output text)

echo "Role ARN: ${ROLE_ARN}"
```

**Important:** Wait 10-15 seconds for IAM role propagation before proceeding.

```bash
sleep 15
```

---

### Step A4: Create AgentCore Runtime (S3 Source)

Now deploy your agent to AgentCore Runtime:

```bash
RUNTIME_NAME="CustomerSupport"

aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name ${RUNTIME_NAME} \
  --execution-role-arn "${ROLE_ARN}" \
  --code-location "s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip" \
  --runtime-version PYTHON_3_14 \
  --protocol HTTP \
  --network-mode PUBLIC \
  --region ${REGION}
```

This command returns JSON output. Extract and save the runtime ARN:

```bash
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region ${REGION} \
  --query "agentRuntimeSummaries[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeArn | [0]" \
  --output text)

echo "Runtime ARN: ${RUNTIME_ARN}"
```

Extract the runtime ID (needed for status checks):

```bash
RUNTIME_ID=$(echo ${RUNTIME_ARN} | cut -d'/' -f2)
echo "Runtime ID: ${RUNTIME_ID}"
```

---

### Step A5: Wait for Runtime to be Ready

The runtime takes 2-3 minutes to provision. Check the status:

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --region ${REGION} \
  --query 'agentRuntime.status' \
  --output text
```

**Expected status progression:**
- `CREATING` → Initial provisioning
- `READY` → Ready to accept requests

Keep running the status check until you see `READY`:

```bash
# Automated polling script
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id ${RUNTIME_ID} \
    --region ${REGION} \
    --query 'agentRuntime.status' \
    --output text)
  
  echo "Current status: ${STATUS}"
  
  if [ "${STATUS}" = "READY" ]; then
    echo "✅ Runtime is ready!"
    break
  elif [ "${STATUS}" = "CREATE_FAILED" ]; then
    echo "❌ Runtime creation failed!"
    exit 1
  fi
  
  echo "Waiting 10 seconds..."
  sleep 10
done
```

---

### Step A6: Invoke Your Deployed Agent

Once the runtime is `READY`, you can invoke it.

#### A6.1 Simple Invocation

Test with a basic query:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "What products do you have?"}' \
  --region ${REGION} \
  --output text \
  --query 'response'
```

#### A6.2 Product Information Query

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "Tell me about the Smart Watch (PROD-002)"}' \
  --region ${REGION} \
  --output text \
  --query 'response'
```

#### A6.3 Return Policy Query

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "What is the return policy for electronics?"}' \
  --region ${REGION} \
  --output text \
  --query 'response'
```

#### A6.4 Multi-Tool Query

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "I bought a Wireless Headphones. Can I return it and what is the policy?"}' \
  --region ${REGION} \
  --output text \
  --query 'response'
```

---

## Option B: Deploy via ECR Container

This method packages your agent as a Docker container and pushes it to Amazon ECR. It provides more flexibility for complex dependencies and custom runtime configurations.

### Step B1: Build Docker Image

Navigate to your project root where the Dockerfile is located:

```bash
cd agentcore-samples/00-getting-started/CustomerSupport
```

Build the Docker image:

```bash
docker build -t customer-support-agent:latest .
```

Verify the image was created:

```bash
docker images | grep customer-support-agent
# Should show your image with 'latest' tag
```

**Optional:** Test the container locally before deploying:

```bash
# Run container locally
docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}" \
  customer-support-agent:latest

# In another terminal, test it
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What products do you have?"}'

# Stop the container with Ctrl+C
```

---

### Step B2: Create ECR Repository

Set up variables:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
REPO_NAME="customer-support-agent"

echo "Account ID: ${ACCOUNT_ID}"
echo "Region: ${REGION}"
echo "Repository: ${REPO_NAME}"
```

Create the ECR repository:

```bash
aws ecr create-repository \
  --repository-name ${REPO_NAME} \
  --region ${REGION}
```

Get the repository URI:

```bash
REPO_URI=$(aws ecr describe-repositories \
  --repository-names ${REPO_NAME} \
  --region ${REGION} \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "Repository URI: ${REPO_URI}"
```

---

### Step B3: Authenticate Docker to ECR

Get authentication token and login:

```bash
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
```

You should see: `Login Succeeded`

---

### Step B4: Tag and Push Image to ECR

Tag your local image with the ECR repository URI:

```bash
docker tag customer-support-agent:latest ${REPO_URI}:latest
```

Push the image to ECR:

```bash
docker push ${REPO_URI}:latest
```

This may take 1-2 minutes depending on your internet speed.

Verify the image was pushed:

```bash
aws ecr describe-images \
  --repository-name ${REPO_NAME} \
  --region ${REGION}
```

---

### Step B5: Create IAM Execution Role

Your agent needs an IAM role with ECR pull permissions.

#### B5.1 Create Trust Policy

```bash
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

#### B5.2 Create the IAM Role

```bash
ROLE_NAME="AgentCoreCustomerSupportRole"

aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://trust-policy.json \
  --description "Execution role for AgentCore Customer Support Agent (ECR)"
```

#### B5.3 Attach Required Policies

Attach Amazon Bedrock permissions:

```bash
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

Attach CloudWatch Logs permissions:

```bash
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

Attach ECR read permissions:

```bash
aws iam attach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

#### B5.4 Get the Role ARN

```bash
ROLE_ARN=$(aws iam get-role \
  --role-name ${ROLE_NAME} \
  --query 'Role.Arn' \
  --output text)

echo "Role ARN: ${ROLE_ARN}"
```

Wait for IAM propagation:

```bash
sleep 15
```

---

### Step B6: Create AgentCore Runtime (ECR Source)

Create the runtime using the ECR image:

```bash
RUNTIME_NAME="CustomerSupport"

aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name ${RUNTIME_NAME} \
  --execution-role-arn "${ROLE_ARN}" \
  --image-uri "${REPO_URI}:latest" \
  --runtime-version PYTHON_3_14 \
  --protocol HTTP \
  --network-mode PUBLIC \
  --region ${REGION}
```

Extract the runtime ARN and ID:

```bash
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region ${REGION} \
  --query "agentRuntimeSummaries[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeArn | [0]" \
  --output text)

RUNTIME_ID=$(echo ${RUNTIME_ARN} | cut -d'/' -f2)

echo "Runtime ARN: ${RUNTIME_ARN}"
echo "Runtime ID: ${RUNTIME_ID}"
```

---

### Step B7: Wait for Runtime to be Ready

Poll the runtime status:

```bash
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id ${RUNTIME_ID} \
    --region ${REGION} \
    --query 'agentRuntime.status' \
    --output text)
  
  echo "Current status: ${STATUS}"
  
  if [ "${STATUS}" = "READY" ]; then
    echo "✅ Runtime is ready!"
    break
  elif [ "${STATUS}" = "CREATE_FAILED" ]; then
    echo "❌ Runtime creation failed!"
    exit 1
  fi
  
  echo "Waiting 10 seconds..."
  sleep 10
done
```

---

### Step B8: Invoke Your Deployed Agent

Test the containerized agent:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "What products do you have?"}' \
  --region ${REGION} \
  --output text \
  --query 'response'
```

---

## Monitoring and Debugging

### View Runtime Details

Get comprehensive runtime information:

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --region ${REGION}
```

### Check CloudWatch Logs

Your agent logs are sent to CloudWatch Logs:

```bash
# List log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/bedrock-agentcore" \
  --region ${REGION}

# Get recent log events (replace LOG_GROUP_NAME and LOG_STREAM_NAME)
aws logs tail /aws/bedrock-agentcore/CustomerSupport \
  --follow \
  --region ${REGION}
```

### Test with Streaming Response

For streaming responses, you can use a simple script:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "${RUNTIME_ARN}" \
  --qualifier DEFAULT \
  --payload '{"prompt": "List all available products with their prices"}' \
  --region ${REGION} \
  | jq -r '.response'
```

---

## Updating Your Agent

When you make changes to your agent code, follow the appropriate update process for your deployment method.

### Option A: Update S3 Zip Deployment

#### 1. Repackage

```bash
cd app/CustomerSupport
uv sync  # Update dependencies if needed
cd ../..
zip -r agent-package.zip app/CustomerSupport \
  -x "*.pyc" -x "*__pycache__*" -x "*.venv/*"
```

#### 2. Upload New Package

```bash
aws s3 cp agent-package.zip \
  s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip
```

#### 3. Update Runtime

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --code-location "s3://${BUCKET_NAME}/CustomerSupport/agent-package.zip" \
  --region ${REGION}
```

#### 4. Wait for Update to Complete

```bash
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id ${RUNTIME_ID} \
    --region ${REGION} \
    --query 'agentRuntime.status' \
    --output text)
  
  echo "Update status: ${STATUS}"
  
  if [ "${STATUS}" = "READY" ]; then
    echo "✅ Update complete!"
    break
  fi
  
  sleep 10
done
```

---

### Option B: Update ECR Container Deployment

#### 1. Rebuild Docker Image

```bash
cd agentcore-samples/00-getting-started/CustomerSupport
docker build -t customer-support-agent:latest .
```

#### 2. Tag with New Version

Use a version tag for better tracking:

```bash
VERSION="v1.1"  # Increment this for each update
docker tag customer-support-agent:latest ${REPO_URI}:${VERSION}
docker tag customer-support-agent:latest ${REPO_URI}:latest
```

#### 3. Push Updated Image

```bash
# Authenticate if needed
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Push both tags
docker push ${REPO_URI}:${VERSION}
docker push ${REPO_URI}:latest
```

#### 4. Update Runtime

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --image-uri "${REPO_URI}:latest" \
  --region ${REGION}
```

#### 5. Wait for Update to Complete

```bash
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id ${RUNTIME_ID} \
    --region ${REGION} \
    --query 'agentRuntime.status' \
    --output text)
  
  echo "Update status: ${STATUS}"
  
  if [ "${STATUS}" = "READY" ]; then
    echo "✅ Update complete!"
    break
  fi
  
  sleep 10
done
```

#### 6. Rollback (if needed)

If the update causes issues, rollback to a previous version:

```bash
# List available image tags
aws ecr list-images \
  --repository-name ${REPO_NAME} \
  --region ${REGION}

# Rollback to specific version
PREVIOUS_VERSION="v1.0"
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --image-uri "${REPO_URI}:${PREVIOUS_VERSION}" \
  --region ${REGION}
```

---

## Cost Considerations

AgentCore uses **consumption-based pricing** — no upfront costs or minimum fees. You pay only for what you use.

> Prices shown are for `us-east-1`. Other regions may vary. Always check the [official pricing pages](#pricing-references) for the latest rates.

---

### 1. AgentCore Runtime

Charged per active session based on vCPU and memory consumed.

| Resource | Price |
|----------|-------|
| vCPU | $0.0895 per vCPU-hour |
| Memory | $0.00945 per GB-hour |

**Example:** A session using 1 vCPU + 2 GB RAM running for 1 hour:
```
(1 × $0.0895) + (2 × $0.00945) = $0.1084 per hour
```

Sessions are billed only while active. Idle time between invocations is not charged.

---

### 2. Amazon Bedrock Model Inference

Charged per token (input + output). Pricing varies by model.

#### Amazon Nova Models (recommended for ap-southeast-1 / APAC)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Nova Micro | $0.035 | $0.14 |
| Nova Lite | $0.06 | $0.24 |
| Nova Pro | $0.80 | $3.20 |

#### Anthropic Claude Models (us-east-1 only)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3 Haiku | $0.25 | $1.25 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude Opus 4.5 | $5.00 | $25.00 |

> Cross-region inference profiles (e.g., `apac.amazon.nova-lite-v1:0`) may have slightly different rates. Check the Bedrock pricing page for details.

---

### 3. Supporting Services

#### Option A: S3 Zip Deployment

| Resource | Price |
|----------|-------|
| S3 Storage | $0.023 per GB/month |
| S3 PUT request (upload) | $0.005 per 1,000 requests |
| S3 GET request (runtime pull) | $0.0004 per 1,000 requests |

For a typical ~5 MB agent package: **< $0.01/month**

#### Option B: ECR Container Deployment

| Resource | Price |
|----------|-------|
| ECR Storage | $0.10 per GB/month |
| ECR Data Transfer (within region) | Free |

For a typical ~300 MB container image: **~$0.03/month**

#### CloudWatch Logs (both options)

| Resource | Price |
|----------|-------|
| Log ingestion | $0.50 per GB |
| Log storage | $0.03 per GB/month |

For typical agent usage: **< $1/month**

---

### Cost Examples

#### Example 1: Light Development Usage
- 50 invocations/day, ~500 tokens each (250 input + 250 output)
- Model: Nova Lite
- Session duration: ~5 seconds per invocation

```
Daily tokens:  50 × 500 = 25,000 tokens
Monthly tokens: 25,000 × 30 = 750,000 tokens

Bedrock (Nova Lite):
  Input:  375,000 × $0.06/1M  = $0.02
  Output: 375,000 × $0.24/1M  = $0.09

Runtime (50 sessions × 5s = 250s = 0.07 hours):
  vCPU:   0.07 × $0.0895      = $0.006
  Memory: 0.07 × 2 × $0.00945 = $0.001

Monthly total: ~$0.12/month
```

#### Example 2: Moderate Production Usage
- 1,000 invocations/day, ~1,000 tokens each
- Model: Claude 3.5 Sonnet
- Session duration: ~10 seconds per invocation

```
Daily tokens:  1,000 × 1,000 = 1,000,000 tokens
Monthly tokens: 1,000,000 × 30 = 30,000,000 tokens

Bedrock (Claude 3.5 Sonnet):
  Input:  15M × $3.00/1M  = $45.00
  Output: 15M × $15.00/1M = $225.00

Runtime (1,000 sessions × 10s = 2.78 hours/day × 30 = 83.3 hours):
  vCPU:   83.3 × $0.0895      = $7.46
  Memory: 83.3 × 2 × $0.00945 = $1.57

Monthly total: ~$279/month
```

#### Example 3: This Tutorial (Getting Started)
- ~20 test invocations total
- Model: Nova Lite or Claude 3 Haiku
- Just learning/testing

```
Estimated total cost: < $0.05
```

---

### Cost Optimization Tips

- **Use Nova Lite** for development and testing — it's ~50x cheaper than Claude 3.5 Sonnet
- **Stop sessions** when done with `stop_runtime_session` to avoid idle charges
- **Set idle timeout** on your runtime to auto-terminate inactive sessions
- **Use prompt caching** for repeated system prompts (reduces input token costs)
- **Monitor with CloudWatch** — set billing alerts at $5, $20, $50 thresholds

Set a billing alert:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-Cost-Alert" \
  --alarm-description "Alert when estimated charges exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:billing-alerts
```

---

### Pricing References

- [Amazon Bedrock AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
- [Amazon Bedrock Model Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon ECR Pricing](https://aws.amazon.com/ecr/pricing/)
- [Amazon S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)

---

## Cleanup

To avoid ongoing charges, delete all resources based on your deployment method.

### Common Cleanup Steps

#### 1. Delete AgentCore Runtime

```bash
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id ${RUNTIME_ID} \
  --region ${REGION}
```

Wait for deletion to complete:

```bash
while true; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id ${RUNTIME_ID} \
    --region ${REGION} \
    --query 'agentRuntime.status' \
    --output text 2>&1)
  
  if echo "${STATUS}" | grep -q "ResourceNotFoundException"; then
    echo "✅ Runtime deleted successfully"
    break
  fi
  
  echo "Deletion in progress..."
  sleep 10
done
```

#### 2. Delete IAM Role

```bash
# Detach policies
aws iam detach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam detach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

# For ECR deployments, also detach:
aws iam detach-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly 2>/dev/null || true

# Delete the role
aws iam delete-role --role-name ${ROLE_NAME}
```

---

### Option A: Cleanup S3 Resources

```bash
# Delete all objects first
aws s3 rm s3://${BUCKET_NAME} --recursive

# Delete the bucket
aws s3 rb s3://${BUCKET_NAME}

# Clean up local files
rm agent-package.zip
rm trust-policy.json
```

---

### Option B: Cleanup ECR Resources

```bash
# Delete all images in the repository
aws ecr batch-delete-image \
  --repository-name ${REPO_NAME} \
  --image-ids "$(aws ecr list-images \
    --repository-name ${REPO_NAME} \
    --region ${REGION} \
    --query 'imageIds[*]' \
    --output json)" \
  --region ${REGION} 2>/dev/null || true

# Delete the ECR repository
aws ecr delete-repository \
  --repository-name ${REPO_NAME} \
  --region ${REGION} \
  --force

# Clean up local Docker images
docker rmi customer-support-agent:latest
docker rmi ${REPO_URI}:latest

# Clean up local files
rm trust-policy.json
```

---

## Troubleshooting

### Runtime Creation Fails

**Error:** `InvalidParameterException: Invalid execution role`

**Solution:** Wait 30 seconds after creating the IAM role for propagation, then retry.

---

### Runtime Status Stuck in CREATING

**Possible causes:**
- S3 package is corrupted or too large
- IAM role lacks required permissions
- Code has syntax errors

**Solution:** Check CloudWatch Logs for error details.

---

### Invocation Returns Empty Response

**Possible causes:**
- Agent code has runtime errors
- Model access not enabled in Bedrock
- Incorrect payload format

**Solution:** 
1. Check CloudWatch Logs for Python exceptions
2. Verify Bedrock model access in console
3. Ensure payload has `{"prompt": "your question"}` format

---

### "Operation not allowed" Error

**Cause:** Bedrock model access not granted

**Solution:** Go to [Bedrock Console → Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess) and enable Claude or Nova models.

---

### Docker Build Fails

**Error:** `Cannot connect to the Docker daemon`

**Solution:** Ensure Docker Desktop is running:
```bash
docker ps  # Should not error
```

---

### ECR Push Fails with "no basic auth credentials"

**Cause:** Docker not authenticated to ECR

**Solution:** Re-authenticate:
```bash
aws ecr get-login-password --region ${REGION} | \
  docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
```

---

### Container Fails Health Check

**Cause:** Agent not responding on port 8080

**Solution:** 
1. Check CloudWatch Logs for Python errors
2. Verify `main.py` has `if __name__ == "__main__": app.run()`
3. Test container locally:
```bash
docker run -p 8080:8080 customer-support-agent:latest
curl http://localhost:8080/ping
```

---

## Choosing Between S3 and ECR Deployment

| Factor | S3 Zip Package | ECR Container |
|--------|----------------|---------------|
| **Setup Complexity** | Simpler | More complex |
| **Build Time** | ~1 min | ~2-3 min |
| **Deployment Speed** | Faster | Slightly slower |
| **Dependency Management** | Limited to Python packages | Full control (system libs, binaries) |
| **Image Size** | Smaller (~5-20 MB) | Larger (~200-500 MB) |
| **Version Control** | Manual tagging | Built-in image tags |
| **Rollback** | Manual S3 versioning | Easy with image tags |
| **Local Testing** | Requires separate setup | Test exact production image |
| **Best For** | Simple agents, quick iterations | Complex deps, reproducible builds |
| **CI/CD Integration** | Basic | Advanced |

### When to Use S3 Zip Package

- ✅ Your agent only needs Python packages
- ✅ You want faster iteration cycles
- ✅ You're prototyping or learning
- ✅ Your dependencies are straightforward

### When to Use ECR Container

- ✅ You need system-level dependencies (e.g., ffmpeg, custom binaries)
- ✅ You want reproducible builds across environments
- ✅ You need easy rollback capabilities
- ✅ You're building production-grade agents
- ✅ You want to test locally with the exact production image

---

## Comparison: Manual vs CLI Deployment

| Aspect | Manual (This Guide) | `agentcore deploy` |
|--------|---------------------|-------------------|
| **Time (S3)** | ~10 minutes | ~4 minutes |
| **Time (ECR)** | ~15 minutes | ~6 minutes |
| **Steps** | 6-8 manual steps | 1 command |
| **Learning** | Understand each component | Abstracted away |
| **Flexibility** | Full control | Opinionated defaults |
| **Updates** | Manual repackage + upload | Automatic |
| **Rollback** | Manual | Built-in |
| **Best For** | Learning, custom setups | Production, iteration |

---

## Next Steps

Now that you understand manual deployment, consider:

1. **Automate with Scripts**: Create a bash script combining these steps
2. **Use Infrastructure as Code**: Convert to CloudFormation or Terraform
3. **Try the CLI**: Experience the simplified workflow with `agentcore deploy`
4. **Add CI/CD**: Integrate deployment into GitHub Actions or AWS CodePipeline

For production deployments, the AgentCore CLI is recommended as it handles edge cases, retries, and state management automatically.

---

## Additional Resources

- [AWS Bedrock AgentCore API Reference](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/)
- [AgentCore CLI Documentation](https://github.com/aws/agentcore-cli)
- [Strands Agents SDK](https://strandsagents.com/)
- [AWS CLI Command Reference](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/bedrock-agentcore/index.html)
