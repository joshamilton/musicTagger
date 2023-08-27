################################################################################
### functions.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import mutagen
import mutagen.flac
import os
import pandas as pd
import re

################################################################################
### Define functions
################################################################################

### Get album-level tags for Renaissance music
def get_album_tags_renaissance(search_dir):

    # Find albums. Folders will have the pattern [yyyy] album (info). Only the [yyyy] part needs to matched.
    year_pattern = re.compile(r'\[\d{4}\]')
    album_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for dirname in dirnames:
            match = year_pattern.match(dirname)
            if match:
                album_path_list.append(os.path.join(dirpath, dirname))
    album_path_list = sorted(album_path_list)
    # Create dataframe to store album-level tags:
    # Album, Year Released, Orchestra, Conductor, Composer, Genre
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    album_tags_df = pd.DataFrame(index = album_path_list, columns = ['Composer', 'Year Released', 'Album', \
                                                                'Orchestra', 'Conductor', 'Soloists', 'Genre', 
                                                                'Record Label'])

    # Loop over albums to extract tags
    # Folders will have the pattern [yyyy] album (info). All parts needed
    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)\s\((.+)\)')
    for album_path in album_path_list:
        # Extract composer and album info
        composer = album_path.split('/')[-2]
        album_info = album_path.split('/')[-1]
        foo, year, album, performer_info, bar = re.split(album_pattern, album_info)
            # Update tags
        album_tags_df.loc[album_path, 'Composer'] = composer
        album_tags_df.loc[album_path, 'Album'] = album # TO DO: exclude b/c album won't contain interpunct, pipe, and colon characters
        album_tags_df.loc[album_path, 'Year Released'] = year
        album_tags_df.loc[album_path, 'Genre'] = 'Renaissance' # TO DO: exclude b/c genre may differ between tracks
        # Process the performer_info (Orchestra, Conductor, Soloist tags)
        # Option 1: ensemble with conductor. Contains 'with' and lacks ','
        # Option 2: ensemble only. Lacks 'with' and ','
        # Option 3: soloists. Contains ',' and lacks 'with'
        if 'with' in performer_info and ',' not in performer_info:
            ensemble, conductor = re.split(' with ', performer_info)
            album_tags_df.loc[album_path, 'Orchestra'] = ensemble
            album_tags_df.loc[album_path, 'Conductor'] = conductor
        elif 'with' not in performer_info and ',' not in performer_info:
            ensemble = performer_info
            album_tags_df.loc[album_path, 'Orchestra'] = ensemble
        elif 'with' not in performer_info and ',' in performer_info:
            soloists = performer_info.replace(', ', ';')
            album_tags_df.loc[album_path, 'Soloists'] = soloists
    
    album_tags_df.to_excel('album_tags.xlsx')
    return(album_tags_df)

