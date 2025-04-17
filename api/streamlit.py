import sys
import os
from pathlib import Path
import subprocess

# Add the repository root to Python path
repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root))

def start_streamlit():
    dashboard_path = repo_root / "dashboard" / "app.py"
    cmd = [
        "streamlit", "run",
        str(dashboard_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.serverAddress", "localhost",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light"
    ]
    
    # Run the process
    return subprocess.Popen(
        cmd,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

# Start the streamlit server
process = start_streamlit()

# Read the output and print for debugging
for line in process.stdout:
    print(line, end="")

# For vercel serverless function
def handler(event, context):
    return {
        "statusCode": 200,
        "body": "Streamlit is running"
    }