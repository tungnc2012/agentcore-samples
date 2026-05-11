"""Scoring Engine - Calculate scores and generate result summaries."""

from exam_mockup_agent.models import ExamResult, ExamSession, QuestionResult

PASS_THRESHOLD = 72.0


def calculate_score(session: ExamSession) -> ExamResult:
    """Calculate the score for a completed exam session.

    A question is correct if and only if the selected answers exactly match
    the correct answers (order-independent set comparison).

    Args:
        session: A completed ExamSession with answers recorded.

    Returns:
        An ExamResult with score breakdown and pass/fail status.
    """
    question_results = []
    correct_count = 0

    for question in session.questions:
        selected = session.answers.get(question.id, [])
        is_correct = set(selected) == set(question.correct_answers)
        if is_correct:
            correct_count += 1
        question_results.append(
            QuestionResult(
                question_id=question.id,
                selected_answers=selected,
                correct_answers=question.correct_answers,
                is_correct=is_correct,
            )
        )

    total_questions = len(session.questions)
    score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
    passed = score_percentage >= PASS_THRESHOLD

    return ExamResult(
        total_questions=total_questions,
        correct_count=correct_count,
        incorrect_count=total_questions - correct_count,
        score_percentage=score_percentage,
        passed=passed,
        question_results=question_results,
    )
