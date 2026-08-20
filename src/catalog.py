################################################################################
### catalog.py
### Copyright (c) 2026, Joshua J Hamilton
### This utility program builds and maintains a persistent database of every
### FLAC track in a music library, keyed on a hash of the track's audio
### stream (not its file path, which this codebase routinely renames). It
### reads canonical tags directly off already-tagged files and writes both a
### SQLite database and a CSV export on every run.
################################################################################

################################################################################
### Import packages
################################################################################
import csv
import logging
import os
import sqlite3
from datetime import datetime

from mutagen.flac import FLAC
from tqdm import tqdm

from standardize import get_tag
from utils import TRACK_MILESTONE_INTERVAL, find_flac_files, get_audio_md5, is_missing_checksum, repair_missing_checksum

logger = logging.getLogger(__name__)

################################################################################
### Schema constants
################################################################################

# The 20 canonical tag fields documented in README.md under "Tag Fields".
CATALOG_FIELDS = [
    'Composer', 'Album', 'Year Recorded', 'Orchestra', 'Conductor', 'Soloists',
    'Arranger', 'Genre', 'DiscNumber', 'TrackNumber', 'Title', 'TrackTitle',
    'Work', 'Work Number', 'InitialKey', 'Catalog #', 'Opus', 'Opus Number',
    'Epithet', 'Movement',
]

MISSING_CHECKSUM_REPORT_FILENAME = 'missing_checksums.csv'
MISSING_CHECKSUM_REPORT_HEADER = ['Path', 'Status', 'New Audio MD5', 'Reason']

DUPLICATE_REPORT_FILENAME = 'duplicates.csv'
DUPLICATE_REPORT_HEADER = ['Audio MD5', 'Path', 'Status']

################################################################################
### Define functions
################################################################################

def to_snake_case(name):
    """
    Convert a display-style tag name to a snake_case database column name.

    Args:
        name (str): Tag display name, e.g. 'Year Recorded' or 'Catalog #'.

    Returns:
        str: snake_case column name, e.g. 'year_recorded' or 'catalog_number'.
    """
    name = name.replace('#', 'Number')
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append('_')
        result.append(char)
    name = ''.join(result).replace(' ', '_')
    while '__' in name:
        name = name.replace('__', '_')
    return name.lower()

FIELD_COLUMN_MAP = {name: to_snake_case(name) for name in CATALOG_FIELDS}
TRACK_COLUMNS = ['audio_md5', 'path', 'last_seen'] + list(FIELD_COLUMN_MAP.values())

def build_track_row(path):
    """
    Read a track's audio checksum and canonical tags directly off the file.

    Args:
        path (str): Path to a FLAC file.

    Returns:
        dict: Keys are TRACK_COLUMNS minus 'last_seen' (added later, per run).

    Raises:
        Exception: If the file cannot be opened as a FLAC file.
    """
    audio = FLAC(path)
    row = {
        'audio_md5': get_audio_md5(audio),
        'path': path,
    }
    for display_name, column in FIELD_COLUMN_MAP.items():
        row[column] = get_tag(audio, display_name)
    return row

def scan_tracks(track_paths):
    """
    Build a catalog row for every track, tallying missing checksums and unreadable files.

    Args:
        track_paths (list): Paths to FLAC files to scan.

    Returns:
        tuple: (rows, missing_checksum_count, skipped_unreadable)
            rows (list): One dict per readable file, including missing-checksum files.
            missing_checksum_count (int): How many of rows have a missing checksum.
            skipped_unreadable (list): Paths that could not be opened as FLAC files.
    """
    rows = []
    missing_checksum_count = 0
    skipped_unreadable = []
    for index, path in enumerate(tqdm(track_paths, desc="Cataloging tracks"), start=1):
        # The milestone check lives in `finally` so it still runs even when
        # an unreadable file takes the `continue` below.
        try:
            try:
                row = build_track_row(path)
            except Exception:
                skipped_unreadable.append(path)
                continue
            if is_missing_checksum(row['audio_md5']):
                missing_checksum_count += 1
            rows.append(row)
        finally:
            if index % TRACK_MILESTONE_INTERVAL == 0:
                logger.info(f"Scanned {index} of {len(track_paths)} tracks...")
    return rows, missing_checksum_count, skipped_unreadable

