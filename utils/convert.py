################################################################################
### cleanup.py
### Copyright (c) 2025, Joshua J Hamilton
### This utility program finds 24 bit FLAC files and converts them to 16 bit,
### 44 kHz FLAC files using SoX. 
### The script features an "overwrite" option to replace the original files.
### The script can be run in dry-run mode to generate reports of files to be 
### converted and other FLAC files with different bit depths or sample rates.
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import csv
import os
import subprocess
from mutagen.flac import FLAC
from tqdm import tqdm

################################################################################
### Define functions
################################################################################

def get_flac_files(search_dir):
    """
    Get a list of FLAC files in the specified directory.

    Args:
        search_dir (str): Directory to search for FLAC files.

    Returns:
        list: List of FLAC file paths.
    """
    flac_files = []
    for dirpath, _, filenames in os.walk(search_dir):
        for file in filenames:
            if file.endswith('.flac'):
                flac_files.append(os.path.join(dirpath, file))
    return flac_files

def check_flac_metadata(file_path):
    """
    Check the bit depth and sample rate of a FLAC file.

    Args:
        file_path (str): Path to the FLAC file.

    Returns:
        tuple: (bit_depth, sample_rate)
    """
    audio = FLAC(file_path)
    bit_depth = audio.info.bits_per_sample
    sample_rate = audio.info.sample_rate
    return bit_depth, sample_rate

def convert_flac(file_path, output_path):
    """
    Convert a FLAC file to 16 bit 44 kHz using SoX.

    Args:
        file_path (str): Path to the input FLAC file.
        output_path (str): Path to the output FLAC file.
    """
    command = [
        'sox', file_path, 
        '-G', 
        '-b', '16', 
        output_path, 
        'rate', '-v', '-L', '44100', 
        'dither'
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return result.stderr.strip()
    if result.stderr:
        return result.stderr.strip()
    return None

def get_file_size(file_path):
    """
    Get the size of a file in bytes.

    Args:
        file_path (str): Path to the file.

    Returns:
        int: Size of the file in bytes.
    """
    return os.path.getsize(file_path)

################################################################################
### Define main function
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Convert FLAC files from 24 bit to 16 bit 44 kHz.")
    parser.add_argument('--dir', required=True, help="Directory to scan for FLAC files.")
    parser.add_argument('--dry-run', action='store_true', help="Generate a report of files to convert without converting.")
    parser.add_argument('--overwrite', action='store_true', help="Overwrite the original files after conversion.")
    args = parser.parse_args()

    flac_files = get_flac_files(args.dir)
    files_to_convert = []
    other_files = []
    total_size_to_convert = 0

    for file_path in flac_files:
        bit_depth, sample_rate = check_flac_metadata(file_path)
        if bit_depth == 24:
            files_to_convert.append((file_path, bit_depth, sample_rate))
            total_size_to_convert += get_file_size(file_path)
        elif bit_depth != 16 or sample_rate != 44100:
            other_files.append((file_path, bit_depth, sample_rate))

    if args.dry_run:
        with open("convert.csv", "w", newline='') as csvfile:
            fieldnames = ['file_path', 'bit_depth', 'sample_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for file, bit_depth, sample_rate in sorted(files_to_convert):
                writer.writerow({'file_path': file, 'bit_depth': bit_depth, 'sample_rate': sample_rate})
        
        with open("other.csv", "w", newline='') as csvfile:
            fieldnames = ['file_path', 'bit_depth', 'sample_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for file, bit_depth, sample_rate in sorted(other_files):
                writer.writerow({'file_path': file, 'bit_depth': bit_depth, 'sample_rate': sample_rate})
        
        print(f"Dry run complete. List of 24-bit files saved to convert.csv. List of files with other bitrates saved to other.csv.")
        print(f"Files to convert: {len(files_to_convert)}")
        print(f"Total size of files to convert: {total_size_to_convert / (1024 * 1024):.2f} MB")
        print(f"Other FLAC files: {len(other_files)}")
    else:
        errors = []
        total_space_saved = 0
        for file, _, _ in tqdm(files_to_convert, desc="Converting files"):
            try:
                original_size = get_file_size(file)
                output_path = file.replace('.flac', '_converted.flac')
                result = convert_flac(file, output_path)
                if result: # non-empty result indicates an error
                    errors.append((file, result))
                    continue
                converted_size = get_file_size(output_path)
                space_saved = original_size - converted_size
                total_space_saved += space_saved
                if args.overwrite:
                    os.remove(file)
                    os.rename(output_path, file)
            except Exception as e:
                errors.append((file, str(e)))

        if errors:
            with open("errors.csv", "w", newline='') as csvfile:
                fieldnames = ['file_path', 'error']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for file, error in errors:
                    writer.writerow({'file_path': file, 'error': error})
            print(f"Conversion complete with errors. Errors logged to errors.csv.")
        else:
            print(f"Conversion complete. All files processed successfully.")
        
        print(f"Files successfully converted: {len(files_to_convert) - len(errors)}")
        print(f"Files with errors: {len(errors)}")
        print(f"Total disk space saved: {total_space_saved / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    main()