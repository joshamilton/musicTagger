################################################################################
### read.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import os
import re
import logging
import mutagen
import mutagen.flac
import pandas as pd
from tqdm import tqdm  # For better progress tracking

################################################################################
### Setup logging
################################################################################

# Import the setup_logging function
from utils import setup_logging
# Initialize the logger
logger = setup_logging(os.getcwd())

################################################################################
### Define functions
### Create dataframe to store tags
################################################################################

def get_flac_files(search_dir):
    """
    Get a list of FLAC files in the specified directory.

    Args:
        search_dir (str): Directory to search for FLAC files.

    Returns:
        list: List of FLAC file paths.

    Raises:
        ValueError: If no FLAC files are found in the directory.
    """
    track_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                track_path_list.append(os.path.join(dirpath, file))
    if not track_path_list:
        raise ValueError("No FLAC files found in the specified directory.")
    return sorted(track_path_list)

def create_tags_dataframe(track_path_list):
    """
    Create an empty dataframe to store tags for the given tracks.

    Args:
        track_path_list (list): List of track file paths.

    Returns:
        pd.DataFrame: DataFrame with track paths as index and columns for tags.
    """
    columns = ['Composer', 'Album', 'Year Recorded', 'Orchestra', 'Conductor', 'Soloists', 'Arranger', 
               'Genre', 'DiscNumber', 'TrackNumber', 'Title', 'TrackTitle', 'Work', 'Work Number', 
               'InitialKey', 'Catalog #', 'Opus', 'Opus Number', 'Epithet', 'Movement']
    return pd.DataFrame(index=track_path_list, columns=columns)

def get_tracks_create_dataframe(search_dir):
    """
    Get list of tracks and create an empty dataframe to store tags.

    Args:
        search_dir (str): Directory to search for FLAC files.

    Returns:
        pd.DataFrame: DataFrame with track paths as index and columns for tags.
    """
    track_path_list = get_flac_files(search_dir)
    return create_tags_dataframe(track_path_list)

################################################################################
### Process track path: get album string, disc number from track path
################################################################################

def get_album_string_from_track_path(track_path):
    """
    Extract album info by walking up the path to find the album folder.

    Args:
        track_path (str): Path to the track file.

    Returns:
        album_string (str): Album information extracted from the path.
    """
    parts = track_path.split('/')
    
    # Find album folder by walking up from file
    for i in range(len(parts)-1, -1, -1):
        folder = parts[i]
        if folder.startswith('Disc') or folder.startswith('Disk') or folder.startswith('CD'):
            # If we hit a Disc folder, use its parent
            if i > 0:
                return parts[i-1]
        elif '.flac' not in folder:
            # First non-Disc, non-file folder is album
            return folder
    return ''

def get_disc_number_from_track_path(track_path):
    """
    Extract disc number from album information.

    Args:
        track_path (str): Album information extracted from the path.

    Returns:
        disc_number (str): Disc number extracted from the album information.
    """
    possible_disc_names = ['Disc', 'Disk', 'CD']
    disc_pattern = r'(' + '|'.join(possible_disc_names) + r')\s(\d+)'
    if any(keyword in track_path for keyword in possible_disc_names):
        disc_match = re.search(disc_pattern, track_path)
        if disc_match:
            return disc_match.group(2)
    return None

################################################################################
### Process album string: Parse album string into fields: album, year_recorded, 
### orchestra, conductor or extract from file tags
################################################################################

def parse_performer_string(orchestra_conductor_string):
    """
    Extract orchestra and conductor names from a combined string.

    The function handles three formats:
    1. "Orchestra with Conductor" - Example: "B'Rock Orchestra with Dmitry Sinkovsky"
    2. "Orchestra, Conductor" or "Conductor, Orchestra" - Examples:
       - "Harnoncourt, Concentus Musicus Wien"
       - "Brandenburg Consort, Goodman"
    3. "Orchestra" only - Example: "Capella Savaria"

    Args:
        orchestra_conductor_string (str): String containing orchestra and/or conductor names

    Returns:
        tuple: (orchestra, conductor) where conductor may be None if not present
    """
    # If naming convention is Orchestra with Conductor
    if 'with' in orchestra_conductor_string:
        parts = orchestra_conductor_string.split('with')
        orchestra = parts[0].strip()
        conductor = parts[1].strip()
    # If naming convention is Orchestra, Conductor or Conductor, Orchestra
    elif ',' in orchestra_conductor_string:
        parts = orchestra_conductor_string.split(',')
        # Determine if the split is orchestra, conductor or conductor, orchestra
        # If the first part is longer, it is the orchestra
        # Otherwise, it is the conductor
        len_first = len(parts[0].split())
        len_second = len(parts[1].split())
        if len_first > len_second:
            orchestra = parts[0]
            conductor = parts[1]
        else:
            orchestra = parts[1]
            conductor = parts[0]
    # Otherwise, assume the entire string is the orchestra
    else:
        orchestra = orchestra_conductor_string
        conductor = None
        
    return orchestra, conductor

