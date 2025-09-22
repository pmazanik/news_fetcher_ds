import json
import os
from datetime import datetime
from typing import List, Dict
import logging

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_output_directory(directory: str):
    """Create output directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logging.info(f"Saved {len(data)} articles to {filename}")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")

def generate_filename(source_name: str) -> str:
    """Generate filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{source_name.lower()}_news_{timestamp}.json"
