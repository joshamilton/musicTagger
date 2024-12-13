################################################################################
### functions.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import os
import re
import mutagen
import mutagen.flac
import mutagen.easyid3
import pandas as pd
from tqdm import tqdm  # For better progress tracking


################################################################################
### Define functions
################################################################################

### Function to get file list and create empty dataframe
def get_tracks_create_dataframe(search_dir):
    """Get list of tracks and create empty dataframe to store tags"""
    # Find tracks: end in .flac
    track_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                track_path_list.append(os.path.join(dirpath, file))
    track_path_list = sorted(track_path_list)

    # Create dataframe to store track-level tags:
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    tags_df = pd.DataFrame(index = track_path_list, columns = ['Composer', 'Album', 'Year Recorded',
                                                                    'Orchestra', 'Conductor', 'Soloists', 'Arranger', 
                                                                    'Genre',  'DiscNumber', 'TrackNumber', 'Title', 'TrackTitle',
                                                                    'Work', 'Work Number', 'InitialKey', 'Catalog #', 'Opus', 'Opus Number', 
                                                                    'Epithet', 'Movement'] )
    
    return tags_df

### Function to extract album info from path
def get_album_info_from_path(track_path):
    """Extract album info by walking up path to find album folder"""
    parts = track_path.split('/')
    
    # Find album folder by walking up from file
    for i in range(len(parts)-1, -1, -1):
        folder = parts[i]
        if folder.startswith('Disc'):
            # If we hit a Disc folder, use its parent
            if i > 0:
                return parts[i-1]
        elif '.flac' not in folder:
            # First non-Disc, non-file folder is album
            return folder
    return ''

### Function to get track- and album-level tags
def get_tags(tags_df):
    """Extract tags from file paths and update dataframe"""
    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)')
    total_files = len(tags_df)
    
    print(f"Processing {total_files} files...")
    
    for track_path in tqdm(tags_df.index, total=total_files, desc="Reading tags"):

        # Get album info from path structure
        album_info = get_album_info_from_path(track_path)
        
        # Extract performer info
        parts = track_path.split('/')
        soloists_idx = parts.index(album_info) - 1
        soloists = parts[soloists_idx] if soloists_idx > 0 else ''
        
        # Parse album info
        match = album_pattern.search(album_info)
        if match:
            year, album = match.groups()
        else:
            year = ''
            album = album_info
            
        # Update tags
        tags_df.loc[track_path, 'Soloists'] = soloists
        tags_df.loc[track_path, 'Album'] = album
        tags_df.loc[track_path, 'Year Recorded'] = year
        
        # Extract disc number if present
        if 'Disc' in track_path:
            disc_match = re.search(r'Disc\s(\d+)', track_path)
            if disc_match:
                tags_df.loc[track_path, 'DiscNumber'] = disc_match.group(1)
                
        track_number, track_info = track_path.split('/')[-1].replace('.flac', '').split(' - ', 1)
        tags_df.loc[track_path, 'TrackNumber'] = track_number

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
        # Album, Composer, Genre, Year Recorded
        # Again enclose in a try block, in case file hasn't already been tagged by me
        try:
            tags_df.loc[track_path, 'Album'] = mutagen.flac.FLAC(track_path)['album'][0]
            tags_df.loc[track_path, 'Composer'] = mutagen.flac.FLAC(track_path)['artist'][0]
            tags_df.loc[track_path, 'Genre'] = mutagen.flac.FLAC(track_path)['genre'][0]
            tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]
        except:
            pass

    return tags_df

### Update tags
def update_tags(tags_df):
    """Update tags by reading from an Excel file
    
    Returns:
        tuple: (successful_df, failed_df) containing the successful and failed entries
    """

    # Initialize tracking dataframes
    successful_paths = []
    failed_paths = []

    # Iterator
    total_files = len(tags_df)
    print(f"Updating {total_files} files...") 

    for file_path in tqdm(tags_df.index, total=total_files, desc="Writing tags"):

        # Delete all ID3 tags
        try:
            audio_file = mutagen.easyid3.EasyID3(file_path)
            audio_file.delete()
        # ID3 tags may not exist
        except:
            pass

        # Update FLAC tags
        try:
            # Delete all FLAC tags
            audio_file = mutagen.flac.FLAC(file_path)
            audio_file.delete()
            # Add new ones
            row = tags_df.loc[file_path]
            for tag, value in row.items():
                # Check for missing values
                if value != 'nan':
                    audio_file[tag] = value

            # Create Title tag
            # General logic: Start with the work as the initial part of the title.
            # Append each piece of metadata to the title_parts list if it is not empty.
            # Join all parts with spaces to form the final title.
            # Get all the metadata
            work = row.get('Work', '')
            work_number = row.get('Work Number', '')
            catalog_number = row.get('Catalog #', '')
            opus = row.get('Opus', '')
            opus_number = row.get('Opus Number', '')
            initial_key = row.get('InitialKey', '')
            epithet = row.get('Epithet', '')
            movement = row.get('Movement', '')
            title_parts = [work]
            if work_number:
                title_parts.append(f", {work_number}")
            if catalog_number:
                title_parts.append(f", {catalog_number}")
            if opus:
                title_parts.append(f", {opus}")
            if opus_number:
                title_parts.append(f", {opus_number}")
            if initial_key:
                title_parts.append(f", in {initial_key}")
            if epithet:
                title_parts.append(f", '{epithet}'")
            if movement:
                title_parts.append(f" - {movement}")

            title = ''.join(title_parts)
            audio_file['Title'] = title

           # Save results
            audio_file.save()

            # Rename the track
            track_number = row.get('TrackNumber', '')
            # Sanitize the title
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
            new_file_name = f"{track_number} - {safe_title}.flac"
            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
            os.rename(file_path, new_file_path)

            # Update tracking
            successful_paths.append(file_path)

        except:
            failed_paths.append(file_path)
    
    # Create success/failure dataframes
    successful_df = tags_df.loc[successful_paths]
    failed_df = tags_df.loc[failed_paths]

    print(f"Completed!")
    print(f"Successfully processed: {len(successful_df)} files")
    print(f"Failed: {len(failed_df)} files")

    return successful_df, failed_df