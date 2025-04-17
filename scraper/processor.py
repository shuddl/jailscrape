import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Import local configuration
import config

# Get logger
logger = logging.getLogger(__name__)

def structure_inmate_data(detail_data: Dict) -> Dict:
    """
    Structure and clean raw inmate data for output.
    
    Args:
        detail_data: Raw dictionary from scrape_inmate_details
        
    Returns:
        dict: Structured and cleaned data ready for CSV output
    """
    # Create a copy to avoid modifying the original
    structured_data = detail_data.copy()
    
    try:
        # Process address into components if it's a combined field
        if "address" in structured_data and structured_data["address"]:
            address = structured_data["address"]
            
            # Try to parse address if city/state/zip are not already separate fields
            if not (structured_data.get("city") and structured_data.get("state") and structured_data.get("zip")):
                try:
                    # Look for patterns like "123 Main St, Houston, TX 77001"
                    # Or "123 Main St\nHouston, TX 77001"
                    address = address.replace("\n", ", ")
                    parts = address.split(",")
                    
                    if len(parts) >= 3:  # Full address with street, city, state/zip
                        structured_data["street_address"] = parts[0].strip()
                        structured_data["city"] = parts[1].strip()
                        
                        # Handle "State Zip" in the last part
                        state_zip = parts[2].strip().split()
                        if len(state_zip) >= 2:
                            structured_data["state"] = state_zip[0].strip()
                            structured_data["zip"] = state_zip[-1].strip()
                    elif len(parts) == 2:  # Maybe just street and city/state/zip
                        structured_data["street_address"] = parts[0].strip()
                        
                        # Try to parse city, state, zip from second part
                        location = parts[1].strip()
                        city_state_zip_match = re.search(r"([^,]+),?\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", location)
                        if city_state_zip_match:
                            structured_data["city"] = city_state_zip_match.group(1).strip()
                            structured_data["state"] = city_state_zip_match.group(2).strip()
                            structured_data["zip"] = city_state_zip_match.group(3).strip()
                    else:
                        # Couldn't parse effectively, just keep the full address
                        structured_data["street_address"] = address
                except Exception as parse_error:
                    logger.warning(f"Error parsing address: {str(parse_error)}")
                    structured_data["street_address"] = address
        
        # Count charges
        if "charges" in structured_data and isinstance(structured_data["charges"], list):
            structured_data["number_of_charges"] = len(structured_data["charges"])
        else:
            structured_data["number_of_charges"] = 0
        
        # Add scrape timestamp if not present
        if "scrape_timestamp_utc" not in structured_data:
            structured_data["scrape_timestamp_utc"] = datetime.utcnow().isoformat()
        
        # Ensure all required fields exist with defaults
        required_fields = [
            "dob", "street_address", "city", "state", "zip", 
            "number_of_charges", "scrape_timestamp_utc"
        ]
        
        for field in required_fields:
            if field not in structured_data or structured_data[field] is None:
                structured_data[field] = ""
        
        return structured_data
        
    except Exception as e:
        logger.error(f"Error structuring inmate data: {str(e)}", exc_info=True)
        # Return the original data if processing fails
        return detail_data

def get_output_csv_path() -> Path:
    """
    Generate the output CSV path based on current date.
    
    Returns:
        Path: The full path to the output CSV file
    """
    try:
        # Ensure output directory exists
        output_dir = Path(config.OUTPUT_CSV).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use provided path from config if it exists
        if config.OUTPUT_CSV:
            return Path(config.OUTPUT_CSV)
        
        # Otherwise generate a dated filename
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"mctx_new_inmates_{today}.csv"
        
        # Use the output directory from config or default to data/
        output_path = output_dir / filename
        
        logger.info(f"Generated output path: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating output path: {str(e)}", exc_info=True)
        # Return a default path if there's an error
        return Path("data/inmates_output.csv")

def write_to_csv(records: List[Dict], output_path: Path = None) -> bool:
    """
    Write inmate records to a CSV file.
    
    Args:
        records: List of structured inmate data dictionaries
        output_path: Optional path override (defaults to config path)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not records:
        logger.warning("No records to write")
        return False
    
    try:
        # Get output path if not provided
        if output_path is None:
            output_path = get_output_csv_path()
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Process records to flatten charge data
        flattened_records = []
        for record in records:
            # Structure and clean the data
            structured_record = structure_inmate_data(record)
            
            # Create a flattened version (without nested lists)
            flat_record = {k: v for k, v in structured_record.items() if k != "charges"}
            
            # Add charge info if available (taking first charge for simplicity)
            if "charges" in structured_record and structured_record["charges"]:
                # Add all charges as a flat structure
                for i, charge in enumerate(structured_record["charges"]):
                    # Only include the first few charges to avoid too many columns
                    if i < 3:  # Limit to 3 charges
                        for charge_key, charge_value in charge.items():
                            flat_record[f"charge{i+1}_{charge_key}"] = charge_value
            
            flattened_records.append(flat_record)
        
        # Get all possible field names from all records
        fieldnames = set()
        for record in flattened_records:
            fieldnames.update(record.keys())
        
        # Sort fieldnames for consistent output
        fieldnames = sorted(list(fieldnames))
        
        # Check if file exists to determine if we need to write headers
        file_exists = output_path.exists() and output_path.stat().st_size > 0
        
        with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Only write header if file is new or empty
            if not file_exists:
                writer.writeheader()
            
            # Write all records
            writer.writerows(flattened_records)
        
        logger.info(f"Successfully wrote {len(records)} records to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing to CSV: {str(e)}", exc_info=True)
        return False