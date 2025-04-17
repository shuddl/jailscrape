#!/usr/bin/env python3
"""
Demo Data Generator for Jail Roster Scraper Dashboard

This script generates sample data for demonstrating the dashboard functionality
without needing to run the actual scraper. It creates:
1. A sample SQLite database with inmate records
2. A sample CSV file with inmate data
"""

import os
import sys
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add the repository root to Python path
repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root))

# Create directories if they don't exist
demo_data_dir = repo_root / "dashboard" / "demo_data"
demo_data_dir.mkdir(exist_ok=True)

# Sample data generation parameters
NUM_RECORDS = 250
START_DATE = datetime.now() - timedelta(days=30)
END_DATE = datetime.now()

# Sample names
FIRST_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Jessica",
    "William", "Jennifer", "James", "Amanda", "Charles", "Elizabeth", "Thomas",
    "Mary", "Daniel", "Patricia", "Matthew", "Linda", "Donald", "Barbara",
    "Steven", "Susan", "Paul", "Margaret", "Andrew", "Kelly", "Joshua", "Nancy"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis",
    "Lee", "Walker", "Hall", "Allen", "Young", "King", "Wright"
]

CHARGES = [
    "Driving Under the Influence",
    "Possession of Controlled Substance",
    "Public Intoxication",
    "Disorderly Conduct",
    "Theft Under $500",
    "Criminal Trespass",
    "Assault",
    "Burglary",
    "Criminal Mischief",
    "Resisting Arrest",
    "Driving With License Invalid",
    "Failure to Appear",
    "Violation of Probation",
    "Criminal Mischief",
    "Domestic Violence",
    "Unlawful Carrying Weapon"
]

def random_date(start, end):
    """Generate a random datetime between start and end"""
    # Handle case where start and end are the same or very close
    if start >= end:
        return start
        
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    
    # Ensure we have at least one second difference
    if int_delta <= 0:
        return start
        
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)

def generate_inmate_data():
    """Generate random inmate data"""
    inmates = []
    
    for i in range(NUM_RECORDS):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        booking_date = random_date(START_DATE, END_DATE)
        
        # Some inmates will be released, others still in custody
        released = random.random() > 0.4
        release_date = None
        if released:
            min_stay = booking_date + timedelta(hours=4)
            max_stay = min(booking_date + timedelta(days=10), END_DATE)
            release_date = random_date(min_stay, max_stay)
        
        # Generate between 1 and 3 charges for each inmate
        num_charges = random.randint(1, 3)
        charges = random.sample(CHARGES, num_charges)
        charge_str = "; ".join(charges)
        
        # Create inmate record
        inmate = {
            'inmate_id': f"{10000 + i}",
            'booking_number': f"BK-{2023}-{10000 + i}",
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f"{first_name} {last_name}",
            'gender': random.choice(['Male', 'Female']),
            'race': random.choice(['White', 'Black', 'Hispanic', 'Asian', 'Other']),
            'booking_date': booking_date.strftime('%Y-%m-%d %H:%M:%S'),
            'release_date': release_date.strftime('%Y-%m-%d %H:%M:%S') if release_date else None,
            'in_custody': not released,
            'charges': charge_str,
            'bond_amount': random.choice([None, 500, 1000, 2000, 5000, 10000, 15000, 25000]),
            'first_seen_timestamp': booking_date.strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'jurisdiction': 'DEMO COUNTY',
            'state': 'TX'
        }
        inmates.append(inmate)
    
    return inmates

def create_database(inmates):
    """Create SQLite database with inmate records"""
    db_path = demo_data_dir / "demo_inmates.db"
    
    # Connect to the database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_inmates (
        inmate_id TEXT PRIMARY KEY,
        booking_number TEXT,
        first_name TEXT,
        last_name TEXT,
        full_name TEXT,
        gender TEXT,
        race TEXT,
        booking_date TEXT,
        release_date TEXT,
        in_custody BOOLEAN,
        charges TEXT,
        bond_amount REAL,
        first_seen_timestamp TEXT,
        last_updated TEXT,
        jurisdiction TEXT,
        state TEXT
    )
    ''')
    
    # Insert data
    for inmate in inmates:
        cursor.execute('''
        INSERT OR REPLACE INTO processed_inmates VALUES (
            :inmate_id, :booking_number, :first_name, :last_name, :full_name,
            :gender, :race, :booking_date, :release_date, :in_custody,
            :charges, :bond_amount, :first_seen_timestamp, :last_updated,
            :jurisdiction, :state
        )
        ''', inmate)
    
    # Commit and close
    conn.commit()
    conn.close()
    
    return db_path

def create_csv(inmates):
    """Create CSV file with inmate records"""
    csv_path = demo_data_dir / "demo_inmates.csv"
    
    # Convert to dataframe and save as CSV
    df = pd.DataFrame(inmates)
    df.to_csv(csv_path, index=False)
    
    return csv_path

def create_env_file():
    """Create .env file pointing to demo data"""
    env_path = repo_root / "dashboard" / ".env"
    
    env_content = f"""
# Demo environment configuration
STATE_DB={demo_data_dir / "demo_inmates.db"}
OUTPUT_CSV={demo_data_dir / "demo_inmates.csv"}
ROSTER_URL=https://example.com/demo-jail-roster
    """
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    return env_path

def main():
    """Main function to generate all demo data"""
    print("Generating demo data for Jail Roster Dashboard...")
    
    # Generate inmate data
    inmates = generate_inmate_data()
    print(f"Generated {len(inmates)} inmate records")
    
    # Create database
    db_path = create_database(inmates)
    print(f"Created demo database at {db_path}")
    
    # Create CSV
    csv_path = create_csv(inmates)
    print(f"Created demo CSV at {csv_path}")
    
    # Create .env file
    env_path = create_env_file()
    print(f"Created demo .env file at {env_path}")
    
    # Create a metadata file to document when this was generated
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "record_count": len(inmates),
        "date_range": {
            "start": START_DATE.isoformat(),
            "end": END_DATE.isoformat()
        }
    }
    
    with open(demo_data_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\nDemo data generation complete!")
    print("To use this data in the dashboard, make sure the paths are correctly configured.")

if __name__ == "__main__":
    main()