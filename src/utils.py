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
import mutagen
import mutagen.flac
from tqdm import tqdm
import csv


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
    """
    Convert a SQLite database to a CSV file.

    Args:
        sqlite_db (str): Path to the SQLite database file
        csv_file (str): Path to the CSV file to write

    Returns:
        None
    """
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

def find_files_with_empty_tags(search_dir):
    empty_tag_files = []
    corrupt_files = []
    flac_files = []

    # First, obtain the list of all FLAC files
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.endswith('.flac'):
                flac_files.append(os.path.join(root, file))

    print(f"Scanning {len(flac_files)} FLAC files...")

    # Iterate over the list of FLAC files with a single progress bar
    for file_path in tqdm(flac_files):
        try:
            audio_file = mutagen.flac.FLAC(file_path)
            if any(tag_value == [''] for tag_value in audio_file.tags.values()):
                empty_tag_files.append(file_path)
        except mutagen.flac.error as e:
            print(f"Corrupt file: {file_path} - {e}")
            corrupt_files.append(file_path)

    print(f"Completed!")
    print(f"Found {len(empty_tag_files)} files with empty tags")
    print(f"Found {len(corrupt_files)} corrupt files")

    # Write the list of files to empty_tags.csv
    with open('empty_tags.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(empty_tag_files):
            writer.writerow([file_path])

    # Write the list of corrupt files to corrupt_files.csv
    with open('corrupt_files.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in corrupt_files:
            writer.writerow([file_path])

    return

def remove_empty_tags():
    """
    Function to remove empty tags. That is, the tag is present but has no value.
    In conjunction with find_empty_tags function, used to retroactively fix improper tags 
    created by an issue that was fixed in commit 1555c62.
    
    Args:
        None (reads a list of files with empty tags from empty_tags.csv)

    Returns:
        None (writes a list of successes and failures to success.csv and failure.csv)
    
    """
    successful_paths = []
    failed_paths = []

    with open('empty_tags.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        files = list(reader)

    print(f"Removing empty tags from {len(files)} files...")

    for file_path in tqdm(files):
        try:
            audio_file = mutagen.flac.FLAC(file_path[0])
            # Extract the comment block
            tags_to_keep = {tag: value for tag, value in audio_file.tags.items() if value != ['']}
            # Delete all tags
            audio_file.delete()
            # Write new comment block with non-empty tags
            for tag, value in tags_to_keep.items():
                audio_file[tag] = value
            audio_file.save()
            successful_paths.append(file_path)
        except Exception as e:
            failed_paths.append(file_path)

    print(f"Completed!")
    print(f"Successfully processed: {len(successful_paths)} files")
    print(f"Failed: {len(failed_paths)} files")

    with open('success.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(successful_paths):
            writer.writerow([file_path])

    with open('failure.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(failed_paths):
            writer.writerow([file_path])  