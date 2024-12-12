################################################################################
### tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

import argparse
import sys
import pandas as pd
import functions

def main():
    """Command-line utility to read or write tags from/to music files"""

    parser = argparse.ArgumentParser(description='Classical music file tagger')
    parser.add_argument('mode', choices=['read', 'write'], help='Operation mode: read tags or write tags')
    parser.add_argument('--dir', '-d', required=False, help='Directory containing music files')
    parser.add_argument('--excel_in', '-i', required=True, help='Excel file path for reading tag information')
    parser.add_argument('--excel_out', '-o', required=False, help='Excel file path for writing tag information')

    args = parser.parse_args()

    try:
        
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