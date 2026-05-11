"""Data models for the Exam Mockup Agent."""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Question:
    """Represents a single exam question."""

    id: int
    text: str
    options: dict[str, str]  # {"A": "...", "B": "...", ...}
    correct_answers: list[str]  # ["A"] or ["A", "C"]
    question_type: str  # "single" or "multiple"


@dataclass
class QuestionResult:
    """Result for a single question in an exam session."""

    question_id: int
    selected_answers: list[str]
    correct_answers: list[str]
    is_correct: bool


@dataclass
class ExamResult:
    """Overall result for a completed exam session."""

    total_questions: int
    correct_count: int
    incorrect_count: int
    score_percentage: float
    passed: bool  # True if score_percentage >= 72.0
    question_results: list[QuestionResult] = field(default_factory=list)


@dataclass
class ExamSession:
    """Represents an active or completed exam session."""

    session_id: str
    mode: str  # "practice" or "timed"
    questions: list[Question]
    current_index: int
    answers: dict[int, list[str]]  # question_id -> selected answers
    start_time: Optional[str]  # ISO format string
    duration_minutes: int  # 120 for timed, 0 for practice
    is_completed: bool
    shuffled_options: dict[int, list[str]] = field(default_factory=dict)  # question_id -> shuffled key order

    def serialize(self) -> str:
        """Serialize session to JSON string."""
        data = {
            "session_id": self.session_id,
            "mode": self.mode,
            "questions": [
                {
                    "id": q.id,
                    "text": q.text,
                    "options": q.options,
                    "correct_answers": q.correct_answers,
                    "question_type": q.question_type,
                }
                for q in self.questions
            ],
            "current_index": self.current_index,
            "answers": {str(k): v for k, v in self.answers.items()},
            "start_time": self.start_time,
            "duration_minutes": self.duration_minutes,
            "is_completed": self.is_completed,
            "shuffled_options": {str(k): v for k, v in self.shuffled_options.items()},
        }
        return json.dumps(data)

    @classmethod
    def deserialize(cls, json_str: str) -> "ExamSession":
        """Deserialize JSON string to ExamSession."""
        data = json.loads(json_str)
        questions = [
            Question(
                id=q["id"],
                text=q["text"],
                options=q["options"],
                correct_answers=q["correct_answers"],
                question_type=q["question_type"],
            )
            for q in data["questions"]
        ]
        answers = {int(k): v for k, v in data["answers"].items()}
        shuffled_options = {int(k): v for k, v in data.get("shuffled_options", {}).items()}
        return cls(
            session_id=data["session_id"],
            mode=data["mode"],
            questions=questions,
            current_index=data["current_index"],
            answers=answers,
            start_time=data["start_time"],
            duration_minutes=data["duration_minutes"],
            is_completed=data["is_completed"],
            shuffled_options=shuffled_options,
        )
