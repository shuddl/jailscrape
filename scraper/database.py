import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Import local configuration
import config

# Get logger
logger = logging.getLogger(__name__)

def initialize_database():
    """
    Initialize the SQLite database and create the necessary tables if they don't exist.
    
    Creates a table to track processed inmates with:
    - name_number (primary key)
    - first_seen_timestamp
    - last_seen_timestamp
    - date_released (NULL until inmate is released)
    """
    try:
        # Ensure the parent directory exists
        Path(config.STATE_DB).parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_inmates (
            name_number TEXT PRIMARY KEY,
            first_seen_timestamp TEXT,
            last_seen_timestamp TEXT,
            date_released TEXT NULL
        )
        ''')
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized successfully at {config.STATE_DB}")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        return False

def is_inmate_processed(name_number: str) -> bool:
    """
    Check if an inmate has been processed before.
    
    Args:
        name_number: The unique name/booking number for the inmate
        
    Returns:
        bool: True if the inmate has been processed before, False otherwise
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Query for the name_number
        cursor.execute(
            "SELECT 1 FROM processed_inmates WHERE name_number = ?",
            (name_number,)
        )
        
        # Check if the query returned a result
        result = cursor.fetchone() is not None
        
        # Close the connection
        conn.close()
        
        return result
    except Exception as e:
        logger.error(f"Error checking if inmate {name_number} is processed: {str(e)}", exc_info=True)
        return False

def mark_inmate_processed(name_number: str):
    """
    Mark an inmate as processed in the database.
    
    Args:
        name_number: The unique name/booking number for the inmate
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the current timestamp
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Insert the inmate into the database, ignore if already exists
        cursor.execute(
            """
            INSERT OR IGNORE INTO processed_inmates 
            (name_number, first_seen_timestamp, last_seen_timestamp)
            VALUES (?, ?, ?)
            """,
            (name_number, timestamp, timestamp)
        )
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error marking inmate {name_number} as processed: {str(e)}", exc_info=True)
        return False

def update_last_seen(processed_ids: set[str]):
    """
    Update the last_seen_timestamp for inmates currently on the roster.
    
    Args:
        processed_ids: Set of name_number values for inmates seen in the current run
        
    Returns:
        int: Number of records updated
    """
    if not processed_ids:
        return 0
        
    try:
        # Get the current timestamp
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Convert the set to a tuple for SQL IN clause
        processed_ids_tuple = tuple(processed_ids)
        
        if len(processed_ids) == 1:
            # Special handling for single item (SQL syntax requires trailing comma)
            query = """
                UPDATE processed_inmates 
                SET last_seen_timestamp = ? 
                WHERE name_number = ?
            """
            cursor.execute(query, (timestamp, next(iter(processed_ids))))
        else:
            # Use IN clause for multiple items
            placeholders = ','.join(['?'] * len(processed_ids))
            query = f"""
                UPDATE processed_inmates 
                SET last_seen_timestamp = ? 
                WHERE name_number IN ({placeholders})
            """
            cursor.execute(query, (timestamp,) + processed_ids_tuple)
        
        # Get the number of rows updated
        updated_count = cursor.rowcount
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        logger.info(f"Updated last_seen_timestamp for {updated_count} inmates")
        return updated_count
    except Exception as e:
        logger.error(f"Error updating last_seen_timestamp: {str(e)}", exc_info=True)
        return 0

def find_released_inmates(current_ids_on_roster: set[str]):
    """
    Find inmates who are no longer on the roster and mark them as released.
    
    Args:
        current_ids_on_roster: Set of name_number values for inmates on the current roster
        
    Returns:
        list: List of name_numbers marked as released in this run
    """
    try:
        # Get the current timestamp
        timestamp = datetime.now().isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(config.STATE_DB)
        cursor = conn.cursor()
        
        # Find inmates in the database not in current_ids_on_roster and not yet marked as released
        cursor.execute(
            """
            SELECT name_number FROM processed_inmates 
            WHERE date_released IS NULL 
            AND name_number NOT IN ({})
            """.format(','.join(['?'] * len(current_ids_on_roster))),
            tuple(current_ids_on_roster)
        ) if current_ids_on_roster else cursor.execute(
            "SELECT name_number FROM processed_inmates WHERE date_released IS NULL"
        )
        
        # Get the list of released inmates
        released_inmates = [row[0] for row in cursor.fetchall()]
        
        # Update the date_released field for these inmates
        if released_inmates:
            placeholders = ','.join(['?'] * len(released_inmates))
            cursor.execute(
                f"""
                UPDATE processed_inmates 
                SET date_released = ? 
                WHERE name_number IN ({placeholders})
                """,
                (timestamp,) + tuple(released_inmates)
            )
            
            logger.info(f"Marked {len(released_inmates)} inmates as released")
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        return released_inmates
    except Exception as e:
        logger.error(f"Error finding released inmates: {str(e)}", exc_info=True)
        return []