# Custom Tagging of Classical Music Files
Copyright (c) 2024, Joshua J. Hamilton  
Email: <joshamilton@gmail.com>  
URL: <https://www.linkedin.com/in/joshamilton/>  
URL: <https://github.com/joshamilton/>  
All rights reserved.

A command-line utility for managing metadata tags in classical music FLAC files, plus related collection-maintenance commands. This tool helps maintain consistent tagging across your classical music collection by extracting information from file paths and existing tags.

The tool was written to reflect my personal idiosyncrasies in tagging classical music, so it is probably not suitable for general use.

## Features
- Reads existing FLAC metadata tags and file path information
- Extracts structured information including:
  - Composer
  - Album
  - Year Recorded
  - Orchestra
  - Conductor
  - Soloists
  - Genre
  - DiscNumber and TrackNumber
  - Work metadata (opus numbers, catalog numbers, keys, etc.)
- Supports batch updates from Excel files
- Preserves unicode characters in tags
- Tracks successful and failed tag operations
- Cleans up non-music files and normalizes extensions
- Converts high-resolution FLAC files to 16-bit 44 kHz
- Organizes album directories (Scans.pdf, disc folders, cleanup)
- Standardizes disc folder names to `Disc N` with shared zero-padding
- Builds a database and CSV catalog of every tagged track, keyed on audio content so it survives renames

## Prerequisites

### Clone the repository
```bash
git clone git@github.com:joshamilton/musicTagger.git
cd musicTagger
```

### Setup the environment
```bash
mamba env create -f musicTagger.yaml 
mamba activate musicTagger
```

## Tag Fields
`write` writes each non-empty Excel column as a FLAC Vorbis comment using these exact field names:

## Work Metadata
- `Work`: The main musical work (e.g. "Symphony", "String Quartet")
- `Work Number`: Numerical designation (e.g. "No 41")
- `InitialKey`: Key signature (e.g. "C major", "E-flat")
- `Catalog #`: Standard catalog reference (e.g. "K 551", "BWV 1046")
- `Opus`: Opus designation (e.g. "Op 55")
- `Opus Number`: Sub-designation within opus (e.g. "No 1")
- `Epithet`: Common name (e.g. "Jupiter", "Eroica")
- `Movement`: Movement number and tempo (e.g. "I. Allegro con brio")
- `Title`: Always reconstructed by `write` from the work fields above (any `Title` column in the Excel is overwritten). Present parts are joined in this order:

  `Work`, `Work Number`, `Catalog #`, `Opus`, `Opus Number`, in `InitialKey`, '`Epithet`' - `Movement`

  Example: `Symphony, No 41, K 551, in C major, 'Jupiter' - I. Allegro`

- `TrackTitle`: Optional field for a manually-entered source title (added by JRiver)

## Recording Metadata
- `Album`: Full album title
- `Year Recorded`: Recording year
- `Orchestra`: Performing ensemble
- `Conductor`: Conductor name
- `Soloists`: Soloist(s) name(s)
- `Arranger`: Arranger name (when present)
- `Composer`: Composer name
- `Genre`: Musical period/style
- `DiscNumber`: For multi-disc sets
- `TrackNumber`: Position on disc

## Usage
All commands are invoked through `python src/tagger.py <command> ...`.

```bash
python src/tagger.py --help
python src/tagger.py <command> --help
```

### Reading Tags
Read existing tags from a directory of FLAC files:

```bash
python src/tagger.py \
    read \
    --dir "path/to/music/files" \
    --excel_out "tags.xlsx"
```

This will:
- Scan the directory recursively for FLAC files
- Extract tags and path information
- Save the results to the specified Excel file

Arguments:
- `--dir`, `-d`: Directory containing music files (required)
- `--excel_out`, `-o`: Output Excel file (required)

### Writing Tags
Update tags from an Excel file:

```bash
python src/tagger.py \
    write \
    --excel_in "updated_tags.xlsx" \
    --excel_out "failed_tags.xlsx"
```

This will:
- Read tags from the input Excel file
- Repair any file that's missing an audio checksum (still all-zero) before writing its tags
- Update the FLAC files with new tags
- Save any failed operations to the output Excel file

