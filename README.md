# Exam Mockup Agent

A cloud provider certification exam simulator powered by AI. Upload XLSX question files, practice in two modes (Practice and Timed), and get AI-powered explanations for answers.

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure AWS credentials for Bedrock access:

```bash
aws configure
```

## Running Locally

Start the Streamlit UI:

```bash
streamlit run exam_mockup_agent/app.py
```

## Running Tests

```bash
pytest tests/
```

## XLSX File Format

Your question file must include these columns:

| Column | Required | Description |
|--------|----------|-------------|
| Question | Yes | The question text |
| Option_A | Yes | First answer option |
| Option_B | Yes | Second answer option |
| Option_C | Yes | Third answer option |
| Option_D | Yes | Fourth answer option |
| Option_E | No | Fifth answer option |
| Option_F | No | Sixth answer option |
| Correct_Answer | Yes | Single letter or comma-separated letters (e.g., "A" or "A,C") |
| Question_Type | Yes | "single" or "multiple" |

## Modes

- **Practice Mode**: Answer all questions at your own pace with immediate feedback and AI explanations.
- **Timed Mode**: 60 randomly selected questions with a 120-minute countdown timer simulating real exam conditions.