def parse_fields_from_matching_album_string(match):

    """
    Extract album metadata from a regex match object containing album string pattern.
    Expected format: '[YEAR] ALBUM_NAME (PERFORMER_INFO: ORCHESTRA and CONDUCTOR)'
    
    Args:
        match (re.Match): Regex match object with two groups:
            1. year_recorded
            2. album_string (includes album name and performer info)
            
    Returns:
        tuple: (album, year_recorded, orchestra, conductor)
    """

    # The match object should have two groups: year_recorded and album_string
    year_recorded, album_string = match.groups()
    logging.info(f"{album_string}: Album info follows the convention. Attempting to extract from file path.")
    # Extract the album, orchestra and conductor
    try:
        album_string = album_string.split(' (')
        album = album_string[0]
        orchestra_conductor = album_string[1].replace(')', '')
        orchestra, conductor = parse_performer_string(orchestra_conductor)
    # Otherwise, asusme orchestra and conductor are not present in album string
    except:
        album = album_string

    return album, year_recorded, orchestra, conductor

def get_tags_from_file_with_unmatched_album_string(track_path):
    """
    Extract album metadata from FLAC file tags when path pattern doesn't match.
    
    Falls back to reading metadata directly from audio file tags when the path
    doesn't follow the expected naming convention.
    
    Args:
        track_path (str): Path to the FLAC audio file
        
    Returns:
        tuple: (album, year_recorded, orchestra, conductor)
            
    Note:
        Any tag that cannot be read will return None for that field
    """
    
    logging.info(f"{track_path}: Album info does not follow the convention. Attempting to extract from file tags.")
    # Extract album, year_recorded, orchestra, conductor
    audio_file = mutagen.flac.FLAC(track_path)
    # Album
    try:
        album = audio_file['album'][0]
    except:
        album = None
    # Year recorded
    try:
        year_recorded = audio_file['year'][0]
    except:
        year_recorded = None
    # Orchestra
    try:
        orchestra = audio_file['orchestra'][0]
    except:
        orchestra = None
    # Conductor
    try:
        conductor = audio_file['conductor'][0]
    except:
        conductor = None

    return album, year_recorded, orchestra, conductor

    
# Master function that integrates the above functions: get_album_string_from_track_path, 
# get_disc_number_from_track_path, parse_fields_from_matching_album_string, 
# get_tags_from_file_with_unmatched_album_string
def get_fields_from_album_string(track_path):
    """
    Extract album information from the track path

    Args:
        track_path (str): Path to the track file.
    
    Returns:
        tuple: (album, year_recorded, orchestra, conductor)
    """

    # Process the path to extract album information
    album_string = get_album_string_from_track_path(track_path)

    # Check that the album matches the expected pattern
    # If so, extract the year and album name
    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)')
    match = album_pattern.search(album_string)
    if match:
        album, year_recorded, orchestra, conductor = parse_fields_from_matching_album_string(match)

    # Otherwise, extract tags from the file
    else:
        album, year_recorded, orchestra, conductor = get_tags_from_file_with_unmatched_album_string(track_path)

    return album, year_recorded, orchestra, conductor
        
################################################################################
### Master function to get track- and album-level tags
################################################################################

