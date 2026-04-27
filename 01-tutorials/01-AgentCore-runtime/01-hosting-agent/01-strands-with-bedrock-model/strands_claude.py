"""
Agent code for AgentCore Runtime deployment.
This file is written by the notebook's %%writefile cells and used as the entrypoint.
"""
from strands import Agent, tool
from strands_tools import calculator
import argparse
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore_starter_toolkit import Runtime
from strands.models import BedrockModel
from boto3.session import Session
boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "strands_claude_getting_started"
response = agentcore_runtime.configure(
    entrypoint="strands_claude.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)
response

app = BedrockAgentCoreApp()
@tool
def weather(city: str):
    """Get weather information.

    Args:
        city: City for which weather will be returned

    Returns:
        Weather of provided city as a string.
    """
    print(city)
    if city.lower() == "athens":
        return "very sunny"
    return "sunny"


model_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
model = BedrockModel(model_id=model_id)

agent = Agent(
    model=model,
    tools=[calculator, weather],
    system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather.",
)


@app.entrypoint
def strands_agent_bedrock(payload):
    """Invoke the agent with a payload."""
    user_input = payload.get("prompt")
    print("User input:", user_input)
    response = agent(user_input)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
