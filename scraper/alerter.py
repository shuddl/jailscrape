import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Import local configuration
import config

# Get logger
logger = logging.getLogger(__name__)

def send_email_alert(subject: str, body: str, recipients=None, html=True):
    """
    Send an email alert about the scraper status
    
    Args:
        subject: Email subject line
        body: Email body content
        recipients: Optional list of recipient email addresses (defaults to config.ALERT_EMAIL_TO)
        html: Whether to send as HTML (True) or plain text (False)
    
    Returns:
        bool: Success status of the email sending operation
    """
    if not hasattr(config, "ENABLE_EMAIL_ALERTS") or not config.ENABLE_EMAIL_ALERTS:
        logger.info("Email alerts disabled in configuration")
        return False
    
    if not hasattr(config, "SMTP_HOST") or not config.SMTP_HOST:
        logger.warning("SMTP host not configured, cannot send email alert")
        return False
    
    if not hasattr(config, "ALERT_EMAIL_FROM") or not config.ALERT_EMAIL_FROM:
        logger.warning("Alert email sender not configured")
        return False
        
    recipient_list = recipients
    if recipient_list is None:
        if not hasattr(config, "ALERT_EMAIL_TO") or not config.ALERT_EMAIL_TO:
            logger.warning("Alert email recipient not configured")
            return False
        recipient_list = [config.ALERT_EMAIL_TO]
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config.ALERT_EMAIL_FROM
        msg['To'] = ", ".join(recipient_list)
        msg['Subject'] = subject
        
        # Add timestamp to the body
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_body = body
        
        if html:
            if not body.strip().startswith("<html>"):
                full_body = f"""
                <html>
                <body>
                    <p><strong>Time:</strong> {timestamp}</p>
                    <hr>
                    {body}
                    <hr>
                    <p><em>This is an automated alert from the Jail Roster Scraper.</em></p>
                </body>
                </html>
                """
            msg.attach(MIMEText(full_body, 'html'))
        else:
            full_body = f"Time: {timestamp}\n\n{body}\n\nThis is an automated alert from the Jail Roster Scraper."
            msg.attach(MIMEText(full_body, 'plain'))
        
        # Connect to SMTP server
        smtp_port = getattr(config, "SMTP_PORT", 587)
        server = smtplib.SMTP(config.SMTP_HOST, smtp_port)
        server.starttls()
        
        # Login if credentials are provided
        if hasattr(config, "SMTP_USER") and hasattr(config, "SMTP_PASSWORD") and config.SMTP_USER:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email alert sent successfully to {', '.join(recipient_list)}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {str(e)}", exc_info=True)
        return False

def send_success_alert(new_count=0, released_count=0, details=""):
    """
    Send a success alert about a completed scraper run
    
    Args:
        new_count: Number of new inmates found
        released_count: Number of released inmates found
        details: Any additional details to include
        
    Returns:
        bool: Success status of the email sending operation
    """
    subject = f"SUCCESS: Jail Roster Scraper - {new_count} New Inmates"
    
    body = f"""
    <html>
    <body>
        <h2>Jail Roster Scraper Completed Successfully</h2>
        <ul>
            <li><strong>{new_count}</strong> new inmates found and processed</li>
            <li><strong>{released_count}</strong> inmates marked as released</li>
        </ul>
        
        {details}
    </body>
    </html>
    """
    
    return send_email_alert(subject, body)

def send_error_alert(error_message, traceback=""):
    """
    Send an error alert about a failed scraper run
    
    Args:
        error_message: The error message
        traceback: Optional traceback information
        
    Returns:
        bool: Success status of the email sending operation
    """
    subject = "ERROR: Jail Roster Scraper Failed"
    
    body = f"""
    <html>
    <body>
        <h2>Jail Roster Scraper Error</h2>
        <p>The scraper encountered an error during execution:</p>
        
        <div style="background-color: #ffeeee; padding: 10px; border: 1px solid #ffcccc;">
            <pre>{error_message}</pre>
        </div>
        
        {f'<h3>Traceback</h3><pre>{traceback}</pre>' if traceback else ''}
        
        <p>Please check the log files for more details.</p>
    </body>
    </html>
    """
    
    return send_email_alert(subject, body)

# Test code when run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    if send_success_alert(5, 2, "Test success alert"):
        print("Success alert sent")
    
    if send_error_alert("Test error", "Sample\nTraceback\nInfo"):
        print("Error alert sent")