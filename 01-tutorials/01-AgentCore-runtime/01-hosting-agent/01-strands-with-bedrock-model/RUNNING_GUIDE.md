# Running the Strands + Bedrock Agent Tutorial (No Jupyter Required)

This guide replaces the notebook cells from **"Deploying the agent to AgentCore Runtime"** onwards.
All steps run from your terminal inside this folder:

```
01-strands-with-bedrock-model/
```

---

## Prerequisites

- Python 3.10+, AWS CLI configured, Docker running
- Dependencies installed: `uv pip install -r requirements.txt`
- Bedrock model access enabled in your target region (see note below)
- AWS credentials with permissions for: ECR, IAM, Bedrock AgentCore

> **Region note:** The default model `global.anthropic.claude-haiku-4-5-20251001-v1:0`
> requires cross-region inference. If you're in `ap-southeast-1`, switch to
> `apac.amazon.nova-lite-v1:0` in `strands_claude.py` and ensure Nova Lite access
> is enabled in the [Bedrock console](https://ap-southeast-1.console.aws.amazon.com/bedrock/home#/modelaccess).

---

## Step 1: Test the Agent Locally (No AWS Runtime)

Before deploying, verify the agent works on your machine:

```bash
python test_local.py '{"prompt": "What is the weather in Brisbane?"}'
python test_local.py '{"prompt": "What is 5 + 7?"}'
```

Expected output: the agent calls the `weather` or `calculator` tool and returns a response.

---

## Step 2: Run the Agent as a Local HTTP Server

This simulates exactly what AgentCore Runtime does in AWS:

```bash
python strands_claude.py
```

The server starts on port 8080. Open a **second terminal** and test it:

```bash
# Health check
curl http://localhost:8080/ping

# Invoke the agent
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the weather in Athens?"}'

# Another invocation
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2 + 2?"}'
```

Press `Ctrl+C` in the first terminal to stop the server when done.

---

## Step 3: Configure the AgentCore Runtime Deployment

> **Skip this step** if `.bedrock_agentcore.yaml` already exists in this folder
> (it was created in a previous run). Delete it first if you want a fresh config:
> `rm .bedrock_agentcore.yaml`

```python
# Run in Python or paste into a python3 interactive session
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session

boto_session = Session()
region = boto_session.region_name
print(f"Region: {region}")

agentcore_runtime = Runtime()
agent_name = "strands_claude_getting_started"

response = agentcore_runtime.configure(
    entrypoint="strands_claude.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name,
)
print(response)
```

Or run it via the deploy script:

```bash
python deploy.py
```

After this step you will see:
- `.bedrock_agentcore.yaml` — local config file
- `Dockerfile` — auto-generated container definition

---

## Step 4: Launch the Agent to AgentCore Runtime

This builds the Docker image, pushes it to ECR, and creates the runtime in AWS.
It takes **3-5 minutes**.

```bash
python deploy.py
```

The deploy script handles the full flow automatically. If you want to run it step by step in Python:

```python
from bedrock_agentcore_starter_toolkit import Runtime

agentcore_runtime = Runtime()
launch_result = agentcore_runtime.launch()

print(f"Agent ARN : {launch_result.agent_arn}")
print(f"Agent ID  : {launch_result.agent_id}")
print(f"ECR URI   : {launch_result.ecr_uri}")
```

---

## Step 5: Check Runtime Status

Poll until status is `READY`:

```python
import time
from bedrock_agentcore_starter_toolkit import Runtime

agentcore_runtime = Runtime()
end_statuses = ["READY", "CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"]

status_response = agentcore_runtime.status()
status = status_response.endpoint["status"]

while status not in end_statuses:
    print(f"Status: {status} — waiting...")
    time.sleep(10)
    status_response = agentcore_runtime.status()
    status = status_response.endpoint["status"]

print(f"Final status: {status}")
```

Or check via AWS CLI:

```bash
# Get your runtime ID from .bedrock_agentcore.yaml first
RUNTIME_ID=$(python3 -c "
import yaml
with open('.bedrock_agentcore.yaml') as f:
    cfg = yaml.safe_load(f)
print(cfg['agents']['strands_claude_getting_started']['bedrock_agentcore']['agent_id'])
")

aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id $RUNTIME_ID \
  --query 'agentRuntime.status' \
  --output text
```

---

## Step 6: Invoke the Deployed Runtime

Once status is `READY`, invoke it:

```python
from bedrock_agentcore_starter_toolkit import Runtime

agentcore_runtime = Runtime()

response = agentcore_runtime.invoke({"prompt": "How is the weather now in Athens?"})
print(response["response"][0])
```

Or use the deploy script's invoke-only mode:

```bash
python deploy.py --invoke-only
```

Or invoke directly with boto3:

```python
import boto3, json
from boto3.session import Session
from bedrock_agentcore_starter_toolkit import Runtime

region = Session().region_name
agentcore_runtime = Runtime()
launch_result = agentcore_runtime.status()
agent_arn = launch_result.endpoint["agentRuntimeArn"]

client = boto3.client("bedrock-agentcore", region_name=region)

response = client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    qualifier="DEFAULT",
    payload=json.dumps({"prompt": "What is 2 + 2?"})
)

runtime_session_id = response.get("runtimeSessionId")
print(f"Session ID: {runtime_session_id}")

events = [e for e in response.get("response", [])]
print(json.loads(events[0].decode("utf-8")))
```

---

## Step 7: Stop a Session

Sessions consume vCPU and memory while active. Stop them when done:

```python
import boto3
from boto3.session import Session

region = Session().region_name
client = boto3.client("bedrock-agentcore", region_name=region)

# Replace with your actual values
agent_arn = "<your-agent-runtime-arn>"
session_id = "<your-runtime-session-id>"  # from invoke response

client.stop_runtime_session(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=session_id,
    qualifier="DEFAULT"
)
print(f"Session {session_id} stopped")
```

---

## Step 8: Lifecycle Configuration (Optional)

Set a shorter idle timeout to auto-terminate inactive sessions:

```python
import boto3
from boto3.session import Session

region = Session().region_name
control_client = boto3.client("bedrock-agentcore-control", region_name=region)

runtime_id = "<your-runtime-id>"  # from .bedrock_agentcore.yaml

# Must re-supply all required fields (UpdateAgentRuntime is a full replacement)
current = control_client.get_agent_runtime(agentRuntimeId=runtime_id)

control_client.update_agent_runtime(
    agentRuntimeId=runtime_id,
    agentRuntimeArtifact=current["agentRuntimeArtifact"],
    roleArn=current["roleArn"],
    networkConfiguration=current["networkConfiguration"],
    lifecycleConfiguration={
        "idleRuntimeSessionTimeout": 300  # 5 minutes
    }
)
print("Idle timeout set to 5 minutes")
```

---

## Step 9: Cleanup

Delete all AWS resources to avoid ongoing charges:

```bash
python deploy.py --cleanup
```

Or manually:

```python
import boto3, os
from boto3.session import Session
from bedrock_agentcore_starter_toolkit import Runtime

region = Session().region_name
agentcore_runtime = Runtime()

# Get IDs
status = agentcore_runtime.status()
agent_id = status.endpoint.get("agentRuntimeId")
ecr_uri = status.endpoint.get("ecrUri", "")

control_client = boto3.client("bedrock-agentcore-control", region_name=region)
ecr_client = boto3.client("ecr", region_name=region)

# Delete runtime
control_client.delete_agent_runtime(agentRuntimeId=agent_id)
print(f"Runtime {agent_id} deleted")

# Delete ECR repo
if ecr_uri:
    repo_name = ecr_uri.split("/")[1]
    ecr_client.delete_repository(repositoryName=repo_name, force=True)
    print(f"ECR repo {repo_name} deleted")

# Remove local config
if os.path.exists(".bedrock_agentcore.yaml"):
    os.remove(".bedrock_agentcore.yaml")
    print(".bedrock_agentcore.yaml deleted")
```

---

## Quick Reference

| Goal | Command |
|------|---------|
| Test agent locally (no server) | `python test_local.py '{"prompt": "..."}'` |
| Run agent as local HTTP server | `python strands_claude.py` |
| Invoke local server | `curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "..."}'` |
| Deploy to AWS (full flow) | `python deploy.py` |
| Deploy + delete after | `python deploy.py --cleanup` |
| Invoke already-deployed runtime | `python deploy.py --invoke-only` |
| Check runtime status (CLI) | `aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id <id> --query 'agentRuntime.status'` |

---

## Cost Reminder

- AgentCore Runtime: **$0.0895/vCPU-hour + $0.00945/GB-hour** (only while sessions are active)
- Bedrock model calls: per token (see [pricing](https://aws.amazon.com/bedrock/pricing/))
- Always run cleanup when done to avoid unexpected charges
