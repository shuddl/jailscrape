#!/bin/bash
# Comprehensive deployment script for jail roster scraper system
# This script performs a full installation and configuration on a Linux server

# Exit on error
set -e

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

# Configuration variables - edit these before running
SERVER_USER="ubuntu"                # Server username
SERVER_IP=""                       # Leave empty for local deployment
PROJECT_DIR="/opt/jailscrape"      # Where to install the application
TIMEZONE="America/Chicago"         # Server timezone
NGINX_PORT="80"                    # Web server port for dashboard
DASHBOARD_PORT="8501"              # Streamlit internal port
DASHBOARD_SUBDOMAIN="dashboard"    # For nginx config (dashboard.yourdomain.com)
DOMAIN_NAME=""                     # Leave empty for IP-only access
RUN_AS_USER="jailscrape"           # Service account to run the scraper
SETUP_HTTPS="false"                # Whether to configure HTTPS with Let's Encrypt
CREATE_SERVICE_ACCOUNT="true"      # Whether to create a dedicated service account

# Email configuration - required for alerts
ENABLE_EMAIL_ALERTS="false"        # Set to true to enable email alerts
SMTP_HOST=""                       # SMTP server hostname
SMTP_PORT="587"                    # SMTP server port
SMTP_USER=""                       # SMTP username
SMTP_PASSWORD=""                   # SMTP password
ALERT_EMAIL_TO=""                  # Recipient email
ALERT_EMAIL_FROM=""                # Sender email

# Function to display section headers
section() {
    echo -e "\n${BOLD}${GREEN}==>${RESET} ${BOLD}$1${RESET}"
}

step() {
    echo -e "${YELLOW}-->${RESET} $1"
}

error() {
    echo -e "${RED}ERROR:${RESET} $1"
    exit 1
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Generate a random password
generate_password() {
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1
}

# Display script header
clear
echo -e "${BOLD}${GREEN}==================================================${RESET}"
echo -e "${BOLD}${GREEN}    Jail Roster Scraper Deployment Script        ${RESET}"
echo -e "${BOLD}${GREEN}==================================================${RESET}"
echo ""
echo -e "This script will deploy the jail roster scraper system."
echo -e "Make sure you've edited the configuration variables at the top of this script."
echo ""
echo -e "${YELLOW}Press ENTER to continue or Ctrl+C to cancel${RESET}"
read

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    error "This script must be run as root or with sudo privileges"
fi

# Validate configuration
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ] && [ -z "$RUN_AS_USER" ]; then
    error "RUN_AS_USER must be set if CREATE_SERVICE_ACCOUNT is true"
fi

if [ "$SETUP_HTTPS" = "true" ] && [ -z "$DOMAIN_NAME" ]; then
    error "DOMAIN_NAME must be set if SETUP_HTTPS is true"
fi

section "Updating system packages"
apt-get update
apt-get upgrade -y

section "Installing required system packages"
apt-get install -y python3 python3-venv python3-pip sqlite3 nginx cron logrotate git \
                   build-essential libffi-dev unzip curl wget sudo software-properties-common

# Install Node.js (required for Playwright)
step "Installing Node.js"
if ! command_exists node; then
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
    apt-get install -y nodejs
fi

# Set timezone
step "Setting timezone to $TIMEZONE"
timedatectl set-timezone "$TIMEZONE"

# Create service account if requested
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    section "Creating service account"
    if id "$RUN_AS_USER" &>/dev/null; then
        step "User $RUN_AS_USER already exists"
    else
        step "Creating user $RUN_AS_USER"
        useradd -m -s /bin/bash "$RUN_AS_USER"
        # Generate a random password
        USER_PASSWORD=$(generate_password)
        echo "$RUN_AS_USER:$USER_PASSWORD" | chpasswd
        step "Set password for $RUN_AS_USER (saved to credentials.txt)"
        echo "User: $RUN_AS_USER" > credentials.txt
        echo "Password: $USER_PASSWORD" >> credentials.txt
        chmod 600 credentials.txt
    fi
fi

# Create project directory
section "Setting up project directory"
if [ -d "$PROJECT_DIR" ]; then
    step "Project directory already exists"
else
    step "Creating project directory at $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
fi

# Set ownership
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    step "Setting ownership to $RUN_AS_USER"
    chown -R "$RUN_AS_USER:$RUN_AS_USER" "$PROJECT_DIR"
fi

# Clone or copy the repository
section "Installing application code"
if [ -d "$PROJECT_DIR/.git" ]; then
    step "Git repository already exists, pulling latest changes"
    cd "$PROJECT_DIR"
    git pull
