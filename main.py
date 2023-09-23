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

################################################################################
### Combination function to extract album- and track-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/01 - Baroque/Handel, Georg Friederich/Keyboard Music new'
track_tags_df = functions.get_tracks_create_dataframe(search_dir)
# Get the tags
functions.get_album_track_tags(track_tags_df)

################################################################################
### Update tags
################################################################################

# Read in the Excel file containing updated tags
file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging - in Progress.xlsx'
sheet_name = 'Handel - Fireworks, Water Music'
tags_df = pd.read_excel(file_path, sheet_name = sheet_name, dtype = str) # convert to string for some reason
tags_df = tags_df.fillna('') # replace NAs so they don't get written e.g., if there is no Disc tag

# Update the tags
functions.update_tags(tags_df)