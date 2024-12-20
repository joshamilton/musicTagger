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