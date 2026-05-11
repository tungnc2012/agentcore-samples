"""Tests for session management."""

import pytest
from datetime import datetime, timezone, timedelta

from exam_mockup_agent.models import ExamSession, Question
from exam_mockup_agent.session import (
    create_practice_session,
    create_timed_session,
    submit_answer,
    is_time_expired,
)


def _make_questions(n: int) -> list[Question]:
    """Helper to create n dummy questions."""
    return [
        Question(
            id=i,
            text=f"Question {i}",
            options={"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            correct_answers=["A"],
            question_type="single",
        )
        for i in range(1, n + 1)
    ]


class TestCreatePracticeSession:
    def test_includes_all_questions(self):
        questions = _make_questions(10)
        session = create_practice_session(questions)
        assert len(session.questions) == 10

    def test_duration_is_zero(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        assert session.duration_minutes == 0

    def test_mode_is_practice(self):
        questions = _make_questions(3)
        session = create_practice_session(questions)
        assert session.mode == "practice"

    def test_initial_state(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        assert session.current_index == 0
        assert session.answers == {}
        assert session.is_completed is False


class TestCreateTimedSession:
    def test_selects_60_from_large_bank(self):
        questions = _make_questions(100)
        session = create_timed_session(questions)
        assert len(session.questions) == 60

    def test_selects_all_when_fewer_than_60(self):
        questions = _make_questions(30)
        session = create_timed_session(questions)
        assert len(session.questions) == 30

    def test_duration_is_120(self):
        questions = _make_questions(10)
        session = create_timed_session(questions)
        assert session.duration_minutes == 120

    def test_mode_is_timed(self):
        questions = _make_questions(10)
        session = create_timed_session(questions)
        assert session.mode == "timed"

    def test_custom_count(self):
        questions = _make_questions(100)
        session = create_timed_session(questions, count=20)
        assert len(session.questions) == 20


class TestSubmitAnswer:
    def test_records_answer(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        submit_answer(session, 1, ["A"])
        assert session.answers[1] == ["A"]

    def test_records_multiple_answers(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        submit_answer(session, 2, ["A", "C"])
        assert session.answers[2] == ["A", "C"]

    def test_overwrites_previous_answer(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        submit_answer(session, 1, ["A"])
        submit_answer(session, 1, ["B"])
        assert session.answers[1] == ["B"]


class TestIsTimeExpired:
    def test_practice_never_expires(self):
        questions = _make_questions(5)
        session = create_practice_session(questions)
        assert is_time_expired(session) is False

    def test_timed_not_expired_when_fresh(self):
        questions = _make_questions(5)
        session = create_timed_session(questions)
        assert is_time_expired(session) is False

    def test_timed_expired_when_past_duration(self):
        questions = _make_questions(5)
        session = create_timed_session(questions)
        # Set start_time to 121 minutes ago
        past = datetime.now(timezone.utc) - timedelta(minutes=121)
        session.start_time = past.isoformat()
        assert is_time_expired(session) is True

    def test_timed_not_expired_within_duration(self):
        questions = _make_questions(5)
        session = create_timed_session(questions)
        # Set start_time to 60 minutes ago (within 120 min)
        past = datetime.now(timezone.utc) - timedelta(minutes=60)
        session.start_time = past.isoformat()
        assert is_time_expired(session) is False

    def test_no_start_time_returns_false(self):
        questions = _make_questions(5)
        session = create_timed_session(questions)
        session.start_time = None
        assert is_time_expired(session) is False
