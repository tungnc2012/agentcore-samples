FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exam_mockup_agent/ ./exam_mockup_agent/
COPY templates/ ./templates/

EXPOSE 5000

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "exam_mockup_agent.flask_app:app"]
