################################################################################
### structure.py
### Copyright (c) 2025, Joshua J Hamilton
### This utility program rearranges the directory structure of a collection of
### audio files. It organizes files into the following structure:
### ALBUM
###    Disc #
###        Track.flac
###        Album.log
###        Album.cue
###    Scans.pdf
### If there is only one disc, the structure is:
### ALBUM
###    Track.flac
###    Album.log
###    Album.cue
###    Scans.pdf
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import csv
import os
import re
import sys

from PIL import Image # 1: convert images to jpg
from fpdf import FPDF # 2: create a PDF from images
from pypdf import PdfWriter # 3: merge PDFs
from tqdm import tqdm

## Temporary fix while developing. Will be removed when the project is made into a package.
# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import setup_logging

################################################################################
### Define functions for creating Scans.pdf
################################################################################

def collect_files(directory, valid_extensions):
    """
    Collect image and PDF files from the directory.

    Args:
        directory (str): Path to the directory.
        valid_extensions (set): Set of valid file extensions.

    Returns:
        tuple: Lists of image files and PDF files.
    """
    image_files = []
    pdf_files = []

    for root, _, files in os.walk(directory):
        for file in sorted(files):
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                file_path = os.path.join(root, file)
                if ext == '.pdf':
                    pdf_files.append(file_path)
                else:
                    image_files.append(file_path)

    return image_files, pdf_files


def create_image_pdf(image_files, temp_image_pdf, logger):
    """
    Create a temporary PDF from image files.

    Args:
        image_files (list): List of image file paths.
        temp_image_pdf (str): Path to the temporary PDF file.
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    pdf = FPDF(unit="pt")
    for image_file in image_files:
        try:
            image = Image.open(image_file)

            # Convert unsupported formats to RGB JPEG
            if image.format not in ['JPEG', 'PNG', 'GIF']:
                image = image.convert(mode="RGB")
                temp_image_path = os.path.splitext(image_file)[0] + ".jpg"
                image.save(temp_image_path, format="JPEG")
                image_file = temp_image_path  # Use the converted file

            # Get image dimensions in points (1 point = 1/72 inch)
            width, height = image.size
            width_pt = width * 72 / image.info.get("dpi", (72, 72))[0]
            height_pt = height * 72 / image.info.get("dpi", (72, 72))[1]

            # Add a page with the exact dimensions of the image
            pdf.add_page(format=(width_pt, height_pt))
            pdf.image(image_file, x=0, y=0, w=width_pt, h=height_pt)
        except Exception as e:
            logger.error(f"Error processing image {image_file}: {e}")
    pdf.output(temp_image_pdf)


def merge_pdfs(pdf_files, output_path, logger):
    """
    Merge all PDFs into a single file.

    Args:
        pdf_files (list): List of PDF file paths.
        output_path (str): Path to the output PDF file.
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    writer = PdfWriter()
    for pdf_file in pdf_files:
        try:
            with open(pdf_file, "rb") as f:
                writer.append(f)
        except Exception as e:
            logger.error(f"Error merging PDF {pdf_file}: {e}")
    with open(output_path, "wb") as f:
        writer.write(f)


