# Deployment Guide for Jail Roster Scraper

This document provides comprehensive instructions for deploying the jail roster scraper in a production environment.

## Environment Setup

1. Set up a Linux server or VM with:
   - Python 3.9 or higher
   - cron
   - Git (optional, for version control)

2. Clone or copy the repository:
   ```bash
   git clone https://github.com/yourusername/jailscrape.git
   # or extract from ZIP archive
   ```

3. Create and activate a virtual environment:
   ```bash
   cd jailscrape
   python -m venv venv
   source venv/bin/activate
   ```

4. Install required dependencies:
   ```bash
   pip install -r scraper/requirements.txt
   ```

5. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

6. Create and configure the `.env` file:
   ```bash
   cp scraper/.env.example .env
   # Edit .env with appropriate settings
   ```

## Configuration

Edit the `.env` file to set:

- `ROSTER_URL`: URL of the jail roster website
- `STATE_DB`: Path to SQLite database (absolute path recommended in production)
- `OUTPUT_CSV`: Path to output CSV file
- `ERROR_LOG`: Path to error log file

If using email alerts:
- `ENABLE_EMAIL_ALERTS=True`
- Configure SMTP settings (`SMTP_HOST`, `SMTP_PORT`, etc.)

## Cron Setup

1. Use the provided setup script:
   ```bash
   bash docs/setup_cron.sh
   ```

2. Or manually add a cron job:
   ```bash
   crontab -e
   ```
   
   Add the following line:
   ```
   0 * * * * cd /full/path/to/jailscrape && /full/path/to/jailscrape/venv/bin/python /full/path/to/jailscrape/scraper/main.py >> /full/path/to/jailscrape/logs/cron.log 2>&1
   ```

3. Verify the cron job is set up:
   ```bash
   crontab -l
   ```

## Dashboard Setup (Optional)

If using the Streamlit dashboard:

1. Install dashboard requirements:
   ```bash
   pip install -r dashboard/requirements.txt
   ```

2. For temporary use, run directly:
   ```bash
   cd dashboard
   streamlit run app.py
   ```

3. For persistent deployment, create a systemd service:
   ```bash
   sudo nano /etc/systemd/system/jailscrape-dashboard.service
   ```
   
   Add the following content:
   ```
   [Unit]
   Description=Jail Roster Dashboard
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/full/path/to/jailscrape/dashboard
   ExecStart=/full/path/to/jailscrape/venv/bin/streamlit run app.py --server.port=8501
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

4. Start and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start jailscrape-dashboard
   sudo systemctl enable jailscrape-dashboard
   ```

5. Access the dashboard at `http://server-ip:8501`

## Maintenance

### Log Rotation

Set up log rotation to prevent logs from growing too large:

```bash
sudo nano /etc/logrotate.d/jailscrape
```

Add:
```
/path/to/jailscrape/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    notifempty
    create 0640 user group
}
```

### Database Management

The SQLite database will grow over time. Consider:

1. Regular backups:
   ```bash
   sqlite3 data/processed_inmates.db .dump > backups/processed_inmates_$(date +%Y%m%d).sql
   ```

2. Periodic archiving of old records:
   ```bash
   sqlite3 data/processed_inmates.db "DELETE FROM processed_inmates WHERE date_released IS NOT NULL AND date_released < date('now', '-6 months')"
   ```

### CSV File Management

For CSV output, consider:

1. Automatic archiving:
   ```bash
   # Add to crontab, run monthly
   0 0 1 * * cd /path/to/jailscrape && mv data/new_inmates.csv data/archive/new_inmates_$(date +%Y%m).csv
   ```

2. Or implement a log rotation policy similar to the logs

## Troubleshooting

Common issues and their solutions:

1. **Browser Automation Issues**:
   - Check if the correct version of Playwright browsers is installed
   - Review debug screenshots in `scraper/debug_screenshots/`
   - Try running with `BROWSER_HEADLESS=False` to observe browser behavior

2. **Database Lock Errors**:
   - Check for concurrent processes using `ps aux | grep python`
   - Ensure cron jobs don't overlap

3. **Email Alert Issues**:
   - Verify SMTP settings in `.env`
   - Check if the SMTP server requires additional security settings

## Security Considerations

1. **Credential Security**:
   - Store the `.env` file with restricted permissions: `chmod 600 .env`
   - Consider using a secret management system for production

2. **Server Hardening**:
   - Run the scraper as a non-privileged user
   - Set appropriate file permissions

3. **Data Privacy**:
   - Ensure output files have appropriate permissions
   - Consider encryption for sensitive data
   - Follow relevant data handling regulations