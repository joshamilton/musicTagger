################################################################################
### standardize.py
### Copyright (c) 2026, Joshua J Hamilton
### Normalize disc folders to "Disc N" and album folders to
###   [YYYY] Album (performance information)
### from FLAC tags. Dry-run writes a CSV; --file-list applies planned rows.
################################################################################

################################################################################
### Import packages
################################################################################

import csv
import os
import re
import uuid
from collections import Counter, defaultdict

from mutagen.flac import FLAC
from tqdm import tqdm

from utils import filenames_match, find_flac_files, normalize_nfc

################################################################################
### Constants
################################################################################

AUDIO_EXTENSIONS = {'.flac', '.ape', '.wv', '.wav', '.iso', '.m4a'}
DISC_LIKE_PATTERN = re.compile(r'^(?:CD|Disc|Disk)\s*(\d+)\b.*', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\d{4}')

CSV_FIELDNAMES = [
    'path',
    'original_name',
    'new_name',
    'type',
    'status',
    'flag_reason',
    'years_observed',
    'albums_observed',
    'orchestras_observed',
    'conductors_observed',
    'soloists_observed',
    'year_chosen',
    'album_chosen',
    'orchestra_chosen',
    'conductor_chosen',
    'soloist_chosen',
    'performance_info',
]

EMPTY_OBSERVED = {
    'years_observed': '',
    'albums_observed': '',
    'orchestras_observed': '',
    'conductors_observed': '',
    'soloists_observed': '',
    'year_chosen': '',
    'album_chosen': '',
    'orchestra_chosen': '',
    'conductor_chosen': '',
    'soloist_chosen': '',
    'performance_info': '',
    'flag_reason': '',
}

################################################################################
### Discovery helpers
################################################################################

def has_audio_files(directory):
    """Return True if directory directly contains at least one audio file."""
    try:
        for entry in os.listdir(directory):
            if os.path.splitext(entry)[1].lower() in AUDIO_EXTENSIONS:
                return True
    except OSError:
        return False
    return False


def has_flac_files(directory):
    """Return True if directory directly contains at least one .flac file."""
    try:
        for entry in os.listdir(directory):
            if entry.lower().endswith('.flac'):
                return True
    except OSError:
        return False
    return False


def parse_disc_number(folder_name):
    """
    Extract the disc number from a disc-like folder name.

    Args:
        folder_name (str): Immediate child folder name.

    Returns:
        int or None: Disc number if the name matches DISC_LIKE_PATTERN.
    """
    match = DISC_LIKE_PATTERN.match(folder_name)
    if match:
        return int(match.group(1))
    return None


def find_disc_children(album_path):
    """
    Return list of (folder_name, disc_number) for disc-like children with audio.

    Args:
        album_path (str): Path to an album directory.

    Returns:
        list: Sorted by disc_number, then folder_name.
    """
    children = []
    try:
        entries = os.listdir(album_path)
    except OSError:
        return children

    for entry in entries:
        child_path = os.path.join(album_path, entry)
        if not os.path.isdir(child_path):
            continue
        disc_number = parse_disc_number(entry)
        if disc_number is None:
            continue
        if not has_audio_files(child_path):
            continue
        children.append((entry, disc_number))

    children.sort(key=lambda x: (x[1], x[0]))
    return children


def is_album_folder(directory):
    """Album if it has FLACs directly or disc children with audio; never a disc folder."""
    name = os.path.basename(directory.rstrip(os.sep))
    if parse_disc_number(name) is not None:
        return False
    return has_flac_files(directory) or bool(find_disc_children(directory))


def find_album_folders(root_dir):
    """
    Walk root_dir and return album folder paths (with or without disc children).
    """
    albums = []
    for dirpath, dirnames, _ in os.walk(root_dir):
        if is_album_folder(dirpath):
            albums.append(dirpath)
            dirnames[:] = [d for d in dirnames if parse_disc_number(d) is None]
    return sorted(albums)


def find_album_folders_with_discs(root_dir):
    """Return album paths that have at least one disc-like child with audio."""
    return [
        path for path in find_album_folders(root_dir)
        if find_disc_children(path)
    ]


def album_folder_for_file(file_path):
    """Album folder containing file_path: its parent, or grandparent if the parent is a disc folder."""
    parent = os.path.dirname(file_path)
    if parse_disc_number(os.path.basename(parent)) is not None:
        return os.path.dirname(parent)
    return parent

################################################################################
### Disc mapping
################################################################################

def build_disc_mappings(album_path):
    """
    Build rename mappings for disc children of an album.

    Preserves each disc's existing number; pads to len(str(max_number)).

    Returns:
        list: Dicts with path, original_name, new_name (basenames), type, needs_rename.
    """
    children = find_disc_children(album_path)
    if not children:
        return []

    max_number = max(number for _, number in children)
    digit_padding = len(str(max_number))

    mappings = []
    for original_basename, number in children:
        new_basename = f"Disc {str(number).zfill(digit_padding)}"
        mappings.append({
            'path': album_path,
            'original_name': original_basename,
            'new_name': new_basename,
            'type': 'disc',
            'needs_rename': original_basename != new_basename,
        })
    return mappings


def row_src(row):
    """Full path of the folder to rename."""
    return os.path.join(row['path'], row['original_name'])


def row_dest(row):
    """Full path of the rename destination."""
    return os.path.join(row['path'], row['new_name'])

################################################################################
### Tag helpers
################################################################################

def get_tag(audio, *keys):
    """Return the first non-empty tag value for any of the given keys (case-insensitive)."""
    if audio.tags is None:
        return None
    lower_map = {k.lower(): k for k in audio.tags.keys()}
    for key in keys:
        actual = lower_map.get(key.lower())
        if actual is None:
            continue
        values = audio.tags.get(actual)
        if not values:
            continue
        value = str(values[0]).strip()
        if value:
            return normalize_nfc(value)
    return None


def collect_track_tags(album_path):
    """
    Collect tag dicts for every FLAC under album_path (including disc children).

    Returns:
        list: Dicts with keys year, album, orchestra, conductor, soloists.
    """
    tracks = []
    for dirpath, dirnames, filenames in os.walk(album_path):
        # Do not walk into nested non-disc junk beyond one level of discs;
        # os.walk still descends; that's fine for Disc N / track.flac layout.
        for name in sorted(filenames):
            if not name.lower().endswith('.flac'):
                continue
            path = os.path.join(dirpath, name)
            try:
                audio = FLAC(path)
            except Exception:
                continue
            tracks.append({
                'year': get_tag(audio, 'Year Recorded'),
                'album': get_tag(audio, 'Album', 'album'),
                'orchestra': get_tag(audio, 'Orchestra', 'orchestra'),
                'conductor': get_tag(audio, 'Conductor', 'conductor'),
                'soloists': get_tag(audio, 'Soloists'),
            })
    return tracks


def empty_unique_tag_sets():
    """Empty sets for unique Album / Orchestra / Conductor / Soloist values."""
    return {
        'albums': set(),
        'orchestras': set(),
        'conductors': set(),
        'soloists': set(),
    }


def add_track_tags_to_uniques(track_tags, uniques):
    """
    Add non-empty tag values from track_tags into unique sets.

    Soloists fields are split on ';' so each person is a separate entry.
    """
    for tags in track_tags:
        album = tags.get('album')
        if album:
            uniques['albums'].add(album)
        orchestra = tags.get('orchestra')
        if orchestra:
            uniques['orchestras'].add(orchestra)
        conductor = tags.get('conductor')
        if conductor:
            uniques['conductors'].add(conductor)
        soloists = tags.get('soloists')
        if not soloists:
            continue
        for part in soloists.split(';'):
            part = part.strip()
            if part:
                uniques['soloists'].add(part)


def write_unique_tag_lists(uniques, output_file):
    """
    Write sorted unique tag values as companion CSV files next to the dry-run CSV.

    For output-file plan.csv, writes plan_albums.csv, plan_orchestras.csv,
    plan_conductors.csv, and plan_soloists.csv with original_*/new_* columns
    (new_* left blank for review).
    """
    base, _ = os.path.splitext(output_file)
    for kind, original_col, new_col, values in (
        ('albums', 'original_album', 'new_album', uniques['albums']),
        ('orchestras', 'original_orchestra', 'new_orchestra', uniques['orchestras']),
        ('conductors', 'original_conductor', 'new_conductor', uniques['conductors']),
        ('soloists', 'original_soloist', 'new_soloist', uniques['soloists']),
    ):
        path = f"{base}_{kind}.csv"
        with open(path, 'w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.writer(handle)
            writer.writerow([original_col, new_col])
            for value in sorted(values, key=lambda s: s.casefold()):
                writer.writerow([value, ''])
        print(f"Wrote {len(values)} unique {kind} to {path}")


# Tag kinds for retag mapping CSVs: (map_key, original_col, new_col, flac_keys_to_read..., write_key)
RETAG_KINDS = (
    ('album', 'original_album', 'new_album', ('Album', 'album'), 'Album'),
    ('orchestra', 'original_orchestra', 'new_orchestra', ('Orchestra', 'orchestra'), 'Orchestra'),
    ('conductor', 'original_conductor', 'new_conductor', ('Conductor', 'conductor'), 'Conductor'),
    ('soloist', 'original_soloist', 'new_soloist', ('Soloists',), 'Soloists'),
)


def earliest_year(year_values):
    """Return the earliest 4-digit year string from a list of year tag values."""
    years = []
    for value in year_values:
        if not value:
            continue
        years.extend(YEAR_PATTERN.findall(value))
    if not years:
        return None
    return min(years)


def most_common_or_tie(values):
    """
    Return (chosen, tied) for non-empty values.
    tied is True if the top two counts are equal.
    """
    cleaned = [v for v in values if v]
    if not cleaned:
        return None, False
    counts = Counter(cleaned)
    ranked = counts.most_common()
    if len(ranked) >= 2 and ranked[0][1] == ranked[1][1]:
        return ranked[0][0], True
    return ranked[0][0], False


def join_observed(values):
    """Pipe-join unique non-empty observed values (sorted)."""
    unique = sorted({v for v in values if v})
    return '|'.join(unique)


def flip_to_first_last(name):
    """Convert 'Last, First' to 'First Last' when there is a single comma."""
    name = name.strip()
    if name.count(',') == 1:
        last, first = [p.strip() for p in name.split(',', 1)]
        if last and first:
            return f"{first} {last}"
    return name


def flip_to_last_first(name):
    """Convert 'First Last' to 'Last, First'; leave names already containing a comma as-is."""
    name = name.strip()
    if ',' in name:
        return name
    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def last_name_key(display_name):
    """Sort key: last whitespace token, case-insensitive."""
    parts = display_name.strip().split()
    if not parts:
        return ''
    return parts[-1].casefold()


def stored_last_name_key(display_name):
    """Sort key for a 'Last, First' formatted name: the text before the first comma."""
    display_name = display_name.strip()
    if ',' in display_name:
        return display_name.split(',', 1)[0].strip().casefold()
    return display_name.casefold()


def format_soloists(soloists_raw):
    """
    Format a Soloists field:
    - Split on ';'
    - Flip Last, First → First Last
    - Sort alphabetically by last name
    - Join: A | A and B | A, B, and C
    """
    if not soloists_raw:
        return None
    people = []
    for part in soloists_raw.split(';'):
        part = part.strip()
        if not part:
            continue
        people.append(flip_to_first_last(part))
    if not people:
        return None
    people = sorted(set(people), key=last_name_key)
    if len(people) == 1:
        return people[0]
    if len(people) == 2:
        return f"{people[0]} and {people[1]}"
    return f"{', '.join(people[:-1])}, and {people[-1]}"


def normalize_soloists_field(soloists_raw):
    """
    Normalize a raw Soloists tag value for storage:
    - Split on ';'
    - Flip each person to 'Last, First'
    - Drop exact duplicates (post-flip)
    - Sort alphabetically by last name
    - Rejoin with '; '
    """
    if not soloists_raw:
        return soloists_raw
    people = []
    seen = set()
    for part in soloists_raw.split(';'):
        part = part.strip()
        if not part:
            continue
        flipped = flip_to_last_first(part)
        if flipped not in seen:
            seen.add(flipped)
            people.append(flipped)
    if not people:
        return soloists_raw
    people.sort(key=stored_last_name_key)
    return '; '.join(people)


def format_conductor(conductor_raw):
    """Format Conductor as First Last when stored as Last, First."""
    if not conductor_raw:
        return None
    return flip_to_first_last(conductor_raw)


def build_performance_info(orchestra, conductor, soloist):
    """
    Build parenthetical performance info, or (None, flag_reason).

    Returns:
        tuple: (performance_info_without_parens or None, flag_reason or None)
    """
    has_o = bool(orchestra)
    has_c = bool(conductor)
    has_s = bool(soloist)

    if has_o and not has_c and not has_s:
        return orchestra, None
    if has_o and has_c and not has_s:
        return f"{orchestra} with {conductor}", None
    if has_o and not has_c and has_s:
        return f"{orchestra} with {soloist}", None
    if not has_o and not has_c and has_s:
        return soloist, None
    if has_o and has_c and has_s:
        return f"{orchestra} with {conductor} and {soloist}", None
    if not has_o and has_c and has_s:
        return f"{conductor} with {soloist}", None

    if not has_o and not has_c and not has_s:
        return None, "no Orchestra/Conductor/Soloists tags"
    if not has_o and has_c and not has_s:
        return None, "Conductor only without Orchestra"
    return None, "unsupported Orchestra/Conductor/Soloists combination"


def sanitize_component(text):
    """Replace path-unsafe characters in a folder name component."""
    return (
        text.replace('/', '-')
        .replace('\\', '-')
        .replace(':', ' -')
    )


def empty_row(album_path, status, flag_reason='', **chosen):
    row = {
        'path': os.path.dirname(album_path),
        'original_name': os.path.basename(album_path),
        'new_name': '',
        'type': 'album',
        'status': status,
        **EMPTY_OBSERVED,
    }
    row['flag_reason'] = flag_reason
    row.update(chosen)
    return row


def analyze_album(album_path, track_tags=None):
    """
    Analyze an album folder and return an album plan row.

    Args:
        album_path (str): Path to the album directory.
        track_tags (list|None): Optional preloaded tag dicts (for tests).

    Returns:
        dict: CSV row for this album (planned, flagged, or skipped).
    """
    if track_tags is None:
        track_tags = collect_track_tags(album_path)

    years = [t.get('year') for t in track_tags]
    albums = [t.get('album') for t in track_tags]
    orchestras = [t.get('orchestra') for t in track_tags]
    conductors = [t.get('conductor') for t in track_tags]
    soloists_list = [t.get('soloists') for t in track_tags]

    observed = {
        'years_observed': join_observed(years),
        'albums_observed': join_observed(albums),
        'orchestras_observed': join_observed(orchestras),
        'conductors_observed': join_observed(conductors),
        'soloists_observed': join_observed(soloists_list),
    }

    year_chosen = earliest_year(years)
    album_chosen, album_tie = most_common_or_tie(albums)
    orchestra_chosen, orch_tie = most_common_or_tie(orchestras)
    conductor_raw, cond_tie = most_common_or_tie(conductors)
    soloists_raw, solo_tie = most_common_or_tie(soloists_list)

    distinct_albums = {a for a in albums if a}
    flag_reasons = []

    if not track_tags:
        flag_reasons.append("no readable FLAC tags")
    if not year_chosen:
        flag_reasons.append("missing Year Recorded")
    if not album_chosen:
        flag_reasons.append("missing Album")
    if len(distinct_albums) > 1:
        flag_reasons.append("conflicting Album titles across tracks")
    if album_tie:
        flag_reasons.append("tie for most common Album")
    if orch_tie:
        flag_reasons.append("tie for most common Orchestra")
    if cond_tie:
        flag_reasons.append("tie for most common Conductor")
    if solo_tie:
        flag_reasons.append("tie for most common Soloists")

    conductor_chosen = format_conductor(conductor_raw)
    soloist_chosen = format_soloists(soloists_raw) if soloists_raw else None
    perf, perf_flag = build_performance_info(
        orchestra_chosen, conductor_chosen, soloist_chosen
    )
    if perf_flag:
        flag_reasons.append(perf_flag)

    parent = os.path.dirname(album_path)
    original_basename = os.path.basename(album_path)
    base = {
        'path': parent,
        'original_name': original_basename,
        'new_name': '',
        'type': 'album',
        **observed,
        'year_chosen': year_chosen or '',
        'album_chosen': album_chosen or '',
        'orchestra_chosen': orchestra_chosen or '',
        'conductor_chosen': conductor_chosen or '',
        'soloist_chosen': soloist_chosen or '',
        'performance_info': perf or '',
        'flag_reason': '',
    }

    if flag_reasons:
        base['status'] = 'flagged'
        base['flag_reason'] = '; '.join(flag_reasons)
        return base

    new_basename = (
        f"[{sanitize_component(year_chosen)}] "
        f"{sanitize_component(album_chosen)} "
        f"({sanitize_component(perf)})"
    )
    base['new_name'] = new_basename

    if filenames_match(original_basename, new_basename):
        base['status'] = 'skipped'
        return base

    base['status'] = 'planned'
    return base


def disc_plan_rows(album_path):
    """Return CSV rows for disc renames that are needed under album_path."""
    rows = []
    for mapping in build_disc_mappings(album_path):
        if not mapping['needs_rename']:
            continue
        row = {
            'path': mapping['path'],
            'original_name': mapping['original_name'],
            'new_name': mapping['new_name'],
            'type': 'disc',
            'status': 'planned',
            **EMPTY_OBSERVED,
        }
        rows.append(row)
    return rows


def build_plan_from_dir(root_dir):
    """
    Build full dry-run plan: disc planned rows + album planned/flagged/skipped.

    Discovers albums first, then analyzes each with a progress bar (known total).

    Returns:
        tuple: (rows, unique_tag_sets) where unique_tag_sets has albums,
        orchestras, conductors, and soloists (soloists split on ';').
    """
    albums = find_album_folders(root_dir)
    rows = []
    uniques = empty_unique_tag_sets()
    for album_path in tqdm(albums, desc="Analyzing albums", unit="album"):
        track_tags = collect_track_tags(album_path)
        add_track_tags_to_uniques(track_tags, uniques)
        rows.extend(disc_plan_rows(album_path))
        rows.append(analyze_album(album_path, track_tags=track_tags))
    return rows, uniques


def planned_renames_from_dir(root_dir):
    """
    Backward-compatible helper: planned disc renames only (minimal keys).
    Prefer build_plan_from_dir for full reports.
    """
    rows, _ = build_plan_from_dir(root_dir)
    return [
        {
            'path': r['path'],
            'original_name': r['original_name'],
            'new_name': r['new_name'],
            'type': r['type'],
        }
        for r in rows
        if r['type'] == 'disc' and r['status'] == 'planned'
    ]

################################################################################
### CSV I/O
################################################################################

def write_rename_csv(rows, output_path):
    """Write plan/report CSV with full schema."""
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            out = {key: row.get(key, '') for key in CSV_FIELDNAMES}
            writer.writerow(out)


def read_rename_list(file_list_path):
    """
    Read a dry-run CSV and return rows eligible for apply (status=planned only).

    original_name and new_name are folder basenames; path is the parent directory.
    """
    rows = []
    with open(file_list_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            path = (row.get('path') or '').strip()
            original_name = (row.get('original_name') or '').strip()
            new_name = (row.get('new_name') or '').strip()
            rename_type = (row.get('type') or '').strip()
            status = (row.get('status') or '').strip()
            if status != 'planned':
                continue
            if not path or not original_name or not new_name or not rename_type:
                continue
            rows.append({
                'path': path,
                'original_name': original_name,
                'new_name': new_name,
                'type': rename_type,
                'status': 'planned',
            })
    return rows


def detect_file_list_kind(file_list_path):
    """
    Detect whether a --file-list CSV is a folder-rename plan or a retag map.

    Returns:
        str: 'rename' or 'retag'

    Raises:
        ValueError: If the CSV is neither kind.
    """
    with open(file_list_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = {name.strip() for name in (reader.fieldnames or []) if name}

    rename_required = {'path', 'original_name', 'new_name'}
    if rename_required.issubset(fieldnames):
        return 'rename'

    for _, original_col, new_col, _, _ in RETAG_KINDS:
        if original_col in fieldnames and new_col in fieldnames:
            return 'retag'

    raise ValueError(
        "Unrecognized --file-list CSV: expected rename columns "
        "(path, original_name, new_name) or retag columns "
        "(original_album/new_album, original_orchestra/new_orchestra, "
        "original_conductor/new_conductor, and/or original_soloist/new_soloist)."
    )


def load_retag_mappings(file_list_path):
    """
    Load original -> new maps from a retag CSV.

    Only rows with non-empty new_* that differ from original_* are included.

    Returns:
        dict: map_key -> {original: new} for each kind present with at least one mapping.
    """
    mappings = {}
    with open(file_list_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = {name.strip() for name in (reader.fieldnames or []) if name}
        rows = list(reader)

    for map_key, original_col, new_col, _, _ in RETAG_KINDS:
        if original_col not in fieldnames or new_col not in fieldnames:
            continue
        kind_map = {}
        for row in rows:
            original = (row.get(original_col) or '').strip()
            new = (row.get(new_col) or '').strip()
            if not original or not new or new == original:
                continue
            kind_map[original] = new
        if kind_map:
            mappings[map_key] = kind_map
    return mappings


def remap_soloists_field(soloists_raw, soloist_map):
    """
    Split Soloists on ';', replace tokens present in soloist_map, rejoin with '; '.

    Returns:
        str: Remapped field (may equal the original if nothing matched).
    """
    parts = []
    for part in soloists_raw.split(';'):
        part = part.strip()
        if not part:
            continue
        parts.append(soloist_map.get(part, part))
    return '; '.join(parts)


def compute_retag_updates(audio, mappings):
    """
    Compute FLAC tag updates for one file from loaded retag mappings.

    Returns:
        dict: canonical write key -> new value (only changed fields).
    """
    updates = {}
    for map_key, _, _, read_keys, write_key in RETAG_KINDS:
        kind_map = mappings.get(map_key)
        if not kind_map:
            continue
        current = get_tag(audio, *read_keys)
        if not current:
            continue
        if map_key == 'soloist':
            remapped = remap_soloists_field(current, kind_map)
            normalized = normalize_soloists_field(remapped)
            if normalized != current:
                updates[write_key] = normalized
        elif current in kind_map:
            updates[write_key] = kind_map[current]
    return updates


def apply_retag_mappings(root_dir, mappings):
    """
    Walk FLACs under root_dir and apply retag mappings in place.

    Discovers files first (progress bar), then retags with a known-total bar.

    Returns:
        tuple: (errors, touched_albums) - error messages (empty on full
        success), and the set of album folder paths containing at least
        one file that was actually updated.
    """
    errors = []
    touched_albums = set()
    if not mappings:
        return errors, touched_albums

    flac_paths = find_flac_files(root_dir)
    updated = 0
    for path in tqdm(flac_paths, desc="Retagging files", unit="file"):
        try:
            audio = FLAC(path)
        except Exception as e:
            errors.append(f"{path}: failed to open ({e})")
            continue
        updates = compute_retag_updates(audio, mappings)
        if not updates:
            continue
        try:
            for key, value in updates.items():
                audio[key] = value
            audio.save()
            updated += 1
            touched_albums.add(album_folder_for_file(path))
        except Exception as e:
            errors.append(f"{path}: failed to save ({e})")
    print(f"Retagged {updated} of {len(flac_paths)} FLAC files.")
    return errors, touched_albums


def normalize_soloists_for_dir(root_dir):
    """
    Walk FLACs under root_dir and normalize each file's Soloists tag in place:
    flip each person to 'Last, First', drop exact duplicates, sort by last name.

    Returns:
        list: Error messages (empty on full success).
    """
    errors = []
    flac_paths = find_flac_files(root_dir)
    updated = 0
    for path in tqdm(flac_paths, desc="Normalizing soloist order", unit="file"):
        try:
            audio = FLAC(path)
        except Exception as e:
            errors.append(f"{path}: failed to open ({e})")
            continue
        current = get_tag(audio, 'Soloists')
        if not current:
            continue
        normalized = normalize_soloists_field(current)
        if normalized == current:
            continue
        try:
            audio['Soloists'] = normalized
            audio.save()
            updated += 1
        except Exception as e:
            errors.append(f"{path}: failed to save ({e})")
    print(f"Normalized soloist order in {updated} of {len(flac_paths)} FLAC files.")
    return errors

################################################################################
### Apply renames
################################################################################

def _apply_renames_in_parent(parent, renames):
    """
    Two-phase rename of folders that share the same parent directory.

    Each rename dict has path, original_name, new_name (basenames).

    Returns:
        list: Error messages (empty on full success).
    """
    errors = []
    renames = [r for r in renames if not filenames_match(r['original_name'], r['new_name'])]
    if not renames:
        return errors

    moving_away = {r['original_name'] for r in renames}
    targets = [r['new_name'] for r in renames]
    if len(targets) != len(set(targets)):
        return ['multiple folders map to the same target name']

    for r in renames:
        target_path = os.path.join(parent, r['new_name'])
        if os.path.exists(target_path) and r['new_name'] not in moving_away:
            return [f"target already exists and is not moving: {target_path}"]

    temp_mappings = []
    for r in renames:
        original_path = row_src(r)
        if not os.path.isdir(original_path):
            errors.append(f"missing source: {original_path}")
            continue
        temp_name = f".std_rename_{uuid.uuid4().hex}"
        temp_path = os.path.join(parent, temp_name)
        try:
            os.rename(original_path, temp_path)
            temp_mappings.append((temp_path, r))
        except OSError as e:
            errors.append(f"{original_path}: {e}")

    for temp_path, r in temp_mappings:
        final_path = row_dest(r)
        try:
            os.rename(temp_path, final_path)
        except OSError as e:
            try:
                os.rename(temp_path, row_src(r))
            except OSError:
                pass
            errors.append(f"{row_src(r)} -> {final_path}: {e}")

    return errors


def apply_album_rename(row):
    """Apply a single album folder rename."""
    src = row_src(row)
    dest = row_dest(row)
    if not os.path.isdir(src):
        return [f"missing source: {src}"]
    if filenames_match(row['original_name'], row['new_name']):
        return []
    if os.path.exists(dest):
        return [f"destination already exists: {dest}"]
    try:
        os.rename(src, dest)
    except OSError as e:
        return [f"{src} -> {dest}: {e}"]
    return []


def apply_rename_rows(rows):
    """
    Apply planned rename rows: disc first (grouped by path), then album.
    """
    errors = []
    disc_rows = [r for r in rows if r['type'] == 'disc']
    album_rows = [r for r in rows if r['type'] == 'album']

    by_parent = defaultdict(list)
    for row in disc_rows:
        by_parent[row['path']].append(row)

    total = len(disc_rows) + len(album_rows)
    with tqdm(total=total, desc="Applying renames", unit="folder") as pbar:
        for parent, renames in sorted(by_parent.items()):
            errors.extend(_apply_renames_in_parent(parent, renames))
            pbar.update(len(renames))

        for row in album_rows:
            errors.extend(apply_album_rename(row))
            pbar.update(1)

    unknown = [r for r in rows if r['type'] not in ('disc', 'album')]
    for row in unknown:
        errors.append(f"unknown type {row['type']!r}: {row_src(row)}")

    return errors


def apply_disc_renames_for_album(album_path):
    """Apply needed disc renames for a single album (live scan path)."""
    mappings = build_disc_mappings(album_path)
    to_rename = [m for m in mappings if m['needs_rename']]
    if not to_rename:
        return []
    return _apply_renames_in_parent(album_path, to_rename)


def apply_plan_live(root_dir):
    """One-pass: disc renames then album renames for each album under root_dir."""
    errors = []
    # Snapshot album paths first so album renames don't disturb the walk.
    albums = find_album_folders(root_dir)
    for album_path in albums:
        errors.extend(apply_disc_renames_for_album(album_path))
    # Re-find albums after disc renames (paths to albums unchanged).
    for album_path in find_album_folders(root_dir):
        row = analyze_album(album_path)
        if row['status'] == 'planned':
            errors.extend(apply_album_rename(row))
    return errors


def apply_plan_live_for_albums(album_paths):
    """Disc then album renames, scoped to specific album folders (e.g. retag-touched albums)."""
    errors = []
    albums = sorted(album_paths)
    for album_path in albums:
        errors.extend(apply_disc_renames_for_album(album_path))
    for album_path in albums:
        row = analyze_album(album_path)
        if row['status'] == 'planned':
            errors.extend(apply_album_rename(row))
    return errors

################################################################################
### Run
################################################################################

def run(args):
    """
    Plan or apply disc/album folder renames, or apply retag mapping CSVs.

    Dry-run with --dir writes a rename CSV plus unique original_*/new_* lists.
    --file-list with rename columns applies folder renames (disc then album).
    --file-list with retag columns requires --dir and remaps FLAC tags;
    a soloist mapping also normalizes the resulting Soloists tag order.
    Afterward, any album with at least one retagged file is rescanned and
    its disc/album folders renamed to match, same as a --dir-only run.
    Live run with --dir alone scans and renames folders in one pass, and
    normalizes every scanned file's Soloists tag order.
    """
    dry_run = args.dry_run
    file_list = getattr(args, 'file_list', None)
    output_file = args.output_file

    if dry_run and file_list:
        raise ValueError("Do not combine --dry-run with --file-list; dry-run writes the list.")
    if dry_run and not output_file:
        raise ValueError("--output-file is required when using --dry-run.")
    if not args.dir and not file_list:
        raise ValueError("You must specify either --dir or --file-list.")

    if dry_run:
        rows, uniques = build_plan_from_dir(args.dir)
        write_rename_csv(rows, output_file)
        write_unique_tag_lists(uniques, output_file)
        return

    if file_list:
        kind = detect_file_list_kind(file_list)
        if kind == 'rename':
            rows = read_rename_list(file_list)
            errors = apply_rename_rows(rows)
            label = 'rename'
        else:
            if not args.dir:
                raise ValueError("Retag --file-list requires --dir.")
            mappings = load_retag_mappings(file_list)
            if not mappings:
                print("No retag mappings to apply (empty or unchanged new_* values).")
                return
            errors, touched_albums = apply_retag_mappings(args.dir, mappings)
            errors.extend(apply_plan_live_for_albums(touched_albums))
            label = 'retag'
    else:
        errors = apply_plan_live(args.dir)
        errors.extend(normalize_soloists_for_dir(args.dir))
        label = 'rename'

    if errors:
        for message in errors:
            print(f"Error: {message}")
        raise RuntimeError(f"{len(errors)} {label} error(s) occurred.")
