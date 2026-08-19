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
    with open('empty_tags.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(empty_tag_files):
            writer.writerow([file_path])

    # Write the list of corrupt files to corrupt_files.csv
    with open('corrupt_files.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
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

    with open('empty_tags.csv', 'r', encoding='utf-8-sig') as csvfile:
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

    with open('success.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(successful_paths):
            writer.writerow([file_path])

    with open('failure.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        for file_path in sorted(failed_paths):
            writer.writerow([file_path])  
