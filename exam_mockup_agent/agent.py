"""AI Explanation Agent - Generate answer explanations using Strands Agents + Bedrock."""

from strands import Agent
from strands.models.bedrock import BedrockModel

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
    """Generate an AI explanation for a question using Strands Agent with Bedrock Claude.

    Args:
        question: The Question object to explain.
        selected_answers: The answers the user selected (e.g. ["A"] or ["A", "C"]).

    Returns:
        A string containing the AI-generated explanation.
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name="us-east-1",
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
    )

    prompt = _build_explanation_prompt(question, selected_answers)
    result = agent(prompt)
    return str(result)
