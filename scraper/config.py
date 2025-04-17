import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Determine project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")

# Configuration variables with defaults
ROSTER_URL = os.getenv("ROSTER_URL", "https://jailroster.mctx.org")

# Ensure all path configurations are absolute
OUTPUT_CSV = Path(os.getenv("OUTPUT_CSV", "data/new_inmates.csv"))
if not OUTPUT_CSV.is_absolute():
    OUTPUT_CSV = PROJECT_ROOT / OUTPUT_CSV

STATE_DB = Path(os.getenv("STATE_DB", "data/processed_inmates.db"))
if not STATE_DB.is_absolute():
    STATE_DB = PROJECT_ROOT / STATE_DB

ERROR_LOG = Path(os.getenv("ERROR_LOG", "logs/scraper_errors.log"))
if not ERROR_LOG.is_absolute():
    ERROR_LOG = PROJECT_ROOT / ERROR_LOG

# Ensure parent directories exist
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
STATE_DB.parent.mkdir(parents=True, exist_ok=True)
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

# Browser configuration
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", 30000))

# Email alert configuration
ENABLE_EMAIL_ALERTS = os.getenv("ENABLE_EMAIL_ALERTS", "False").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")