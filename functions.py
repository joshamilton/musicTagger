################################################################################
### functions.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import mutagen
import mutagen.flac
import pandas as pd

################################################################################
### Define functions
################################################################################

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