else
    step "Copying application code to $PROJECT_DIR"
    # Clone our repository if using git
    if [ -d "$(pwd)/.git" ]; then
        git clone "$(pwd)" "$PROJECT_DIR"
    else
        # Otherwise, copy all files
        rsync -a --exclude "venv" --exclude "__pycache__" --exclude "*.pyc" "$(pwd)/" "$PROJECT_DIR/"
    fi
fi

# Create required directories
step "Creating data and log directories"
mkdir -p "$PROJECT_DIR/scraper/data"
mkdir -p "$PROJECT_DIR/scraper/logs"
mkdir -p "$PROJECT_DIR/scraper/debug_screenshots"

# Set proper permissions
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    chown -R "$RUN_AS_USER:$RUN_AS_USER" "$PROJECT_DIR"
    chmod -R 750 "$PROJECT_DIR"
fi

# Set up virtual environment
section "Setting up Python virtual environment"
cd "$PROJECT_DIR"

if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    sudo -u "$RUN_AS_USER" bash -c "python3 -m venv venv"
    sudo -u "$RUN_AS_USER" bash -c "source venv/bin/activate && pip install --upgrade pip"
    sudo -u "$RUN_AS_USER" bash -c "source venv/bin/activate && pip install -r scraper/requirements.txt"
    sudo -u "$RUN_AS_USER" bash -c "source venv/bin/activate && pip install -r dashboard/requirements.txt"
else
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r scraper/requirements.txt
    pip install -r dashboard/requirements.txt
    deactivate
fi

# Install Playwright browsers
section "Installing Playwright browsers"
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    sudo -u "$RUN_AS_USER" bash -c "source venv/bin/activate && playwright install chromium"
else
    source venv/bin/activate
    playwright install chromium
    deactivate
fi

# Create .env file
section "Creating configuration file"
ENV_FILE="$PROJECT_DIR/.env"

# Check if .env file already exists
if [ -f "$ENV_FILE" ]; then
    step "Configuration file already exists at $ENV_FILE"
    step "Backing up existing file to ${ENV_FILE}.bak"
    cp "$ENV_FILE" "${ENV_FILE}.bak"
else
    step "Creating new configuration file at $ENV_FILE"
fi

cat > "$ENV_FILE" << EOL
# Jail Roster Scraper Configuration
# Generated by deployment script on $(date)

# Target website
ROSTER_URL=https://jailroster.mctx.org

# File paths
STATE_DB=${PROJECT_DIR}/scraper/data/processed_inmates.db
OUTPUT_CSV=${PROJECT_DIR}/scraper/data/new_inmates.csv
ERROR_LOG=${PROJECT_DIR}/scraper/logs/scraper_errors.log

# Browser configuration
BROWSER_TIMEOUT=30000
BROWSER_HEADLESS=True

# Email alerts
ENABLE_EMAIL_ALERTS=${ENABLE_EMAIL_ALERTS}
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
ALERT_EMAIL_TO=${ALERT_EMAIL_TO}
ALERT_EMAIL_FROM=${ALERT_EMAIL_FROM}
EOL

# Set proper permissions for .env file
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    chown "$RUN_AS_USER:$RUN_AS_USER" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"

# Set up log rotation
section "Setting up log rotation"
LOGROTATE_CONFIG="/etc/logrotate.d/jailscrape"

cat > "$LOGROTATE_CONFIG" << EOL
${PROJECT_DIR}/scraper/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ${RUN_AS_USER:-root} ${RUN_AS_USER:-root}
}
EOL

chmod 644 "$LOGROTATE_CONFIG"

# Set up cron job
section "Setting up cron job"
CRON_FILE="/etc/cron.d/jailscrape"

cat > "$CRON_FILE" << EOL
# Jail Roster Scraper - Run hourly
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""

