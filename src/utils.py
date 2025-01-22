################################################################################
### utils.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import os
import logging
from datetime import datetime
import json
import sqlite3
import pandas as pd

################################################################################
### Define functions
################################################################################

def setup_logging(path_to_run_data):
    """
    Set up logging to a file.

    Args:
        path_to_run_data (str): Path to the run data directory

    Returns:
        logging.Logger: Configured logger object
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(path_to_run_data, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'{timestamp}.log')

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file)
        ]
    )

    return logging.getLogger(__name__)

def sqlite_to_csv(sqlite_db, csv_file):
    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db)
    cursor = conn.cursor()

    # Query to get all filenames
    cursor.execute('SELECT id, filepath FROM filename')
    filenames = cursor.fetchall()

    # Initialize a dictionary to store the data
    data = {}

    # Fetch original tags
    cursor.execute('SELECT filename_id, tag_key, tag_value FROM original_tags')
    for row in cursor.fetchall():
        filename_id, tag_key, tag_value = row
        if filename_id not in data:
            data[filename_id] = {}
        data[filename_id][f'original_{tag_key}'] = tag_value

    # Fetch updated tags
    cursor.execute('SELECT filename_id, tag_key, tag_value FROM updated_tags')
    for row in cursor.fetchall():
        filename_id, tag_key, tag_value = row
        if filename_id not in data:
            data[filename_id] = {}
        data[filename_id][f'updated_{tag_key}'] = tag_value

    # Create a DataFrame from the data
    rows = []
    for filename_id, tags in data.items():
        row = {'filename': next(filepath for id, filepath in filenames if id == filename_id)}
        row.update(tags)
        rows.append(row)

    result_df = pd.DataFrame(rows)

    # Rearrange columns to be in the specified order
    columns_order = [
        'filename', 'updated_composer', 'updated_album', 'updated_year recorded', 'updated_orchestra',
        'updated_conductor', 'updated_soloists', 'updated_arranger', 'updated_genre', 'updated_discnumber',
        'updated_tracknumber', 'updated_title', 'updated_tracktitle', 'updated_work', 'updated_work number',
        'updated_initialkey', 'updated_catalog #', 'updated_opus', 'updated_opus number', 'updated_epithet', 
        'updated_movement'
    ]
    # Add any remaining columns that are not in the specified order
    remaining_columns = [col for col in result_df.columns if col not in columns_order]
    result_df = result_df[columns_order + remaining_columns]

    # Write to CSV
    result_df.to_csv(csv_file, index=False)

    # Close the connection
    conn.close()
    print('Data successfully written to CSV file')