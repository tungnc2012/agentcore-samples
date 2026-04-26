# Dockerfile for AgentCore Customer Support Agent
# This containerizes the agent for deployment via Amazon ECR

FROM public.ecr.aws/docker/library/python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/CustomerSupport/ /app/

# Install Python dependencies
# Using pip instead of uv for simpler container builds
RUN pip install --no-cache-dir \
    aws-opentelemetry-distro \
    bedrock-agentcore>=1.0.3 \
    "botocore[crt]>=1.35.0" \
    mcp>=1.19.0 \
    strands-agents>=1.13.0

# Expose port 8080 (AgentCore Runtime default)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

# Run the agent
CMD ["python", "main.py"]
