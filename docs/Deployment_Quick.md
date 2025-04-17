# Quick Deployment Guide

This guide provides quick instructions for deploying the jail roster scraper using the automated deployment script.

## Prerequisites

- A Linux server (Ubuntu 20.04 or higher recommended)
- Root or sudo access
- Domain name (optional, for HTTPS and proper subdomain configuration)

## Deployment Steps

1. Clone or download the repository to your server:

   ```bash
   git clone https://github.com/yourusername/jailscrape.git
   cd jailscrape
   ```

2. Edit the deployment script configuration variables:

   ```bash
   nano deploy.sh
   ```

   Set the following at minimum:
   - `SERVER_USER`: Your server username
   - `PROJECT_DIR`: Directory where the application will be installed
   - `RUN_AS_USER`: Service account to run the application
   - Email configuration (if you want alerts)

3. Make the script executable:

   ```bash
   chmod +x deploy.sh
   ```

4. Run the deployment script:

   ```bash
   sudo ./deploy.sh
   ```

5. Follow the prompts and review the output for any errors.

## What the Script Does

The deployment script automates:

- System package installation
- Python environment setup
- Playwright browser installation
- Configuration file creation
- Cron job setup
- Log rotation setup
- Systemd service configuration for the dashboard
- Nginx configuration
- SSL certificate setup (if enabled)
- Initial test run

## After Deployment

1. The script will display URLs and commands for monitoring the application.

2. Check that the dashboard is accessible at:
   - `http://your-server-ip` (without domain)
   - `http://dashboard.your-domain.com` (with domain, no HTTPS)
   - `https://dashboard.your-domain.com` (with domain, with HTTPS)

3. Verify the scraper is running correctly:

   ```bash
   tail -f /opt/jailscrape/scraper/logs/scraper_errors.log
   ```

4. Monitor cron runs:

   ```bash
   tail -f /opt/jailscrape/scraper/logs/cron.log
   ```

## Troubleshooting

If you encounter issues:

1. Check service status:

   ```bash
   systemctl status jailscrape-dashboard
   ```

2. Check Nginx configuration:

   ```bash
   nginx -t
   ```

3. Examine error logs:

   ```bash
   tail -f /var/log/nginx/jailscrape-dashboard-error.log
   tail -f /opt/jailscrape/scraper/logs/scraper_errors.log
   ```

4. Manually test the scraper:

   ```bash
   sudo -u jailscrape /opt/jailscrape/venv/bin/python /opt/jailscrape/scraper/main.py
   ```

## Customization

If you need to customize the deployment further, you can:

1. Modify the `.env` file for scraper settings:

   ```bash
   nano /opt/jailscrape/scraper/.env
   ```

2. Adjust the Nginx configuration:

   ```bash
   nano /etc/nginx/sites-available/jailscrape-dashboard
   ```

3. Modify the systemd service:

   ```bash
   nano /etc/systemd/system/jailscrape-dashboard.service
   systemctl daemon-reload
   ```

For more detailed instructions, refer to the complete [Deployment Guide](Deployment.md).
