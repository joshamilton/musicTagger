################################################################################
### tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import logging
import os
import sys
from datetime import datetime
import pandas as pd
import catalog
import cleanup
import convert
import read
import remove_flac
import standardize
import structure
import utils
import write

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
    For remove-flac: ensures that a valid directory path is given
    For convert: ensures that either a valid directory or file list is given
    For structure: ensures that a valid directory path is given
    For standardize: ensures that either a valid directory or file list is given
    For catalog: ensures that a valid directory path is given, and that the
        database output path is valid (the XLSX export path is derived from it)

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
    elif args.command == 'remove-flac':
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
    elif args.command == 'standardize':
        if not args.dir and not args.file_list:
            raise ValueError("You must specify either --dir or --file-list.")
        if args.dir and not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
        if args.file_list and not os.path.isfile(args.file_list):
            raise ValueError("Invalid or missing file list path.")
        if args.dry_run and args.file_list:
            raise ValueError("Do not combine --dry-run with --file-list.")
        if args.dry_run and not args.output_file:
            raise ValueError("--output-file is required when using --dry-run.")
        if args.output_file:
            output_dir = os.path.dirname(args.output_file) or '.'
            if not os.path.isdir(output_dir):
                raise ValueError("Invalid or missing directory for --output-file.")
        # Retag mapping CSVs require --dir; rename CSVs do not.
        if args.file_list and not args.dry_run:
            kind = standardize.detect_file_list_kind(args.file_list)
            if kind == 'retag' and (not args.dir or not os.path.isdir(args.dir)):
                raise ValueError("Retag --file-list requires a valid --dir.")
    elif args.command == 'catalog':
        if not args.dir or not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
        if not args.db:
            raise ValueError("Invalid or missing path for the catalog database.")
        db_dir = os.path.dirname(args.db) or '.'
        if not os.path.isdir(db_dir):
            raise ValueError("Invalid or missing path for the catalog database.")
    else:
        raise ValueError("Invalid command.")
    
def build_log_parent_parser():
    """
    Build a parent parser providing the --log-level and --log-file flags
    shared by every subcommand.

    Returns:
        argparse.ArgumentParser: Parent parser to pass via parents=[...] to
            each subcommand's parser.
    """
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Logging verbosity shown on screen (default: INFO)')
    parent.add_argument('--log-file', default=None,
                        help='Path to the log file (default: logs/<command>_<timestamp>.log in the repo root)')
    return parent

def main():
    """Command-line utility for classical music file tagging and maintenance"""

    log_parent = build_log_parent_parser()
    parser = argparse.ArgumentParser(description='Classical music file tagger')
    subparsers = parser.add_subparsers(dest='command', required=True)

    read_parser = subparsers.add_parser('read', help='Read tags from music files', parents=[log_parent])
    read_parser.add_argument('--dir', '-d', required=True,
                             help='Directory containing music files')
    read_parser.add_argument('--excel_out', '-o', required=True,
                             help='Excel file path for writing tag information')

    write_parser = subparsers.add_parser('write', help='Write tags to music files', parents=[log_parent])
    write_parser.add_argument('--excel_in', '-i', required=True,
                              help='Excel file path for reading tag information')
    write_parser.add_argument('--excel_out', '-o', required=True,
                              help='Excel file path for writing failed tags')

    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up non-music files and normalize extensions', parents=[log_parent])
    cleanup_parser.add_argument('--dir', '-d', required=True,
                                help='Directory containing music files')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                                help='Generate a report without making changes')

    remove_flac_parser = subparsers.add_parser('remove-flac', help='Delete FLAC, log, cue, and image/playlist files (post-conversion cleanup)', parents=[log_parent])
    remove_flac_parser.add_argument('--dir', '-d', required=True,
                                    help='Directory containing music files')

    convert_parser = subparsers.add_parser('convert', help='Convert FLAC files to 16 bit 44 kHz', parents=[log_parent])
    convert_parser.add_argument('--dir', '-d',
                                help='Directory to scan for FLAC files')
    convert_parser.add_argument('--file-list',
                                help='CSV file containing a list of files to convert')
    convert_parser.add_argument('--dry-run', action='store_true',
                                help='Generate a report of files to convert without converting')
    convert_parser.add_argument('--overwrite', action='store_true',
                                help='Overwrite the original files after conversion')

    structure_parser = subparsers.add_parser('structure', help='Organize album directories and Scans.pdf', parents=[log_parent])
    structure_parser.add_argument('--dir', '-d', required=True,
                                  help='Directory containing music files')
    structure_parser.add_argument('--mode', required=True,
                                  choices=['make_scans', 'fix_scans', 'rename_dirs', 'cleanup', 'all'],
                                  help='Mode of operation')
    structure_parser.add_argument('--dry-run', action='store_true',
                                  help='Perform a dry run without making changes')
    structure_parser.add_argument('--output-csv',
                                  help='Path to the output CSV file (default: output.csv in --dir)')

    standardize_parser = subparsers.add_parser(
        'standardize',
        help='Normalize disc/album folders and retag from mapping CSVs',
        parents=[log_parent],
    )
    standardize_parser.add_argument('--dir', '-d',
                                    help='Directory containing music files')
    standardize_parser.add_argument(
        '--file-list',
        help=(
            'CSV to apply: rename plan (path, original_name, new_name) or '
            'retag map (original_*/new_*); retag requires --dir'
        ),
    )
    standardize_parser.add_argument('--dry-run', action='store_true',
                                    help='Write planned/flagged renames without making changes')
    standardize_parser.add_argument(
        '--output-file',
        help='CSV report of planned/flagged renames (required with --dry-run)',
    )

    catalog_parser = subparsers.add_parser(
        'catalog',
        help='Build/update a database and CSV catalog of tagged tracks',
        parents=[log_parent],
    )
    catalog_parser.add_argument('--dir', '-d', required=True,
                                help='Directory containing music files')
    catalog_parser.add_argument('--db', required=True,
                                help='Path to the SQLite catalog database; .db is appended if omitted '
                                     '(catalog -> catalog.db), and the XLSX export is written alongside '
                                     'it (catalog.xlsx)')
    catalog_parser.add_argument('--prune', action='store_true',
                                help='Remove catalog rows for tracks no longer found in --dir')

    args = parser.parse_args()

    log_file = args.log_file
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(utils.get_repo_root(), 'logs', f'{args.command}_{timestamp}.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    utils.setup_logging(args.log_level, log_file)
    logger = logging.getLogger(__name__)

    try:
        # Validate inputs
        validate_inputs(args)

        if args.command == 'read':
            # Create dataframe and get tags
            tags_df = read.get_tracks_create_dataframe(args.dir)
            tags_df = read.get_tags(tags_df)
            # Use XLSXwriter engine to allow for foreign-language characters
            tags_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            logger.info(f"Tags saved to {args.excel_out}")

        elif args.command == 'write':
            # Read tags from Excel and update files
            tags_df = pd.read_excel(args.excel_in, dtype=str, index_col=0)
            tags_df = tags_df.fillna('')
            successful_df, failed_df = write.update_tags(tags_df)
            # Use XLSXwriter engine to allow for foreign-language characters
            failed_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            logger.info(f"Failed tags saved to {args.excel_out}")

        elif args.command == 'cleanup':
            cleanup.run(args)

        elif args.command == 'remove-flac':
            remove_flac.run(args)

        elif args.command == 'convert':
            convert.run(args)

        elif args.command == 'structure':
            structure.run(args)

        elif args.command == 'standardize':
            standardize.run(args)

        elif args.command == 'catalog':
            catalog.run(args)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