def delete_original_files(files, logger):
    """
    Delete original files.

    Args:
        files (list): List of file paths to delete.
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    for file in files:
        if os.path.basename(file).lower() == "scans.pdf":
            logger.info(f"Skipping deletion of {file}")
            continue
        try:
            os.remove(file)
            logger.info(f"Deleted: {file}")
        except Exception as e:
            logger.error(f"Error deleting file {file}: {e}")

def create_scans(subdirectory_path, dry_run, writer, logger):
    valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.svg', '.pdf'}
    image_files, pdf_files = collect_files(subdirectory_path, valid_extensions)

    if not image_files and not pdf_files:
        logger.warning(f"No image or PDF files found in {subdirectory_path}.")
        return

    if dry_run:
        logger.info(f"Dry run: The following files would be included in Scans.pdf for {subdirectory_path}:")
        for file in image_files + pdf_files:
            logger.info(f"  - {file}")
            writer.writerow([subdirectory_path, file])
        return

    temp_image_pdf = os.path.join(subdirectory_path, "temp_images.pdf")
    if image_files:
        create_image_pdf(image_files, temp_image_pdf, logger)
        pdf_files.insert(0, temp_image_pdf)

    output_path = os.path.join(subdirectory_path, "Scans.pdf")
    merge_pdfs(pdf_files, output_path, logger)

    if os.path.exists(temp_image_pdf):
        os.remove(temp_image_pdf)

    delete_original_files(image_files + pdf_files, logger)
    logger.info(f"Scans.pdf created at: {output_path}")


################################################################################
### Define functions for renaming "Disc" folders
################################################################################

def identify_and_map_disc_folders(directory, logger):
    """
    Identify disc folders and map them to new names in the format 'Disc #'.

    Args:
        directory (str): Path to the directory containing potential disc folders.
        logger (logging.Logger): Logger object.

    Returns:
        list: A list of tuples containing the original folder path and revised folder name.
    """
    disc_folders = []
    non_disc_folders = []

    # Regex to identify potential disc folder names
    disc_name_patterns = [
        r'cd\s*(\d+)',   # Matches "CD 1", "CD01", etc., capturing the number
        r'disc\s*(\d+)', # Matches "Disc 1", "Disc01", etc., capturing the number
        r'disk\s*(\d+)', # Matches "Disk 1", "Disk01", etc., capturing the number
        r'(\d+)$',       # Matches names ending with numbers, capturing the number
    ]

    # Supported audio file extensions
    audio_extensions = {'.flac', '.ape', '.wv', '.wav', '.iso', '.m4a'}

    # Walk through the directory to identify folders
    for folder_name in sorted(os.listdir(directory)):
        folder_path = os.path.join(directory, folder_name)
        if os.path.isdir(folder_path):
            # Check if the folder contains .flac files
            contains_audio = any(file.lower().endswith(ext) for ext in audio_extensions for file in os.listdir(folder_path))
            if contains_audio:
                # Extract disc number if the folder name matches any disc name pattern
                disc_number = None
                for pattern in disc_name_patterns:
                    match = re.search(pattern, folder_name, re.IGNORECASE) # Match case-insensitively
                    if match:
                        disc_number = int(match.group(1))  # Extract the captured number
                        break

                if disc_number is not None:
                    disc_folders.append((disc_number, folder_name))
                else:
                    logger.warning(f"Folder '{folder_name}' contains .flac files but does not match disc patterns.")
                    disc_folders.append((float('inf'), folder_name))  # Assign a high number for sorting
            else:
                non_disc_folders.append(folder_name)

    # Sort disc folders by their extracted disc number
    disc_folders.sort(key=lambda x: x[0])

    # Determine the number of digits for padding
    max_disc_number = len(disc_folders)
    digit_padding = len(str(max_disc_number))

    # Map original folder names to new names
    folder_mappings = []
    for index, (_, folder_name) in enumerate(disc_folders, start=1):
        new_name = f"Disc {str(index).zfill(digit_padding)}"
        folder_mappings.append((os.path.join(directory, folder_name), new_name))

    # Log non-disc folders for reference
    if non_disc_folders:
        logger.info(f"Non-disc folders identified in {directory}: {non_disc_folders}")

    return folder_mappings


def rename_disc_folders(subdirectory_path, dry_run, writer, logger):
    mappings = identify_and_map_disc_folders(subdirectory_path, logger)

    for original_path, new_name in mappings:
        if dry_run:
            logger.info(f"Dry run: Would rename {original_path} to {new_name}")
            writer.writerow([original_path, new_name])
        else:
            new_path = os.path.join(os.path.dirname(original_path), new_name)
            try:
                os.rename(original_path, new_path)
                logger.info(f"Renamed: {original_path} -> {new_path}")
                writer.writerow([original_path, new_name])
            except Exception as e:
                logger.error(f"Error renaming {original_path} to {new_path}: {e}")


################################################################################
### Define functions for removing miscellaneous files
################################################################################

def cleanup_directory(subdirectory_path, dry_run, writer, logger):
    """
    Removes miscellaneous files and empty directories within the given subdirectory.

    Args:
        subdirectory_path (str): Path to the subdirectory to clean up.
        dry_run (bool): If True, logs the actions without making changes.
        writer (csv.writer): CSV writer object for logging actions.
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    # Define the set of file extensions to keep
    files_to_keep = {".pdf", ".log", ".cue", ".flac", ".ape", ".wv", ".wav"}

    # Remove miscellaneous files
    for root, _, files in os.walk(subdirectory_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not any(file.lower().endswith(ext) for ext in files_to_keep):
                if dry_run:
                    logger.info(f"Dry run: Would delete {file_path}")
                    writer.writerow([file_path])
                else:
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted: {file_path}")
                        writer.writerow([file_path])
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")

    # Remove empty directories
    for root, dirs, _ in os.walk(subdirectory_path, topdown=False):  # Process subdirectories first
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):  # Check if the directory is empty
                if dry_run:
                    logger.info(f"Dry run: Would remove empty directory {dir_path}")
                    writer.writerow([dir_path])
                else:
                    try:
                        os.rmdir(dir_path)
                        logger.info(f"Removed empty directory: {dir_path}")
                        writer.writerow([dir_path])
                    except Exception as e:
                        logger.error(f"Error removing directory {dir_path}: {e}")