Arguments:
- `--excel_in`, `-i`: Input Excel file with tags (required)
- `--excel_out`, `-o`: Output Excel file for failed tags (required)

### Cleanup
Find and remove files that are not FLAC, CUE, LOG, or PDF. Also renames files with uppercase extensions to lowercase, strips any FLAC tag not in the canonical Tag Fields list, and reports albums missing a LOG or CUE file.

Tags removed are logged to `tags.csv` in `--dir`.

```bash
python src/tagger.py \
    cleanup \
    --dir "path/to/music/files" \
    [--dry-run]
```

Arguments:
- `--dir`, `-d`: Directory to scan for files (required)
- `--dry-run`: Generate a report without making changes

### Convert
Convert FLAC files that are not already 16-bit 44 kHz to 16-bit 44 kHz using SoX. Supports an overwrite option and dry-run reports.

```bash
python src/tagger.py \
    convert \
    --dir "path/to/music/files" \
    [--dry-run] [--overwrite]
```

Or convert from a previously generated file list:

```bash
python src/tagger.py \
    convert \
    --file-list "convert.csv" \
    [--overwrite]
```

Arguments:
- `--dir`, `-d`: Directory to scan for FLAC files
- `--file-list`: CSV of files to convert (must specify `--dir` or `--file-list`)
- `--dry-run`: Generate a report of files to convert without converting
- `--overwrite`: Overwrite the original files after conversion

### Structure
Organize and clean up album directories. Supports creating `Scans.pdf`, renaming disc folders, and removing unnecessary files and empty directories. Generates a CSV summarizing all actions.

```bash
python src/tagger.py \
    structure \
    --dir "path/to/music/files" \
    --mode [make_scans|fix_scans|rename_dirs|cleanup|all] \
    [--dry-run] [--output-csv "output.csv"]
```

Arguments:
- `--dir`, `-d`: Directory to process (required)
- `--mode`: Mode of operation (required). Options:
  - `make_scans`: Creates `Scans.pdf` for each subdirectory and deletes original image and PDF files.
  - `fix_scans`: Detects and repairs existing `Scans.pdf` files whose pages are absurdly oversized due to bogus image DPI metadata.
  - `rename_dirs`: Renames disc folders based on audio file content and naming patterns.
  - `cleanup`: Removes unnecessary files and empty directories.
  - `all`: Combines all modes into a single operation (run in the order `make_scans` -> `fix_scans` -> `rename_dirs` -> `cleanup`).
- `--dry-run`: Logs actions without making changes.
- `--output-csv`: Path to the output CSV file summarizing all actions (default: `output.csv` in `--dir`).

#### Structure modes
1. **`make_scans`**:
   - Combines image and PDF files in each subdirectory into a single `Scans.pdf`.
   - Deletes the original files after creating the PDF.
   - Logs included files to the CSV file.
   - Image DPI metadata is clamped to a sane range (36-1200) before computing page dimensions, so a bogus value like `dpi=1` no longer produces a 700-inch-wide page.

2. **`fix_scans`**:
   - Scans every `Scans.pdf` under `--dir` and flags any page wider or taller than 200 inches (14400 pt).
   - Rebuilds each offending page from its embedded image at its natural pixel size (72 dpi). Pages that are not oversized, or that don't contain a single embedded image (e.g. merged-in booklet PDFs), are passed through unchanged.
   - The fixed file is written next to the original and atomically swapped in.
   - With `--dry-run`, only reports offending pages with current dimensions; no files are modified.

3. **`rename_dirs`**:
   - Renames disc folders to a standardized format (`Disc #`) based on audio file content.
   - Generates a CSV file with mappings of original folder names to revised names.

4. **`cleanup`**:
   - Removes files that do not match allowed extensions (`.pdf`, `.log`, `.cue`, `.flac`, `.ape`, `.wv`, `.wav`).
   - Removes empty directories.
   - Logs deleted files and directories to the CSV file.
   - Note: this is distinct from the top-level `cleanup` command.