def get_track_tags_renaissance(search_dir):
    # Find tracks: end in .flac
    track_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                track_path_list.append(os.path.join(dirpath, file))
    track_path_list = sorted(track_path_list)

    # Create dataframe to store track-level tags:
    # Include album for merging with album_tags dataframe
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    track_tags_df = pd.DataFrame(index = track_path_list, columns = ['Album', 'DiscNumber', 'TrackNumber', 'Title',
                                                                'Work', 'InitialKey', 'Catalog #', 'Opus', 'Number', 
                                                                'Name', 'Movement', 'Year Written', 'Year Recorded'])

    # # Loop over tracks to extract tags
    # Folders will have the pattern [yyyy] album (info)/Disc 1 - subtitle/01 - title.flac. Disc is optional
    for track_path in track_path_list:

        # Extract album info
        # Sometimes the track title has text in parentheses, so need to add a '/' to restrict to album
        album_title = re.search(r'\[(\d{4})\]\s(.+)\s\((.+)\)\/', track_path).group(2)
        track_tags_df.loc[track_path, 'Album'] = album_title

        # Extract disc info
        if 'Disc' in track_path:
            disc_number = re.search(r'Disc\s\d+', track_path).group(0).split(' ')[1]
            track_tags_df.loc[track_path, 'DiscNumber'] = disc_number

        # Extract track info
        track_number, track_info = track_path.split('/')[-1].replace('.flac', '').split(' - ', 1)
        track_tags_df.loc[track_path, 'TrackNumber'] = track_number
        track_tags_df.loc[track_path, 'Title'] = track_info

        # Process the track info
        # In general, tracks are formatted as:
        # String Quartet No 76 in G,          Op 76 No 2, Hob III: 76, 'Fifths' - I. Allegro
        # WORK                 in INITIALKEY, OPUS  NUMBER, CATALOG #, 'NAME'   - MOVEMENT
        # With all fields other than WORK being optional
        # Begin by searching for fields that are consistently demarcated
        # MOVEMENT - begins with ' - ' followed by Roman numerals
        work = track_info
        work_match = re.search(r'(.+)\s-\s([IVXLCDM]+?\.\s.+)', work)
        if work_match:
            work = work_match.group(1)
            movement = work_match.group(2)
            track_tags_df.loc[track_path, 'Movement'] = movement
        # NAME - will be in quotes, preceding comma may be optional
        name_match = re.search(r'(.+),?\s\'(.+)\'', work)
        if name_match:
            work = name_match.group(1)
            name = name_match.group(2)
            track_tags_df.loc[track_path, 'Name'] = name
        # NUMBER - begins with NO // OPUS - begins with Op
        # Either, or, both, or neither may be present
        both_match = re.search(r'(.+),*\s(Op\s\d+)\s(No\s\d+)(.*)', work)
        opus_match = re.search(r'(.+),\s(Op\s\d+)(.*)', work)
        num_match = re.search(r'(.+),\s(No\s\d+)(.*)', work)
        # Check for both
        if both_match:
            work = both_match.group(1) + both_match.group(4)
            opus = both_match.group(2)
            number = both_match.group(3)
            track_tags_df.loc[track_path, 'Opus'] = opus
            track_tags_df.loc[track_path, 'Number'] = number
        # Check for Opus only
        elif opus_match:
            work = opus_match.group(1) + opus_match.group(3)
            opus = opus_match.group(2)
            track_tags_df.loc[track_path, 'Opus'] = opus
        # Check for No only
        elif num_match:
            work = num_match.group(1) + num_match.group(3)
            number = num_match.group(2)
            track_tags_df.loc[track_path, 'Number'] = number
        # CATALOG # - variable. But with OPUS, NUMBER, NAME, MOVEMENT all removed, CATALOG # should be what remains after the final comma
        # Check that CATALOG # ends with a digit to avoid WORKs with commas in the name, but with out CATALOG #
        catalog_match = re.search(r'(.+),(.+\d$)', work)
        if catalog_match:
            work = catalog_match.group(1)
            catalog = catalog_match.group(2).strip() # remove whitespace from preceding comma
            track_tags_df.loc[track_path, 'Catalog #'] = catalog
        # INITIALKEY - begins with valid keys (A through G) and terminates (major key) or indicates minor key (ends with minor)
        # This avoids tiltes with ' in ' in them
        key_match = re.search(r'(.+)\sin\s([A-G]$|[A-G]\sminor)', work)
        if key_match:
            work = key_match.group(1)
            key = key_match.group(2)
            track_tags_df.loc[track_path, 'InitialKey'] = key
        # WORK - whatever remains. Strip trailing comma if necessary
        if work.endswith(','):
            track_tags_df.loc[track_path, 'Work'] = work.rstrip(',')
        else:
            track_tags_df.loc[track_path, 'Work'] = work
        # Update with year recorded, pulled from tag
        track_tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]

    track_tags_df.to_excel('track_tags.xlsx')
    return(track_tags_df)

### Update tags
def update_tags(tags_df):

    # Iterator
    total_files = len(tags_df)

    for index, row in tags_df.iterrows():
        file_path = row['File']
        audio_file = mutagen.flac.FLAC(file_path)
        # Delete existing tags
        audio_file.delete()
        # Add new ones
        for tag, value in row.iloc[1:].items():
            # Check for missing values
            if value != 'nan':
                audio_file[tag] = value
        # Save results
        audio_file.save()
        # Report on progress
        print('Completed ' + str(index + 1) + ' of ' + str(total_files))