def repair_missing_checksum_tracks(rows):
    """
    Attempt to repair every row whose audio checksum is missing.

    Repaired rows have their 'audio_md5' updated in place (rows holds the
    same dicts later passed to upsert_tracks), so a repaired track gets its
    own catalog row instead of collapsing onto the shared missing-checksum
    key. Rows that fail to repair are left untouched, falling back to
    today's collapsing behavior.

    Args:
        rows (list): Rows from scan_tracks.

    Returns:
        list: One report dict per missing-checksum row encountered, with
            keys 'path', 'status' ('repaired' or 'failed'), 'new_audio_md5',
            and 'reason'.
    """
    missing_checksum_rows = [row for row in rows if is_missing_checksum(row['audio_md5'])]
    if not missing_checksum_rows:
        return []

    report = []
    repaired_count = 0
    failed_count = 0
    total = len(missing_checksum_rows)
    for index, row in enumerate(tqdm(missing_checksum_rows, desc="Repairing missing checksums"), start=1):
        new_md5, error = repair_missing_checksum(row['path'])
        if new_md5:
            row['audio_md5'] = new_md5
            report.append({
                'path': row['path'], 'status': 'repaired',
                'new_audio_md5': new_md5, 'reason': '',
            })
            repaired_count += 1
        else:
            report.append({
                'path': row['path'], 'status': 'failed',
                'new_audio_md5': '', 'reason': error,
            })
            failed_count += 1
        if index % TRACK_MILESTONE_INTERVAL == 0:
            logger.info(f"Repaired {index} of {total} so far ({repaired_count} repaired, {failed_count} failed)...")
    return report

def write_missing_checksum_report(report, csv_path):
    """Write one row per missing-checksum file encountered, with repair status."""
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(MISSING_CHECKSUM_REPORT_HEADER)
        for entry in report:
            writer.writerow([entry['path'], entry['status'], entry['new_audio_md5'], entry['reason']])

def find_duplicate_tracks(rows):
    """
    Group rows by audio_md5 and report any group with more than one path:
    tracks whose audio content is identical, which upsert_tracks collapses
    onto a single catalog row (the last path scanned in each group, since
    that's the order rows are applied in via ON CONFLICT DO UPDATE).

    Rows still on the missing-checksum key are excluded here -- that
    collision is a different, already-reported situation (repair failed),
    not genuine duplicate audio content.

    Args:
        rows (list): Rows from scan_tracks/repair_missing_checksum_tracks.

    Returns:
        list: One report dict per path involved in a duplicate-audio group,
            with keys 'audio_md5', 'path', and 'status' ('kept' for the
            path that survives in the catalog, 'shadowed' for the rest).
    """
    by_md5 = {}
    for row in rows:
        if is_missing_checksum(row['audio_md5']):
            continue
        by_md5.setdefault(row['audio_md5'], []).append(row['path'])

    report = []
    for audio_md5, paths in by_md5.items():
        if len(paths) < 2:
            continue
        for path in paths[:-1]:
            report.append({'audio_md5': audio_md5, 'path': path, 'status': 'shadowed'})
        report.append({'audio_md5': audio_md5, 'path': paths[-1], 'status': 'kept'})
    return report

def write_duplicate_report(report, csv_path):
    """Write one row per path involved in a duplicate-audio group, with its status."""
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(DUPLICATE_REPORT_HEADER)
        for entry in report:
            writer.writerow([entry['audio_md5'], entry['path'], entry['status']])

