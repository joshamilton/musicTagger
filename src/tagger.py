################################################################################
### tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import os
import sys
import pandas as pd
import cleanup
import convert
import read
import structure
import write
from predict import DataManager

################################################################################
### Define functions
################################################################################

def validate_inputs(args):
    """
    Validate inputs for tagger commands.
    For read: ensures that a valid directory path is given
    For read: ensures that the output Excel file path is valid
    For write: ensures that the input Excel file path is valid
    For write: ensures that the output Excel file path is valid
    For cleanup: ensures that a valid directory path is given
    For convert: ensures that either a valid directory or file list is given
    For structure: ensures that a valid directory path is given

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        ValueError: If any of the input arguments are invalid.
    """
    if args.command == 'read':
        if not args.dir or not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
        if not args.excel_out:
            raise ValueError("Invalid or missing file path for writing tag information.")
        output_dir = os.path.dirname(args.excel_out) or '.'  # Default to current directory if no directory given
        if not args.excel_out or not os.path.isdir(output_dir):
            raise ValueError("Invalid or missing file path for writing tag information.")
    elif args.command == 'write':
        if not args.excel_in or not os.path.isfile(args.excel_in):
            raise ValueError("Invalid or missing file path for reading tag information.")
        if not args.excel_out:
            raise ValueError("Invalid or missing file path for writing failed tags.")
        output_dir = os.path.dirname(args.excel_out) or '.'  # Default to current directory if no directory given
        if not args.excel_out or not os.path.isdir(output_dir):
            raise ValueError("Invalid or missing file path for writing failed tags.")
    elif args.command == 'cleanup':
        if not args.dir or not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
    elif args.command == 'convert':
        if not args.dir and not args.file_list:
            raise ValueError("You must specify either --dir or --file-list.")
        if args.dir and not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
        if args.file_list and not os.path.isfile(args.file_list):
            raise ValueError("Invalid or missing file list path.")
    elif args.command == 'structure':
        if not args.dir or not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
    else:
        raise ValueError("Invalid command.")
    
def main():
    """Command-line utility for classical music file tagging and maintenance"""

    parser = argparse.ArgumentParser(description='Classical music file tagger')
    subparsers = parser.add_subparsers(dest='command', required=True)

    read_parser = subparsers.add_parser('read', help='Read tags from music files')
    read_parser.add_argument('--dir', '-d', required=True,
                             help='Directory containing music files')
    read_parser.add_argument('--excel_out', '-o', required=True,
                             help='Excel file path for writing tag information')
    read_parser.add_argument('--store_data', action='store_true',
                             help='Archive tag data during operations')

    write_parser = subparsers.add_parser('write', help='Write tags to music files')
    write_parser.add_argument('--excel_in', '-i', required=True,
                              help='Excel file path for reading tag information')
    write_parser.add_argument('--excel_out', '-o', required=True,
                              help='Excel file path for writing failed tags')
    write_parser.add_argument('--store_data', action='store_true',
                              help='Archive tag data during operations')

    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up non-music files and normalize extensions')
    cleanup_parser.add_argument('--dir', '-d', required=True,
                                help='Directory containing music files')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                                help='Generate a report without making changes')

    convert_parser = subparsers.add_parser('convert', help='Convert FLAC files to 16 bit 44 kHz')
    convert_parser.add_argument('--dir', '-d',
                                help='Directory to scan for FLAC files')
    convert_parser.add_argument('--file-list',
                                help='CSV file containing a list of files to convert')
    convert_parser.add_argument('--dry-run', action='store_true',
                                help='Generate a report of files to convert without converting')
    convert_parser.add_argument('--overwrite', action='store_true',
                                help='Overwrite the original files after conversion')

    structure_parser = subparsers.add_parser('structure', help='Organize album directories and Scans.pdf')
    structure_parser.add_argument('--dir', '-d', required=True,
                                  help='Directory containing music files')
    structure_parser.add_argument('--mode', required=True,
                                  choices=['make_scans', 'fix_scans', 'rename_dirs', 'cleanup', 'all'],
                                  help='Mode of operation')
    structure_parser.add_argument('--dry-run', action='store_true',
                                  help='Perform a dry run without making changes')
    structure_parser.add_argument('--output-csv',
                                  help='Path to the output CSV file (default: output.csv in --dir)')

    args = parser.parse_args()

    try:
        # Validate inputs
        validate_inputs(args)

        if args.command == 'read':
            data_mgr = DataManager() if args.store_data else None
            # Create dataframe and get tags
            tags_df = read.get_tracks_create_dataframe(args.dir)
            tags_df = read.get_tags(tags_df, data_mgr)
            # Use XLSXwriter engine to allow for foreign-language characters
            tags_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            print(f"Tags saved to {args.excel_out}")
            
        elif args.command == 'write':
            data_mgr = DataManager() if args.store_data else None
            # Read tags from Excel and update files
            tags_df = pd.read_excel(args.excel_in, dtype=str, index_col=0)
            tags_df = tags_df.fillna('')
            successful_df, failed_df = write.update_tags(tags_df, data_mgr)
            # Use XLSXwriter engine to allow for foreign-language characters
            failed_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            print(f"Failed tags saved to {args.excel_out}")

        elif args.command == 'cleanup':
            cleanup.run(args)

        elif args.command == 'convert':
            convert.run(args)

        elif args.command == 'structure':
            structure.run(args)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
