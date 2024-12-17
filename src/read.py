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
    disc_pattern = r'(' + '|'.join(possible_disc_names) + r')\s?(\d+)'
    if any(keyword in track_path for keyword in possible_disc_names):
        disc_match = re.search(disc_pattern, track_path)
        if disc_match:
            return disc_match.group(2)
    return None

################################################################################
### Process album string: Parse album string into fields: album, year_recorded, 
### orchestra, conductor
### OR extract from file tags
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
            orchestra = parts[0].strip()
            conductor = parts[1].strip()
        else:
            orchestra = parts[1].strip()
            conductor = parts[0].strip()
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
def get_album_fields_from_track_path(track_path):
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
### Process track tag: Parse title tag into fields: work, work_number, 
### initial_key, catalog_number, opus, opus_number, epithet, movement
### OR extract from file tags
################################################################################

def parse_fields_from_title_tag(track_path):
    """
    Extract track info from the track_path.

    Falls back to reading metadata directly from audio file tags when the track string
    doesn't follow the expected naming convention.
    
    Args:
        track_path (str): Path to the FLAC audio file
        
    Returns:
        tuple: track_number, work, work_number, initial_key, catalog_number, opus, opus_number, epithet, movement
            
    Note:
        Any tag that cannot be read will return None for that field
    """

    logging.info(f"{track_path}: Track tag exists. Attempting to extract fields from title tag.")

    audio_file = mutagen.flac.FLAC(track_path)
    work = audio_file['title'][0]

    # Attempt to parse the track string. The hand-tagged format of the 'title' tag is:
    # Work, Work Number, in Initial Key, 'Epithet', Catalog #, Opus, Opus Number - I. Movement

    # MOVEMENT - will follow a hyphen and begin with a Roman numeral. Occurs at the end of the string
    work_match = re.search(r'(.+)\s-\s([IVXLCDM]+?\.\s.+)', work)
    if work_match:
        work = work_match.group(1)
        movement = work_match.group(2)
    else:
        movement = None
    # Now looks like: Work, Work Number, in Initial Key, 'Epithet', Catalog #, Opus, Opus Number

    # EPITHET - will be in quotes, preceding comma may be optional
    # If trailing comma is present, needs to be stripped
    epithet_match = re.search(r'(.+),?\s\'(.+)\'', work)
    if epithet_match:
        work = epithet_match.group(1)
        if work.endswith(','):
            work = work.rstrip(',')
        epithet = epithet_match.group(2)
    else:
        epithet = None
    # Now looks like: Work, Work Number in Initial Key, Catalog #, Opus, Opus Number

    # NUMBER - begins with NO // OPUS - begins with Op
    # Either, or, both, or neither may be present
    both_match = re.search(r'(.+)\s(No\s\d+),*\s(Op\s\d+)\s(No\s\d+)(.*)', work)
    opus_match = re.search(r'(.+),\s(Op\s\d+)(.*)', work)
    num_match = re.search(r'(.+),\s(No\s\d+)(.*)', work)
    # Check for both - opus # and work #
    if both_match:
        work = both_match.group(1) + both_match.group(5)
        work_number = both_match.group(2)
        opus = both_match.group(3)
        opus_number = both_match.group(4)
    # Check for Opus only - opus #
    elif opus_match:
        work = opus_match.group(1) + opus_match.group(3)
        opus_number = opus_match.group(2)
    # Check for No only - work #
    elif num_match:
        work = num_match.group(1) + num_match.group(3)
        work_number = num_match.group(2)
    # Neither
    else:
        opus = None
        opus_number = None
        work_number = None
    # Now looks like: Work in Initial Key, Catalog #

    # CATALOG # - variable. But with OPUS, NUMBER, NAME, MOVEMENT all removed, CATALOG # should be what remains after the final comma
    # Check that CATALOG # ends with a digit to avoid WORKs with commas in the name, but with out CATALOG #
    catalog_match = re.search(r'(.+),(.+\d$)', work)
    if catalog_match:
        work = catalog_match.group(1)
        catalog_number = catalog_match.group(2).strip() # remove whitespace from preceding comma
    else:
        catalog_number = None
    # Now looks like: Work in Initial Key

    # INITIALKEY - begins with valid keys (A through G) and terminates (major key) or indicates minor key (ends with minor, or -flat, or -sharp)
    # This avoids tiltes with ' in ' in them
    key_match = re.search(r'(.+)\sin\s([A-G]$|[A-G]\sminor|[A-G]-flat|[A-G]-sharp)', work)
    if key_match:
        work = key_match.group(1)
        initial_key = key_match.group(2)
    else:
        initial_key = None
    # Now looks like: Work

    # WORK - whatever remains. Strip trailing comma if necessary
    if work.endswith(','):
        work = work.rstrip(',')
    
    return work, work_number, initial_key, catalog_number, opus, opus_number, epithet, movement
    
