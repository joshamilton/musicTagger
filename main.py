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
### Guess album-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
album_tags = functions.get_album_tags_renaissance(search_dir)

################################################################################
### Guess track-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
track_tags = functions.get_track_tags_renaissance(search_dir)

################################################################################
### Merge album and track tags, and write to file
################################################################################
tags_df = pd.merge(album_tags, track_tags.reset_index(), on = 'Album').set_index('index')
tags_df.to_excel('tags.xlsx')

# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
# sheet_name = 'Wind Ensemble - composer'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# # Update the tags
# functions.update_tags(tags_df)