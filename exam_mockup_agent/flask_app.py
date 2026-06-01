"""Flask UI - Web interface for the Exam Mockup Agent."""

import os
import sys
import tempfile
import uuid
import json

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, session, flash

from exam_mockup_agent.parser import parse_xlsx, validate_xlsx_structure, ValidationError
from exam_mockup_agent.session import (
    create_practice_session,
    create_timed_session,
    submit_answer,
    is_time_expired,
)
from exam_mockup_agent.scorer import calculate_score
from exam_mockup_agent.models import ExamSession

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Use server-side filesystem sessions to avoid cookie size limits
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(tempfile.gettempdir(), "flask_sessions")
app.config["SESSION_PERMANENT"] = False

from flask_session import Session
Session(app)


def _get_exam_session() -> ExamSession | None:
    """Retrieve the exam session from Flask session storage."""
    data = session.get("exam_session")
    if data is None:
        return None
    return ExamSession.deserialize(data)


def _save_exam_session(exam_session: ExamSession):
    """Save the exam session to Flask session storage."""
    session["exam_session"] = exam_session.serialize()


@app.route("/", methods=["GET"])
def home():
    """Home page - upload XLSX and select mode."""
    return render_template("home.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Handle XLSX file upload."""
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("home"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("home"))

    if not file.filename.endswith(".xlsx"):
        flash("Please upload an .xlsx file.", "error")
        return redirect(url_for("home"))

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        is_valid, missing_cols = validate_xlsx_structure(tmp_path)
        if not is_valid:
            flash(f"Invalid XLSX. Missing columns: {', '.join(missing_cols)}", "error")
            os.unlink(tmp_path)
            return redirect(url_for("home"))

        questions = parse_xlsx(tmp_path)
        os.unlink(tmp_path)

        if not questions:
            flash("No questions found in the file.", "error")
            return redirect(url_for("home"))

        # Debug: Print first question to verify parsing
        if questions:
            print(f"DEBUG: First question parsed:")
            print(f"  ID: {questions[0].id}")
            print(f"  Text: {questions[0].text[:50]}...")
            print(f"  Options: {questions[0].options}")
            print(f"  Correct answers: {questions[0].correct_answers}")
            print(f"  Question type: {questions[0].question_type}")

        # Store questions in session
        session["questions"] = [
            {
                "id": q.id,
                "text": q.text,
                "options": q.options,
                "correct_answers": q.correct_answers,
                "question_type": q.question_type,
                "explanation": q.explanation,
            }
            for q in questions
        ]
        session["question_count"] = len(questions)

        flash(f"Successfully loaded {len(questions)} questions.", "success")
        return redirect(url_for("select_mode"))

    except ValidationError as e:
        flash(str(e), "error")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error processing file: {e}", "error")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return redirect(url_for("home"))


@app.route("/select-mode")
def select_mode():
    """Mode selection page."""
    count = session.get("question_count", 0)
    if count == 0:
        flash("Please upload a question file first.", "error")
        return redirect(url_for("home"))
    return render_template("select_mode.html", question_count=count)


@app.route("/start", methods=["POST"])
def start_exam():
    """Start an exam session."""
    from exam_mockup_agent.models import Question

    mode = request.form.get("mode", "practice")
    questions_json = session.get("questions")
    if not questions_json:
        flash("No questions loaded. Please upload a file.", "error")
        return redirect(url_for("home"))

    questions_data = questions_json if isinstance(questions_json, list) else json.loads(questions_json)
    questions = [
        Question(**q) for q in questions_data
    ]

    if mode == "timed":
        exam_session = create_timed_session(questions)
    else:
        exam_session = create_practice_session(questions)

    _save_exam_session(exam_session)
    session["feedback"] = {}
    session["marked_for_review"] = []
    session["mode"] = mode

    return redirect(url_for("exam", idx=0))


@app.route("/exam/<int:idx>")
def exam(idx: int):
    """Display a question."""
    exam_session = _get_exam_session()
    if exam_session is None:
        flash("No active session.", "error")
        return redirect(url_for("home"))

    # Check time expiry for timed mode
    if exam_session.mode == "timed" and is_time_expired(exam_session):
        return redirect(url_for("finish"))

    if idx < 0 or idx >= len(exam_session.questions):
        idx = 0

    exam_session.current_index = idx
    _save_exam_session(exam_session)

    question = exam_session.questions[idx]
    shuffled_keys = exam_session.shuffled_options.get(question.id, list(question.options.keys()))

    feedback = session.get("feedback", {})
    if isinstance(feedback, str):
        feedback = json.loads(feedback)
    q_feedback = feedback.get(str(question.id))

    return render_template(
        "exam.html",
        question=question,
        questions=exam_session.questions,
        idx=idx,
        total=len(exam_session.questions),
        shuffled_keys=shuffled_keys,
        mode=exam_session.mode,
        answers=exam_session.answers,
        feedback=q_feedback,
        all_feedback=feedback,
        all_answers=exam_session.answers,
        marked_for_review=session.get("marked_for_review", []),
        start_time=exam_session.start_time,
        duration_minutes=exam_session.duration_minutes,
        ai_explanation=session.get("ai_explanations", {}).get(str(question.id)),
    )


@app.route("/submit-answer", methods=["POST"])
def submit_answer_route():
    """Handle answer submission."""
    exam_session = _get_exam_session()
    if exam_session is None:
        return redirect(url_for("home"))

    idx = int(request.form.get("idx", 0))
    question = exam_session.questions[idx]

    # Get selected answers
    if question.question_type == "single":
        selected = request.form.getlist("answer")
    else:
        selected = request.form.getlist("answer")

    if not selected:
        flash("Please select an answer.", "warning")
        return redirect(url_for("exam", idx=idx))

    # Clean and normalize the selected answers
    selected = [s.strip().upper() for s in selected]

    submit_answer(exam_session, question.id, selected)
    _save_exam_session(exam_session)

    # Store feedback for practice mode
    if exam_session.mode == "practice":
        is_correct = set(selected) == set(question.correct_answers)
        
        # Debug logging
        print(f"DEBUG: Question ID: {question.id}")
        print(f"DEBUG: Selected: {selected}")
        print(f"DEBUG: Correct answers: {question.correct_answers}")
        print(f"DEBUG: Is correct: {is_correct}")
        print(f"DEBUG: Selected set: {set(selected)}")
        print(f"DEBUG: Correct set: {set(question.correct_answers)}")
        
        feedback = session.get("feedback", {})
        if isinstance(feedback, str):
            feedback = json.loads(feedback)
        feedback[str(question.id)] = {
            "correct": is_correct,
            "selected": selected,
            "correct_answers": question.correct_answers,
        }
        session["feedback"] = feedback

    return redirect(url_for("exam", idx=idx))


@app.route("/mark-review/<int:idx>", methods=["POST"])
def mark_review(idx: int):
    """Toggle mark-for-review on a question."""
    marked = session.get("marked_for_review", [])
    if idx in marked:
        marked.remove(idx)
    else:
        marked.append(idx)
    session["marked_for_review"] = marked
    return redirect(url_for("exam", idx=idx))


@app.route("/finish")
def finish():
    """Finish the exam and show results."""
    exam_session = _get_exam_session()
    if exam_session is None:
        return redirect(url_for("home"))

    exam_session.is_completed = True
    result = calculate_score(exam_session)
    _save_exam_session(exam_session)

    # Store result for the results page
    session["result"] = {
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
    }

    return redirect(url_for("results"))


@app.route("/results")
def results():
    """Display exam results."""
    result_json = session.get("result")
    exam_session = _get_exam_session()

    if result_json is None or exam_session is None:
        flash("No results available.", "error")
        return redirect(url_for("home"))

    result = result_json if isinstance(result_json, dict) else json.loads(result_json)

    return render_template(
        "results.html",
        result=result,
        questions=exam_session.questions,
    )


@app.route("/review/<int:idx>")
def review(idx: int):
    """Review a specific question from results."""
    result_json = session.get("result")
    exam_session = _get_exam_session()

    if result_json is None or exam_session is None:
        return redirect(url_for("home"))

    result = result_json if isinstance(result_json, dict) else json.loads(result_json)

    if idx < 0 or idx >= len(result["question_results"]):
        return redirect(url_for("results"))

    qr = result["question_results"][idx]
    question = exam_session.questions[idx]

    return render_template(
        "review.html",
        question=question,
        qr=qr,
        idx=idx,
        total=result["total_questions"],
        question_results=result["question_results"],
        ai_explanation=session.get("ai_explanations", {}).get(str(idx)),
    )


@app.route("/explain/<int:idx>", methods=["POST"])
def explain(idx: int):
    """Call Bedrock AI to explain a question."""
    exam_session = _get_exam_session()
    result_json = session.get("result")

    if exam_session is None or result_json is None:
        return redirect(url_for("home"))

    result = result_json if isinstance(result_json, dict) else json.loads(result_json)

    if idx < 0 or idx >= len(result["question_results"]):
        return redirect(url_for("results"))

    question = exam_session.questions[idx]
    qr = result["question_results"][idx]

    try:
        from exam_mockup_agent.agent import explain_answer as ai_explain
        explanation = ai_explain(question, qr["selected_answers"])
    except Exception as e:
        explanation = f"Error calling AI: {e}"

    # Store in session
    ai_explanations = session.get("ai_explanations", {})
    ai_explanations[str(idx)] = explanation
    session["ai_explanations"] = ai_explanations

    return redirect(url_for("review", idx=idx))


@app.route("/explain-practice/<int:idx>", methods=["POST"])
def explain_practice(idx: int):
    """Call Bedrock AI to explain a question during a practice session."""
    exam_session = _get_exam_session()
    if exam_session is None:
        return redirect(url_for("home"))

    if idx < 0 or idx >= len(exam_session.questions):
        return redirect(url_for("exam", idx=idx))

    question = exam_session.questions[idx]
    selected_answers = exam_session.answers.get(question.id, [])

    try:
        from exam_mockup_agent.agent import explain_answer as ai_explain
        explanation = ai_explain(question, selected_answers)
    except Exception as e:
        explanation = f"Error calling AI: {e}"

    # Store in session keyed by question id
    ai_explanations = session.get("ai_explanations", {})
    ai_explanations[str(question.id)] = explanation
    session["ai_explanations"] = ai_explanations

    return redirect(url_for("exam", idx=idx))


@app.route("/reset")
def reset():
    """Reset session and go home."""
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
