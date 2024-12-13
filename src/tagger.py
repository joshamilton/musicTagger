################################################################################
### tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

import argparse
import os
import sys
import pandas as pd
import functions

def validate_inputs(args):
    """Validate inputs for read and write modes."""
    if args.mode == 'read':
        if not args.dir or not os.path.isdir(args.dir):
            raise ValueError("Invalid or missing directory path containing music files.")
        if not args.excel_out:
            raise ValueError("Invalid or missing file path for writing tag information.")
        output_dir = os.path.dirname(args.excel_out) or '.'  # Default to current directory if no directory given
        if not args.excel_out or not os.path.isdir(output_dir):
            raise ValueError("Invalid or missing file path for writing tag information.")
    elif args.mode == 'write':
        if not args.excel_in or not os.path.isfile(args.excel_in):
            raise ValueError("Invalid or missing file path for reading tag information.")
        if not args.excel_out:
            raise ValueError("Invalid or missing file path for writing failed tags.")
        output_dir = os.path.dirname(args.excel_out) or '.'  # Default to current directory if no directory given
        if not args.excel_out or not os.path.isdir(output_dir):
            raise ValueError("Invalid or missing file path for writing failed tags.")
    else:
        raise ValueError("Invalid mode. Choose 'read' or 'write'.")
    
def main():
    """Command-line utility to read or write tags from/to music files"""

    parser = argparse.ArgumentParser(description='Classical music file tagger')
    parser.add_argument('mode', choices=['read', 'write'], help='Operation mode: read tags or write tags')
    parser.add_argument('--dir', '-d', required=False, help='Directory containing music files')
    parser.add_argument('--excel_in', '-i', required=False, help='Excel file path for reading tag information')
    parser.add_argument('--excel_out', '-o', required=True, help='Excel file path for writing tag information')

    args = parser.parse_args()

    try:
        # Validate inputs
        validate_inputs(args)

        if args.mode == 'read':
            # Create dataframe and get tags
            tags_df = functions.get_tracks_create_dataframe(args.dir)
            tags_df = functions.get_tags(tags_df)
            # Use XLSXwriter engine to allow for foreign-language characters
            tags_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            print(f"Tags saved to {args.excel_out}")
            
        elif args.mode == 'write':
            # Read tags from Excel and update files
            tags_df = pd.read_excel(args.excel_in, dtype=str, index_col=0)
            tags_df = tags_df.fillna('')
            successful_df, failed_df = functions.update_tags(tags_df)
            # Use XLSXwriter engine to allow for foreign-language characters
            failed_df.to_excel(args.excel_out, engine = 'xlsxwriter')
            print(f"Failed tags saved to {args.excel_out}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()