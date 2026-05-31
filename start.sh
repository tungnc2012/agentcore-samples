#!/bin/bash
# Quick start script for Exam Mockup Agent

set -e

echo "🚀 Starting Exam Mockup Agent..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "⚠️  Warning: AWS credentials not configured."
    echo "   AI explanations will not work without Bedrock access."
    echo "   Run 'aws configure' to set up credentials."
    echo ""
fi

# Start the app
echo "✅ Starting Flask app on http://localhost:5001"
echo ""
python exam_mockup_agent/flask_app.py
