"""
Lambda function that proxies requests to the AgentCore Runtime agent.
Receives a prompt from API Gateway and returns the agent's response.
"""

import os
import json
import boto3

AGENT_ARN = os.environ["AGENT_RUNTIME_ARN"]
REGION = os.environ.get("AWS_REGION", "us-east-1")

agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)


def handler(event, context):
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, "")

    try:
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")
        if not prompt:
            return _cors_response(400, {"error": "prompt is required"})

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": prompt}),
        )

        # Collect streamed response
        content = []
        for chunk in response.get("response", []):
            if isinstance(chunk, bytes):
                content.append(chunk.decode("utf-8"))
            else:
                content.append(str(chunk))

        return _cors_response(200, {"response": "".join(content)})

    except Exception as e:
        print(f"Error: {e}")
        return _cors_response(500, {"error": str(e)})


def _cors_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body) if isinstance(body, dict) else body,
    }
