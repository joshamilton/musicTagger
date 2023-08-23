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

################################################################################
### Guess album-level tags
################################################################################

# Specify search dir
search_dir = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Classical - composer/00 - Renaissance'

# Find albums. Folders will have the pattern [yyyy] album (info). Only the [yyyy] part needs to matched.
pattern = re.compile(r'\[\d{4}\]')
album_list = []
for dirpath, dirnames, filenames in os.walk(search_dir):
    for dirname in dirnames:
        match = pattern.match(dirname)
        if match:
            album_list.append(dirname)

# Create dataframe to store album-level tags:
# Album, Year Released, Orchestra, Conductor, Composer, Genre
album_tags_df = pd.DataFrame(index = album_list, columns = ['Album', 'Year Released', \
                                                            'Orchestra', 'Conductor', \
                                                            'Soloists', 'Genre'])


### Rewrite to exlucde album and genre
### Album won't contain interpunct, pipe, and colon characters - extract from tag
### Genre may differ between tracks
# Loop over albums to extract tags
# Folders will have the pattern [yyyy] album (info). All parts needed
pattern = re.compile(r'\[(\d{4})\]\s(.+)\s\((.+)\)')
for album_info in album_list:
   foo, year, album, performer_info, bar = re.split(pattern, album_info)
   album_tags_df.loc[album_info, 'Album'] = album
   album_tags_df.loc[album_info, 'Year Released'] = year
   album_tags_df.loc[album_info, 'Genre'] = 'Renaissance' 
   # Process the performer_info (Orchestra, Conductor, Soloist tags)
   # Option 1: ensemble with conductor. Contains 'with' and lacks ','
   # Option 2: ensemble only. Lacks 'with' and ','
   # Option 3: soloists. Contains ',' and lacks 'with'
   if 'with' in performer_info and ',' in performer_info:
   elif 'with' in performer_info:
   elif ',' in performer_info:
       
       

album_tags_df.to_excel('tags.xlsx')


# ################################################################################
# ### Update tags
# ################################################################################

# # Read in the Excel file containing updated tags
# file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
# sheet_name = 'Wind Ensemble - composer'
# tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# # Update the tags
# update_tags(tags_df)