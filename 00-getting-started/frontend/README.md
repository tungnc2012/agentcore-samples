# Frontend: S3 Static Website + Lambda + API Gateway

## Architecture

```
User → S3 Static Website → API Gateway (REST) → Lambda → AgentCore Runtime
```

## Setup Steps

### 1. Deploy the agent to AgentCore Runtime

```bash
cd 00-getting-started
agentcore deploy
```

Note the Agent Runtime ARN from the output.

### 2. Create the Lambda function

1. Go to AWS Lambda console → Create function
2. Runtime: Python 3.12
3. Upload `lambda/handler.py` as the function code
4. Set environment variable: `AGENT_RUNTIME_ARN` = your agent ARN
5. Attach an IAM policy allowing `bedrock-agentcore:InvokeAgentRuntime` on your agent ARN
6. Set timeout to at least 60 seconds (agent responses can take time)

### 3. Create API Gateway

1. Go to API Gateway console → Create REST API
2. Create a resource `/chat` with POST method → point to your Lambda
3. Enable CORS on the `/chat` resource
4. Deploy to a stage (e.g., `prod`)
5. Copy the invoke URL (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod/chat`)

### 4. Configure and upload the static website

1. Edit `s3-website/index.html` — replace `YOUR_API_GATEWAY_URL` with your API Gateway URL
2. Create an S3 bucket with static website hosting enabled
3. Upload `s3-website/index.html` to the bucket
4. Set the bucket policy to allow public read (or use CloudFront with OAC for private access)

### 5. (Optional) Add CloudFront

For HTTPS and caching, create a CloudFront distribution pointing to your S3 bucket.

## Lambda IAM Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock-agentcore:InvokeAgentRuntime",
            "Resource": "YOUR_AGENT_RUNTIME_ARN"
        }
    ]
}
```