5. **`all`**:
   - Combines `make_scans`, `fix_scans`, `rename_dirs`, and `cleanup` into a single operation, in that order, so any newly-created `Scans.pdf` is also checked/repaired before the later modes run.
   - Logs all actions to the CSV file, separated by mode.

#### CSV Output
The CSV file summarizes all actions performed, or that would be performed in `--dry-run` mode. Each mode is separated by a blank line and includes appropriate headers.

### Standardize
Rename album folders to standard form. Also supports bulk retagging of specific field values.

#### Folder renaming

Scan and rename folders in one step: 

```bash
python src/tagger.py \
    standardize \
    --dir "path/to/music/files"
```

Standard form for an album folder is:

```text
[YYYY] Album (performance information)
```

Performance info follows these templates:

| Tags present | Parenthetical |
|---|---|
| Orchestra | `(Orchestra)` |
| Orchestra + Conductor | `(Orchestra with Conductor)` |
| Orchestra + Soloist | `(Orchestra with Soloist)` |
| Soloist | `(Soloist)` |
| Orchestra + Conductor + Soloist | `(Orchestra with Conductor and Soloist)` |
| Conductor + Soloist | `(Conductor with Soloist)` |

Other combinations are flagged and not renamed.

Dry-run mode writes one row per planned disc rename, planned album rename, or flagged album:

```bash
python src/tagger.py \
    standardize \
    --dir "path/to/music/files" \
    --dry-run \
    --output-file "renames.csv"
```

Columns:

- `path`: parent directory of the folder to rename
- `original_name` / `new_name`: folder name
- `type` (`disc` \| `album`), `status` (`planned` \| `flagged` \| `skipped`), `flag_reason`
- observed tag summaries and chosen year/album/orchestra/conductor/soloist
- `performance_info`

Before applying, manually review each row whose `status` is empty, `planned`, or `flagged`. Edit `new_name` when needed. For empty or `flagged` rows you want to apply, set `status` to `planned` (and fill in a `new_name` if it was blank). Rows that are not `planned` are skipped.

Apply the reviewed CSV:

```bash
python src/tagger.py \
    standardize \
    --file-list "renames.csv"
```

Arguments:
- `--dir`, `-d`: Directory to scan (required for dry-run, one-pass rename, and retag; optional for rename `--file-list`)
- `--file-list`: Rename plan CSV or retag map CSV (detected by columns)
- `--dry-run`: Write planned/flagged renames without making changes (`--output-file` required)
- `--output-file`: CSV report (required with `--dry-run`)

#### Bulk-retagging

Dry-run mode also writes unique tag lists next to `--output-file`: `{stem}_albums.csv`, `{stem}_orchestras.csv`, `{stem}_conductors.csv`, and `{stem}_soloists.csv`. 

Review those lists to standardize tag spellings before applying renames.

Then apply a reviewed retag map: 

```bash
python src/tagger.py \
    standardize \
    --dir "path/to/music/files" \
    --file-list "classical_conductors_reviewed.csv"
```

Only rows with non-empty `new_*` that differ from `original_*` are applied. Album / Orchestra / Conductor use whole-field exact match; Soloists remap matching `;`-separated tokens and rejoin with `; `. If the reviewed CSV includes soloist rows, the remapped Soloists tag is also normalized on every matching file: each person is stored as `Last, First`, exact duplicates are dropped, and the list is sorted alphabetically by last name.

After retagging, any album with at least one changed file is rescanned and its disc/album folders are renamed to match the current tags, following the same `[YYYY] Album (performance information)` convention as a plain `--dir` run above. Albums the retag map didn't touch are left alone.

### Catalog
Build or update a persistent inventory of every FLAC track in a directory, with its canonical tags. Unlike `read`, which extracts *legacy* tags for migration into the canonical schema, `catalog` reads the canonical tags already present on already-tagged files, and is meant to be rerun periodically as the library changes.

```bash
python src/tagger.py \
    catalog \
    --dir "path/to/music/library" \
    --db "catalog.db" \
    --csv "catalog.csv" \
    [--prune]
```

