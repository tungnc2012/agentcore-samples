# Exam Mockup Agent

A cloud provider certification exam simulator powered by AI. Upload XLSX question files, practice in two modes (Practice and Timed), and get AI-powered explanations for answers.

## Architecture

| Module | Purpose |
|--------|---------|
| `flask_app.py` | Flask web server — main entry point for the UI |
| `agent.py` | Amazon Bedrock (Claude) integration for AI explanations |
| `parser.py` | XLSX file parser — supports two column formats |
| `session.py` | Exam session management (create, answer, timer) |
| `scorer.py` | Score calculation and pass/fail logic (72% threshold) |
| `models.py` | Data classes: `Question`, `ExamSession`, `ExamResult` |
| `agentcore_app.py` | Headless API entrypoint for Bedrock AgentCore deployment |
| `templates/` | Jinja2 HTML templates rendered by Flask |

## Local Setup (Mac)

### Prerequisites

- Python 3.11+
- AWS credentials configured with access to Amazon Bedrock (Claude)

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS credentials for Bedrock access

```bash
aws configure
```

Make sure your IAM user or role has permission to call `bedrock:InvokeModel` for
`us.anthropic.claude-sonnet-4-20250514` in `us-east-1`. The AI explanation feature
requires this — the rest of the app works without it.

### 4. Run the Flask app

```bash
python exam_mockup_agent/flask_app.py
```

Then open your browser at [http://localhost:5000](http://localhost:5000).

Alternatively, run with Flask's CLI:

```bash
flask --app exam_mockup_agent.flask_app run --debug
```

## Running Tests

```bash
pytest tests/
```

## XLSX File Format

The app supports two column formats.

### Format 1 — Standard

| Column | Required | Description |
|--------|----------|-------------|
| `Question` | Yes | The question text |
| `Option_A` | Yes | First answer option |
| `Option_B` | Yes | Second answer option |
| `Option_C` | Yes | Third answer option |
| `Option_D` | Yes | Fourth answer option |
| `Option_E` | No | Fifth answer option |
| `Option_F` | No | Sixth answer option |
| `Correct_Answer` | Yes | Single letter or comma-separated (e.g. `A` or `A,C`) |
| `Question_Type` | Yes | `single` or `multiple` |

### Format 2 — Alternative (Google Sheets / AI-generated)

| Column | Required | Description |
|--------|----------|-------------|
| `Question Text` | Yes | The question text |
| `Option A` | Yes | First answer option |
| `Option B` | Yes | Second answer option |
| `Option C` | Yes | Third answer option |
| `Option D` | Yes | Fourth answer option |
| `Option E` | No | Fifth answer option |
| `Option F` | No | Sixth answer option |
| `Correct answer` | Yes | Letter(s) + optional explanation separated by a newline (e.g. `B\nExplanation...`) |
| `Question Number` | No | Row identifier |

## Exam Modes

- **Practice Mode** — all questions, no time limit, immediate feedback and AI explanation after each answer.
- **Timed Mode** — 60 randomly selected questions, 120-minute countdown, results shown after submission or time expiry.

Pass threshold is **72%**.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for Flask session encryption | `dev-secret-key-change-in-prod` |
| `AWS_DEFAULT_REGION` | AWS region for Bedrock calls | `us-east-1` |

> Always set a strong `FLASK_SECRET_KEY` before exposing the app outside localhost.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on deploying to:
- AWS ECS Fargate (Flask web UI)
- Amazon EC2 (quick single-instance)
- Amazon Bedrock AgentCore (headless API)
