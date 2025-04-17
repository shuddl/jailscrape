# Testing Guide for Jail Roster Scraper

This document outlines the testing procedures for the jail roster scraper to ensure it functions correctly in various scenarios.

## Manual Execution Test

Before deploying the scraper to run automatically, perform these manual tests:

1. Run the scraper with default configuration:
   ```bash
   cd /path/to/jailscrape
   source venv/bin/activate
   python scraper/main.py
   ```

2. Verify the following:
   - Configuration loads correctly
   - Connection to the roster website succeeds
   - Data extraction functions properly
   - SQLite database is created and updated
   - CSV output is generated (if new inmates found)
   - Log files are written correctly

3. Check log files for any errors or warnings:
   - `logs/scraper_errors.log` should contain no errors
   - Any warnings should be non-critical

## Error Recovery Tests

Test the scraper's ability to handle common error scenarios:

1. **Network Errors**: Temporarily disconnect from the internet during a scrape
   - The scraper should log the error properly
   - It should exit with a non-zero code for cron to detect
   - Debug screenshots should be saved for diagnosis

2. **Database Errors**: Create a permissions issue with the DB file
   - The scraper should log the error
   - It should attempt retries for transient errors
   - Email alerts should be sent if configured

3. **Invalid Configuration**: Deliberately introduce an invalid config value
   - The scraper should validate configs and provide a clear error message
   - Email alerts should report the specific configuration issue

## Hourly Cron Test

Test automatic execution with cron:

1. Configure cron to run the scraper every 5 minutes temporarily:
   ```
   */5 * * * * /full/path/to/venv/bin/python /full/path/to/jailscrape/scraper/main.py >> /full/path/to/jailscrape/logs/cron.log 2>&1
   ```

2. Let it run for 3-4 cycles to verify:
   - No resource leaks occur between runs
   - Database locks don't cause issues
   - CSV files are appended correctly
   - Email alerts function as expected

3. Check resource usage during runs:
   ```bash
   top -b -n 1 | grep python
   ```

## Data Validation Test

Manually verify the accuracy of extracted data:

1. Visit the jail roster website in a browser
2. Find a specific inmate and note their details
3. Run the scraper and find the same inmate in the output CSV
4. Compare fields to ensure accuracy:
   - Name formatting
   - Dates (DOB, confinement date)
   - Charges information
   - Address/location data

## Streamlit Dashboard Test

If using the Streamlit dashboard:

1. Start the dashboard:
   ```bash
   cd /path/to/jailscrape/dashboard
   streamlit run app.py
   ```

2. Verify:
   - Dashboard loads without errors
   - Data is displayed correctly
   - Filtering and visualization features work
   - Auto-refresh functions (if enabled)

## Recommendations

- After initial validation, reduce cron frequency to hourly
- Monitor logs for the first few days of deployment
- Perform periodic validation of data accuracy
- Check disk usage growth rate to plan for rotation/archiving