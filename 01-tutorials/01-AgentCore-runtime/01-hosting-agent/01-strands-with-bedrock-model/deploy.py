"""
deploy.py — mirrors the deployment cells from the notebook.

Steps:
  1. Configure the AgentCore Runtime (generates Dockerfile, IAM role, ECR repo)
  2. Launch (build image, push to ECR, create runtime)
  3. Poll until READY
  4. Invoke and print the response
  5. Cleanup (delete runtime, ECR repo, local config file)

Usage:
  python deploy.py              # deploy + invoke + keep resources
  python deploy.py --cleanup    # deploy + invoke + delete all resources
  python deploy.py --invoke-only  # invoke an already-deployed runtime (reads agent_arn from .bedrock_agentcore.yaml)
"""
import argparse
import json
import os
import time

import boto3
from boto3.session import Session
from bedrock_agentcore_starter_toolkit import Runtime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_status(runtime_obj, end_statuses, label="Runtime"):
    """Poll runtime status until it reaches a terminal state."""
    status_response = runtime_obj.status()
    status = status_response.endpoint["status"]
    while status not in end_statuses:
        print(f"  {label} status: {status} — waiting...")
        time.sleep(10)
        status_response = runtime_obj.status()
        status = status_response.endpoint["status"]
    print(f"  {label} final status: {status}")
    return status


def invoke_and_print(runtime_obj, prompt):
    """Invoke the runtime and pretty-print the response."""
    print(f"\nInvoking with prompt: '{prompt}'")
    response = runtime_obj.invoke({"prompt": prompt})
    text = response["response"][0]
    print(f"Response: {text}\n")
    return text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Deploy Strands agent to AgentCore Runtime")
    parser.add_argument("--cleanup", action="store_true", help="Delete all AWS resources after invocation")
    parser.add_argument("--invoke-only", action="store_true", help="Skip deploy, only invoke existing runtime")
    args = parser.parse_args()

    boto_session = Session()
    region = boto_session.region_name
    print(f"AWS region: {region}")

    end_statuses = ["READY", "CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"]

    # ------------------------------------------------------------------
    # DEPLOY
    # ------------------------------------------------------------------
    if not args.invoke_only:
        print("\n=== Step 1: Configure ===")
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
        print(f"Configure response: {response}")

        print("\n=== Step 2: Launch ===")
        launch_result = agentcore_runtime.launch()
        print(f"Agent ARN : {launch_result.agent_arn}")
        print(f"Agent ID  : {launch_result.agent_id}")
        print(f"ECR URI   : {launch_result.ecr_uri}")

        print("\n=== Step 3: Wait for READY ===")
        status = wait_for_status(agentcore_runtime, end_statuses)
        if status != "READY":
            print(f"Deployment failed with status: {status}")
            return

        print("\n=== Step 4: Invoke ===")
        invoke_and_print(agentcore_runtime, "How is the weather now in Athens?")
        invoke_and_print(agentcore_runtime, "What is 2 + 2?")

        # ------------------------------------------------------------------
        # LIFECYCLE DEMO — second runtime with short idle timeout
        # ------------------------------------------------------------------
        print("\n=== Step 5: Lifecycle demo (short idle timeout runtime) ===")
        agentcore_runtime_short = Runtime()
        agent_name_short = "strands_claude_short_timeout"

        agentcore_runtime_short.configure(
            entrypoint="strands_claude.py",
            auto_create_execution_role=True,
            auto_create_ecr=True,
            requirements_file="requirements.txt",
            region=region,
            agent_name=agent_name_short,
        )

        launch_result_short = agentcore_runtime_short.launch()
        print(f"Short-timeout runtime launched: {launch_result_short.agent_id}")

        status_short = wait_for_status(agentcore_runtime_short, end_statuses, label="Short-timeout runtime")

        if status_short == "READY":
            # Update idle timeout to 5 minutes via boto3
            agentcore_control_client = boto3.client("bedrock-agentcore-control", region_name=region)
            current_runtime = agentcore_control_client.get_agent_runtime(
                agentRuntimeId=launch_result_short.agent_id
            )
            agentcore_control_client.update_agent_runtime(
                agentRuntimeId=launch_result_short.agent_id,
                agentRuntimeArtifact=current_runtime["agentRuntimeArtifact"],
                roleArn=current_runtime["roleArn"],
                networkConfiguration=current_runtime["networkConfiguration"],
                lifecycleConfiguration={"idleRuntimeSessionTimeout": 300},
            )
            print("✅ Runtime updated with 5-minute idle timeout")

            invoke_and_print(agentcore_runtime_short, "What is 3 + 3?")

        # ------------------------------------------------------------------
        # CLEANUP
        # ------------------------------------------------------------------
        if args.cleanup:
            print("\n=== Cleanup ===")
            agentcore_client = boto3.client("bedrock-agentcore", region_name=region)
            agentcore_control_client = boto3.client("bedrock-agentcore-control", region_name=region)
            ecr_client = boto3.client("ecr", region_name=region)

            # Delete original runtime
            try:
                agentcore_control_client.delete_agent_runtime(agentRuntimeId=launch_result.agent_id)
                print(f"✅ Original runtime '{launch_result.agent_id}' deleted")
            except Exception as e:
                print(f"⚠️  Could not delete original runtime: {e}")

            # Delete short-timeout runtime
            try:
                agentcore_control_client.delete_agent_runtime(agentRuntimeId=launch_result_short.agent_id)
                print(f"✅ Short-timeout runtime '{launch_result_short.agent_id}' deleted")
            except Exception as e:
                print(f"⚠️  Could not delete short-timeout runtime: {e}")

            # Delete ECR repos
            for result, label in [(launch_result, "original"), (launch_result_short, "short-timeout")]:
                try:
                    repo_name = result.ecr_uri.split("/")[1]
                    ecr_client.delete_repository(repositoryName=repo_name, force=True)
                    print(f"✅ ECR repository '{repo_name}' ({label}) deleted")
                except Exception as e:
                    print(f"⚠️  Could not delete ECR repo ({label}): {e}")

            # Remove local config
            config_file = ".bedrock_agentcore.yaml"
            if os.path.exists(config_file):
                os.remove(config_file)
                print(f"✅ {config_file} deleted")

    # ------------------------------------------------------------------
    # INVOKE ONLY (existing runtime)
    # ------------------------------------------------------------------
    else:
        print("\n=== Invoke-only mode ===")
        agentcore_runtime = Runtime()
        invoke_and_print(agentcore_runtime, "How is the weather now in Athens?")
        invoke_and_print(agentcore_runtime, "What is 5 + 7?")


if __name__ == "__main__":
    main()
