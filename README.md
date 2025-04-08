# Custom Tagging of Classical Music Files
Copyright (c) 2024, Joshua J. Hamilton  
Email: <joshamilton@gmail.com>  
URL: <https://www.linkedin.com/in/joshamilton/>  
URL: <https://github.com/joshamilton/>  
All rights reserved.

A command-line utility for managing metadata tags in classical music FLAC files. This tool helps maintain consistent tagging across your classical music collection by extracting information from file paths and existing tags.

The tool was written to reflect my personal idiosyncrasies in tagging classical music, so it is probably not suitable for general use.

## Features
- Reads existing FLAC metadata tags and file path information
- Extracts structured information including:
  - Composer
  - Album
  - Year Recorded
  - Orchestra
  - Conductor
  - Soloist
  - Genre
  - Disc and Track Numbers
  - Work metadata (opus numbers, catalog numbers, keys, etc.)
- Supports batch updates from Excel files
- Preserves unicode characters in tags
- Tracks successful and failed tag operations

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

## Usage
The utility has two modes: read and write.

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
- Update the FLAC files with new tags
- Save any failed operations to the output Excel file

### Arguments
- mode: Operation mode (read or write)
- --dir, -d: Directory containing music files (required for read mode)
- --excel_in, -i: Input Excel file with tags (required for write mode)
- --excel_out, -o: Output Excel file (required)

### Tag Fields
The utility manages the following tag fields:

#### Work Metadata
- Work: The main musical work (e.g. "Symphony", "String Quartet")
- Work Number: Numerical designation (e.g. "No 41")
- Initial Key: Key signature (e.g. "C major", "E-flat")
- Catalog Number: Standard catalog reference (e.g. "K 551", "BWV 1046")
- Opus: Opus designation (e.g. "Op 55")
- Opus Number: Sub-designation within opus (e.g. "No 1")
- Epithet: Common name (e.g. "Jupiter", "Eroica")
- Movement: Movement number and tempo (e.g. "I. Allegro con brio")
- Title: Full title constructed according to the following pattern: 
  
  \<Work\> \<Work Number\>, \<Catalog Number\>, \<Opus\>, \<Opus Number\>, in \<Initial Key\>, '\<Epithet\>' - \<Movement\>

#### Recording Metadata
- Album: Full album title
- Year Recorded: Recording year
- Orchestra: Performing ensemble
- Conductor: Conductor name
- Composer: Composer name
- Genre: Musical period/style
- Disc Number: For multi-disc sets
- Track Number: Position on disc

### Error Handling
- Failed tag operations are logged to a separate Excel file
- The utility preserves the original tags if an update operation fails
- Unicode characters are properly handled using the XLSXWriter engine

## Utility Scripts

### Folder Structure Script
The `structure.py` script organizes and cleans up album directories. It supports multiple modes of operation, including creating `Scans.pdf`, renaming disc folders, and cleaning up unnecessary files and empty directories. The script can also generate a single CSV file summarizing all actions for human inspection.

#### Usage
```bash
python utils/structure.py --dir "path/to/music/files" --mode [make_scans|rename_dirs|cleanup|all] [--dry-run] [--output-csv "output.csv"]
```

- `--dir`: Directory to process (required).
- `--mode`: Mode of operation (required). Options:
  - `make_scans`: Creates `Scans.pdf` for each subdirectory and deletes original image and PDF files.
  - `rename_dirs`: Renames disc folders based on audio file content and naming patterns.
  - `cleanup`: Removes unnecessary files and empty directories.
  - `all`: Combines all modes into a single operation.
- `--dry-run`: Logs actions without making changes.
- `--output-csv`: Path to the output CSV file summarizing all actions (default: `output.csv`).

#### Modes
1. **`make_scans`**:
   - Combines image and PDF files in each subdirectory into a single `Scans.pdf`.
   - Deletes the original files after creating the PDF.
   - Logs included files to the CSV file.

2. **`rename_dirs`**:
   - Renames disc folders to a standardized format (`Disc #`) based on audio file content.
   - Generates a CSV file with mappings of original folder names to revised names.

