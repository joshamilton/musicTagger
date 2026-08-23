################################################################################
### remove_flac.py
### Copyright (c) 2026, Joshua J Hamilton
### This utility program deletes FLAC, log, cue, accurip, playlist, and image
### files recursively under a directory. It is meant to be run after a FLAC
### album has been converted to MP3 by some other tool, to leave behind only
### the MP3s and anything else not in the removal list.
################################################################################

################################################################################
### Import packages
################################################################################
import logging
import os

from tqdm import tqdm

from utils import walk_with_progress

logger = logging.getLogger(__name__)

################################################################################
### Define functions
################################################################################

REMOVE_EXTENSIONS = frozenset({
    '.flac', '.log', '.cue', '.accurip', '.m3u', '.m3u8',
    '.jpg', '.png', '.tif', '.bmp',
})

def find_files_to_remove(directory):
    logger.info('Scanning directory for files to remove...')
    files_to_remove = []
    for root, _, files in walk_with_progress(directory, desc="Scanning directory", unit="folder"):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext.lower() in REMOVE_EXTENSIONS:
                file_path = os.path.join(root, file)
                files_to_remove.append(file_path)
                logger.debug(f"Remove candidate: {file_path}")
    return sorted(files_to_remove)

def remove_files(files):
    busy_files = []
    for file in tqdm(files, desc="Removing files"):
        try:
            os.remove(file)
        except OSError as e:
            if e.errno == 16:  # Resource busy
                busy_files.append(file)
            else:
                raise
    return busy_files

################################################################################
### Define run function
################################################################################

def run(args):
    """
    Run remove-flac: delete FLAC, log, cue, accurip, playlist, and image
    files recursively under --dir.

    Args:
        args (argparse.Namespace): Parsed arguments with dir.
    """
    files_to_remove = find_files_to_remove(args.dir)
    busy_files = remove_files(files_to_remove)
    logger.info(f"Removed {len(files_to_remove) - len(busy_files)} file(s).")
    for file in busy_files:
        logger.error(f"Could not remove (file busy): {file}")
