# Exam Mockup Agent

A cloud provider certification exam simulator powered by AI. Upload XLSX question files, practice in two modes (Practice and Timed), and get AI-powered explanations for answers.

## Features

- 📝 **Two exam modes**: Practice (unlimited time, immediate feedback) and Timed (60 questions, 120 minutes)
- 🤖 **AI explanations**: Get detailed explanations for any question using Amazon Bedrock (Claude)
- 📊 **Question navigator**: Visual grid showing answered/unanswered/correct/incorrect questions
- 🔖 **Mark for review**: Flag questions to revisit later
- 📈 **Score tracking**: 72% pass threshold with detailed results breakdown
- 📁 **Flexible XLSX format**: Supports two different column formats (standard and Google Sheets)

## Architecture

| Module | Purpose |
|--------|---------|
| `flask_app.py` | Flask web server — main entry point for the UI |
| `agent.py` | Amazon Bedrock (Claude) integration for AI explanations |
| `parser.py` | XLSX file parser — supports two column formats |
| `session.py` | Exam session management (create, answer, timer) |
| `scorer.py` | Score calculation and pass/fail logic (72% threshold) |
| `models.py` | Data classes: `Question`, `ExamSession`, `ExamResult` |
| `writer.py` | XLSX writer for round-trip testing |
| `agentcore_app.py` | Headless API entrypoint for Bedrock AgentCore deployment |
| `templates/` | Jinja2 HTML templates rendered by Flask |

---

## Quick Start (Mac)

### Option 1: Use the start script (easiest)

```bash
./start.sh
```

This will:
- Create a virtual environment if it doesn't exist
- Install all dependencies
- Check AWS credentials
- Start the Flask app on http://localhost:5001

### Option 2: Manual setup

### 1. Clone and navigate to the project

```bash
cd /path/to/agentcore-samples
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure AWS credentials

The app needs access to Amazon Bedrock for AI explanations. Configure your AWS credentials:

```bash
aws configure
```

**Required IAM permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-20250514-v1:0"
    }
  ]
}
```

> **Note:** The AI explanation feature requires Bedrock access. The rest of the app (upload, practice, scoring) works without it.

### 5. Run the Flask app

```bash
python exam_mockup_agent/flask_app.py
```

The app will start on **http://localhost:5001**

Open your browser and navigate to:
```
http://localhost:5001
```

### Alternative: Run with Flask CLI

```bash
flask --app exam_mockup_agent.flask_app run --debug --port 5001
```

---

## Usage

### 1. Upload Questions

- Click **"Upload your exam questions (.xlsx file)"** on the home page
- Select an XLSX file with questions (see format below)
- The app will validate and parse the file

### 2. Select Mode

**Practice Mode:**
- All questions included
- No time limit
- Immediate feedback after each answer
- AI explanation button available after submitting each answer

**Timed Mode:**
- 60 randomly selected questions
- 120-minute countdown timer
- No immediate feedback (results shown at the end)
- AI explanations available in the review screen after finishing

### 3. Answer Questions

- Select your answer(s) and click **"Submit Answer"**
- In practice mode, you'll see if you're correct immediately
- Click **"✨ 🤖 Ask AI to explain"** to get a detailed explanation (practice mode only)
- Use the question navigator grid on the right to jump between questions
- Mark questions for review using the **"🔖 Mark for Review"** button

### 4. Review Results

- Click **"🏁 Finish"** when done
- View your score and pass/fail status (72% threshold)
- Click any question number to review it
- Get AI explanations for any question in the review screen

---

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
| `Correct answer` | Yes | Letter(s) + optional explanation separated by newline (e.g. `B\nExplanation...`) |
| `Question Number` | No | Row identifier |

---

## Running Tests

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=exam_mockup_agent --cov-report=html
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for Flask session encryption | `dev-secret-key-change-in-prod` |
| `AWS_DEFAULT_REGION` | AWS region for Bedrock calls | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials (if not using IAM role) | — |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials (if not using IAM role) | — |

> **Security:** Always set a strong `FLASK_SECRET_KEY` before exposing the app outside localhost.

---

## Troubleshooting

### Port 5000 already in use

On macOS, AirPlay Receiver uses port 5000 by default. The app now runs on port 5001 to avoid conflicts.

If you need to use port 5000:
1. Disable AirPlay Receiver: **System Settings → General → AirDrop & Handoff → toggle off "AirPlay Receiver"**
2. Change the port in `flask_app.py` (line 420): `app.run(debug=True, host="0.0.0.0", port=5000)`

### Bedrock model not found

If you see `ValidationException: The provided model identifier is invalid`:

1. Check available models in your region:
   ```bash
   aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'claude')]"
   ```

2. Verify you have access to the model:
   ```bash
   aws bedrock list-inference-profiles --region us-east-1
   ```

3. The app uses `us.anthropic.claude-sonnet-4-20250514-v1:0` — update `agent.py` if you need a different model

### AWS credentials not configured

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)
```

Or use environment variables:
```bash
export AWS_ACCESS_KEY_ID=your-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on deploying to:
- AWS ECS Fargate (Flask web UI)
- Amazon EC2 (quick single-instance)
- Amazon Bedrock AgentCore (headless API)

---

## License

See [LICENSE](LICENSE) for details.
