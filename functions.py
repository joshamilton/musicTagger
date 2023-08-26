################################################################################
### functions.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import mutagen
import mutagen.flac
import os
import pandas as pd
import re

################################################################################
### Define functions
################################################################################

### Get album-level tags for Renaissance music
def get_album_tags_renaissance(search_dir):

    # Find albums. Folders will have the pattern [yyyy] album (info). Only the [yyyy] part needs to matched.
    year_pattern = re.compile(r'\[\d{4}\]')
    album_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for dirname in dirnames:
            match = year_pattern.match(dirname)
            if match:
                album_path_list.append(os.path.join(dirpath, dirname))
    album_path_list = sorted(album_path_list)
    # Create dataframe to store album-level tags:
    # Album, Year Released, Orchestra, Conductor, Composer, Genre
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    album_tags_df = pd.DataFrame(index = album_path_list, columns = ['Composer', 'Year Released', 'Album', \
                                                                'Orchestra', 'Conductor', 'Soloists', 'Genre', 
                                                                'Record Label'])

    # Loop over albums to extract tags
    # Folders will have the pattern [yyyy] album (info). All parts needed
    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)\s\((.+)\)')
    for album_path in album_path_list:
        # Extract composer and album info
        composer = album_path.split('/')[-2]
        album_info = album_path.split('/')[-1]
        foo, year, album, performer_info, bar = re.split(album_pattern, album_info)
            # Update tags
        album_tags_df.loc[album_path, 'Composer'] = composer
        album_tags_df.loc[album_path, 'Album'] = album # TO DO: exclude b/c album won't contain interpunct, pipe, and colon characters
        album_tags_df.loc[album_path, 'Year Released'] = year
        album_tags_df.loc[album_path, 'Genre'] = 'Renaissance' # TO DO: exclude b/c genre may differ between tracks
        # Process the performer_info (Orchestra, Conductor, Soloist tags)
        # Option 1: ensemble with conductor. Contains 'with' and lacks ','
        # Option 2: ensemble only. Lacks 'with' and ','
        # Option 3: soloists. Contains ',' and lacks 'with'
        if 'with' in performer_info and ',' not in performer_info:
            ensemble, conductor = re.split(' with ', performer_info)
            album_tags_df.loc[album_path, 'Orchestra'] = ensemble
            album_tags_df.loc[album_path, 'Conductor'] = conductor
        elif 'with' not in performer_info and ',' not in performer_info:
            ensemble = performer_info
            album_tags_df.loc[album_path, 'Orchestra'] = ensemble
        elif 'with' not in performer_info and ',' in performer_info:
            soloists = performer_info.replace(', ', ';')
            album_tags_df.loc[album_path, 'Soloists'] = soloists
    
    album_tags_df.to_excel('album_tags.xlsx')
    return(album_tags)

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
