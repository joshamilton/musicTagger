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
import subprocess
import tempfile
from datetime import datetime
import json
import pandas as pd
import mutagen
import mutagen.flac
from mutagen.flac import FLAC
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

def find_flac_files(search_dir):
    """
    Recursively find FLAC files under a directory, showing progress as they're found.

    Args:
        search_dir (str): Directory to search for FLAC files.

    Returns:
        list: Sorted paths of files ending in '.flac' (case-insensitive).
    """
    flac_files = []
    with tqdm(desc="Finding FLAC files", unit="file") as pbar:
        for dirpath, _, filenames in os.walk(search_dir):
            for file in filenames:
                if file.lower().endswith('.flac'):
                    flac_files.append(os.path.join(dirpath, file))
                    pbar.update(1)
    return sorted(flac_files)

MISSING_CHECKSUM_MD5 = '0' * 32

def get_audio_md5(audio):
    """
    Get the FLAC STREAMINFO audio checksum as a hex string.

    This is the MD5 of the decoded audio samples, computed by the encoder
    and stored in the file. It is unaffected by tag edits or renames, and
    only changes if the audio itself is re-encoded.

    Args:
        audio (mutagen.flac.FLAC): An open FLAC file.

    Returns:
        str: 32-character hex string.
    """
    return f"{audio.info.md5_signature:032x}"

def is_missing_checksum(audio_md5):
    """Check whether an audio checksum is the all-zero value some encoders leave behind instead of computing one."""
    return audio_md5 == MISSING_CHECKSUM_MD5

def repair_missing_checksum(path):
    """
    Compute the real audio checksum for a file whose STREAMINFO checksum was
    never computed (left as all zeros), and write it back into the file's
    own STREAMINFO block.

    Decodes and re-encodes the file through sox into a throwaway temporary
    file, purely so sox's encoder computes a correct MD5 of the decoded
    audio. This has to be a real, seekable file rather than a pipe: the
    encoder writes the STREAMINFO header before it knows the checksum, then
    seeks back to patch it in once encoding finishes, which it cannot do on
    a non-seekable stream (confirmed by testing: piping sox's FLAC output
    to stdout leaves the checksum missing). Reads the computed checksum
    back via mutagen, deletes the temp file, then patches only the
    STREAMINFO md5_signature field of the original file and saves it. sox
    is given no rate/bit-depth flags, so this is a lossless pass-through;
    the original file's compressed audio bytes and tags are never touched
    by sox, only by the mutagen write below.

    Args:
        path (str): Path to a FLAC file with a missing audio checksum.

    Returns:
        tuple: (new_md5, error)
            new_md5 (str or None): 32-character hex checksum on success,
                else None.
            error (str or None): Reason repair failed, else None.
    """
    directory = os.path.dirname(path) or '.'
    temp_fd, temp_path = tempfile.mkstemp(prefix='.flac-repair-', suffix='.tmp', dir=directory)
    os.close(temp_fd)
    os.remove(temp_path)  # reserve a unique name; sox needs to write a fresh file, not overwrite one

    try:
        command = ['sox', path, '-t', 'flac', temp_path]
        try:
            result = subprocess.run(command, capture_output=True)
        except OSError as e:
            return None, f"could not run sox: {e}"

        stderr = result.stderr.decode('utf-8', errors='replace').strip()
        if result.returncode != 0:
            return None, stderr or f"sox exited with code {result.returncode}"
        if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
            return None, stderr or "sox produced no output file"

        try:
            new_md5 = get_audio_md5(FLAC(temp_path))
        except Exception as e:
            return None, f"could not read checksum from re-encoded audio: {e}"

        if is_missing_checksum(new_md5):
            return None, "re-encoded audio also produced a missing (all-zero) checksum"

        try:
            original = FLAC(path)
            original.info.md5_signature = int(new_md5, 16)
            original.save()
        except Exception as e:
            return None, f"computed checksum but could not write it back to the file: {e}"

        return new_md5, None
    finally:
        if os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

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
