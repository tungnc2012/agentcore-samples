FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exam_mockup_agent/ ./exam_mockup_agent/

EXPOSE 8080

ENTRYPOINT ["python", "-m", "exam_mockup_agent.agentcore_app"]
