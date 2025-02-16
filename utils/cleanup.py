################################################################################
### cleanup.py
### Copyright (c) 2025, Joshua J Hamilton
### This utility program finds and removes files that are not flac, cue, log or
### pdf. In addition, it renames files with uppercase extensions to lowercase.
### Finally, the script reports all albums that are missing either a flac or
### cue file.
### The script can be run in dry-run mode to generate a report without making
### any changes to the filesystem.
################################################################################

################################################################################
### Import packages
################################################################################
import csv
import os
import argparse
from tqdm import tqdm

################################################################################
### Define functions
################################################################################

def get_files_to_process(directory):
    print('Scanning directory for files to process...')
    files_to_rename = []
    files_to_delete = []
    valid_extensions = {'.flac', '.log', '.cue', '.pdf'}
    valid_files = {'README.txt', 'Setlist Info.txt'}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1]
            if (ext.lower() in valid_extensions) or (file in valid_files):
                if ext != ext.lower():
                    files_to_rename.append(file_path)
            else:
                files_to_delete.append(file_path)
    return files_to_rename, files_to_delete

def rename_files(files):
    busy_files = []
    for file in tqdm(files, desc="Renaming files"):
        base, ext = os.path.splitext(file)
        new_file = base + ext.lower()
        if file != new_file:
            temp_file = base + ".tmp"
            try:
                os.rename(file, temp_file)
                os.rename(temp_file, new_file)
            except OSError as e:
                if e.errno == 16:  # Resource busy
                    busy_files.append(file)
                else:
                    raise
    return busy_files

def delete_files(files):
    busy_files = []
    for file in tqdm(files, desc="Deleting files"):
        try:
            os.remove(file)
        except OSError as e:
            if e.errno == 16:  # Resource busy
                busy_files.append(file)
            else:
                raise
    return busy_files

def generate_report(files_to_rename, files_to_delete, busy_files_rename, busy_files_delete):
    with open("rename.txt", "w") as rename_file:
        rename_file.write("Files to be renamed:\n")
        for file in files_to_rename:
            base, ext = os.path.splitext(file)
            rename_file.write(f"{file} -> {base + ext.lower()}\n")
    
    with open("delete.txt", "w") as delete_file:
        delete_file.write("Files to be deleted:\n")
        for file in files_to_delete:
            delete_file.write(f"{file}\n")
    
    with open("busy.txt", "w") as busy_file:
        busy_file.write("Files that are busy and could not be processed:\n")
        busy_file.write("Renaming:\n")
        for file in busy_files_rename:
            busy_file.write(f"{file}\n")
        busy_file.write("\nDeleting:\n")
        for file in busy_files_delete:
            busy_file.write(f"{file}\n")

def generate_missing_files_report(directory):
    print('Generating missing files report...')
    report_data = []
    for root, _, files in os.walk(directory):
        has_flac = any(file.lower().endswith('.flac') for file in files)
        if has_flac:
            has_log = any(file.lower().endswith('.log') for file in files)
            has_cue = any(file.lower().endswith('.cue') for file in files)
            if not has_log or not has_cue:
                report_data.append([root, 'Yes' if has_log else 'No', 'Yes' if has_cue else 'No'])

    with open("missing.csv", "w", newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Folder', 'Log', 'Cue'])
        csvwriter.writerows(report_data)

################################################################################
### Define main function
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Cleanup script for music files.")
    parser.add_argument('--dir', required=True, help="Input directory to process")
    parser.add_argument('--dry-run', action='store_true', help="Generate a report without making changes")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Error: The directory '{args.dir}' does not exist.")
        return

    files_to_rename, files_to_delete = get_files_to_process(args.dir)

    if args.dry_run:
        generate_report(files_to_rename, files_to_delete, [], [])
        print(f"Dry run complete. {len(files_to_rename)} files to be renamed and {len(files_to_delete)} files to be deleted.")
    else:
        busy_files_rename = rename_files(files_to_rename)
        busy_files_delete = delete_files(files_to_delete)
        generate_report(files_to_rename, files_to_delete, busy_files_rename, busy_files_delete)
        print(f"Operation complete. {len(files_to_rename)} files renamed, {len(files_to_delete)} files deleted, and {len(busy_files_rename) + len(busy_files_delete)} files could not be processed due to being busy.")

    generate_missing_files_report(args.dir)
    print("Missing files report generated.")
    
if __name__ == "__main__":
    main()
