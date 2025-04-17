import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path
from playwright.async_api import async_playwright, Page, Locator, TimeoutError as PlaywrightTimeoutError

# Import local modules
import config

# Get logger
logger = logging.getLogger(__name__)

# Ensure screenshots directory exists
SCREENSHOTS_DIR = Path(__file__).parent / "debug_screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True, parents=True)

# Database functions
def setup_database():
    """
    Initialize the SQLite database and create necessary tables if they don't exist.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Create the processed_inmates table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_inmates (
            name_number TEXT PRIMARY KEY,
            processed_timestamp TEXT
        )
        ''')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info(f"Database setup complete at {config.STATE_DB}")
        return True
    except Exception as e:
        logger.error(f"Database setup error: {str(e)}", exc_info=True)
        return False

def load_processed_ids() -> Set[str]:
    """
    Load all previously processed inmate IDs from the database.
    
    Returns:
        set: Set of name_number strings for previously processed inmates
    """
    processed_ids = set()
    retry_count = 0
    max_retries = 2
    
    while retry_count <= max_retries:
        try:
            # Connect to the database
            conn = sqlite3.connect(config.STATE_DB)
            cursor = conn.cursor()
            
            # Query all processed inmate IDs
            cursor.execute("SELECT name_number FROM processed_inmates")
            
            # Add each ID to the set
            for row in cursor.fetchall():
                processed_ids.add(row[0])
            
            # Close the connection
            conn.close()
            
            logger.info(f"Loaded {len(processed_ids)} previously processed inmate IDs")
            return processed_ids
        
        except sqlite3.OperationalError as oe:
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"Database operational error (retry {retry_count}/{max_retries}): {str(oe)}")
                # Short delay before retry
                asyncio.sleep(1)
            else:
                logger.error(f"Database operational error after {max_retries} retries: {str(oe)}")
                return set()
        except Exception as e:
            logger.error(f"Error loading processed IDs: {str(e)}", exc_info=True)
            return set()

def mark_as_processed(conn, name_number: str):
    """
    Mark an inmate as processed in the database.
    
    Args:
        conn: SQLite connection
        name_number: The inmate's unique name/booking number
    """
    try:
        cursor = conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        
        # Insert or ignore (if already exists)
        cursor.execute(
            "INSERT OR IGNORE INTO processed_inmates (name_number, processed_timestamp) VALUES (?, ?)",
            (name_number, timestamp)
        )
        
        return True
    except Exception as e:
        logger.error(f"Error marking inmate {name_number} as processed: {str(e)}", exc_info=True)
        return False

def mark_inmate_processed(name_number: str):
    """Alternative interface for marking an inmate as processed"""
    try:
        conn = sqlite3.connect(config.STATE_DB)
        result = mark_as_processed(conn, name_number)
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error in mark_inmate_processed: {str(e)}", exc_info=True)
        return False

# Scraping functions
async def scrape_main_roster(page: Page) -> List[Dict]:
    """
    Scrape the main roster page and extract data from the inmate table.
    
    Args:
        page: Playwright page object
        
    Returns:
        list: List of dictionaries containing inmate data
    """
    inmates = []
    
    try:
        # Navigate to the roster URL with retries
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Navigating to {config.ROSTER_URL} (attempt {retry_count + 1}/{max_retries})")
                
                # First wait for networkidle to ensure page fully loads
                await page.goto(config.ROSTER_URL, timeout=config.BROWSER_TIMEOUT, wait_until="networkidle")
                break  # Success, exit retry loop
                
            except PlaywrightTimeoutError as timeout_error:
                retry_count += 1
                error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = SCREENSHOTS_DIR / f"page_load_timeout_{error_timestamp}.png"
                
                try:
                    # Take screenshot of the current state
                    await page.screenshot(path=screenshot_path)
                    logger.warning(f"Page load timed out. Screenshot saved to {screenshot_path}")
                except Exception as ss_error:
                    logger.warning(f"Failed to save screenshot: {str(ss_error)}")
                
                if retry_count >= max_retries:
                    logger.error(f"Failed to navigate to {config.ROSTER_URL} after {max_retries} attempts")
                    await page.screenshot(path=SCREENSHOTS_DIR / f"final_failed_load_{error_timestamp}.png")
                    raise timeout_error
                
                # Wait before retrying
                await asyncio.sleep(5)
        
        # Wait for the inmate table to be visible
        # Using a specific selector for the main inmates table - this needs verification against the live site
        table_selector = "table#inmateTable" # This is a placeholder - adjust based on actual site inspection
        
        try:
            logger.info(f"Waiting for table to be visible: {table_selector}")
            await page.wait_for_selector(table_selector, timeout=config.BROWSER_TIMEOUT)
        except PlaywrightTimeoutError:
            # Try alternative selector before giving up
            alternative_selector = "table.inmates-list"  # Example alternative
            logger.warning(f"Table selector '{table_selector}' not found, trying alternative: '{alternative_selector}'")
            
            try:
                await page.wait_for_selector(alternative_selector, timeout=config.BROWSER_TIMEOUT)
                table_selector = alternative_selector  # Use the working selector
            except PlaywrightTimeoutError as e:
                error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = SCREENSHOTS_DIR / f"table_not_found_{error_timestamp}.png"
                html_path = SCREENSHOTS_DIR / f"table_not_found_{error_timestamp}.html"
                
                # Capture diagnostics
                await page.screenshot(path=screenshot_path)
                html_content = await page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                logger.error(f"Table not found. Screenshot saved to {screenshot_path}, HTML to {html_path}")
                raise e
        
        # Find all inmate rows within the table body
        rows = await page.locator(f"{table_selector} tbody tr").all()
        logger.info(f"Found {len(rows)} inmate rows")
        
        # Process each row
        for row in rows:
            inmate_data = {}
            
            # Extract text from cells - these selectors need verification
            try:
                # The column indices need verification against the actual site structure
                inmate_data["last_name"] = await row.locator("td:nth-child(1)").text_content() or ""
                inmate_data["first_name"] = await row.locator("td:nth-child(2)").text_content() or ""
                inmate_data["middle_name"] = await row.locator("td:nth-child(3)").text_content() or ""
                inmate_data["suffix"] = await row.locator("td:nth-child(4)").text_content() or ""
                inmate_data["age"] = await row.locator("td:nth-child(5)").text_content() or ""
                inmate_data["race"] = await row.locator("td:nth-child(6)").text_content() or ""
                inmate_data["gender"] = await row.locator("td:nth-child(7)").text_content() or ""
                inmate_data["date_confined"] = await row.locator("td:nth-child(8)").text_content() or ""
                inmate_data["name_number"] = await row.locator("td:nth-child(9)").text_content() or ""
                
                # Create full name
                full_name_parts = [inmate_data["first_name"], inmate_data["middle_name"], inmate_data["last_name"]]
                if inmate_data["suffix"]:
                    full_name_parts.append(inmate_data["suffix"])
                inmate_data["full_name"] = " ".join(part for part in full_name_parts if part).strip()
                
                # Normalize data
                for key in inmate_data:
                    inmate_data[key] = inmate_data[key].strip()
                
                # Only add inmates with a valid name_number
                if inmate_data["name_number"]:
                    inmates.append(inmate_data)
                else:
                    logger.warning("Skipping inmate with no name_number")
                    
            except Exception as cell_error:
                logger.warning(f"Error extracting cell data: {str(cell_error)}")
                continue
        
        logger.info(f"Successfully extracted data for {len(inmates)} inmates")
        return inmates
        
    except Exception as e:
        logger.error(f"Error scraping main roster: {str(e)}", exc_info=True)
        # Take screenshot of the error state
        try:
            error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=SCREENSHOTS_DIR / f"roster_error_{error_timestamp}.png")
        except:
            pass
        return []

async def scrape_inmate_details(page: Page, name_number: str, inmate_row_element: Optional[Locator] = None) -> Optional[Dict]:
    """
    Scrape detailed information for a specific inmate by clicking on their row in the roster.
    
    Args:
        page: Playwright page object
        name_number: The unique name/booking number of the inmate
        inmate_row_element: Optional locator for the inmate's row element. If not provided,
                           the function will attempt to find it based on name_number.
    
    Returns:
        dict: Dictionary containing detailed inmate information, or None if details cannot be retrieved
        Will include a "missing_fields" key listing any fields that could not be extracted
    """
    missing_fields = []
    
    try:
        # Find the inmate row if not provided
        if inmate_row_element is None:
            # Find the row containing the name_number
            table_selector = "table#inmateTable" # This needs verification against the live site
            rows = await page.locator(f"{table_selector} tbody tr").all()
            
            inmate_row_element = None
            for row in rows:
                # Adjust the column index based on actual site structure
                cell_text = await row.locator("td:nth-child(9)").text_content()  # Assuming name_number is in column 9
                if cell_text and cell_text.strip() == name_number:
                    inmate_row_element = row
                    break
            
            if inmate_row_element is None:
                logger.warning(f"Could not find inmate with name_number {name_number} in the roster")
                return None
        
        logger.info(f"Found inmate row for {name_number}, attempting to click for details")
        
        # The interaction pattern needs verification against the actual site:
        # Try clicking with retry logic
        max_retries = 2
        retry_count = 0
        click_success = False
        
        while retry_count <= max_retries and not click_success:
            try:
                # Try clicking the row itself
                await inmate_row_element.click()
                click_success = True
            except Exception as click_error:
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"Click failed (retry {retry_count}/{max_retries}): {str(click_error)}")
                    await asyncio.sleep(1)  # Short delay before retry
                else:
                    logger.error(f"Click failed after {max_retries} retries: {str(click_error)}")
                    
                    # Try alternative strategy - look for a specific clickable element within the row
                    try:
                        logger.info("Trying to click a specific element within the row")
                        # Try to find a link or button inside the row
                        link = await inmate_row_element.locator("a, button").first
                        if link:
                            await link.click()
                            click_success = True
                            logger.info("Successfully clicked element within row")
                        else:
                            # Take screenshot of the failed click
                            error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            await page.screenshot(path=SCREENSHOTS_DIR / f"click_failed_{name_number}_{error_timestamp}.png")
                            return None
                    except Exception as alt_click_error:
                        logger.error(f"Alternative click strategy failed: {str(alt_click_error)}")
                        # Take screenshot of the error state
                        error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        await page.screenshot(path=SCREENSHOTS_DIR / f"click_failed_{name_number}_{error_timestamp}.png")
                        return None
        
        # Wait for the detail view to appear
        detail_pane = None
        detail_selectors = [
            "div.inmateDetails",  # Example primary selector
            "div.modal-dialog",   # Example alternative selector
            "div.detail-pane",    # Another possible selector
            "#detailsPanel"       # Another possibility
        ]
        
        # Try each selector
        for selector in detail_selectors:
            try:
                logger.info(f"Waiting for detail pane with selector: {selector}")
                detail_pane = await page.wait_for_selector(selector, timeout=15000)
                if detail_pane:
                    logger.info(f"Found detail pane with selector: {selector}")
                    break
            except Exception as wait_error:
                logger.warning(f"Selector {selector} not found: {str(wait_error)}")
        
        if not detail_pane:
            logger.error(f"Could not find detail view with any selector for inmate {name_number}")
            # Take screenshot of the error state
            error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=SCREENSHOTS_DIR / f"detail_not_found_{name_number}_{error_timestamp}.png")
            return None
        
        # Successfully found detail pane, extract information
        logger.info("Detail pane found, extracting information")
        
        details = {}
        
        # Attempt to extract each field, but continue even if some fail
        try:
            # Basic personal information
            try:
                details["dob"] = await extract_text_or_empty(page, "div.inmateDetails .dob")
            except Exception:
                missing_fields.append("dob")
                details["dob"] = ""
            
            try:
                details["address"] = await extract_text_or_empty(page, "div.inmateDetails .address")
            except Exception:
                missing_fields.append("address")
                details["address"] = ""
            
            # Try to extract city, state, zip
            try:
                location_text = await extract_text_or_empty(page, "div.inmateDetails .location")
                if location_text:
                    # Parse combined location field (common format: "City, State Zip")
                    location_parts = location_text.split(",", 1)
                    details["city"] = location_parts[0].strip() if len(location_parts) > 0 else ""
                    
                    if len(location_parts) > 1:
                        # Try to split state and zip (common format: "State Zip")
                        state_zip = location_parts[1].strip().split(" ", 1)
                        details["state"] = state_zip[0].strip() if len(state_zip) > 0 else ""
                        details["zip"] = state_zip[1].strip() if len(state_zip) > 1 else ""
                    else:
                        details["state"] = ""
                        details["zip"] = ""
                else:
                    # Try individual fields if available
                    details["city"] = await extract_text_or_empty(page, "div.inmateDetails .city")
                    details["state"] = await extract_text_or_empty(page, "div.inmateDetails .state")
                    details["zip"] = await extract_text_or_empty(page, "div.inmateDetails .zip")
                    
                    # Check if we found any location data
                    if not any([details["city"], details["state"], details["zip"]]):
                        missing_fields.append("location")
            except Exception:
                missing_fields.append("location")
                details["city"] = ""
                details["state"] = ""
                details["zip"] = ""
            
            # Extract charges - try multiple potential selectors
            charges = []
            charge_container_found = False
            
            charge_container_selectors = [
                "div.charges .charge-item",  # Example selector
                "table.charges-table tbody tr",  # Alternative table structure
                "div.inmate-charges .charge",  # Another possibility
            ]
            
            for selector in charge_container_selectors:
                try:
                    charge_elements = await page.locator(selector).all()
                    
                    if charge_elements and len(charge_elements) > 0:
                        charge_container_found = True
                        logger.info(f"Found {len(charge_elements)} charges using selector: {selector}")
                        
                        # Process the first few charges (limit to avoid overwhelming)
                        for i, charge_elem in enumerate(charge_elements[:5]):  # Limit to 5 charges
                            charge = {}
                            
                            # Try different ways to extract charge data
                            if selector.endswith("tr"):  # Table row format
                                # Table structure - use column indices
                                try:
                                    charge["description"] = await extract_text_from_element_or_empty(charge_elem, "td:nth-child(1)")
                                    charge["offense_date"] = await extract_text_from_element_or_empty(charge_elem, "td:nth-child(2)")
                                    charge["court_reference"] = await extract_text_from_element_or_empty(charge_elem, "td:nth-child(3)")
                                    charge["disposition"] = await extract_text_from_element_or_empty(charge_elem, "td:nth-child(4)")
                                except Exception:
                                    charge["description"] = f"Failed to extract charge #{i+1}"
                            else:
                                # Div structure - use class selectors
                                try:
                                    charge["description"] = await extract_text_from_element_or_empty(charge_elem, ".charge-description, .description")
                                    charge["offense_date"] = await extract_text_from_element_or_empty(charge_elem, ".offense-date, .date")
                                    charge["court_reference"] = await extract_text_from_element_or_empty(charge_elem, ".court-reference, .court")
                                    charge["disposition"] = await extract_text_from_element_or_empty(charge_elem, ".disposition, .status")
                                except Exception:
                                    charge["description"] = f"Failed to extract charge #{i+1}"
                            
                            charges.append(charge)
                        
                        break  # Stop after finding charges with the first working selector
                    
                except Exception as charge_error:
                    logger.warning(f"Error extracting charges with selector {selector}: {str(charge_error)}")
            
            if not charge_container_found:
                missing_fields.append("charges")
                logger.warning(f"No charge elements found for inmate {name_number}")
            
            details["charges"] = charges
            details["number_of_charges"] = len(charges)
            
            # Add timestamp and missing fields list
            details["scrape_timestamp_utc"] = datetime.utcnow().isoformat()
            details["missing_fields"] = missing_fields
            
            if missing_fields:
                logger.warning(f"Some fields could not be extracted for inmate {name_number}: {', '.join(missing_fields)}")
            
            logger.info(f"Successfully extracted details for inmate {name_number} with {len(charges)} charges")
            return details
            
        except Exception as extraction_error:
            logger.error(f"Error extracting inmate details: {str(extraction_error)}", exc_info=True)
            # Take screenshot of the error state
            error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=SCREENSHOTS_DIR / f"extraction_error_{name_number}_{error_timestamp}.png")
            return None
    
    except Exception as e:
        logger.error(f"Error in scrape_inmate_details: {str(e)}", exc_info=True)
        # Take screenshot of the error state
        try:
            error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=SCREENSHOTS_DIR / f"detail_error_{name_number}_{error_timestamp}.png")
        except:
            pass
        return None

async def extract_text_or_empty(page: Page, selector: str) -> str:
    """Helper function to safely extract text from an element or return empty string if not found."""
    try:
        element = await page.locator(selector).first
        if element:
            return (await element.text_content() or "").strip()
        return ""
    except Exception:
        return ""

async def extract_text_from_element_or_empty(element: Locator, selector: str) -> str:
    """Helper function to safely extract text from a child element or return empty string if not found."""
    try:
        child = await element.locator(selector).first
        if child:
            return (await child.text_content() or "").strip()
        return ""
    except Exception:
        return ""

async def initialize_browser():
    """
    Initialize and return Playwright browser and page objects.
    
    Returns:
        tuple: (playwright, browser, page) instances
    """
    # Read headless mode from config with default true
    headless = True
    if hasattr(config, "BROWSER_HEADLESS"):
        # Convert string to boolean if it's a string
        if isinstance(config.BROWSER_HEADLESS, str):
            headless = config.BROWSER_HEADLESS.lower() == "true"
        else:
            headless = bool(config.BROWSER_HEADLESS)
    
    logger.info(f"Initializing browser in {'headless' if headless else 'headed'} mode")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()
    
    # Set default timeout from config
    page.set_default_timeout(config.BROWSER_TIMEOUT)
    
    return playwright, browser, page

async def close_browser(playwright, browser):
    """
    Properly close Playwright browser and playwright instance.
    
    Args:
        playwright: Playwright instance
        browser: Browser instance
    """
    try:
        await browser.close()
        await playwright.stop()
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")

async def main():
    """Main entry point for the scraper module when run independently."""
    try:
        logger.info("Starting jail roster scraper")
        
        # Setup database
        setup_database()
        
        # Load previously processed inmate IDs
        processed_ids = load_processed_ids()
        logger.info(f"Found {len(processed_ids)} previously processed inmates in database")
        
        # Initialize list for new inmate data
        new_inmate_data = []
        
        # Use context managers for better resource handling
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            
            try:
                # Create a new browser context and page
                context = await browser.new_context()
                page = await context.new_page()
                
                # Set default timeout
                page.set_default_timeout(config.BROWSER_TIMEOUT)
                
                # Scrape the main roster
                inmates = await scrape_main_roster(page)
                logger.info(f"Found {len(inmates)} inmates on main roster")
                
                # Process inmates
                for inmate in inmates:
                    name_number = inmate["name_number"]
                    
                    # Check if this is a new inmate
                    if name_number not in processed_ids:
                        logger.info(f"Processing NEW inmate: {name_number}")
                        
                        # Get detailed information for the new inmate
                        details = await scrape_inmate_details(page, name_number)
                        
                        if details:
                            # Combine main roster data and detail data
                            full_record = {**inmate, **details}
                            full_record['timestamp_processed_utc'] = datetime.utcnow().isoformat()
                            new_inmate_data.append(full_record)
                            logger.info(f"Successfully processed details for NEW inmate: {name_number}")
                        else:
                            logger.warning(f"Failed to get details for NEW inmate: {name_number}")
                
                logger.info(f"Processed {len(new_inmate_data)} new inmates")
                
                # Mark all inmates as processed in the database
                conn = sqlite3.connect(config.STATE_DB)
                for inmate in inmates:
                    mark_as_processed(conn, inmate['name_number'])
                
                # Commit changes and close connection
                conn.commit()
                conn.close()
                
                # Print summary
                if new_inmate_data:
                    logger.info(f"First new inmate data: {new_inmate_data[0]}")
                
            finally:
                # Close the browser properly
                await browser.close()
                
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Configure basic logging when run as a standalone script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main())