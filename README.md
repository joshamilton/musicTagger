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
python tagger.py \
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
python tagger.py \
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

- Album
- Composer
- Genre
- Year Recorded
- Orchestra
- Conductor
- Soloists
- Arranger
- Disc Number
- Track Number
- Title
- Track Title
- Work
- Work Number
- Initial Key
- Catalog Number
- Opus
- Opus Number
- Epithet
- Movement

### Error Handling
- Failed tag operations are logged to a separate Excel file
- The utility preserves the original tags if an update operation fails
- Unicode characters are properly handled using the XLSXWriter engine