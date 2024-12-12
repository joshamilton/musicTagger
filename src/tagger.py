################################################################################
### tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

import argparse
import os
import sys
import pandas as pd
import functions

def validate_inputs(mode, dir_path, excel_in, excel_out):
    """Validate inputs for read and write modes."""
    if mode == 'read':
        if not dir_path or not os.path.isdir(dir_path):
            raise ValueError("Invalid or missing directory path containing music files.")
        if not excel_out or not os.path.isdir(os.path.dirname(excel_out)):
            raise ValueError("Invalid or missing file path for writing tag information.")
    elif mode == 'write':
        if not excel_in or not os.path.isfile(excel_in):
            raise ValueError("Invalid or missing file path for reading tag information.")
        if not excel_out or not os.path.isdir(os.path.dirname(excel_out)):
            raise ValueError("Invalid or missing directory path for writing failed tags.")
    else:
        raise ValueError("Invalid mode. Choose 'read' or 'write'.")
    
def main():
    """Command-line utility to read or write tags from/to music files"""

    parser = argparse.ArgumentParser(description='Classical music file tagger')
    parser.add_argument('mode', choices=['read', 'write'], help='Operation mode: read tags or write tags')
    parser.add_argument('--dir', '-d', required=False, help='Directory containing music files')
    parser.add_argument('--excel_in', '-i', required=True, help='Excel file path for reading tag information')
    parser.add_argument('--excel_out', '-o', required=False, help='Excel file path for writing tag information')

    args = parser.parse_args()

    try:
        # Validate inputs
        validate_inputs(args.mode, args.dir, args.excel_in, args.excel_out)

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