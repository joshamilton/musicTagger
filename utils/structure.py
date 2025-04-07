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
import os
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
### Define functions
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
        try:
            os.remove(file)
            logger.info(f"Deleted: {file}")
        except Exception as e:
            logger.error(f"Error deleting file {file}: {e}")

def create_scans(directory, delete_scan_files=False, logger=None):
    """
    Combines all image and PDF files in the folder into a single PDF named Scans.pdf.
    Optionally deletes the original files after creating the PDF.

    Args:
        directory (str): Path to the directory.
        delete_originals (bool): Whether to delete original files.

    Returns:
        None
    """

    valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.svg', '.pdf'}

    logger.info(f"Starting processing for directory: {directory}")
    image_files, pdf_files = collect_files(directory, valid_extensions)

    if not image_files and not pdf_files:
        logger.warning("No image or PDF files found.")
        return

    # Create a temporary PDF for images
    temp_image_pdf = os.path.join(directory, "temp_images.pdf")
    if image_files:
        create_image_pdf(image_files, temp_image_pdf, logger)
        pdf_files.insert(0, temp_image_pdf)  # Add the image PDF to the list of PDFs

    # Merge all PDFs
    output_path = os.path.join(directory, "Scans.pdf")
    merge_pdfs(pdf_files, output_path, logger)

    # Clean up temporary image PDF
    if os.path.exists(temp_image_pdf):
        os.remove(temp_image_pdf)

    # Optionally delete original files
    if delete_scan_files:
        delete_original_files(image_files + pdf_files, logger)

    logger.info(f"Scans.pdf created at: {output_path}")

def remove_misc_files(directory, files_to_keep, logger):
    """
    Remove all files in the directory that do not match the specified extensions.

    Args:
        directory (str): Path to the directory to clean.
        files_to_keep (set): Set of file extensions to keep (e.g., {".pdf", ".log"}).
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if not any(file.lower().endswith(ext) for ext in files_to_keep):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
    logger.info("Removed all miscellaneous files.")

def remove_empty_dirs(directory, logger):
    """
    Recursively removes all empty directories within the given directory.
    """
    for root, dirs, _ in os.walk(directory, topdown=False):  # Process subdirectories first
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):  # Check if the directory is empty
                os.rmdir(dir_path)
                logger.info(f"Removed empty directory: {dir_path}")

################################################################################
### Define main function
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Combine image and PDF files into a single Scans.pdf.")
    parser.add_argument('--dir', required=True, help="Path to the directory containing image and PDF files.")
    parser.add_argument('--delete_scan', action='store_true', help="Delete original files after creating Scans.pdf.")
    parser.add_argument('--delete_misc', action='store_true', help="Delete other unnecessary files.")
    
    args = parser.parse_args()

    # Set up logging in the root project directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    logger = setup_logging(root_dir)

    if not os.path.isdir(args.dir):
        print(f"Error: The directory '{args.dir}' does not exist.")
        return

    # Get the list of subdirectories
    subdirectories = [os.path.join(args.dir, subdirectory) for subdirectory in sorted(os.listdir(args.dir)) if os.path.isdir(os.path.join(args.dir, subdirectory))]

    # Process each subdirectory with a progress bar
    for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories"):
        create_scans(subdirectory_path, delete_scan_files=args.delete_scan, logger=logger)

    # Remove all non-essential files if --delete_misc is specified
    if args.delete_misc:
        files_to_keep = {".pdf", ".log", ".cue", ".flac"}
        remove_misc_files(args.dir, files_to_keep, logger)
    
    # Remove any empty directories
    remove_empty_dirs(args.dir, logger)
    print("Removed all empty directories.")

if __name__ == "__main__":
    main()