################################################################################
### main.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import os
import pandas as pd
import re
from functions import update_tags
from functions import get_album_tags_renaissance

################################################################################
### Guess album-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'
get_album_tags_renaissance(search_dir)

################################################################################
### Guess track-level tags
################################################################################

# # Specify search dir
# search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'

# # Find tracks: end in .flac
# track_list = []
# for dirpath, dirnames, filenames in os.walk(search_dir):
#     for file in filenames:
#         if file.endswith('.flac'):
#             track_list.append(os.path.join(search_dir, file))

# # Create dataframe to store album-level tags:
# # Album, Year Released, Orchestra, Conductor, Composer, Genre
# track_tags_df = pd.DataFrame(index = track_list, columns = ['Year Released', 'Album', \
#                                                             'Orchestra', 'Conductor', \
#                                                             'Soloists', 'Genre'])

# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
# sheet_name = 'Wind Ensemble - composer'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# # Update the tags
# update_tags(tags_df)