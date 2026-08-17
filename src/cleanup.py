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
from collections import defaultdict

from mutagen.flac import FLAC
from tqdm import tqdm

from read import ALLOWED_TAGS

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

def generate_report(files_to_rename, files_to_delete, busy_files_rename, busy_files_delete, output_dir):
    with open(os.path.join(output_dir, "rename.txt"), "w") as rename_file:
        rename_file.write("Files to be renamed:\n")
        for file in files_to_rename:
            base, ext = os.path.splitext(file)
            rename_file.write(f"{file} -> {base + ext.lower()}\n")
    
    with open(os.path.join(output_dir, "delete.txt"), "w") as delete_file:
        delete_file.write("Files to be deleted:\n")
        for file in files_to_delete:
            delete_file.write(f"{file}\n")
    
    with open(os.path.join(output_dir, "busy.txt"), "w") as busy_file:
        busy_file.write("Files that are busy and could not be processed:\n")
        busy_file.write("Renaming:\n")
        for file in busy_files_rename:
            busy_file.write(f"{file}\n")
        busy_file.write("\nDeleting:\n")
        for file in busy_files_delete:
            busy_file.write(f"{file}\n")

def generate_missing_files_report(directory, output_dir):
    print('Generating missing files report...')
    report_data = []
    for root, _, files in os.walk(directory):
        has_flac = any(file.lower().endswith('.flac') for file in files)
        if has_flac:
            has_log = any(file.lower().endswith('.log') for file in files)
            has_cue = any(file.lower().endswith('.cue') for file in files)
            if not has_log or not has_cue:
                report_data.append([root, 'Yes' if has_log else 'No', 'Yes' if has_cue else 'No'])

    with open(os.path.join(output_dir, "missing.csv"), "w", newline='', encoding='utf-8-sig') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Folder', 'Log', 'Cue'])
        csvwriter.writerows(report_data)

def find_disallowed_tags(directory):
    """Scan FLAC tags under directory; list every tag key not in ALLOWED_TAGS."""
    print('Scanning FLAC tags for disallowed fields...')
    allowed_lower = {name.lower() for name in ALLOWED_TAGS}
    actions = []
    errors = []
    flac_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files if file.lower().endswith('.flac')
    ]
    for path in tqdm(sorted(flac_paths), desc="Scanning FLAC tags"):
        try:
            audio = FLAC(path)
        except Exception as e:
            errors.append(f"{path}: failed to open ({e})")
            continue
        if audio.tags is None:
            continue
        for key in audio.tags.keys():
            if key.lower() not in allowed_lower:
                actions.append({'path': path, 'tag': key})
    return actions, errors

def write_tag_report(actions, output_dir):
    with open(os.path.join(output_dir, "tags.csv"), "w", newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['path', 'tag'])
        for action in actions:
            writer.writerow([action['path'], action['tag']])

def apply_tag_actions(actions):
    """Remove the planned disallowed tags from each affected file."""
    errors = []
    by_path = defaultdict(set)
    for action in actions:
        by_path[action['path']].add(action['tag'].lower())

    for path, remove_lower in tqdm(by_path.items(), desc="Stripping tags"):
        try:
            audio = FLAC(path)
        except Exception as e:
            errors.append(f"{path}: failed to open ({e})")
            continue
        if audio.tags is None:
            continue
        tags_to_keep = {
            key: value for key, value in audio.tags.items()
            if key.lower() not in remove_lower
        }
        try:
            audio.delete()
            for key, value in tags_to_keep.items():
                audio[key] = value
            audio.save()
        except Exception as e:
            errors.append(f"{path}: failed to save ({e})")
    return errors

################################################################################
### Define run function
################################################################################

def run(args):
    """
    Run cleanup: rename uppercase extensions, delete non-music files, report
    missing cues/logs, and strip any FLAC tag not in read.ALLOWED_TAGS.

    Args:
        args (argparse.Namespace): Parsed arguments with dir and dry_run.
    """
    files_to_rename, files_to_delete = get_files_to_process(args.dir)

    if args.dry_run:
        generate_report(files_to_rename, files_to_delete, [], [], args.dir)
        print(f"Dry run complete. {len(files_to_rename)} files to be renamed and {len(files_to_delete)} files to be deleted.")
    else:
        busy_files_rename = rename_files(files_to_rename)
        busy_files_delete = delete_files(files_to_delete)
        generate_report(files_to_rename, files_to_delete, busy_files_rename, busy_files_delete, args.dir)
        print(f"Operation complete. {len(files_to_rename)} files renamed, {len(files_to_delete)} files deleted, and {len(busy_files_rename) + len(busy_files_delete)} files could not be processed due to being busy.")

    generate_missing_files_report(args.dir, args.dir)
    print("Missing files report generated.")

    tag_actions, tag_errors = find_disallowed_tags(args.dir)
    write_tag_report(tag_actions, args.dir)
    affected_files = len({action['path'] for action in tag_actions})
    if args.dry_run:
        print(f"Dry run: {len(tag_actions)} disallowed tag(s) across {affected_files} file(s) would be removed.")
    else:
        tag_errors.extend(apply_tag_actions(tag_actions))
        print(f"Tag cleanup complete. {len(tag_actions)} disallowed tag(s) removed across {affected_files} file(s).")
    for message in tag_errors:
        print(f"Error: {message}")