# Run hourly at minute 0
0 * * * * ${RUN_AS_USER:-root} cd ${PROJECT_DIR} && ${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/scraper/main.py >> ${PROJECT_DIR}/scraper/logs/cron.log 2>&1
EOL

chmod 644 "$CRON_FILE"

# Set up systemd service for the dashboard
section "Setting up systemd service for dashboard"
SERVICE_FILE="/etc/systemd/system/jailscrape-dashboard.service"

cat > "$SERVICE_FILE" << EOL
[Unit]
Description=Jail Roster Dashboard
After=network.target

[Service]
User=${RUN_AS_USER:-root}
WorkingDirectory=${PROJECT_DIR}/dashboard
ExecStart=${PROJECT_DIR}/venv/bin/streamlit run app.py --server.port=${DASHBOARD_PORT} --server.address=127.0.0.1
Restart=on-failure
RestartSec=5
StartLimitInterval=60s
StartLimitBurst=3
Environment="PATH=${PROJECT_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOL

chmod 644 "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable jailscrape-dashboard

# Configure Nginx
section "Configuring Nginx"
NGINX_CONF="/etc/nginx/sites-available/jailscrape-dashboard"

if [ -n "$DOMAIN_NAME" ]; then
    SERVER_NAME="${DASHBOARD_SUBDOMAIN}.${DOMAIN_NAME}"
else
    SERVER_NAME="_"
fi

cat > "$NGINX_CONF" << EOL
server {
    listen ${NGINX_PORT};
    server_name ${SERVER_NAME};

    access_log /var/log/nginx/jailscrape-dashboard-access.log;
    error_log /var/log/nginx/jailscrape-dashboard-error.log;

    location / {
        proxy_pass http://127.0.0.1:${DASHBOARD_PORT};
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOL

# Create symbolic link to enable the site
if [ -f "/etc/nginx/sites-enabled/jailscrape-dashboard" ]; then
    rm "/etc/nginx/sites-enabled/jailscrape-dashboard"
fi
ln -s "/etc/nginx/sites-available/jailscrape-dashboard" "/etc/nginx/sites-enabled/"

# Set up HTTPS if requested
if [ "$SETUP_HTTPS" = "true" ] && [ -n "$DOMAIN_NAME" ]; then
    section "Setting up HTTPS with Let's Encrypt"
    
    # Install certbot
    step "Installing Certbot"
    apt-get install -y certbot python3-certbot-nginx
    
    # Obtain certificate
    step "Obtaining SSL certificate for ${DASHBOARD_SUBDOMAIN}.${DOMAIN_NAME}"
    certbot --nginx -d "${DASHBOARD_SUBDOMAIN}.${DOMAIN_NAME}" --non-interactive --agree-tos -m "${ALERT_EMAIL_FROM:-admin@example.com}" --redirect
    
    # Set up auto-renewal
    step "Setting up certificate auto-renewal"
    systemctl enable certbot.timer
    systemctl start certbot.timer
fi

# Test nginx configuration
step "Testing Nginx configuration"
nginx -t

# Restart Nginx
step "Restarting Nginx"
systemctl restart nginx

# Start the dashboard service
section "Starting the dashboard service"
systemctl start jailscrape-dashboard

# Run an initial test
section "Running initial test"
if [ "$CREATE_SERVICE_ACCOUNT" = "true" ]; then
    step "Running test as $RUN_AS_USER"
    sudo -u "$RUN_AS_USER" bash -c "cd $PROJECT_DIR && source venv/bin/activate && python scraper/main.py --test-mode"
else
    step "Running test"
    cd "$PROJECT_DIR" && source venv/bin/activate && python scraper/main.py --test-mode
fi

# Final information
section "Deployment complete!"
echo -e "The jail roster scraper has been deployed successfully."
echo -e ""
echo -e "${BOLD}Dashboard URL:${RESET}"
if [ -n "$DOMAIN_NAME" ]; then
    if [ "$SETUP_HTTPS" = "true" ]; then
        echo -e "  https://${DASHBOARD_SUBDOMAIN}.${DOMAIN_NAME}"
    else
        echo -e "  http://${DASHBOARD_SUBDOMAIN}.${DOMAIN_NAME}"
    fi
else
    echo -e "  http://$(hostname -I | awk '{print $1}'):${NGINX_PORT}"
fi
echo -e ""
echo -e "${BOLD}Scraper Status:${RESET}"
echo -e "  The scraper is scheduled to run hourly via cron."
echo -e "  Logs are available at: ${PROJECT_DIR}/scraper/logs/"
echo -e ""
echo -e "${BOLD}Commands:${RESET}"
echo -e "  Check dashboard service status:  ${YELLOW}systemctl status jailscrape-dashboard${RESET}"
echo -e "  View scraper logs:               ${YELLOW}tail -f ${PROJECT_DIR}/scraper/logs/scraper_errors.log${RESET}"
echo -e "  View cron logs:                  ${YELLOW}tail -f ${PROJECT_DIR}/scraper/logs/cron.log${RESET}"
echo -e ""
echo -e "${BOLD}${GREEN}==================================================${RESET}"