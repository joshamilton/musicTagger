################################################################################
### main.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import mutagen.flac
import os
import pandas as pd
import re
import functions

# ################################################################################
# ### Guess album-level tags
# ################################################################################

# # Specify search dir
# search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
# album_tags = functions.get_album_tags_renaissance(search_dir)

# ################################################################################
# ### Guess track-level tags
# ################################################################################

# # Specify search dir
# search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
# track_tags = functions.get_track_tags_renaissance(search_dir)

# ################################################################################
# ### Merge album and track tags, and write to file
# ################################################################################
# tags_df = pd.merge(album_tags, track_tags.reset_index(), on = 'Album').set_index('index')
# tags_df.to_excel('tags.xlsx')

# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
# sheet_name = 'Wind Ensemble - composer'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# # Update the tags
# functions.update_tags(tags_df)


################################################################################
### Combination function to extract album- and track-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/02 - Classical'

# Find tracks: end in .flac
track_path_list = []
for dirpath, dirnames, filenames in os.walk(search_dir):
    for file in filenames:
        if file.endswith('.flac'):
            track_path_list.append(os.path.join(dirpath, file))
track_path_list = sorted(track_path_list)

# Create dataframe to store track-level tags:
# Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
track_tags_df = pd.DataFrame(index = track_path_list, columns = ['Composer', 'Album', 'Year Released', 'Record Label',
                                                                 'Orchestra', 'Conductor', 'Soloists', 'Genre', 
                                                                 'DiscNumber', 'TrackNumber', 'Title',
                                                                 'Work', 'InitialKey', 'Catalog #', 'Opus', 'Number', 
                                                                 'Name', 'Movement', 'Year Written', 'Year Recorded'])

album_pattern = re.compile(r'\[(\d{4})\]\s(.+)\s\((.+)\)')
for track_path in track_path_list:
    # Extract performer and year released info. All other is either encoded in tags, or must be added manually
    composer = track_path.split('/')[7]
    album_info = track_path.split('/')[8] # can't split backwards, because some albums will have a Disc
    foo, year, album, performer_info, bar = re.split(album_pattern, album_info)
        # Update tags
    track_tags_df.loc[track_path, 'Year Released'] = year
    # Process the performer_info (Orchestra, Conductor)
    # Option 1: ensemble with conductor. Contains 'with'
    # Option 2: ensemble only. Lacks 'with'
    # Known Limitations:
    if 'with' in performer_info:
        ensemble, conductor = re.split(' with ', performer_info)
        track_tags_df.loc[track_path, 'Orchestra'] = ensemble
        track_tags_df.loc[track_path, 'Conductor'] = conductor
    else:
        ensemble = performer_info
        track_tags_df.loc[track_path, 'Orchestra'] = ensemble

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


track_tags_df.to_excel('track_tags.xlsx')