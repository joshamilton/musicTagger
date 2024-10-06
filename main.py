################################################################################
### main.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import functions
import pandas as pd

import os
import re
import mutagen
import mutagen.flac
import mutagen.easyid3
import pandas as pd
import xlsxwriter

###############################################################################
## Combination function to extract album- and track-level tags
###############################################################################

# # Specify search dir
# search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical/Classical - composer/01 - Baroque/Bach, Johann Sebastian/'
# # Extract tags from metadata
# track_tags_df = functions.get_tracks_create_dataframe(search_dir)
# # Get the tags and write to file
# functions.get_album_track_tags(track_tags_df)
# functions.get_album_track_tags_second_round(track_tags_df)


# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Users/joshamilton/Documents/Personal/classical_music/Tagging - in Progress.xlsx'
# sheet_name = 'Complete'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name, dtype = str) # convert to string for some reason
# tags_df = tags_df.fillna('') # replace NAs so they don't get written e.g., if there is no Disc tag

# # Update the tags
# functions.update_tags(tags_df)

################################################################################
### Used to ensure consistency across tracks that were added in batches
################################################################################

# Read in the Excel file containing original tags
file_path = '/Users/joshamilton/Documents/Personal/classical_music/tagging/track_tags.xlsx'
sheet_name = 'Sheet1'
orig_tags_df = pd.read_excel(file_path, sheet_name = sheet_name, dtype = str) # convert to string for some reason
orig_tags_df = orig_tags_df.fillna('') # replace NAs so they don't get written e.g., if there is no Disc tag

# Read in the Excel file containing oupdated tags
file_path = '/Users/joshamilton/Documents/Personal/classical_music/tagging/track_tags_revised.xlsx'
sheet_name = 'Sheet1'
new_tags_df = pd.read_excel(file_path, sheet_name = sheet_name, dtype = str) # convert to string for some reason
new_tags_df = new_tags_df.fillna('') # replace NAs so they don't get written e.g., if there is no Disc tag

# Update the tags
functions.update_tags_second_round(orig_tags_df, new_tags_df)