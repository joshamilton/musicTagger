################################################################################
### functions.py
### Copyright (c) 2023, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import os
import re
import mutagen
import mutagen.flac
import mutagen.easyid3
import pandas as pd
import xlsxwriter

################################################################################
### Define functions
################################################################################

### Function to get file list and create empty dataframe
def get_tracks_create_dataframe(search_dir):
    # Find tracks: end in .flac
    track_path_list = []
    for dirpath, dirnames, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                track_path_list.append(os.path.join(dirpath, file))
    track_path_list = sorted(track_path_list)

    # Create dataframe to store track-level tags:
    # Some fields can't get filled from existing tags. Retain them in the dataframe so I can manually fill them in later.
    track_tags_df = pd.DataFrame(index = track_path_list, columns = ['Composer', 'Album', 'Year Recorded',
                                                                    'Orchestra', 'Conductor', 'Soloists', 'Arranger', 
                                                                    'Genre',  'DiscNumber', 'TrackNumber', 'Title', 'TrackTitle',
                                                                    'Work', 'InitialKey', 'Catalog #', 'Opus', 'Number', 
                                                                    'Name', 'Movement'] )
    
    return track_tags_df

### Function to get track- and album-level tags
def get_album_track_tags(track_tags_df):

    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)')
    for track_path in track_tags_df.index:
        # Extract performer and year released info. All other is either encoded in tags, or must be added manually
        soloists = track_path.split('/')[8]
        album_info = track_path.split('/')[9] # can't split backwards, because some albums will have a Disc
        foo, year, album, bar = re.split(album_pattern, album_info)
            # Update tags
#        track_tags_df.loc[track_path, 'Year Released'] = year # No longer tracking this field
        # Process the performer_info (Orchestra, Conductor)
        track_tags_df.loc[track_path, 'Soloists'] = soloists

        # Extract disc info and track numbers
        # Must check track path b/c albums are not always tagged with the Disc #
        if 'Disc' in track_path: 
            disc_number = re.search(r'Disc\s\d+', track_path).group(0).split(' ')[1]
            track_tags_df.loc[track_path, 'DiscNumber'] = disc_number
        track_number, track_info = track_path.split('/')[-1].replace('.flac', '').split(' - ', 1)
        track_tags_df.loc[track_path, 'TrackNumber'] = track_number

        # Extract title for processing
        # Enclose in a try block, in case file hasn't already been tagged by me
        try:
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
        except:
            pass

        # Update with other fields pulled from the tags
        # Album, Composer, Genre, Year Recorded
        # Again enclose in a try block, in case file hasn't already been tagged by me
        try:
            track_tags_df.loc[track_path, 'Album'] = mutagen.flac.FLAC(track_path)['album'][0]
            track_tags_df.loc[track_path, 'Composer'] = mutagen.flac.FLAC(track_path)['artist'][0]
            track_tags_df.loc[track_path, 'Genre'] = mutagen.flac.FLAC(track_path)['genre'][0]
            track_tags_df.loc[track_path, 'Year Recorded'] = mutagen.flac.FLAC(track_path)['date'][0]
        except:
            pass

    # Use XLSXwriter engine to allow for foreign-language characters
    track_tags_df.to_excel('track_tags.xlsx', engine = 'xlsxwriter')

    return

### Function to get track-and album-level tags following initial update
### Used to ensure consistency across tracks that were added in batches
def get_album_track_tags_second_round(track_tags_df):
    tags = ['Composer', 'Album', 'Year Recorded',
            'Orchestra', 'Conductor', 'Soloists', 'Arranger', 
            'Genre',  'DiscNumber', 'TrackNumber', 'Title', 'TrackTitle',
            'Work', 'InitialKey', 'Catalog #', 'Opus', 'Number', 
            'Name', 'Movement']

    total_tracks = len(track_tags_df.index)
    processed_tracks = 0
    last_progress = 0

    for track_path in track_tags_df.index:
        try:
            audio = mutagen.flac.FLAC(track_path)
            
            # Extract all available tags using exact names
            for tag in tags:
                if tag in audio:
                    track_tags_df.at[track_path, tag] = audio[tag][0]
                
        except Exception as e:
            print(f"Error processing {track_path}: {str(e)}")
        
        # Update progress
        processed_tracks = processed_tracks + 1
        current_progress = (processed_tracks * 100) // total_tracks
        
        # Only print when progress percentage changes
        if current_progress > last_progress:
            print(f"Progress: {current_progress}% ({processed_tracks}/{total_tracks} tracks processed)")
            last_progress = current_progress

    # Use XLSXwriter engine to allow for foreign-language characters
    track_tags_df.to_excel('track_tags.xlsx', engine='xlsxwriter')
    print("Completed! All tracks processed and Excel file generated.")

    return

### Update tags
def update_tags(tags_df):

    # Iterator
    total_files = len(tags_df)
    processed_files = 0
    last_progress = -1

    for index, row in tags_df.iterrows():
        file_path = row['File']

        # Delete all ID3 tags
        try:
            audio_file = mutagen.easyid3.EasyID3(file_path)
            audio_file.delete()
        except:
            pass

        # Delete all FLAC tags
        audio_file = mutagen.flac.FLAC(file_path)
        audio_file.delete()
        # Add new ones
        for tag, value in row.iloc[1:].items():
            # Check for missing values
            if value != 'nan':
                audio_file[tag] = value
        # Save results
        audio_file.save()

        # Update progress
        processed_files += 1
        current_progress = (processed_files * 100) // total_files
        
        # Only print when progress percentage changes
        if current_progress > last_progress:
            print(f"Progress: {current_progress}% ({processed_files}/{total_files} files processed, {updated_files} updated)")
            last_progress = current_progress

    print(f"\nCompleted! Processed {processed_files} files.")


def update_tags_second_round(original_df, new_df):
    # Ensure both dataframes use file_path as index for easier comparison
    original_df = original_df.set_index('File') if 'File' in original_df.columns else original_df
    new_df = new_df.set_index('File') if 'File' in new_df.columns else new_df
    
    # Find common files
    common_files = set(original_df.index) & set(new_df.index)
    total_files = len(common_files)
    processed_files = 0
    updated_files = 0
    last_progress = -1

    for file_path in common_files:
        changes_needed = False
        original_row = original_df.loc[file_path]
        new_row = new_df.loc[file_path]
        
        # Compare tags
        for column in new_df.columns:
            if column != 'file_path':  # Skip the file path column if it exists
                original_value = str(original_row.get(column, 'nan'))
                new_value = str(new_row.get(column, 'nan'))
                
                if original_value != new_value and new_value != 'nan':
                    changes_needed = True
                    break
        
        if changes_needed:
            try:
                # Delete all ID3 tags
                try:
                    audio_file = mutagen.easyid3.EasyID3(file_path)
                    audio_file.delete()
                except:
                    pass

                # Delete and update FLAC tags
                audio_file = mutagen.flac.FLAC(file_path)
                audio_file.delete()
                
                # Add new tags
                for tag, value in new_row.items():
                    if str(value) != 'nan':
                        audio_file[tag] = str(value)
                
                audio_file.save()
                updated_files += 1
                
            except Exception as e:
                print(f"Error updating {file_path}: {str(e)}")
        
        # Update progress
        processed_files += 1
        current_progress = (processed_files * 100) // total_files
        
        # Only print when progress percentage changes
        if current_progress > last_progress:
            print(f"Progress: {current_progress}% ({processed_files}/{total_files} files processed, {updated_files} updated)")
            last_progress = current_progress

    print(f"\nCompleted! Processed {processed_files} files, updated {updated_files} files.")
    return updated_files