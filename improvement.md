# UI Improvement Notes

## Pending Improvements

### 1. Question Navigator Position
- Move the Question Navigator from the top of the page to the **left-hand sidebar**
- Currently rendered inline above the question content
- Should use Streamlit's `st.sidebar` to place the navigator on the left

### 2. Question Text Size
- Increase the font size of the question text for better readability
- Currently rendered with default markdown bold (`**text**`)
- Should use a larger heading style (e.g., `###` or custom CSS via `st.markdown` with `<style>`)

---

## Spec

### Requirements
- The Question Navigator must appear in the left-hand sidebar in both Practice and Timed modes
- Question text must be visually larger and easier to read than the current default bold markdown
- Changes must not break existing functionality (answer submission, navigation, feedback display)

### Design
- **Question Navigator**: Already uses `st.sidebar` in `_render_question_navigator()`. Verify it renders correctly on the left and is not duplicated elsewhere in the main content area.
- **Question Text Size**: Inject a custom CSS block via `st.markdown` with `unsafe_allow_html=True` to increase the font size of question text. Target a wrapper class or use an HTML `<div>` with inline style around the question text.

### Tasks
- [ ] Audit `_render_question_card()` and `render_timed_page()` to confirm the navigator is only rendered via `st.sidebar`
- [ ] Add a `st.markdown` CSS injection in `main()` to increase question text font size (target: ~20px or `1.3rem`)
- [ ] Test both Practice and Timed modes to confirm layout and readability improvements
- [ ] Update this file to mark tasks complete