3. **`cleanup`**:
   - Removes files that do not match allowed extensions (`.pdf`, `.log`, `.cue`, `.flac`, `.ape`, `.wv`, `.wav`).
   - Removes empty directories.
   - Logs deleted files and directories to the CSV file.

4. **`all`**:
   - Combines `make_scans`, `rename_dirs`, and `cleanup` into a single operation.
   - Logs all actions to the CSV file, separated by mode.

5. **`--dry-run`**:
   - Generates a report of actions without making any changes.

#### CSV Output
The CSV file provides a clear summary of all actions performed, or that would be performed in `--dry-run` mode. The script generates a single CSV file summarizing all actions. Each mode is separated by a blank line and includes appropriate headers. 


### Cleanup Script
The `cleanup.py` script finds and removes files that are not FLAC, CUE, LOG, or PDF. It also renames files with uppercase extensions to lowercase and reports albums missing either a FLAC or CUE file.

#### Usage
```bash
python utils/cleanup.py --dir "path/to/music/files" [--dry-run]
```

- `--dir`: Directory to scan for files.
- `--dry-run`: Generate a report without making changes.

### Convert Script
The `convert.py` script converts 24-bit FLAC files to 16-bit, 44 kHz FLAC files using SoX. It features an "overwrite" option to replace the original files and can be run in dry-run mode to generate reports.

#### Usage
```bash
python utils/convert.py --dir "path/to/music/files" [--dry-run] [--overwrite]
```

- `--dir`: Directory to scan for FLAC files.
- `--dry-run`: Generate a report of files to convert without converting.
- `--overwrite`: Overwrite the original files after conversion.

### Find and Remove Empty Tags Script
The `find_remove_empty_tags.py` script finds and removes empty tags from FLAC files. It can be run in dry-run mode to generate a report of files with empty tags.

#### Usage
```bash
python utils/find_remove_empty_tags.py --dir "path/to/music/files" [--remove]
```

- `--dir`: Directory to search for FLAC files.
- `--remove`: Remove empty tags from files listed in `empty_tags.csv`.

### SQLite to CSV Script
The `sqlite_to_csv.py` script converts a SQLite database to a CSV file.

#### Usage
```bash
python utils/sqlite_to_csv.py --sqlite_db "path/to/tags.db" --csv_file "output.csv"
```

- `--sqlite_db`: Path to the SQLite database file.
- `--csv_file`: Path to the CSV file to write.
## Utility Scripts

### Cleanup Script
The `cleanup.py` script finds and removes files that are not FLAC, CUE, LOG, or PDF. It also renames files with uppercase extensions to lowercase and reports albums missing either a FLAC or CUE file.

#### Usage
```bash
python utils/cleanup.py --dir "path/to/music/files" [--dry-run]
```

- `--dir`: Directory to scan for files.
- `--dry-run`: Generate a report without making changes.

### Convert Script
The `convert.py` script converts 24-bit FLAC files to 16-bit, 44 kHz FLAC files using SoX. It features an "overwrite" option to replace the original files and can be run in dry-run mode to generate reports.

#### Usage
```bash
python utils/convert.py --dir "path/to/music/files" [--dry-run] [--overwrite]
```

- `--dir`: Directory to scan for FLAC files.
- `--dry-run`: Generate a report of files to convert without converting.
- `--overwrite`: Overwrite the original files after conversion.

### Find and Remove Empty Tags Script
The `find_remove_empty_tags.py` script finds and removes empty tags from FLAC files. It can be run in dry-run mode to generate a report of files with empty tags.

#### Usage
```bash
python utils/find_remove_empty_tags.py --dir "path/to/music/files" [--remove]
```

- `--dir`: Directory to search for FLAC files.
- `--dry-run`: Generate a report of files to update `empty_tags.csv` without updating.

### SQLite to CSV Script
The `sqlite_to_csv.py` script converts a SQLite database to a CSV file.

#### Usage
```bash
python utils/sqlite_to_csv.py --sqlite_db "path/to/tags.db" --csv_file "output.csv"
```

- `--sqlite_db`: Path to the SQLite database file.
- `--csv_file`: Path to the CSV file to write.

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