def get_tags(tags_df):
    """
    Extract tags from file paths and update the dataframe.

    Args:
        tags_df (pd.DataFrame): DataFrame with track paths as index and columns for tags.

    Returns:
        pd.DataFrame: Updated DataFrame with extracted tags.
    """

    total_files = len(tags_df)    
    print(f"Processing {total_files} files...")
    
    for track_path in tqdm(tags_df.index, total=total_files, desc="Reading tags"):

        # Get album info from path structure
        album, year_recorded, orchestra, conductor = get_fields_from_album_string(track_path)
        tags_df.loc[track_path, 'Album'] = album
        tags_df.loc[track_path, 'Year Recorded'] = year_recorded
        tags_df.loc[track_path, 'Orchestra'] = orchestra
        tags_df.loc[track_path, 'Conductor'] = conductor

        # Get disc number from path structure
        disc_number = get_disc_number_from_track_path(track_path)
        tags_df.loc[track_path, 'DiscNumber'] = disc_number

        # Extract title for processing
        # Enclose in a try block, in case file hasn't already been tagged by me
        try:
            work = mutagen.flac.FLAC(track_path)['title'][0]
            tags_df.loc[track_path, 'Title'] = work
            # Process title into new fields
            work_match = re.search(r'(.+)\s-\s([IVXLCDM]+?\.\s.+)', work)
            if work_match:
                work = work_match.group(1)
                movement = work_match.group(2)
                tags_df.loc[track_path, 'Movement'] = movement
            # NAME - will be in quotes, preceding comma may be optional
            # If trailing comma is present, needs to be stripped
            name_match = re.search(r'(.+),?\s\'(.+)\'', work)
            if name_match:
                work = name_match.group(1)
                if work.endswith(','):
                    work = work.rstrip(',')
                name = name_match.group(2)
                tags_df.loc[track_path, 'Epithet'] = name
            # NUMBER - begins with NO // OPUS - begins with Op
            # Either, or, both, or neither may be present
            both_match = re.search(r'(.+),*\s(Op\s\d+)\s(No\s\d+)(.*)', work)
            opus_match = re.search(r'(.+),\s(Op\s\d+)(.*)', work)
            num_match = re.search(r'(.+),\s(No\s\d+)(.*)', work)
            # Check for both - opus # and work #
            if both_match:
                work = both_match.group(1) + both_match.group(4)
                opus = both_match.group(2)
                number = both_match.group(3)
                tags_df.loc[track_path, 'Opus'] = opus
                tags_df.loc[track_path, 'Opus Number'] = number
            # Check for Opus only - opus #
            elif opus_match:
                work = opus_match.group(1) + opus_match.group(3)
                opus = opus_match.group(2)
                tags_df.loc[track_path, 'Opus'] = opus
            # Check for No only - work #
            elif num_match:
                work = num_match.group(1) + num_match.group(3)
                number = num_match.group(2)
                tags_df.loc[track_path, 'Work Number'] = number
            # CATALOG # - variable. But with OPUS, NUMBER, NAME, MOVEMENT all removed, CATALOG # should be what remains after the final comma
            # Check that CATALOG # ends with a digit to avoid WORKs with commas in the name, but with out CATALOG #
            catalog_match = re.search(r'(.+),(.+\d$)', work)
            if catalog_match:
                work = catalog_match.group(1)
                catalog = catalog_match.group(2).strip() # remove whitespace from preceding comma
                tags_df.loc[track_path, 'Catalog #'] = catalog
            # INITIALKEY - begins with valid keys (A through G) and terminates (major key) or indicates minor key (ends with minor, or -flat, or -sharp)
            # This avoids tiltes with ' in ' in them
            key_match = re.search(r'(.+)\sin\s([A-G]$|[A-G]\sminor|[A-G]-flat|[A-G]-sharp)', work)
            if key_match:
                work = key_match.group(1)
                key = key_match.group(2)
                tags_df.loc[track_path, 'InitialKey'] = key
            # WORK - whatever remains. Strip trailing comma if necessary
            if work.endswith(','):
                tags_df.loc[track_path, 'Work'] = work.rstrip(',')
            else:
                tags_df.loc[track_path, 'Work'] = work
            # Update with year recorded, pulled from tag
            tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]
        except:
            pass

        # Update with other fields pulled from the tags
        # Composer, Genre, Year Recorded
        # Again enclose in a try block, in case file hasn't already been tagged by me
        try:
            tags_df.loc[track_path, 'Composer'] = mutagen.flac.FLAC(track_path)['artist'][0]
            tags_df.loc[track_path, 'Genre'] = mutagen.flac.FLAC(track_path)['genre'][0]
            tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]
        except:
            pass

    return tags_df

