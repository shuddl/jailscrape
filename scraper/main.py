import asyncio
import logging
import sqlite3
import traceback
import sys
from datetime import datetime
from pathlib import Path

# Import local modules
import config
from scraper import initialize_browser, close_browser, scrape_main_roster, scrape_inmate_details
from processor import structure_inmate_data, write_to_csv, get_output_csv_path
from alerter import send_success_alert, send_error_alert

# Configure logging
def setup_logging():
    """Configure logging to both console and file"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]: 
        root_logger.removeHandler(handler) 
        
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console)
    
    # Add file handler
    file_handler = logging.FileHandler(config.ERROR_LOG)
    file_handler.setLevel(logging.ERROR)  # Only log errors to file
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

def validate_config():
    """Validate that all required configuration values are set"""
    required_configs = {
        "ROSTER_URL": "URL of the jail roster website",
        "STATE_DB": "Path to the SQLite database",
        "OUTPUT_CSV": "Path to the output CSV file",
        "ERROR_LOG": "Path to the error log file",
        "BROWSER_TIMEOUT": "Timeout for browser operations in milliseconds"
    }
    
    missing = []
    invalid = []
    
    for config_key, description in required_configs.items():
        # Check if the config exists
        if not hasattr(config, config_key):
            missing.append(f"{config_key}: {description}")
            continue
            
        # Validate specific configs
        value = getattr(config, config_key)
        if config_key == "ROSTER_URL" and not value.startswith(("http://", "https://")):
            invalid.append(f"{config_key}: Must be a valid URL starting with http:// or https://")
        elif config_key in ["STATE_DB", "OUTPUT_CSV", "ERROR_LOG"]:
            # These should be valid paths - ensure parent directories exist
            try:
                path = Path(value)
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                invalid.append(f"{config_key}: Invalid path - {str(e)}")
        elif config_key == "BROWSER_TIMEOUT":
            try:
                timeout = int(value)
                if timeout <= 0:
                    invalid.append(f"{config_key}: Must be a positive integer")
            except ValueError:
                invalid.append(f"{config_key}: Must be a valid integer")
    
    if missing or invalid:
        error_msg = "Configuration errors detected:\n"
        if missing:
            error_msg += "\nMissing required configurations:\n- " + "\n- ".join(missing)
        if invalid:
            error_msg += "\nInvalid configurations:\n- " + "\n- ".join(invalid)
        
        raise ValueError(error_msg)
    
    return True

async def run_hourly_scrape():
    """Main function to run the hourly scraping workflow"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Track statistics for reporting
    new_count = 0
    released_count = 0
    
    try:
        # Validate configuration
        logger.info("Validating configuration")
        validate_config()
        
        start_time = datetime.now()
        logger.info(f"Starting hourly jail roster scrape at {start_time}")
        
        # Initialize list for new inmate records
        new_inmate_records = []
        
        # Initialize the database
        logger.info("Initializing database")
        from database import initialize_database, load_processed_ids, mark_inmate_processed, update_last_seen, find_released_inmates
        initialize_database()
        
        # Load previously processed inmate IDs
        processed_ids = load_processed_ids()
        logger.info(f"Found {len(processed_ids)} previously processed inmates in database")
        
        # Initialize browser
        logger.info("Initializing browser")
        playwright, browser, page = await initialize_browser()
        
        try:
            # Scrape the main roster
            logger.info(f"Scraping main roster from {config.ROSTER_URL}")
            inmates = await scrape_main_roster(page)
            
            if not inmates:
                logger.error("No inmates found or error scraping the roster")
                return
                
            logger.info(f"Found {len(inmates)} inmates on main roster")
            
            # Get all name numbers currently on the roster
            name_numbers_on_roster = set(inmate['name_number'] for inmate in inmates)
            
            # Process inmates
            for inmate in inmates:
                name_number = inmate["name_number"]
                
                # Check if this is a new inmate
                if name_number not in processed_ids:
                    logger.info(f"Processing NEW inmate: {name_number}")
                    new_count += 1
                    
                    # Get detailed information for the new inmate
                    details = await scrape_inmate_details(page, name_number)
                    
                    if details:
                        # Combine main roster data and detail data
                        raw_record = {**inmate, **details}
                        
                        # Structure and clean the data
                        structured_record = structure_inmate_data(raw_record)
                        structured_record['timestamp_processed_utc'] = datetime.utcnow().isoformat()
                        
                        # Add to new inmates list
                        new_inmate_records.append(structured_record)
                        mark_inmate_processed(name_number)
                        
                        logger.info(f"Successfully processed details for NEW inmate: {name_number}")
                    else:
                        logger.warning(f"Failed to get details for NEW inmate: {name_number}")
                        # Still mark as processed to avoid repeated attempts
                        mark_inmate_processed(name_number)
            
            logger.info(f"Found {new_count} new inmates")
            
            # Write new inmate records to CSV if there are any
            if new_inmate_records:
                csv_path = get_output_csv_path()
                success = write_to_csv(new_inmate_records, csv_path)
                
                if success:
                    logger.info(f"Successfully appended {len(new_inmate_records)} new records to {csv_path}")
                else:
                    logger.error(f"Failed to write new inmate records to CSV")
            else:
                logger.info("No new inmates found this run")
            
            # Update last seen timestamp for all current inmates
            update_last_seen(name_numbers_on_roster)
            logger.info(f"Updated last seen timestamp for {len(name_numbers_on_roster)} inmates")
            
            # Find released inmates (no longer on roster)
            released_inmates = find_released_inmates(name_numbers_on_roster)
            if released_inmates:
                released_count = len(released_inmates)
                logger.info(f"Found {released_count} inmates who were released")
            
            # Send success alert if there were new or released inmates
            if new_count > 0 or released_count > 0:
                if hasattr(config, "ENABLE_EMAIL_ALERTS") and config.ENABLE_EMAIL_ALERTS:
                    # Generate detailed report
                    details = ""
                    if new_count > 0:
                        details += f"<h3>New Inmates ({new_count})</h3><ul>"
                        for i, inmate in enumerate(new_inmate_records[:10]):  # Limit to 10 for the email
                            details += f"<li>{inmate.get('full_name', 'Unknown')} ({inmate.get('name_number', 'Unknown')})</li>"
                        if new_count > 10:
                            details += f"<li>... and {new_count - 10} more</li>"
                        details += "</ul>"
                    
                    if released_count > 0:
                        details += f"<h3>Released Inmates ({released_count})</h3>"
                        # You might want to fetch more info about released inmates here
                    
                    send_success_alert(new_count, released_count, details)
            
        finally:
            # Ensure browser is closed even if an error occurs
            await close_browser(playwright, browser)
            
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Hourly scrape completed in {duration.total_seconds():.2f} seconds")
        
    except Exception as e:
        logger.exception(f"Fatal error in hourly scrape: {str(e)}")
        
        # Send error alert
        if hasattr(config, "ENABLE_EMAIL_ALERTS") and config.ENABLE_EMAIL_ALERTS:
            tb_str = traceback.format_exc()
            send_error_alert(str(e), tb_str)
            
        # Exit with error code for cron monitoring
        sys.exit(1)

async def main():
    """Entry point for the scraper"""
    try:
        await run_hourly_scrape()
    except Exception as e:
        logging.exception(f"Uncaught exception in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())