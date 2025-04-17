# Jail Roster Scraper

A Python-based scraper for extracting, processing, and monitoring inmate data from public jail roster websites. The system automatically tracks new and released inmates, notifies about changes, and provides a visual dashboard for data analysis.

## Features

- **Automated Data Collection**: Extract inmate data from jail roster websites
- **Incremental Updates**: Only process new inmates, track when existing inmates are released
- **Resilient Operation**: Robust error handling, retry mechanisms, and screenshot-on-failure
- **Data Management**: Structured data storage in SQLite and CSV formats
- **Dashboard**: Visual interface for monitoring and analyzing data
- **Alerting**: Email notifications for new inmates, releases, and errors
- **Scheduled Execution**: Designed for unattended operation via cron

## Project Structure

```
jailscrape/
├── scraper/              # Core scraper components
│   ├── main.py           # Main entry point
│   ├── scraper.py        # Playwright implementation
│   ├── database.py       # SQLite database interactions
│   ├── processor.py      # Data cleaning and CSV output
│   ├── config.py         # Configuration loading
│   ├── alerter.py        # Email alerting functionality
│   ├── data/             # Directory for DB and output
│   ├── debug_screenshots/# Error diagnostics
│   └── logs/             # Log files
├── dashboard/            # Streamlit data dashboard
│   ├── app.py            # Dashboard application
│   └── requirements.txt  # Dashboard dependencies
├── docs/                 # Documentation
│   ├── Deployment.md     # Deployment instructions
│   ├── Testing.md        # Testing procedures
│   ├── LiveTestingPlan.md# Detailed validation steps
│   └── setup_cron.sh     # Cron setup script
├── deploy.sh             # Automated deployment script
├── .env.example          # Configuration template
└── README.md
```

## Quick Start

### Local Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/jailscrape.git
   cd jailscrape
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install requirements:

   ```bash
   pip install -r scraper/requirements.txt
   ```

4. Install Playwright browsers:

   ```bash
   playwright install
   ```

5. Copy `.env.example` to `.env` and configure settings:

   ```bash
   cp scraper/.env.example .env
   # Edit .env with appropriate values
   ```

### Server Deployment

For production deployment on a server, use the automated script:

1. Edit deployment configuration:

   ```bash
   nano deploy.sh  # Set SERVER_USER, PROJECT_DIR, etc.
   ```

2. Run the deployment script:

   ```bash
   sudo ./deploy.sh
   ```

For details, see the [Quick Deployment Guide](docs/Deployment_Quick.md).

### Streamlit Cloud Deployment

For a quick demo version without the scraper functionality:

1. Fork or push this repository to your GitHub account

2. Sign up for a free Streamlit Cloud account at https://streamlit.io/cloud

3. From the Streamlit Cloud dashboard, click "New app"

4. Connect your GitHub account and select this repository

5. In the deployment settings:
   - Set the Main file path to: `streamlit_app.py`
   - You can leave other settings as default

6. Click "Deploy" and wait for the build process to complete

7. Your dashboard will be available at a URL like: `https://your-app-name.streamlit.app`

Note: The Streamlit Cloud deployment will automatically generate demo data for demonstration purposes, as the actual scraper functionality requires a server environment.

## Usage

### Manual Execution

Run the scraper manually:

```bash
python scraper/main.py
```

### Dashboard

To use the data visualization dashboard:

1. Install dashboard requirements:

   ```bash
   pip install -r dashboard/requirements.txt
   ```

2. Run the dashboard:

   ```bash
   cd dashboard
   streamlit run app.py
   ```

3. Access the dashboard in your web browser at <http://localhost:8501>

## Configuration

The scraper uses environment variables for configuration, which can be set in a `.env` file:

### Required Configuration

- `ROSTER_URL`: URL of the jail roster website
- `OUTPUT_CSV`: Path to save extracted data
- `STATE_DB`: SQLite database for tracking processed data
- `ERROR_LOG`: Location for error logs
- `BROWSER_TIMEOUT`: Playwright timeout in milliseconds (e.g., 30000 for 30 seconds)

### Optional Configuration

- `BROWSER_HEADLESS`: Set to "False" to see the browser during scraping (default: "True")
- `OUTPUT_CSV_DIR`: Directory for CSV output (defaults to data/)

### Email Alerting (Optional)

- `ENABLE_EMAIL_ALERTS`: Set to "True" to enable email alerts
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port (typically 587 for TLS)
- `SMTP_USER`: Username for SMTP authentication
- `SMTP_PASSWORD`: Password for SMTP authentication
- `ALERT_EMAIL_TO`: Recipient email address
- `ALERT_EMAIL_FROM`: Sender email address

## Output

### Database

The system maintains a SQLite database (`STATE_DB` path) to:

- Track previously processed inmates
- Record when inmates were first and last seen
- Detect when inmates are released from custody

### CSV Files

New inmate records are appended to a CSV file (specified by `OUTPUT_CSV`):

- New records are appended to existing files
- Headers are written only when creating a new file
- Data includes both basic info and detailed fields from inmate pages
- Charges are flattened with column prefixes (e.g., `charge1_description`)

## Documentation

For detailed documentation, see:

- [Deployment Guide](docs/Deployment.md) - Full deployment instructions
- [Quick Deployment Guide](docs/Deployment_Quick.md) - Fast server deployment
- [Testing Guide](docs/Testing.md) - Testing procedures
- [Live Testing Plan](docs/LiveTestingPlan.md) - Comprehensive validation

## Customization

The scraper is designed to work with the Montgomery County Jail Roster website by default, but can be adapted to other jail roster systems by:

1. Modifying CSS selectors in `scraper.py` to match the target website
2. Adjusting field extraction in `scrape_inmate_details()` function
3. Updating data processing in `processor.py` if needed

## Troubleshooting

If errors occur:

1. Check the error log file specified in your `.env`
2. Look for debug screenshots in `scraper/debug_screenshots/`
3. Try running with `BROWSER_HEADLESS=False` to observe the browser
4. Verify the website structure hasn't changed

## License

[MIT License](LICENSE)
