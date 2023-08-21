################################################################################
### main.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import pandas as pd
from functions import update_tags

################################################################################
### Update tags
################################################################################

# Read in the Excel file containing updated tags
file_path = '/Volumes/TheLibrary/Audio/Lossless-Classical-Untagged/Tagging.xlsx'
sheet_name = 'Wind Ensemble - composer'
tags_df = pd.read_excel(file_path, sheet_name = sheet_name).astype(str) # convert to string for some reason

# Update the tags
update_tags(tags_df)