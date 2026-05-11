"""AgentCore deployment entrypoint for the Exam Mockup Agent.

Wraps core agent logic with BedrockAgentCoreApp for deployment
to Amazon Bedrock AgentCore.
"""

import json
import tempfile
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from exam_mockup_agent.agent import explain_answer
from exam_mockup_agent.models import ExamSession, Question
from exam_mockup_agent.parser import parse_xlsx, ValidationError
from exam_mockup_agent.scorer import calculate_score
from exam_mockup_agent.session import (
    create_practice_session,
    create_timed_session,
    submit_answer,
    is_time_expired,
)

app = BedrockAgentCoreApp()


def _handle_upload(payload: dict) -> dict:
    """Handle XLSX file upload action.

    Expects payload:
        file_content_base64: str - Base64-encoded XLSX file content
        file_name: str - Original filename

    Returns:
        questions: list of serialized Question dicts
        count: number of questions parsed
    """
    import base64

    file_content = base64.b64decode(payload["file_content_base64"])
    file_name = payload.get("file_name", "upload.xlsx")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        questions = parse_xlsx(tmp_path)
        return {
            "status": "success",
            "questions": [
                {
                    "id": q.id,
                    "text": q.text,
                    "options": q.options,
                    "correct_answers": q.correct_answers,
                    "question_type": q.question_type,
                }
                for q in questions
            ],
            "count": len(questions),
        }
    except ValidationError as e:
        return {"status": "error", "message": str(e)}
    finally:
        os.unlink(tmp_path)


def _handle_start_session(payload: dict) -> dict:
    """Handle session creation action.

    Expects payload:
        mode: str - "practice" or "timed"
        questions: list of Question dicts
        count: int (optional) - number of questions for timed mode

    Returns:
        session_json: serialized ExamSession
    """
    questions = [
        Question(
            id=q["id"],
            text=q["text"],
            options=q["options"],
            correct_answers=q["correct_answers"],
            question_type=q["question_type"],
        )
        for q in payload["questions"]
    ]

    mode = payload.get("mode", "practice")
    if mode == "timed":
        count = payload.get("count", 60)
        session = create_timed_session(questions, count=count)
    else:
        session = create_practice_session(questions)

    return {"status": "success", "session": json.loads(session.serialize())}


def _handle_submit_answer(payload: dict) -> dict:
    """Handle answer submission action.

    Expects payload:
        session_json: str - serialized ExamSession JSON
        question_id: int - ID of the question being answered
        selected_answers: list[str] - selected option letters

    Returns:
        session: updated serialized session
        time_expired: bool - whether the session timer has expired
    """
    session = ExamSession.deserialize(payload["session_json"])
    question_id = payload["question_id"]
    selected_answers = payload["selected_answers"]

    submit_answer(session, question_id, selected_answers)

    time_expired = is_time_expired(session)
    if time_expired:
        session.is_completed = True

    return {
        "status": "success",
        "session": json.loads(session.serialize()),
        "time_expired": time_expired,
    }


def _handle_get_explanation(payload: dict) -> dict:
    """Handle AI explanation request action.

    Expects payload:
        question: dict - Question data
        selected_answers: list[str] - user's selected answers

    Returns:
        explanation: str - AI-generated explanation
    """
    question = Question(
        id=payload["question"]["id"],
        text=payload["question"]["text"],
        options=payload["question"]["options"],
        correct_answers=payload["question"]["correct_answers"],
        question_type=payload["question"]["question_type"],
    )
    selected_answers = payload.get("selected_answers", [])

    explanation = explain_answer(question, selected_answers)
    return {"status": "success", "explanation": explanation}


def _handle_get_results(payload: dict) -> dict:
    """Handle results calculation action.

    Expects payload:
        session_json: str - serialized ExamSession JSON

    Returns:
        results: dict with score breakdown and pass/fail status
    """
    session = ExamSession.deserialize(payload["session_json"])
    session.is_completed = True
    result = calculate_score(session)

    return {
        "status": "success",
        "results": {
            "total_questions": result.total_questions,
            "correct_count": result.correct_count,
            "incorrect_count": result.incorrect_count,
            "score_percentage": result.score_percentage,
            "passed": result.passed,
            "question_results": [
                {
                    "question_id": qr.question_id,
                    "selected_answers": qr.selected_answers,
                    "correct_answers": qr.correct_answers,
                    "is_correct": qr.is_correct,
                }
                for qr in result.question_results
            ],
        },
    }


ACTION_HANDLERS = {
    "upload": _handle_upload,
    "start_session": _handle_start_session,
    "submit_answer": _handle_submit_answer,
    "get_explanation": _handle_get_explanation,
    "get_results": _handle_get_results,
}


@app.entrypoint
def handler(payload: dict) -> dict:
    """Main AgentCore entrypoint. Routes actions to appropriate handlers.

    Expects payload:
        action: str - one of: upload, start_session, submit_answer, get_explanation, get_results
        ... additional fields depending on action

    Returns:
        dict with status and action-specific response data
    """
    action = payload.get("action")
    if not action:
        return {"status": "error", "message": "Missing 'action' field in payload"}

    handler_fn = ACTION_HANDLERS.get(action)
    if not handler_fn:
        return {
            "status": "error",
            "message": f"Unknown action: '{action}'. Valid actions: {list(ACTION_HANDLERS.keys())}",
        }

    try:
        return handler_fn(payload)
    except Exception as e:
        return {"status": "error", "message": f"Error processing '{action}': {str(e)}"}


if __name__ == "__main__":
    app.run()
