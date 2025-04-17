import streamlit as st
import pandas as pd
import sqlite3
import os
import glob
from datetime import datetime, timedelta
from pathlib import Path
import sys
import plotly.express as px
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent, "dashboard.log"))
    ]
)
logger = logging.getLogger("dashboard")

# Add the parent directory to sys.path to import the scraper's config
sys.path.append(str(Path(__file__).parent.parent))
try:
    from scraper import config
    logger.info("Successfully imported config from scraper module")
except ImportError as e:
    logger.warning(f"Could not import scraper config: {e}. Using fallback config.")
    # Fallback if the import fails
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    class FallbackConfig:
        def __init__(self):
            self.STATE_DB = os.getenv("STATE_DB", "../data/processed_inmates.db")
            self.OUTPUT_CSV = os.getenv("OUTPUT_CSV", "../data/new_inmates.csv")
            self.OUTPUT_CSV_DIR = os.getenv("OUTPUT_CSV_DIR", "../data")
    
    config = FallbackConfig()
    logger.info(f"Using fallback config with STATE_DB={config.STATE_DB}, OUTPUT_CSV={config.OUTPUT_CSV}")

# Set page configuration
st.set_page_config(
    page_title="Jail Roster Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page header
st.title("📊 Jail Roster Data Monitor")
st.markdown("Dashboard for monitoring jail roster data collected by the scraper.")

# Define paths
if hasattr(config, "STATE_DB"):
    db_path = Path(config.STATE_DB)
else:
    db_path = Path("../data/processed_inmates.db")

if hasattr(config, "OUTPUT_CSV"):
    csv_path = Path(config.OUTPUT_CSV)
else:
    csv_path = Path("../data/new_inmates.csv")

if hasattr(config, "OUTPUT_CSV_DIR"):
    csv_dir = Path(config.OUTPUT_CSV_DIR)
else:
    csv_dir = Path("../data")

# Make paths absolute if they're relative
if not db_path.is_absolute():
    db_path = Path(Path(__file__).parent.parent / db_path)

if not csv_path.is_absolute():
    csv_path = Path(Path(__file__).parent.parent / csv_path)

if not csv_dir.is_absolute():
    csv_dir = Path(Path(__file__).parent.parent / csv_dir)

logger.info(f"Using paths - DB: {db_path}, CSV: {csv_path}, CSV Dir: {csv_dir}")

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_csv_file():
    """Get the latest CSV file based on modification time"""
    try:
        # Make sure the directory exists
        if not csv_dir.exists():
            logger.warning(f"CSV directory {csv_dir} does not exist")
            return None
            
        # Get all CSV files
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in {csv_dir}")
            return None
            
        # Sort by modification time (newest first)
        latest_file = max(csv_files, key=os.path.getmtime)
        logger.info(f"Found latest CSV file: {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"Error finding latest CSV file: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_csv():
    """Load data from the latest CSV file"""
    try:
        # Try to use the direct path first
        if csv_path.exists():
            logger.info(f"Loading data from configured CSV path: {csv_path}")
            df = pd.read_csv(csv_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(csv_path))
            return df, last_modified, csv_path
            
        # If not found, try to find the latest CSV file in the directory
        latest_file = get_latest_csv_file()
        if latest_file and latest_file.exists():
            logger.info(f"Loading data from latest CSV file: {latest_file}")
            df = pd.read_csv(latest_file)
            last_modified = datetime.fromtimestamp(os.path.getmtime(latest_file))
            return df, last_modified, latest_file
            
        # If no CSV found
        logger.warning("No CSV files found to load data from")
        return None, None, None
    except Exception as e:
        logger.error(f"Error loading CSV data: {e}")
        return None, None, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_db(hours_back=24):
    """Load data from the SQLite database"""
    try:
        if not db_path.exists():
            logger.warning(f"Database file {db_path} does not exist")
            return None, None
            
        # Connect to the database
        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        
        # Get the last X hours of inmate data
        timestamp_threshold = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        # Try different queries based on the possible schema
        queries = [
            # Query for the schema with first_seen_timestamp
            """
            SELECT * FROM processed_inmates 
            WHERE first_seen_timestamp >= ? 
            ORDER BY first_seen_timestamp DESC
            """,
            # Query for the schema with processed_timestamp
            """
            SELECT * FROM processed_inmates 
            WHERE processed_timestamp >= ? 
            ORDER BY processed_timestamp DESC
            """,
            # Query for the schema with timestamp_processed_utc
            """
            SELECT * FROM processed_inmates 
            WHERE timestamp_processed_utc >= ? 
            ORDER BY timestamp_processed_utc DESC
            """,
            # Fallback query - just get everything
            """
            SELECT * FROM processed_inmates
            """
        ]
        
        df = None
        
        for i, query in enumerate(queries):
            try:
                if i < 3:  # First 3 queries need a parameter
                    df = pd.read_sql_query(query, conn, params=(timestamp_threshold,))
                else:  # Last query doesn't need a parameter
                    df = pd.read_sql_query(query, conn)
                
                if not df.empty:
                    logger.info(f"Successfully loaded {len(df)} records using query #{i+1}")
                    break
            except Exception as query_error:
                if i < len(queries) - 1:
                    logger.warning(f"Query #{i+1} failed: {query_error}. Trying next query.")
                else:
                    logger.error(f"All queries failed. Last error: {query_error}")
        
        last_modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        conn.close()
        
        if df is not None and not df.empty:
            return df, last_modified
        else:
            logger.warning("No data found in the database or all queries failed")
            return None, None
    except Exception as e:
        logger.error(f"Error loading database data: {e}")
        return None, None

# Function to load data based on any available source
def load_recent_data(source_preference=None):
    """
    Load recent data from any available source - adaptively tries different sources
    
    Args:
        source_preference: "CSV", "DB", or None (auto-detect)
    """
    data = None
    last_modified = None
    source_used = None
    
    # If preference is specified, try that first
    if source_preference == "CSV":
        data, last_modified, file_path = load_data_from_csv()
        if data is not None:
            source_used = f"CSV ({file_path.name})"
    elif source_preference == "DB":
        data, last_modified = load_data_from_db()
        if data is not None:
            source_used = f"Database ({db_path.name})"
    
    # If preference failed or no preference, try both
    if data is None:
        # Try CSV first
        data, last_modified, file_path = load_data_from_csv()
        if data is not None:
            source_used = f"CSV ({file_path.name})"
        else:
            # Try DB if CSV failed
            data, last_modified = load_data_from_db()
            if data is not None:
                source_used = f"Database ({db_path.name})"
    
    return data, last_modified, source_used

# Sidebar filters
st.sidebar.header("Filters")
st.sidebar.markdown("### Select Data Source")
data_source = st.sidebar.radio(
    "Choose data source:",
    ["Auto-detect", "CSV File", "Database"],
    index=0
)

# Mapping from UI choices to function parameters
source_map = {
    "Auto-detect": None,
    "CSV File": "CSV",
    "Database": "DB"
}

# Get the time range for database queries
if data_source == "Database" or data_source == "Auto-detect":
    hours_back = st.sidebar.slider(
        "Hours to look back:",
        min_value=1,
        max_value=168,  # 1 week
        value=24,
        step=1
    )
else:
    hours_back = 24  # Default

# Load the data
data, last_modified, source_used = load_recent_data(source_map[data_source])

# Display the data source actually used
if source_used:
    st.sidebar.success(f"Loaded data from: {source_used}")
else:
    st.sidebar.error("Could not load data from any source")

# Allow filtering by column
if data is not None and not data.empty:
    filter_column = st.sidebar.selectbox(
        "Filter by column:",
        options=data.columns.tolist()
    )
    
    if filter_column:
        if data[filter_column].dtype == 'object':
            filter_value = st.sidebar.text_input(f"Filter {filter_column} containing:")
            if filter_value:
                data = data[data[filter_column].astype(str).str.contains(filter_value, case=False, na=False)]
        else:
            min_val, max_val = st.sidebar.slider(
                f"Filter {filter_column} range:",
                min_value=float(data[filter_column].min()),
                max_value=float(data[filter_column].max()),
                value=(float(data[filter_column].min()), float(data[filter_column].max()))
            )
            data = data[(data[filter_column] >= min_val) & (data[filter_column] <= max_val)]

# Display the data
st.subheader("Jail Roster Data")

# Status information
col1, col2, col3 = st.columns(3)

with col1:
    if last_modified:
        st.info(f"💾 Last Data Update: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("⚠️ No data update time available")

with col2:
    if data is not None:
        st.info(f"🔢 Records: {len(data)}")
    else:
        st.warning("⚠️ No records found")

with col3:
    if source_used:
        st.info(f"📂 Data Source: {source_used}")
    else:
        st.warning("⚠️ No data source available")

# Display the dataframe
if data is not None and not data.empty:
    st.dataframe(data)
    
    # Auto-detect date/timestamp columns
    date_columns = []
    for col in data.columns:
        if ('date' in col.lower() or 'time' in col.lower()) and data[col].dtype == 'object':
            # Try to convert to datetime to confirm it's a date/time column
            try:
                pd.to_datetime(data[col])
                date_columns.append(col)
            except:
                pass
    
    # If we have date columns, offer visualization options
    if date_columns:
        st.subheader("Visualizations")
        
        viz_col = st.selectbox("Select date/time column for visualization:", date_columns)
        
        if viz_col:
            # Convert to datetime for plotting
            data['plot_date'] = pd.to_datetime(data[viz_col], errors='coerce')
            
            # Drop NaT values that couldn't be converted
            plot_data = data.dropna(subset=['plot_date'])
            
            if not plot_data.empty:
                # Create a count by date
                date_counts = plot_data.groupby(plot_data['plot_date'].dt.date).size().reset_index()
                date_counts.columns = ['date', 'count']
                
                # Plot the data
                fig = px.bar(
                    date_counts, 
                    x='date', 
                    y='count',
                    title=f"Records by {viz_col}",
                    labels={'date': 'Date', 'count': 'Number of Records'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No valid dates found for visualization")
else:
    st.error("No data available to display")

# System status
st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")

# Check if scraper files exist
scraper_exists = Path("../scraper/main.py").exists()
db_exists = db_path.exists()
csv_exists = csv_path.exists() or get_latest_csv_file() is not None

status_items = {
    "Scraper": "✅ Available" if scraper_exists else "❌ Not found",
    "Database": f"✅ Found ({db_path.name})" if db_exists else "❌ Not found",
    "CSV Data": f"✅ Found" if csv_exists else "❌ Not found"
}

for item, status in status_items.items():
    st.sidebar.text(f"{item}: {status}")

# Basic refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# Dashboard info
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    """
    This dashboard displays data collected by the jail roster scraper.
    
    Refresh the page or click the Refresh Data button to update the data.
    
    For more information, see the README.md in the project repository.
    """
)

# Footer
st.markdown("---")
st.caption("Jail Roster Monitor Dashboard • Data automatically updates every 5 minutes")