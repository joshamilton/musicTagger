################################################################################
### write.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################


################################################################################
### Import packages
################################################################################
import os
import pandas as pd
import re
import unicodedata
import mutagen
import mutagen.flac
import mutagen.easyid3
from tqdm import tqdm  # For better progress tracking

from utils import get_audio_md5, is_missing_checksum, repair_missing_checksum

################################################################################
### Define functions
################################################################################

### Build title tag
def build_title(work, work_number='', catalog_number='', opus='', opus_number='',
                 initial_key='', epithet='', movement=''):
    """
    Build the Title tag from its component fields.

    General logic: Start with the work as the initial part of the title.
    Append each piece of metadata if it is not empty. Join all parts to
    form the final title, normalized to a single consistent Unicode form.

    Args:
        work (str): Work name.
        work_number (str): Work number, e.g. "No 2".
        catalog_number (str): Catalog number, e.g. "BWV 1006".
        opus (str): Opus, e.g. "Op 27".
        opus_number (str): Opus number, e.g. "No 2".
        initial_key (str): Key signature, e.g. "C minor".
        epithet (str): Epithet, e.g. "Moonlight".
        movement (str): Movement, e.g. "I. Allegro".

    Returns:
        str: The assembled title, normalized to NFC.
    """
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
    return unicodedata.normalize('NFC', title)

### Build filename
def build_safe_filename(track_number, title, extension='.flac', max_bytes=255):
    """
    Build a filesystem-safe filename from a track number and title.

    Replaces characters that are forbidden in filenames, then shortens the
    title if needed so the full filename fits within max_bytes when UTF-8
    encoded (some tracks span multiple works and their Title tag legitimately
    exceeds the filesystem's filename length limit; the tag itself is left
    untouched, only the on-disk filename is shortened). Truncation happens on
    a UTF-8 character boundary so multi-byte characters are never split.

    Args:
        track_number (str): Track number, zero-padded as desired.
        title (str): Title text to use for the filename.
        extension (str): File extension, including the leading dot.
        max_bytes (int): Maximum filename length in UTF-8 bytes.

    Returns:
        str: A filename of the form "{track_number} - {title}{extension}",
            truncated if necessary to fit within max_bytes.
    """
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    prefix = f"{track_number} - "
    budget = max_bytes - len((prefix + extension).encode('utf-8'))
    encoded_title = safe_title.encode('utf-8')
    if len(encoded_title) > budget:
        safe_title = encoded_title[:budget].decode('utf-8', errors='ignore')
    return f"{prefix}{safe_title}{extension}"

### Compare filenames
def filenames_match(name_a, name_b):
    """
    Compare two filenames as Unicode text, treating names that differ only by
    normalization form (e.g. NFD vs NFC accented characters) as equal.

    Some network shares always store accented filenames in decomposed (NFD)
    form no matter what encoding a rename request uses, so a rename that
    would only change normalization form can never actually take effect.
    Callers should skip renaming when this returns True.

    Args:
        name_a (str): First filename to compare.
        name_b (str): Second filename to compare.

    Returns:
        bool: True if the names are equal once both are normalized to NFC.
    """
    return unicodedata.normalize('NFC', name_a) == unicodedata.normalize('NFC', name_b)

### Update tags
def update_tags(tags_df):
    """
    Update tags by reading from an Excel file.

    Also repairs a missing (all-zero) audio checksum on a file before
    writing its tags, so newly-encoded files get a real checksum as soon as
    they're first tagged.

    Args:
        tags_df (pd.DataFrame): DataFrame with track paths as index and columns for tags.

    Returns:
        tuple: (successful_df, failed_df) containing the entries which were successfully processed and those which failed.
    """

    # Initialize tracking dataframes
    successful_paths = []
    failed_paths = []
    repaired_paths = []          # paths whose missing checksum was fixed before tagging
    still_missing_paths = []     # (path, reason) for missing checksums that could not be repaired

    # Iterator
    total_files = len(tags_df)
    print(f"Updating {total_files} files...")

    for file_path in tqdm(tags_df.index, total=total_files, desc="Writing tags"):

        # Repair a missing audio checksum before any tags are written, so a
        # newly-ripped/encoded file gets a real checksum as soon as it's first
        # tagged (catalog.py's own repair pass then only needs to catch
        # stragglers that never went through write). This must finish before
        # the FLAC object below is opened: that object caches whatever
        # checksum it sees at open time and rewrites that cached value on
        # save(), so opening it any earlier would let its later .save()
        # silently overwrite a same-iteration repair back to all-zero. This
        # probe never calls .save() on itself. A repair failure, or a file
        # that can't even be opened here, must not prevent tags from being
        # written and must not abort the loop -- an unreadable file is
        # still caught and reported by the block below, same as before.
        try:
            probe = mutagen.flac.FLAC(file_path)
            if is_missing_checksum(get_audio_md5(probe)):
                new_md5, error = repair_missing_checksum(file_path)
                if new_md5:
                    repaired_paths.append(file_path)
                else:
                    still_missing_paths.append((file_path, error))
        except Exception:
            pass

        # Delete all ID3 tags
        try:
            audio_file = mutagen.easyid3.EasyID3(file_path)
            audio_file.delete()
        # ID3 tags may not exist
        except:
            pass

        # Update FLAC tags
        try:
            # Delete all FLAC tags and images
            audio_file = mutagen.flac.FLAC(file_path)
            audio_file.delete()
            audio_file.clear_pictures()
            # Add new ones
            row = tags_df.loc[file_path]
            for tag, value in row.items():
                # Check for missing values
                if pd.notna(value) and value != '':
                    # Normalize accented characters to a single consistent form
                    # (source tags mix precomposed and decomposed encodings)
                    if isinstance(value, str):
                        value = unicodedata.normalize('NFC', value)
                    audio_file[tag] = value

            # Create Title tag from its component fields
            title = build_title(
                work=row.get('Work', ''),
                work_number=row.get('Work Number', ''),
                catalog_number=row.get('Catalog #', ''),
                opus=row.get('Opus', ''),
                opus_number=row.get('Opus Number', ''),
                initial_key=row.get('InitialKey', ''),
                epithet=row.get('Epithet', ''),
                movement=row.get('Movement', ''),
            )
            audio_file['Title'] = title

           # Save results
            audio_file.save()

            # Update tracking
            successful_paths.append(file_path)

            # Rename the track
            track_number = row.get('TrackNumber', '')
            track_number = track_number.zfill(2)  # Pad the track number to two digits
            new_file_name = build_safe_filename(track_number, title)
            current_file_name = os.path.basename(file_path)
            if not filenames_match(new_file_name, current_file_name):
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
    if repaired_paths:
        print(f"Repaired a missing audio checksum on {len(repaired_paths)} file(s) before tagging.")
    if still_missing_paths:
        print(f"{len(still_missing_paths)} file(s) are still missing an audio checksum "
              f"(tags were still written; rerun catalog to retry repair):")
        for path, reason in still_missing_paths:
            print(f"  {path}: {reason}")

    return successful_df, failed_df