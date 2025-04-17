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

# Set page configuration first - must be the first Streamlit command
st.set_page_config(
    page_title="Jail Roster Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    
    try:
        # Generate demo data
        inmates = generate_inmate_data()
        db_path = create_database(inmates)
        csv_path = create_csv(inmates)
        
        # Set environment variables to point to the demo data
        os.environ["STATE_DB"] = str(db_path)
        os.environ["OUTPUT_CSV"] = str(csv_path)
        os.environ["ROSTER_URL"] = "https://example.com/demo-jail-roster"
        
        st.success(f"Successfully created demo data with {len(inmates)} inmate records")
    except Exception as e:
        st.error(f"Error generating demo data: {e}")
        st.exception(e)
else:
    st.sidebar.warning("⚠️ Could not generate demo data. Using default paths.")

# Display the dashboard content
st.title("📊 Jail Roster Data Monitor")
st.markdown("Dashboard for monitoring jail roster data collected by the scraper.")

# Load and display data directly here instead of importing dashboard/app.py
try:
    # Add the scraper directory to path to import config
    sys.path.append(str(Path(__file__).parent))
    
    # Import necessary modules
    import sqlite3
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Define paths
    db_path = os.environ.get("STATE_DB", "dashboard/demo_data/demo_inmates.db")
    csv_path = os.environ.get("OUTPUT_CSV", "dashboard/demo_data/demo_inmates.csv")
    
    # Status information
    col1, col2, col3 = st.columns(3)
    
    if os.path.exists(db_path):
        last_modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        
        with col1:
            st.info(f"💾 Last Data Update: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Connect to database and get counts
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM processed_inmates")
        total_count = cursor.fetchone()[0]
        
        # Get in custody count
        cursor.execute("SELECT COUNT(*) FROM processed_inmates WHERE in_custody=1")
        in_custody = cursor.fetchone()[0]
        
        with col2:
            st.info(f"🔢 Total Records: {total_count}")
            
        with col3:
            st.info(f"🔒 Currently In Custody: {in_custody}")
        
        # Allow filtering
        st.subheader("Inmate Data")
        
        # Load data
        df = pd.read_sql_query("SELECT * FROM processed_inmates ORDER BY booking_date DESC", conn)
        
        # Filters in sidebar
        st.sidebar.header("Filters")
        
        # Filter by custody status
        custody_status = st.sidebar.radio(
            "Custody Status:",
            ["All", "In Custody", "Released"],
            index=0
        )
        
        if custody_status == "In Custody":
            df = df[df["in_custody"] == True]
        elif custody_status == "Released":
            df = df[df["in_custody"] == False]
        
        # Display data
        st.dataframe(df)
        
        # Basic statistics
        st.subheader("Statistics")
        
        # Check if we have race column for demographics
        if "race" in df.columns:
            # Demographics by race
            race_counts = df["race"].value_counts()
            st.bar_chart(race_counts)
        
        # Close connection
        conn.close()
    else:
        st.error(f"Database file not found at {db_path}")
        
except Exception as e:
    st.error(f"Error displaying dashboard data: {e}")
    st.exception(e)