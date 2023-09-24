################################################################################
### functions.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import mutagen
import mutagen.flac
import mutagen.easyid3
import os
import pandas as pd
import re

################################################################################
### Define functions
################################################################################

### Function to get file list and create empty dataframe
def get_tracks_create_dataframe(search_dir):
    # Find tracks: end in .flac
    track_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                track_path_list.append(os.path.join(dirpath, file))
    track_path_list = sorted(track_path_list)

    # Create dataframe to store track-level tags:
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    track_tags_df = pd.DataFrame(index = track_path_list, columns = ['Composer', 'Album', 'Year Recorded',
                                                                    'Orchestra', 'Conductor', 'Soloists', 'Genre', 
                                                                    'DiscNumber', 'TrackNumber', 'Title',
                                                                    'Work', 'InitialKey', 'Catalog #', 'Opus', 'Number', 
                                                                    'Name', 'Movement'])
    
    return track_tags_df

### Function to get track- and album-level tags
def get_album_track_tags(track_tags_df):

    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)')
    for track_path in track_tags_df.index:
        # Extract performer and year released info. All other is either encoded in tags, or must be added manually
        soloist = track_path.split('/')[8]
        album_info = track_path.split('/')[9] # can't split backwards, because some albums will have a Disc
        foo, year, album, bar = re.split(album_pattern, album_info)
            # Update tags
#        track_tags_df.loc[track_path, 'Year Released'] = year # No longer tracking this field
        # Process the performer_info (Orchestra, Conductor)
        track_tags_df.loc[track_path, 'Soloist'] = soloist

        # Extract disc info and track numbers
        # Must check track path b/c albums are not always tagged with the Disc #
        if 'Disc' in track_path: 
            disc_number = re.search(r'Disc\s\d+', track_path).group(0).split(' ')[1]
            track_tags_df.loc[track_path, 'DiscNumber'] = disc_number
        track_number, track_info = track_path.split('/')[-1].replace('.flac', '').split(' - ', 1)
        track_tags_df.loc[track_path, 'TrackNumber'] = track_number

        # Extract title for processing
        work = mutagen.flac.FLAC(track_path)['title'][0]
        track_tags_df.loc[track_path, 'Title'] = work

        # Process title into new fields
        work_match = re.search(r'(.+)\s-\s([IVXLCDM]+?\.\s.+)', work)
        if work_match:
            work = work_match.group(1)
            movement = work_match.group(2)
            track_tags_df.loc[track_path, 'Movement'] = movement
        # NAME - will be in quotes, preceding comma may be optional
        # If trailing comma is present, needs to be stripped
        name_match = re.search(r'(.+),?\s\'(.+)\'', work)
        if name_match:
            work = name_match.group(1)
            if work.endswith(','):
                work = work.rstrip(',')
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
        # INITIALKEY - begins with valid keys (A through G) and terminates (major key) or indicates minor key (ends with minor, or -flat, or -sharp)
        # This avoids tiltes with ' in ' in them
        key_match = re.search(r'(.+)\sin\s([A-G]$|[A-G]\sminor|[A-G]-flat|[A-G]-sharp)', work)
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

        # Update with other fields pulled from the tags
        # Album, Composer, Genre, Year Recorded
        track_tags_df.loc[track_path, 'Album'] = mutagen.flac.FLAC(track_path)['album'][0]
        track_tags_df.loc[track_path, 'Composer'] = mutagen.flac.FLAC(track_path)['artist'][0]
        track_tags_df.loc[track_path, 'Genre'] = mutagen.flac.FLAC(track_path)['genre'][0]
        track_tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]

    # Use XLSXwriter engine to allow for foreign-language characters
    track_tags_df.to_excel('track_tags.xlsx', engine = 'xlsxwriter')

    return


### Update tags
def update_tags(tags_df):

    # Iterator
    total_files = len(tags_df)

    for index, row in tags_df.iterrows():
        file_path = row['File']

        # Delete all ID3 tags
        audio_file = mutagen.easyid3.EasyID3(file_path)
        audio_file.delete()

        # Delete all FLAC tags
        audio_file = mutagen.flac.FLAC(file_path)
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
