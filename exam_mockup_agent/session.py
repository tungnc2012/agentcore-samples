"""Session Manager - Manage exam session state, progress, answers, and timing."""

import random
import uuid
from datetime import datetime, timezone

from exam_mockup_agent.models import ExamSession, Question


def shuffle_options(question: Question) -> list[str]:
    """Return the option keys in their natural order (A, B, C, D, E, F).
    
    Shuffling is disabled to maintain consistent answer order.

    Args:
        question: The question whose option keys to return.

    Returns:
        A sorted list of option keys (e.g. ["A", "B", "C", "D"]).
    """
    keys = list(question.options.keys())
    return sorted(keys)  # Always return in alphabetical order


def _generate_shuffled_options(questions: list[Question]) -> dict[int, list[str]]:
    """Generate shuffled option orders for all questions.

    Args:
        questions: List of questions to generate shuffled orders for.

    Returns:
        Dict mapping question_id to shuffled key order.
    """
    return {q.id: shuffle_options(q) for q in questions}


def create_practice_session(questions: list[Question]) -> ExamSession:
    """Create a practice session that includes all questions with no time limit.

    Args:
        questions: The full question bank to practice with.

    Returns:
        An ExamSession in practice mode with duration=0.
    """
    question_list = list(questions)
    return ExamSession(
        session_id=str(uuid.uuid4()),
        mode="practice",
        questions=question_list,
        current_index=0,
        answers={},
        start_time=datetime.now(timezone.utc).isoformat(),
        duration_minutes=0,
        is_completed=False,
        shuffled_options=_generate_shuffled_options(question_list),
    )


def create_timed_session(questions: list[Question], count: int = 60) -> ExamSession:
    """Create a timed session with randomly selected questions and 120-minute duration.

    Selects min(count, len(questions)) questions randomly from the bank.

    Args:
        questions: The full question bank to select from.
        count: Maximum number of questions to select (default 60).

    Returns:
        An ExamSession in timed mode with duration=120.
    """
    selected_count = min(count, len(questions))
    selected_questions = random.sample(questions, selected_count)
    return ExamSession(
        session_id=str(uuid.uuid4()),
        mode="timed",
        questions=selected_questions,
        current_index=0,
        answers={},
        start_time=datetime.now(timezone.utc).isoformat(),
        duration_minutes=120,
        is_completed=False,
        shuffled_options=_generate_shuffled_options(selected_questions),
    )


def submit_answer(session: ExamSession, question_id: int, selected_answers: list[str]) -> None:
    """Record a user's answer for a given question.

    Args:
        session: The active exam session.
        question_id: The ID of the question being answered.
        selected_answers: The list of selected option letters (e.g. ["A"] or ["A", "C"]).
    """
    session.answers[question_id] = selected_answers


def is_time_expired(session: ExamSession) -> bool:
    """Check if a timed session has exceeded its duration.

    Practice sessions (duration_minutes=0) never expire.

    Args:
        session: The exam session to check.

    Returns:
        True if the session's elapsed time exceeds duration_minutes, False otherwise.
    """
    if session.duration_minutes == 0:
        return False
    if session.start_time is None:
        return False
    start = datetime.fromisoformat(session.start_time)
    now = datetime.now(timezone.utc)
    elapsed_minutes = (now - start).total_seconds() / 60
    return elapsed_minutes > session.duration_minutes
