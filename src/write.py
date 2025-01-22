################################################################################
### write.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################


################################################################################
### Import packages
################################################################################
import os
import re
import mutagen
import mutagen.flac
import mutagen.easyid3
from tqdm import tqdm  # For better progress tracking

################################################################################
### Define functions
################################################################################

### Update tags
def update_tags(tags_df, data_mgr = None):
    """
    Update tags by reading from an Excel file.

    Args:
        tags_df (pd.DataFrame): DataFrame with track paths as index and columns for tags.

    Returns:
        tuple: (successful_df, failed_df) containing the entries which were successfully processed and those which failed.
    """

    # Initialize tracking dataframes
    successful_paths = []
    failed_paths = []

    # Iterator
    total_files = len(tags_df)
    print(f"Updating {total_files} files...") 

    for file_path in tqdm(tags_df.index, total=total_files, desc="Writing tags"):

        # Delete all ID3 tags
        try:
            audio_file = mutagen.easyid3.EasyID3(file_path)
            audio_file.delete()
        # ID3 tags may not exist
        except:
            pass

        # Update FLAC tags
        try:
            # Delete all FLAC tags
            audio_file = mutagen.flac.FLAC(file_path)
            audio_file.delete()
            # Add new ones
            row = tags_df.loc[file_path]
            for tag, value in row.items():
                # Check for missing values
                if value != 'nan':
                    audio_file[tag] = value

            # Create Title tag
            # General logic: Start with the work as the initial part of the title.
            # Append each piece of metadata to the title_parts list if it is not empty.
            # Join all parts with spaces to form the final title.
            # Get all the metadata
            work = row.get('Work', '')
            work_number = row.get('Work Number', '')
            catalog_number = row.get('Catalog #', '')
            opus = row.get('Opus', '')
            opus_number = row.get('Opus Number', '')
            initial_key = row.get('InitialKey', '')
            epithet = row.get('Epithet', '')
            movement = row.get('Movement', '')
            title_parts = [work]
            if work_number:
                title_parts.append(f", {work_number}")
            if catalog_number:
                title_parts.append(f", {catalog_number}")
            if opus:
                title_parts.append(f", {opus}")
            if opus_number:
                title_parts.append(f", {opus_number}")
            if initial_key:
                title_parts.append(f", in {initial_key}")
            if epithet:
                title_parts.append(f", '{epithet}'")
            if movement:
                title_parts.append(f" - {movement}")

            title = ''.join(title_parts)
            audio_file['Title'] = title

           # Save results
            audio_file.save()

            # Update tracking and DataManager object
            successful_paths.append(file_path)
            if data_mgr:
                audio_file = mutagen.flac.FLAC(file_path)
                all_tags = dict(audio_file.tags)
                data_mgr.save_updated_tags(file_path, all_tags)

            # Rename the track
            track_number = row.get('TrackNumber', '')
            # Sanitize the title
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
            new_file_name = f"{track_number} - {safe_title}.flac"
            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
            os.rename(file_path, new_file_path)

        except Exception as e:
            failed_paths.append(file_path)
            print(e)
    
    # Create success/failure dataframes
    successful_df = tags_df.loc[successful_paths]
    failed_df = tags_df.loc[failed_paths]

    print(f"Completed!")
    print(f"Successfully processed: {len(successful_df)} files")
    print(f"Failed: {len(failed_df)} files")

    return successful_df, failed_df