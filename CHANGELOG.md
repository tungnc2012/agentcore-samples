# Changelog

## Recent Updates

### AI Explanation in Practice Mode (Latest)

**Added:**
- AI explanation button now appears in practice mode after submitting an answer
- New route `/explain-practice/<idx>` to handle AI explanations during practice sessions
- AI explanations persist as you navigate between questions (stored in session by question ID)
- Matches the same UI/UX as the review screen's AI explanation feature

**Changed:**
- `flask_app.py`: Added `explain_practice()` route and updated `exam()` route to pass `ai_explanation` to template
- `templates/exam.html`: Added AI explanation button and display panel (practice mode only)

### Model ID Fix

**Fixed:**
- Updated Bedrock model ID from `us.anthropic.claude-sonnet-4-20250514` to `us.anthropic.claude-sonnet-4-20250514-v1:0`
- This fixes the `ValidationException: The provided model identifier is invalid` error

### Port Configuration

**Changed:**
- Default port changed from 5000 to 5001 to avoid conflict with macOS AirPlay Receiver
- Updated in `flask_app.py` line 420

### Documentation Updates

**Added:**
- Comprehensive README with step-by-step setup instructions
- Quick start script (`start.sh`) for one-command setup
- Troubleshooting section for common issues
- Clear explanation of both XLSX formats supported
- IAM permissions example for Bedrock access
- Usage guide with screenshots descriptions

**Fixed:**
- Removed incorrect Streamlit references (app uses Flask, not Streamlit)
- Added missing `flask-session` dependency to `requirements.txt`

### Dependencies

**Added:**
- `flask-session>=0.8.0` (was missing, required by `flask_app.py`)

## Features

### Current Features
- ✅ Flask web UI with Jinja2 templates
- ✅ Two exam modes: Practice and Timed
- ✅ AI explanations via Amazon Bedrock (Claude Sonnet 4)
- ✅ Question navigator grid
- ✅ Mark for review functionality
- ✅ Score tracking with 72% pass threshold
- ✅ Support for two XLSX formats (standard and Google Sheets)
- ✅ Session persistence using Flask-Session
- ✅ Timer for timed mode with auto-submit on expiry
- ✅ Detailed results review screen

### Architecture
- `flask_app.py` - Main Flask web server
- `agent.py` - Bedrock AI integration
- `parser.py` - XLSX parser (supports 2 formats)
- `session.py` - Session management
- `scorer.py` - Score calculation
- `models.py` - Data models
- `writer.py` - XLSX writer
- `agentcore_app.py` - Headless API for AgentCore deployment
- `templates/` - Jinja2 HTML templates

## Migration Notes

### From Streamlit to Flask
The original `app.py` was a Streamlit application. The current production UI is Flask-based (`flask_app.py`). The Streamlit file still exists but is not actively used.

### Running the App
- **Old:** `streamlit run exam_mockup_agent/app.py`
- **New:** `python exam_mockup_agent/flask_app.py` or `./start.sh`
- **URL:** http://localhost:5001 (changed from 5000)