def create_tracks_table(conn):
    """Create the tracks table if it doesn't already exist."""
    columns_sql = ',\n            '.join(f"{column} TEXT" for column in TRACK_COLUMNS[3:])
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS tracks (
            audio_md5 TEXT PRIMARY KEY NOT NULL,
            path TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            {columns_sql}
        )
    """)
    conn.commit()

def upsert_tracks(conn, rows, run_timestamp):
    """
    Insert or update one row per track, stamping last_seen with the current run's timestamp.

    Args:
        conn (sqlite3.Connection): Open connection to the catalog database.
        rows (list): Dicts from build_track_row/scan_tracks (without 'last_seen').
        run_timestamp (str): ISO 8601 timestamp for this run, stamped onto every row.
    """
    if not rows:
        return
    for row in rows:
        row['last_seen'] = run_timestamp
    placeholders = ', '.join(f":{column}" for column in TRACK_COLUMNS)
    update_clause = ', '.join(
        f"{column} = excluded.{column}" for column in TRACK_COLUMNS if column != 'audio_md5'
    )
    conn.executemany(f"""
        INSERT INTO tracks ({', '.join(TRACK_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT(audio_md5) DO UPDATE SET {update_clause}
    """, rows)
    conn.commit()

def prune_stale_tracks(conn, run_timestamp):
    """
    Remove rows not touched by the current run (i.e. not found in this scan).

    Args:
        conn (sqlite3.Connection): Open connection to the catalog database.
        run_timestamp (str): The current run's timestamp; rows with any other
            last_seen value were not seen in this scan.

    Returns:
        int: Number of rows removed.
    """
    cursor = conn.execute("DELETE FROM tracks WHERE last_seen != ?", (run_timestamp,))
    conn.commit()
    return cursor.rowcount

def dump_tracks_to_csv(conn, csv_path):
    """Write the full contents of the tracks table to a CSV file, using display-style headers."""
    header = ['Audio MD5', 'Path', 'Last Seen'] + CATALOG_FIELDS
    cursor = conn.execute(f"SELECT {', '.join(TRACK_COLUMNS)} FROM tracks ORDER BY path")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(cursor.fetchall())

################################################################################
### Define run function
################################################################################

def run(args):
    """
    Scan a music directory and build/update a SQLite and CSV catalog of its tracks.

    Args:
        args (argparse.Namespace): Parsed arguments with dir, db, csv, and prune.
    """
    run_timestamp = datetime.now().isoformat()
    track_paths = find_flac_files(args.dir)
    if not track_paths:
        raise ValueError("No FLAC files found in the specified directory.")
    logger.info(f"Found {len(track_paths)} FLAC file(s).")
    rows, missing_checksum_count, skipped_unreadable = scan_tracks(track_paths)

    if missing_checksum_count:
        logger.info(f"{missing_checksum_count} file(s) are missing an audio checksum. Repairing them now...")
    missing_checksum_report = repair_missing_checksum_tracks(rows)

    duplicate_report = find_duplicate_tracks(rows)

    logger.info(f"Writing {len(rows)} track(s) to catalog...")
    conn = sqlite3.connect(args.db)
    create_tracks_table(conn)
    upsert_tracks(conn, rows, run_timestamp)
    pruned = prune_stale_tracks(conn, run_timestamp) if args.prune else 0
    dump_tracks_to_csv(conn, args.csv)
    total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    conn.close()
    logger.info("Catalog written.")

    output_dir = os.path.dirname(args.csv) or '.'

    missing_checksum_report_path = os.path.join(output_dir, MISSING_CHECKSUM_REPORT_FILENAME)
    if missing_checksum_report:
        write_missing_checksum_report(missing_checksum_report, missing_checksum_report_path)
    elif os.path.isfile(missing_checksum_report_path):
        os.remove(missing_checksum_report_path)  # clear a stale report from a previous run

    duplicate_report_path = os.path.join(output_dir, DUPLICATE_REPORT_FILENAME)
    if duplicate_report:
        write_duplicate_report(duplicate_report, duplicate_report_path)
    elif os.path.isfile(duplicate_report_path):
        os.remove(duplicate_report_path)  # clear a stale report from a previous run

    logger.info(f"Scanned {len(track_paths)} FLAC file(s); catalogued {len(rows)}.")
    if missing_checksum_report:
        repaired = sum(1 for r in missing_checksum_report if r['status'] == 'repaired')
        failed = sum(1 for r in missing_checksum_report if r['status'] == 'failed')
        logger.info(f"{len(missing_checksum_report)} file(s) were missing an audio checksum.")
        if repaired:
            logger.info(f"  {repaired} were repaired: the real checksum was written into the file and used in the catalog.")
        if failed:
            logger.warning(
                f"  {failed} could not be repaired and are still catalogued under the shared "
                "missing-checksum key, so they may share one row with each other."
            )
        logger.info(f"  Details for every file: {missing_checksum_report_path}")
    if duplicate_report:
        shadowed = sum(1 for r in duplicate_report if r['status'] == 'shadowed')
        groups = len({r['audio_md5'] for r in duplicate_report})
        logger.info(
            f"{shadowed} file(s) have identical audio to another file already in the catalog "
            f"({groups} group(s) of duplicates); only the most recently scanned file in each "
            "group is kept."
        )
        logger.info(f"  Details for every file: {duplicate_report_path}")
    if skipped_unreadable:
        logger.warning(f"{len(skipped_unreadable)} file(s) could not be read and were skipped:")
        for path in skipped_unreadable:
            logger.warning(f"  {path}")
    if args.prune:
        logger.info(f"Pruned {pruned} stale row(s) not seen in this scan.")
    logger.info(f"Catalog now contains {total} track(s). Database: {args.db}  CSV: {args.csv}")
