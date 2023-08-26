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
from functions import update_tags
from functions import get_album_tags_renaissance

################################################################################
### Guess album-level tags
################################################################################

# Specify search dir
# search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
# album_tags = get_album_tags_renaissance(search_dir)

################################################################################
### Guess track-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'

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
    album_title = re.search('\[(\d{4})\]\s(.+)\s\((.+)\)', track_path).group(2)
    track_tags_df.loc[track_path, 'Album'] = album_title

    # Extract disc info
    if 'Disc' in track_path:
        disc_number = re.search('Disc\s\d+', track_path).group(0).split(' ')[1]
        track_tags_df.loc[track_path, 'DiscNumber'] = disc_number

    # Extract track info
    track_number, track_info = track_path.split('/')[-1].replace('.flac', '').split(' - ', 1)
    track_tags_df.loc[track_path, 'TrackNumber'] = track_number
    track_tags_df.loc[track_path, 'Title'] = track_info

    # Process the track info
    # In general, tracks are formatted as:
    # String Quartet No 76 in G,          Op 76 No 2, Hob III: 76, 'Fifths' - I. Allegro
    # WORK                 in INITIALKEY, OPUS  NUMBER, CATALOG #, 'NAME'   - MOVEMENT
    # With all tags other than WORK being optional
    # INITIALKEY - begins with valid keys (A through G)
    # OPUS - begins with Op
    # NUMBER - begins with No
    # CATALOG # - variable
    # NAME - will be in quotes
    # MOVEMENT - begins with Roman numerals
    


    # Update remaining
    track_tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]

track_tags_df.to_excel('track_tags.xlsx')

################################################################################
### Merge album and track tags, and write to file
################################################################################


# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
# sheet_name = 'Wind Ensemble - composer'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# # Update the tags
# update_tags(tags_df)