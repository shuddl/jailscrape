#!/bin/bash
# setup_cron.sh - Script to setup cron job for the jail roster scraper

# Stop on errors
set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
SCRIPT_PATH="${PROJECT_DIR}/scraper/main.py"
LOG_PATH="${PROJECT_DIR}/logs/cron.log"
CRON_SCHEDULE="0 * * * *"  # Run hourly at minute 0

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_PATH")"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please create it first with: python -m venv $VENV_DIR"
    exit 1
fi

# Get the Python executable from the virtual environment
PYTHON_PATH="$VENV_DIR/bin/python"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    exit 1
fi

# Check if main script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Main script not found at $SCRIPT_PATH"
    exit 1
fi

# Create the cron job line
CRON_CMD="$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$SCRIPT_PATH" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo "A cron job for the jail roster scraper already exists:"
    echo "$EXISTING_CRON"
    echo "Do you want to replace it? (y/n)"
    read -r REPLACE
    if [ "$REPLACE" != "y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
    # Remove existing cron job
    (crontab -l 2>/dev/null | grep -v -F "$SCRIPT_PATH") | crontab -
fi

# Add the new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job set up successfully!"
echo "The jail roster scraper will run $CRON_SCHEDULE"
echo "Command: $CRON_CMD"
echo "Logs will be written to: $LOG_PATH"
echo ""
echo "You can verify the cron job with: crontab -l"