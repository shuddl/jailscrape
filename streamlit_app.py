"""
Jail Roster Scraper Dashboard - Streamlit Cloud Entry Point

This script serves as the main entry point for the Streamlit Cloud deployment.
It generates demo data and then launches the main dashboard application.
"""

import os
import sys
import shutil
from pathlib import Path
import streamlit as st

# Add the current directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Import the demo data generator
try:
    from api.generate_demo_data import generate_inmate_data, create_database, create_csv
    demo_data_imported = True
except ImportError:
    demo_data_imported = False

# Create the necessary directory structure
demo_data_dir = Path("dashboard/demo_data")
demo_data_dir.mkdir(exist_ok=True, parents=True)

# Generate demo data if the module was imported successfully
if demo_data_imported:
    st.sidebar.info("🔄 Demo data has been generated for this deployment")
    
    # Generate demo data
    inmates = generate_inmate_data()
    db_path = create_database(inmates)
    csv_path = create_csv(inmates)
    
    # Set environment variables to point to the demo data
    os.environ["STATE_DB"] = str(db_path)
    os.environ["OUTPUT_CSV"] = str(csv_path)
    os.environ["ROSTER_URL"] = "https://example.com/demo-jail-roster"
else:
    st.sidebar.warning("⚠️ Could not generate demo data. Using default paths.")

# Import and run the main dashboard app
try:
    import dashboard.app
except ImportError as e:
    st.error(f"Error importing dashboard app: {e}")
    st.write("""
    ## Configuration Error
    
    There was a problem loading the dashboard application. Please check the repository structure 
    and make sure all required files are present.
    
    ### Troubleshooting
    
    - Make sure the dashboard/app.py file exists
    - Check that all required dependencies are installed
    - Review error message above for specific details
    """)