def get_tags_from_file_without_title_tag(track_path):

    logging.info(f"{track_path}: Track tag does not exist. Attempting to extract from file tags.")

    # Extract album, year_recorded, orchestra, conductor
    audio_file = mutagen.flac.FLAC(track_path)
    # Track number
    try:
        track_number = audio_file['tracknumber'][0]
    except:
        track_number = None
    # Work
    try:
        work = audio_file['title'][0]
    except:
        work = None
    # Work number
    try:
        work_number = audio_file['work number'][0]
    except:
        work_number = None
    # Initial key
    try:
        initial_key = audio_file['initialkey'][0]
    except:
        initial_key = None
    # Catalog number
    try:
        catalog_number = audio_file['catalog #'][0]
    except:
        catalog_number = None
    # Opus
    try:
        opus = audio_file['opus'][0]
    except:
        opus = None
    # Opus number
    try:
        opus_number = audio_file['opus number'][0]
    except:
        opus_number = None
    # Epithet
    try:
        epithet = audio_file['epithet'][0]
    except:
        epithet = None
    # Movement
    try:
        movement = audio_file['movement'][0]
    except:
        movement = None

    return work, work_number, initial_key, catalog_number, opus, opus_number, epithet, movement

# Master function that integrates the above functions: get_track_string_from_track_path, 
# parse_fields_from_matching_track_string, get_tags_from_file_with_unmatched_track_string
def get_track_fields_from_track_path(track_path):
    """
    Extract track information from the track path

    Args:
        track_path (str): Path to the track file.
    
    Returns:
        tuple: (track_number, work, work_number, initial_key, catalog_number, opus, opus_number, epithet, movement)
    """

    # Attempt to read the title string:
    audio_file = mutagen.flac.FLAC(track_path)
    # If it exists, extract tags from the title tag. Falling back to reading tags directly from the file if necessary
    if audio_file['tracknumber'][0]:
        work, work_number, initial_key, catalog_number, opus, \
            opus_number, epithet, movement = parse_fields_from_title_tag(track_path)
    # Otherwise, extract tags directly from the file
    else:
        work, work_number, initial_key, catalog_number, opus, \
            opus_number, epithet, movement = get_tags_from_file_without_title_tag(track_path)
    # Finally, read the track number from the 'tracknumber' tag
    try:
        track_number = audio_file['tracknumber'][0]
    except:
        track_number = None

    return track_number, work, work_number, initial_key, catalog_number, opus, \
            opus_number, epithet, movement

################################################################################
### Read remaining tags: composer, genre
################################################################################

def get_genre_composer_tags_from_file(track_path):
    """
    Extract track metadata from FLAC file tags
    
    Args:
        track_path (str): Path to the FLAC audio file
        
    Returns:
        tuple: (genre, composer)
            
    Note:
        Any tag that cannot be read will return None for that field
    """

    # Extract genre, composer
    audio_file = mutagen.flac.FLAC(track_path)
    # Album
    try:
        genre = audio_file['genre'][0]
    except:
        genre = None
    # Year recorded
    try:
        composer = audio_file['composer'][0]
    except:
        composer = None

    return genre, composer

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
        album, year_recorded, orchestra, conductor = get_album_fields_from_track_path(track_path)
        tags_df.loc[track_path, 'Album'] = album
        tags_df.loc[track_path, 'Year Recorded'] = year_recorded
        tags_df.loc[track_path, 'Orchestra'] = orchestra
        tags_df.loc[track_path, 'Conductor'] = conductor

        # Get disc number from path structure
        disc_number = get_disc_number_from_track_path(track_path)
        tags_df.loc[track_path, 'DiscNumber'] = disc_number
        
        # Get track info from path structure
        track_number, work, work_number, initial_key, catalog_number, opus, \
            opus_number, epithet, movement = get_track_fields_from_track_path(track_path)
        tags_df.loc[track_path, 'TrackNumber'] = track_number
        tags_df.loc[track_path, 'Work'] = work
        tags_df.loc[track_path, 'Work Number'] = work_number
        tags_df.loc[track_path, 'InitialKey'] = initial_key
        tags_df.loc[track_path, 'Catalog #'] = catalog_number
        tags_df.loc[track_path, 'Opus'] = opus
        tags_df.loc[track_path, 'Opus Number'] = opus_number
        tags_df.loc[track_path, 'Epithet'] = epithet
        tags_df.loc[track_path, 'Movement'] = movement
    
        # Get genre and composer from file tags
        genre, composer = get_genre_composer_tags_from_file(track_path)
        tags_df.loc[track_path, 'Genre'] = genre
        tags_df.loc[track_path, 'Composer'] = composer

    return tags_df

