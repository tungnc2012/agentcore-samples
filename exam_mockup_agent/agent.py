"""AI Explanation Agent - Generate answer explanations using Amazon Bedrock."""

import json

import boto3

from exam_mockup_agent.models import Question


SYSTEM_PROMPT = """You are an expert certification exam tutor. Your role is to help candidates \
understand exam questions by providing clear, educational explanations.

When explaining an answer:
1. State which answer(s) are correct.
2. Explain WHY each correct answer is correct, referencing the relevant concept or best practice.
3. Explain WHY each incorrect option is wrong, noting common misconceptions.
4. Keep explanations concise but thorough - focus on helping the candidate learn the underlying concept.
5. Use a professional, encouraging tone appropriate for certification preparation.

Do not use unnecessary filler. Be direct and informative."""


def _build_explanation_prompt(question: Question, selected_answers: list[str]) -> str:
    """Build the user prompt for the explanation agent."""
    options_text = "\n".join(
        f"  {key}. {value}" for key, value in sorted(question.options.items())
    )

    correct_str = ", ".join(sorted(question.correct_answers))
    selected_str = ", ".join(sorted(selected_answers)) if selected_answers else "(none)"

    prompt = (
        f"Question: {question.text}\n\n"
        f"Options:\n{options_text}\n\n"
        f"Correct answer(s): {correct_str}\n"
        f"User selected: {selected_str}\n\n"
        f"Please explain why the correct answer(s) are correct and why each "
        f"incorrect option is wrong."
    )
    return prompt


def explain_answer(question: Question, selected_answers: list[str]) -> str:
    """Generate an AI explanation for a question using Amazon Bedrock Claude.

    Args:
        question: The Question object to explain.
        selected_answers: The answers the user selected (e.g. ["A"] or ["A", "C"]).

    Returns:
        A string containing the AI-generated explanation.
    """
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    prompt = _build_explanation_prompt(question, selected_answers)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    })

    response = client.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-20250514",
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
