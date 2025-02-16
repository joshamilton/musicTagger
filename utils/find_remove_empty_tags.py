################################################################################
### find_remove_empty_tags.py
### Copyright (c) 2025, Joshua J Hamilton
### This utility program finds and removes empty tags from FLAC files. Due to
### an error in the write.py script, some tags were written with empty values 
### (e.g., ''). This script scans a directory for FLAC files and identifies such
### files. It then removes the empty tags from the files using the optional
### --remove flag.
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import os
import mutagen
import mutagen.flac
from tqdm import tqdm
import csv

################################################################################
### Function definitions
################################################################################

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

def remove_empty_tags(files):
    successful_paths = []
    failed_paths = []

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and remove empty tags from FLAC files")
    parser.add_argument('dir', help="Directory to search for FLAC files")
    parser.add_argument('--dry-run', action='store_true', help="Generate a report without making changes")
    args = parser.parse_args()

    empty_tag_files = find_files_with_empty_tags(args.dir)

    if not args.dry_run:
        remove_empty_tags(empty_tag_files)