This will:
- Scan the directory recursively for FLAC files
- Read the canonical Tag Fields (see above) directly from each file
- Repair any file that's missing an audio checksum (still all-zero), and catalog it under its real checksum
- Add or update one row per track in the SQLite database and the CSV export

Arguments:
- `--dir`, `-d`: Directory containing music files (required)
- `--db`: Path to the SQLite catalog database (required)
- `--csv`: Path to the CSV catalog export (required)
- `--prune`: Remove rows for tracks no longer found in `--dir`

#### Track identity
Each track is keyed on `audio_md5`, a checksum of the decoded audio samples that FLAC's encoder embeds in every file. Unlike a file path, this key survives everything else in this tool that renames files or folders (`write`, `structure --mode rename_dirs`, `standardize`) — a track keeps the same catalog row across any of those operations, with its `path` column simply updated to match. The key only changes if the audio itself changes, for example after `convert`.

Because the key is derived from the audio itself, two different files can end up sharing one catalog row, for two different reasons:

- **Missing checksums.** A small number of FLAC encoders never compute this checksum, leaving it as all zeros. `catalog` repairs these automatically: it decodes the file with `sox`, computes the real checksum, and writes it back into the file's own STREAMINFO block, so the repair is permanent and the file gets its own catalog row from then on. If a repair attempt fails (for example, `sox` isn't installed, or the file can't be decoded), the file falls back to the old behavior: it's still catalogued, but under the shared all-zero key, so it may share a row with other unrepaired files. Every file `catalog` finds missing a checksum, whether repaired or not, is listed in `missing_checksums.csv`, written next to the CSV catalog export. Each row has the file's path, whether it was repaired, the new checksum if it was, and the reason if it wasn't.
- **Genuinely identical audio.** Two different files can have real, correctly-computed checksums that just happen to match — the same recording appearing on more than one release, for example. `catalog` can't repair this (there's nothing wrong with either file), so it reports it instead: every file involved in such a match is listed in `duplicates.csv`, written next to the CSV catalog export, with the file that ends up kept in the catalog marked `kept` and the rest marked `shadowed`. Deciding what to do about a genuine duplicate (keep both, remove one, merge tags) is left to you.

#### Staying in sync
Because files can be deleted or moved outside this tool, `catalog` can't be told about a deletion directly — it notices one the next time it scans and a previously-catalogued track isn't there. Every track found in a scan gets its `last_seen` timestamp updated; run without `--prune`, a track missing from the current scan just stops getting a fresh `last_seen` (it stays in the catalog, visibly stale). Run with `--prune`, any row not touched by the current scan is deleted.

#### Output files
The SQLite database has one `tracks` table, with `audio_md5` as the primary key, a `path` column, a `last_seen` timestamp, and one column per canonical Tag Field, named in snake_case (`year_recorded`, `catalog_number`, and so on). The CSV export mirrors the same table but uses the actual tag names as headers (`Year Recorded`, `Catalog #`, and so on) instead of the snake_case column names.

If any checksums were missing, `catalog` also writes `missing_checksums.csv` in the same directory as `--csv`; if any genuine audio duplicates were found, it writes `duplicates.csv` there too (see "Track identity" above for both).

### Error Handling
- Failed tag operations are logged to a separate Excel file
- The utility preserves the original tags if an update operation fails
- Unicode characters are properly handled using the XLSXWriter engine

## Utility Scripts
These standalone scripts remain under `utils/` and are not yet integrated into `tagger.py`.

### Find and Remove Empty Tags Script
The `find_remove_empty_tags.py` script finds and removes empty tags from FLAC files.

#### Usage
```bash
python utils/find_remove_empty_tags.py "path/to/music/files" [--dry-run]
```

- `dir`: Directory to search for FLAC files.
- `--dry-run`: Generate a report without removing empty tags.

## Testing
The codebase includes comprehensive unit tests using pytest. Tests cover:

- Tag parsing from file paths and FLAC metadata
- Album metadata extraction from paths and tags
- Track metadata parsing including:
  - Movement parsing
  - Epithet extraction 
  - Opus/catalog number handling
  - Key signature detection
  - Work and movement titles
- Error handling and edge cases
- DataFrame operations

Run tests with:
```bash
pytest
```
