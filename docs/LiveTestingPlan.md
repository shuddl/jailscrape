# Live Testing Plan

This document outlines the detailed steps to validate the jail roster scraper before deployment to production.

## Preparation

1. Ensure all requirements are installed:

   ```bash
   pip install -r scraper/requirements.txt
   ```

2. Install Playwright browsers:

   ```bash
   playwright install chromium
   ```

3. Create a `.env` file with test settings:

   ```bash
   cp scraper/.env.example .env
   # Edit .env for testing
   ```

4. Ensure all directories exist:

   ```bash
   mkdir -p data logs scraper/debug_screenshots
   ```

## Testing Process

### Step 1: Configuration Validation

1. Run the scraper with deliberately invalid settings to test error handling:

   ```bash
   # Make a backup of .env
   cp .env .env.backup
   
   # Test with invalid URL
   echo "ROSTER_URL=not-a-url" >> .env
   python scraper/main.py
   # Should fail with clear config validation error
   
   # Restore valid config
   cp .env.backup .env
   ```

2. Test with minimal valid configuration:

   ```bash
   # Create minimal .env
   cat > .env << EOL
   ROSTER_URL=https://jailroster.mctx.org
   STATE_DB=data/test_inmates.db
   OUTPUT_CSV=data/test_inmates.csv
   ERROR_LOG=logs/test_errors.log
   BROWSER_TIMEOUT=30000
   EOL
   ```

### Step 2: Initial Run

1. Run the scraper with clean state:

   ```bash
   # Remove test database if it exists
   rm -f data/test_inmates.db
   
   # Run the scraper
   python scraper/main.py
   ```

2. Verify output:
   - Check console output for proper logging
   - Examine `data/test_inmates.db` to confirm it was created
   - Verify `data/test_inmates.csv` was created if new inmates were found
   - Check `logs/test_errors.log` for any errors

3. Capture statistics:
   - Number of inmates processed
   - Execution time
   - Number of new inmates found

### Step 3: Incremental Run Test

1. Run the scraper again with existing state:

   ```bash
   python scraper/main.py
   ```

2. Verify that:
   - Previously processed inmates are recognized
   - Only new inmates (if any) are processed
   - `last_seen_timestamp` is updated for existing inmates
   - No duplicate entries are created in the CSV

### Step 4: Error Recovery Testing

1. Test network resilience:

   ```bash
   # In one terminal, start a proxy that can be interrupted
   # This step would require a proxy tool like mitmproxy
   
   # In another terminal, run with the proxy configuration
   # and interrupt the proxy during execution
   ```

2. Test screenshot-on-failure:

   ```bash
   # Modify a selector in scraper.py to an invalid one
   # Run the scraper and verify screenshot is captured
   ```

3. Test database error recovery:

   ```bash
   # Create a read-only database file
   touch data/readonly.db
   chmod 444 data/readonly.db
   
   # Run with this db file
   STATE_DB=data/readonly.db python scraper/main.py
   
   # Should fail gracefully with clear error message
   ```

### Step 5: Load and Performance Testing

1. Measure resource usage:

   ```bash
   /usr/bin/time -v python scraper/main.py
   ```

2. Check for memory leaks or excessive resource usage:

   ```bash
   # Run multiple times in sequence
   for i in {1..5}; do
     python scraper/main.py
     sleep 5
   done
   ```

### Step 6: Dashboard Testing (if applicable)

1. Start the dashboard:

   ```bash
   cd dashboard
   streamlit run app.py
   ```

2. Verify that:
   - Dashboard loads correctly
   - Data is displayed properly
   - Filtering works as expected
   - Statistics are accurate

### Step 7: Email Alert Testing

1. Configure email settings in `.env`:

   ```
   ENABLE_EMAIL_ALERTS=True
   SMTP_HOST=your-smtp-host
   SMTP_PORT=587
   SMTP_USER=your-username
   SMTP_PASSWORD=your-password
   ALERT_EMAIL_TO=recipient@example.com
   ALERT_EMAIL_FROM=sender@example.com
   ```

2. Trigger success and error alerts:

   ```bash
   # For success alerts, run normally
   python scraper/main.py
   
   # For error alerts, cause a deliberate error
   # by modifying ROSTER_URL to an invalid URL
   ```

3. Check email inbox for both types of alerts

## Validation Checklist

Use this checklist to track testing progress:

- [ ] Configuration validation works correctly
- [ ] Initial run completes successfully
- [ ] Database is created and populated
- [ ] CSV output is generated correctly
- [ ] Incremental run correctly identifies previously processed inmates
- [ ] Error handling functions as expected
- [ ] Screenshots are captured on failures
- [ ] Resource usage is within acceptable limits
- [ ] Dashboard displays data correctly (if applicable)
- [ ] Email alerts are sent correctly (if configured)
- [ ] Log files contain appropriate information

## Final Validation

After completing all tests:

1. Restore any modified files:

   ```bash
   git checkout scraper/scraper.py
   ```

2. Clean up test files:

   ```bash
   rm -f data/test_inmates.db data/test_inmates.csv
   ```

3. Set up production configuration and deploy according to the Deployment Guide.