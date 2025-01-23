################################################################################
### sqlite_to_csv.py
### Copyright (c) 2025, Joshua J Hamilton
### This utility program converts a SQLite database to a CSV file.
################################################################################

################################################################################
### Import packages
################################################################################

import argparse
import sqlite3
import pandas as pd
import csv

################################################################################
### Define functions
################################################################################

def sqlite_to_csv(sqlite_db, csv_file):
    """
    Convert a SQLite database to a CSV file.

    Args:
        sqlite_db (str): Path to the SQLite database file
        csv_file (str): Path to the CSV file to write

    Returns:
        None
    """
    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db)
    cursor = conn.cursor()

    # Query to get all filenames
    cursor.execute('SELECT id, filepath FROM filename')
    filenames = cursor.fetchall()

    # Initialize a dictionary to store the data
    data = {}

    # Fetch original tags
    cursor.execute('SELECT filename_id, tag_key, tag_value FROM original_tags')
    for row in cursor.fetchall():
        filename_id, tag_key, tag_value = row
        if filename_id not in data:
            data[filename_id] = {}
        data[filename_id][f'original_{tag_key}'] = tag_value

    # Fetch updated tags
    cursor.execute('SELECT filename_id, tag_key, tag_value FROM updated_tags')
    for row in cursor.fetchall():
        filename_id, tag_key, tag_value = row
        if filename_id not in data:
            data[filename_id] = {}
        data[filename_id][f'updated_{tag_key}'] = tag_value

    # Create a DataFrame from the data
    rows = []
    for filename_id, tags in data.items():
        row = {'filename': next(filepath for id, filepath in filenames if id == filename_id)}
        row.update(tags)
        rows.append(row)

    result_df = pd.DataFrame(rows)

    # Rearrange columns to be in the specified order
    columns_order = [
        'filename', 'updated_composer', 'updated_album', 'updated_year recorded', 'updated_orchestra',
        'updated_conductor', 'updated_soloists', 'updated_arranger', 'updated_genre', 'updated_discnumber',
        'updated_tracknumber', 'updated_title', 'updated_tracktitle', 'updated_work', 'updated_work number',
        'updated_initialkey', 'updated_catalog #', 'updated_opus', 'updated_opus number', 'updated_epithet', 
        'updated_movement'
    ]
    # Add any remaining columns that are not in the specified order
    remaining_columns = [col for col in result_df.columns if col not in columns_order]
    result_df = result_df[columns_order + remaining_columns]

    # Write to CSV
    result_df.to_csv(csv_file, index=False)

    # Close the connection
    conn.close()
    print('Data successfully written to CSV file')

def main():
    parser = argparse.ArgumentParser(description="Convert a SQLite database to a CSV file")
    parser.add_argument('--sqlite_db', required=True, help="Path to the SQLite database file")
    parser.add_argument('--csv_file', required=True, help="Path to the CSV file to write")
    args = parser.parse_args()

    sqlite_to_csv(args.sqlite_db, args.csv_file)

if __name__ == "__main__":
    main()