################################################################################
### Define main function
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Utility script for organizing audio files.")
    parser.add_argument('--dir', required=True, help="Path to the root directory to process.")
    parser.add_argument('--mode', required=True, choices=['make_scans', 'rename_dirs', 'cleanup', 'all'],
                        help="Mode of operation: make_scans, rename_dirs, cleanup, or all.")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without making changes.")
    parser.add_argument('--output-csv', help="Path to the output CSV file (default: output.csv).")
    args = parser.parse_args()

    # Set up logging in the root project directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    logger = setup_logging(root_dir)

    if not os.path.isdir(args.dir):
        print(f"Error: The directory '{args.dir}' does not exist.")
        return

    # Set default output CSV path if not provided
    output_csv = args.output_csv or os.path.join(args.dir, "output.csv")

    # Get the list of subdirectories
    subdirectories = [os.path.join(args.dir, subdirectory) for subdirectory in sorted(os.listdir(args.dir)) if os.path.isdir(os.path.join(args.dir, subdirectory))]

    # Open the CSV file for writing
    with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        # Process based on the selected mode
        if args.mode in ['make_scans', 'all']:
            writer.writerow(["Mode: make_scans"])
            writer.writerow(["Directory", "Included Files"])
            for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories for Scans.pdf"):
                create_scans(subdirectory_path, args.dry_run, writer, logger)
            writer.writerow([])  # Add a blank line between modes

        if args.mode in ['rename_dirs', 'all']:
            writer.writerow(["Mode: rename_dirs"])
            writer.writerow(["Original Folder Path", "Revised Folder Name"])
            for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories for renaming"):
                rename_disc_folders(subdirectory_path, args.dry_run, writer, logger)
            writer.writerow([])  # Add a blank line between modes

        if args.mode in ['cleanup', 'all']:
            writer.writerow(["Mode: cleanup"])
            writer.writerow(["Deleted Files"])
            for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories for cleanup"):
                cleanup_directory(subdirectory_path, args.dry_run, writer, logger)
            writer.writerow([])  # Add a blank line between modes

    print(f"Processing complete. Output written to {output_csv}.")

if __name__ == "__main__":
    main()