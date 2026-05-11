"""Streamlit UI - Web interface for all user interactions."""

import tempfile
import os

import streamlit as st

from exam_mockup_agent.parser import parse_xlsx, validate_xlsx_structure, ValidationError
from exam_mockup_agent.session import (
    create_practice_session,
    create_timed_session,
    submit_answer,
    is_time_expired,
)
from exam_mockup_agent.scorer import calculate_score
from exam_mockup_agent.agent import explain_answer


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "questions" not in st.session_state:
        st.session_state.questions = None
    if "exam_session" not in st.session_state:
        st.session_state.exam_session = None
    if "exam_result" not in st.session_state:
        st.session_state.exam_result = None
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}  # question_id -> {"submitted": bool, "correct": bool}
    if "explanations" not in st.session_state:
        st.session_state.explanations = {}  # question_id -> explanation text


def render_home_page():
    """Render the home page with file upload and mode selection."""
    st.title("📝 DevOps Prep")
    st.subheader("Cloud Certification Exam Simulator")

    uploaded_file = st.file_uploader(
        "Upload your exam questions (.xlsx file)",
        type=["xlsx"],
        help="Upload an XLSX file with columns: Question, Option_A-D (E,F optional), Correct_Answer, Question_Type",
    )

    if uploaded_file is not None:
        # Save to temp file for parsing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            # Validate structure first
            is_valid, missing_cols = validate_xlsx_structure(tmp_path)
            if not is_valid:
                st.error(
                    f"❌ Invalid XLSX file. Missing required columns: {', '.join(missing_cols)}"
                )
                os.unlink(tmp_path)
                return

            # Parse the file
            questions = parse_xlsx(tmp_path)
            os.unlink(tmp_path)

            if not questions:
                st.error("❌ No questions found in the uploaded file.")
                return

            st.session_state.questions = questions
            st.success(f"✅ Successfully loaded {len(questions)} questions.")

            # Mode selection
            st.markdown("---")
            st.subheader("Select Exam Mode")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 📖 Practice Mode")
                st.markdown("- All questions included")
                st.markdown("- No time limit")
                st.markdown("- Immediate feedback after each answer")
                if st.button("Start Practice", use_container_width=True, type="primary"):
                    session = create_practice_session(questions)
                    st.session_state.exam_session = session
                    st.session_state.exam_result = None
                    st.session_state.feedback = {}
                    st.session_state.explanations = {}
                    st.session_state.page = "practice"
                    st.rerun()

            with col2:
                st.markdown("### ⏱️ Timed Mode")
                question_count = min(60, len(questions))
                st.markdown(f"- {question_count} randomly selected questions")
                st.markdown("- 120-minute time limit")
                st.markdown("- Results shown after completion")
                if len(questions) < 60:
                    st.warning(
                        f"⚠️ Only {len(questions)} questions available (fewer than 60)."
                    )
                if st.button("Start Timed Exam", use_container_width=True, type="primary"):
                    session = create_timed_session(questions)
                    st.session_state.exam_session = session
                    st.session_state.exam_result = None
                    st.session_state.feedback = {}
                    st.session_state.explanations = {}
                    st.session_state.page = "timed"
                    st.rerun()

        except ValidationError as e:
            st.error(f"❌ {str(e)}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)



def _render_question_navigator(session):
    """Render the question navigator grid in the sidebar."""
    st.sidebar.markdown("### 📋 Question Navigator")
    total = len(session.questions)
    cols_per_row = 5

    for row_start in range(0, total, cols_per_row):
        cols = st.sidebar.columns(cols_per_row)
        for i, col in enumerate(cols):
            q_idx = row_start + i
            if q_idx >= total:
                break
            q = session.questions[q_idx]
            is_current = q_idx == session.current_index
            is_answered = q.id in session.answers

            if is_current:
                label = f"**{q_idx + 1}**"
                btn_type = "primary"
            elif is_answered:
                label = f"{q_idx + 1}"
                btn_type = "secondary"
            else:
                label = f"{q_idx + 1}"
                btn_type = "secondary"

            with col:
                if st.button(
                    label,
                    key=f"nav_{q_idx}",
                    use_container_width=True,
                    type=btn_type if is_current else "secondary",
                ):
                    session.current_index = q_idx
                    st.rerun()


def _render_question_card(session, show_feedback=True):
    """Render the current question with answer options.

    Returns the selected answers if user interacts, or None.
    """
    question = session.questions[session.current_index]
    shuffled_keys = session.shuffled_options.get(question.id, list(question.options.keys()))

    # Progress indicator
    st.markdown(
        f"**Question {session.current_index + 1} / {len(session.questions)}** "
        f"&nbsp;&nbsp; `{session.mode.upper()}`"
    )
    st.markdown("---")

    # Question text
    st.markdown(f"**{question.text}**")
    st.markdown("")

    # Check if already answered and feedback shown
    q_feedback = st.session_state.feedback.get(question.id)
    already_submitted = q_feedback is not None and q_feedback.get("submitted", False)

    # Build options in shuffled order
    option_labels = [f"{key}. {question.options[key]}" for key in shuffled_keys]

    selected = None

    if question.question_type == "single":
        # Radio buttons for single choice
        prev_answer = session.answers.get(question.id, [])
        default_idx = None
        if prev_answer:
            # Find index of previously selected key in shuffled order
            for idx, key in enumerate(shuffled_keys):
                if key == prev_answer[0]:
                    default_idx = idx
                    break

        choice = st.radio(
            "Select your answer:",
            options=option_labels,
            index=default_idx,
            key=f"radio_{question.id}_{session.current_index}",
            disabled=already_submitted,
        )
        if choice:
            selected_key = shuffled_keys[option_labels.index(choice)]
            selected = [selected_key]
    else:
        # Checkboxes for multiple choice
        st.markdown("*Select all that apply:*")
        prev_answer = session.answers.get(question.id, [])
        selected_keys = []
        for idx, key in enumerate(shuffled_keys):
            label = f"{key}. {question.options[key]}"
            default_val = key in prev_answer
            checked = st.checkbox(
                label,
                value=default_val,
                key=f"check_{question.id}_{key}_{session.current_index}",
                disabled=already_submitted,
            )
            if checked:
                selected_keys.append(key)
        selected = selected_keys if selected_keys else None

    return selected, already_submitted


def render_practice_page():
    """Render the practice mode exam page."""
    session = st.session_state.exam_session
    if session is None:
        st.session_state.page = "home"
        st.rerun()
        return

    # Sidebar navigator
    _render_question_navigator(session)

    # Home button in sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.session_state.exam_session = None
        st.rerun()

    # Main content
    selected, already_submitted = _render_question_card(session, show_feedback=True)
    question = session.questions[session.current_index]

    # Submit button
    if not already_submitted:
        if st.button("Submit Answer", type="primary"):
            if selected:
                submit_answer(session, question.id, selected)
                is_correct = set(selected) == set(question.correct_answers)
                st.session_state.feedback[question.id] = {
                    "submitted": True,
                    "correct": is_correct,
                }
                st.rerun()
            else:
                st.warning("Please select an answer before submitting.")

    # Show feedback if submitted
    if already_submitted:
        q_feedback = st.session_state.feedback[question.id]
        if q_feedback["correct"]:
            st.success("✅ Correct!")
        else:
            correct_str = ", ".join(
                f"{k}: {question.options[k]}" for k in sorted(question.correct_answers)
            )
            st.error(f"❌ Incorrect. Correct answer(s): {correct_str}")

        # Explain button
        if question.id not in st.session_state.explanations:
            if st.button("🤖 Explain Answer"):
                with st.spinner("Generating explanation..."):
                    try:
                        explanation = explain_answer(
                            question, session.answers.get(question.id, [])
                        )
                        st.session_state.explanations[question.id] = explanation
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate explanation: {e}")
        else:
            st.markdown("---")
            st.markdown("**AI Explanation:**")
            st.markdown(st.session_state.explanations[question.id])

    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if session.current_index > 0:
            if st.button("⬅️ Previous"):
                session.current_index -= 1
                st.rerun()

    with col3:
        if session.current_index < len(session.questions) - 1:
            if st.button("Next ➡️"):
                session.current_index += 1
                st.rerun()
        else:
            # Last question - show finish button
            answered_count = len(session.answers)
            total = len(session.questions)
            if st.button(f"🏁 Finish ({answered_count}/{total} answered)"):
                session.is_completed = True
                result = calculate_score(session)
                st.session_state.exam_result = result
                st.session_state.page = "results"
                st.rerun()



def _render_timer(session):
    """Render the countdown timer in the sidebar for timed mode."""
    from datetime import datetime, timezone

    if session.start_time is None:
        return False

    start = datetime.fromisoformat(session.start_time)
    now = datetime.now(timezone.utc)
    elapsed_seconds = (now - start).total_seconds()
    total_seconds = session.duration_minutes * 60
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    hours = int(remaining_seconds // 3600)
    minutes = int((remaining_seconds % 3600) // 60)
    seconds = int(remaining_seconds % 60)

    if remaining_seconds <= 0:
        st.sidebar.error("⏰ Time's up!")
        return True  # expired

    if remaining_seconds < 300:  # less than 5 minutes
        st.sidebar.warning(f"⏱️ **{hours:02d}:{minutes:02d}:{seconds:02d}**")
    else:
        st.sidebar.info(f"⏱️ **{hours:02d}:{minutes:02d}:{seconds:02d}**")

    return False


def render_timed_page():
    """Render the timed mode exam page."""
    session = st.session_state.exam_session
    if session is None:
        st.session_state.page = "home"
        st.rerun()
        return

    # Check timer expiry
    time_expired = _render_timer(session)

    if time_expired or is_time_expired(session):
        # Auto-submit
        session.is_completed = True
        result = calculate_score(session)
        st.session_state.exam_result = result
        st.session_state.page = "results"
        st.rerun()
        return

    # Sidebar navigator
    _render_question_navigator(session)

    # Submit exam button in sidebar
    st.sidebar.markdown("---")
    answered_count = len(session.answers)
    total = len(session.questions)
    st.sidebar.markdown(f"**Answered:** {answered_count} / {total}")

    if st.sidebar.button("📤 Submit Exam", type="primary"):
        session.is_completed = True
        result = calculate_score(session)
        st.session_state.exam_result = result
        st.session_state.page = "results"
        st.rerun()

    if st.sidebar.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.session_state.exam_session = None
        st.rerun()

    # Main content - question card (no immediate feedback in timed mode)
    question = session.questions[session.current_index]
    shuffled_keys = session.shuffled_options.get(question.id, list(question.options.keys()))

    # Progress indicator
    st.markdown(
        f"**Question {session.current_index + 1} / {len(session.questions)}** "
        f"&nbsp;&nbsp; `TIMED`"
    )
    st.markdown("---")
    st.markdown(f"**{question.text}**")
    st.markdown("")

    # Build options in shuffled order
    option_labels = [f"{key}. {question.options[key]}" for key in shuffled_keys]

    if question.question_type == "single":
        prev_answer = session.answers.get(question.id, [])
        default_idx = None
        if prev_answer:
            for idx, key in enumerate(shuffled_keys):
                if key == prev_answer[0]:
                    default_idx = idx
                    break

        choice = st.radio(
            "Select your answer:",
            options=option_labels,
            index=default_idx,
            key=f"timed_radio_{question.id}_{session.current_index}",
        )
        if choice:
            selected_key = shuffled_keys[option_labels.index(choice)]
            submit_answer(session, question.id, [selected_key])
    else:
        st.markdown("*Select all that apply:*")
        prev_answer = session.answers.get(question.id, [])
        selected_keys = []
        for key in shuffled_keys:
            label = f"{key}. {question.options[key]}"
            default_val = key in prev_answer
            checked = st.checkbox(
                label,
                value=default_val,
                key=f"timed_check_{question.id}_{key}_{session.current_index}",
            )
            if checked:
                selected_keys.append(key)
        if selected_keys:
            submit_answer(session, question.id, selected_keys)
        elif question.id in session.answers and not selected_keys:
            # User unchecked all - remove answer
            del session.answers[question.id]

    # Navigation buttons
    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if session.current_index > 0:
            if st.button("⬅️ Previous"):
                session.current_index -= 1
                st.rerun()

    with col2:
        if session.current_index < len(session.questions) - 1:
            if st.button("Next ➡️"):
                session.current_index += 1
                st.rerun()



def render_results_page():
    """Render the results page with pass/fail status and question breakdown."""
    result = st.session_state.exam_result
    session = st.session_state.exam_session

    if result is None or session is None:
        st.session_state.page = "home"
        st.rerun()
        return

    st.title("📊 Exam Results")

    # Pass/Fail banner
    if result.passed:
        st.success(f"## ✅ PASSED")
    else:
        st.error(f"## ❌ FAILED")

    # Score summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{result.correct_count}/{result.total_questions}")
    with col2:
        st.metric("Percentage", f"{result.score_percentage:.1f}%")
    with col3:
        st.metric("Pass Threshold", "72%")

    st.markdown("---")

    # Per-question breakdown
    st.subheader("Question Breakdown")

    # Question grid showing correct/incorrect
    cols_per_row = 10
    for row_start in range(0, result.total_questions, cols_per_row):
        cols = st.columns(cols_per_row)
        for i, col in enumerate(cols):
            q_idx = row_start + i
            if q_idx >= result.total_questions:
                break
            qr = result.question_results[q_idx]
            with col:
                icon = "🟢" if qr.is_correct else "🔴"
                if st.button(
                    f"{icon}{q_idx + 1}",
                    key=f"result_q_{q_idx}",
                    use_container_width=True,
                ):
                    st.session_state["review_question_idx"] = q_idx

    # Review selected question
    review_idx = st.session_state.get("review_question_idx")
    if review_idx is not None and review_idx < len(result.question_results):
        st.markdown("---")
        qr = result.question_results[review_idx]
        question = session.questions[review_idx]

        st.markdown(f"### Question {review_idx + 1}")
        st.markdown(f"**{question.text}**")

        # Show options with indicators
        for key in sorted(question.options.keys()):
            option_text = question.options[key]
            is_correct = key in question.correct_answers
            is_selected = key in qr.selected_answers

            if is_correct and is_selected:
                st.markdown(f"✅ **{key}. {option_text}** *(your answer - correct)*")
            elif is_correct and not is_selected:
                st.markdown(f"🟢 **{key}. {option_text}** *(correct answer)*")
            elif not is_correct and is_selected:
                st.markdown(f"❌ {key}. {option_text} *(your answer - incorrect)*")
            else:
                st.markdown(f"⬜ {key}. {option_text}")

        # Explain button for this question
        if question.id not in st.session_state.explanations:
            if st.button("🤖 Explain Answer", key=f"explain_result_{review_idx}"):
                with st.spinner("Generating explanation..."):
                    try:
                        explanation = explain_answer(question, qr.selected_answers)
                        st.session_state.explanations[question.id] = explanation
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate explanation: {e}")
        else:
            st.markdown("**AI Explanation:**")
            st.markdown(st.session_state.explanations[question.id])

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Back to Home"):
            st.session_state.page = "home"
            st.session_state.exam_session = None
            st.session_state.exam_result = None
            st.session_state.feedback = {}
            st.session_state.explanations = {}
            st.rerun()
    with col2:
        if st.button("🔄 Retry Exam"):
            st.session_state.page = "home"
            st.session_state.exam_session = None
            st.session_state.exam_result = None
            st.session_state.feedback = {}
            st.session_state.explanations = {}
            st.rerun()


def main():
    """Main entry point for the Streamlit app."""
    st.set_page_config(
        page_title="DevOps Prep - Exam Simulator",
        page_icon="📝",
        layout="wide",
    )

    init_session_state()

    # Route to the correct page
    page = st.session_state.page
    if page == "home":
        render_home_page()
    elif page == "practice":
        render_practice_page()
    elif page == "timed":
        render_timed_page()
    elif page == "results":
        render_results_page()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()
