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

import csv
import io
import math
import os
import re

from PIL import Image # 1: convert images to jpg
from fpdf import FPDF # 2: create a PDF from images
from pypdf import PdfReader, PdfWriter # 3: merge / inspect / rewrite PDFs
from tqdm import tqdm

from utils import setup_logging

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


SANE_DPI_MIN = 36
SANE_DPI_MAX = 1200
DEFAULT_DPI = 72


def sane_dpi(value):
    """
    Clamp a DPI value to a physically reasonable range.

    Some images (especially scans) carry bogus DPI metadata (e.g. 1) which,
    when used to compute PDF page dimensions, produces pages hundreds of
    inches wide. Treat anything outside the sane range as the default.

    Args:
        value: The reported DPI value (any type).

    Returns:
        tuple: (sane_value, was_clamped)
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_DPI, True
    if not math.isfinite(v) or v < SANE_DPI_MIN or v > SANE_DPI_MAX:
        return DEFAULT_DPI, True
    return v, False


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

            # Get image dimensions in points (1 point = 1/72 inch).
            # Clamp DPI to a sane range so bogus metadata (e.g. dpi=1)
            # doesn't blow page sizes up to hundreds of inches.
            width, height = image.size
            raw_dpi = image.info.get("dpi", (DEFAULT_DPI, DEFAULT_DPI))
            dpi_x, clamped_x = sane_dpi(raw_dpi[0])
            dpi_y, clamped_y = sane_dpi(raw_dpi[1])
            if clamped_x or clamped_y:
                logger.warning(
                    f"Clamped suspicious DPI {raw_dpi} to ({dpi_x}, {dpi_y}) for {image_file}"
                )
            width_pt = width * 72 / dpi_x
            height_pt = height * 72 / dpi_y

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
### Define functions for fixing oversized Scans.pdf files
################################################################################

# PDF coordinates are points (1 pt = 1/72 inch). 14400 pt = 200 in, which is
# also the historical PDF 1.x maximum page side. Anything larger is almost
# certainly the bogus-DPI bug from create_image_pdf and should be repaired.
OVERSIZE_LIMIT_PT = 14400


def find_oversized_pages(pdf_path):
    """
    Identify pages whose MediaBox is wider or taller than OVERSIZE_LIMIT_PT.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        list: Tuples of (page_index, width_pt, height_pt) for offending pages.
    """
    reader = PdfReader(pdf_path)
    oversized = []
    for index, page in enumerate(reader.pages):
        mb = page.mediabox
        width_pt = float(mb.width)
        height_pt = float(mb.height)
        if width_pt > OVERSIZE_LIMIT_PT or height_pt > OVERSIZE_LIMIT_PT:
            oversized.append((index, width_pt, height_pt))
    return oversized


def rebuild_oversized_page(page):
    """
    Extract the single embedded image from a page so it can be re-rendered
    onto a sanely-sized page.

    Args:
        page: A pypdf PageObject.

    Returns:
        tuple or None: (image_bytes, format, width_px, height_px) when the
        page contains exactly one embedded image; otherwise None.
    """
    try:
        images = list(page.images)
    except Exception:
        return None
    if len(images) != 1:
        return None
    image_file = images[0]
    pil = image_file.image
    width_px, height_px = pil.size
    fmt = (pil.format or "PNG").upper()
    if fmt == "JPEG":
        save_kwargs = {"format": "JPEG", "quality": 95}
    else:
        fmt = "PNG"
        save_kwargs = {"format": "PNG"}
    buf = io.BytesIO()
    pil.save(buf, **save_kwargs)
    return buf.getvalue(), fmt, width_px, height_px


def _build_replacement_page_pdf(image_bytes, fmt, width_px, height_px):
    """
    Build a single-page PDF (in memory) sized to the image's pixel dims at
    72 dpi, with the image filling the page.

    Returns:
        bytes: The PDF file contents.
    """
    width_pt = float(width_px)
    height_pt = float(height_px)
    pdf = FPDF(unit="pt")
    pdf.add_page(format=(width_pt, height_pt))
    suffix = ".jpg" if fmt == "JPEG" else ".png"
    image_stream = io.BytesIO(image_bytes)
    image_stream.name = f"replacement{suffix}"
    pdf.image(image_stream, x=0, y=0, w=width_pt, h=height_pt)
    return bytes(pdf.output())


def fix_scans_pdf(pdf_path, dry_run, writer, logger):
    """
    Detect (and optionally repair) a Scans.pdf with oversized pages.

    In dry-run mode, log and CSV-record each offending page without writing
    to disk. Otherwise, rebuild any oversized image-only page at its image's
    natural size (72 dpi); pass other pages through unchanged. The fixed
    file is written next to the original and atomically swapped in.

    Args:
        pdf_path (str): Path to the Scans.pdf to inspect.
        dry_run (bool): If True, only report; do not modify files.
        writer (csv.writer): CSV writer for action records.
        logger (logging.Logger): Logger object.

    Returns:
        None
    """
    try:
        oversized = find_oversized_pages(pdf_path)
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        return

    if not oversized:
        logger.info(f"OK (no oversized pages): {pdf_path}")
        return

    if dry_run:
        logger.info(f"Dry run: {len(oversized)} oversized page(s) in {pdf_path}")
        for index, width_pt, height_pt in oversized:
            logger.info(
                f"  - page {index + 1}: {width_pt:.0f} x {height_pt:.0f} pt"
            )
            writer.writerow([pdf_path, index + 1, f"{width_pt:.0f}", f"{height_pt:.0f}"])
        return

    oversized_indices = {i for i, _, _ in oversized}
    try:
        reader = PdfReader(pdf_path)
        out_writer = PdfWriter()
        fixed = 0
        passed_through = 0
        for index, page in enumerate(reader.pages):
            if index in oversized_indices:
                rebuilt = rebuild_oversized_page(page)
                if rebuilt is not None:
                    image_bytes, fmt, width_px, height_px = rebuilt
                    new_pdf_bytes = _build_replacement_page_pdf(
                        image_bytes, fmt, width_px, height_px
                    )
                    new_reader = PdfReader(io.BytesIO(new_pdf_bytes))
                    out_writer.add_page(new_reader.pages[0])
                    fixed += 1
                    logger.info(
                        f"Rebuilt page {index + 1} of {pdf_path} at {width_px} x {height_px} pt"
                    )
                    continue
                logger.warning(
                    f"Page {index + 1} of {pdf_path} is oversized but could not be rebuilt; passing through"
                )
            out_writer.add_page(page)
            passed_through += 1

        fixed_path = pdf_path + ".fixed"
        with open(fixed_path, "wb") as f:
            out_writer.write(f)
        os.replace(fixed_path, pdf_path)
        logger.info(
            f"Fixed {pdf_path}: rebuilt {fixed} page(s), passed through {passed_through} page(s)"
        )
    except Exception as e:
        logger.error(f"Error fixing PDF {pdf_path}: {e}")
        try:
            if os.path.exists(pdf_path + ".fixed"):
                os.remove(pdf_path + ".fixed")
        except Exception:
            pass


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
### Define run function
################################################################################

def run(args):
    """
    Organize album directories: Scans.pdf, disc folder renaming, and cleanup.

    Args:
        args (argparse.Namespace): Parsed arguments with dir, mode, dry_run, output_csv.
    """
    # Set up logging in the root project directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    logger = setup_logging(root_dir)

    # Set default output CSV path if not provided
    output_csv = args.output_csv or os.path.join(args.dir, "output.csv")

    # Get the list of subdirectories
    subdirectories = [os.path.join(args.dir, subdirectory) for subdirectory in sorted(os.listdir(args.dir)) if os.path.isdir(os.path.join(args.dir, subdirectory))]

    # Open the CSV file for writing
    with open(output_csv, mode='w', newline='', encoding='utf-8-sig') as csv_file:
        writer = csv.writer(csv_file)

        # Process based on the selected mode
        if args.mode in ['make_scans', 'all']:
            writer.writerow(["Mode: make_scans"])
            writer.writerow(["Directory", "Included Files"])
            for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories for Scans.pdf"):
                create_scans(subdirectory_path, args.dry_run, writer, logger)
            writer.writerow([])  # Add a blank line between modes

        if args.mode in ['fix_scans', 'all']:
            writer.writerow(["Mode: fix_scans"])
            writer.writerow(["PDF", "Page", "Width (pt)", "Height (pt)"])
            for subdirectory_path in tqdm(subdirectories, desc="Processing subdirectories for fix_scans"):
                pdf_path = os.path.join(subdirectory_path, "Scans.pdf")
                if os.path.isfile(pdf_path):
                    fix_scans_pdf(pdf_path, args.dry_run, writer, logger)
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
