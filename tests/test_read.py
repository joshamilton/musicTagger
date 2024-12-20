################################################################################
### test_read.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import os
import pandas as pd
import pytest
from src.read import (
                    # Create dataframe to store tags
                    get_flac_files, create_tags_dataframe, get_tracks_create_dataframe,
                    # Process track path: get album string, disc number from track path
                    get_album_string_from_track_path, get_disc_number_from_track_path,
                    parse_performer_string, parse_fields_from_matching_album_string,
                    get_tags_from_file_with_unmatched_album_string, 
                    get_album_fields_from_track_path,
                    # Process track string:
                    parse_movement_from_title, parse_epithet_from_title,
                    parse_opus_opusnumber_worknumber_from_title, parse_catalog_from_title,
                    parse_initialkey_from_title, parse_fields_from_title_tag, 
                    get_tags_from_file_without_title_tag, get_track_fields_from_track_path,
                    # Read remaining tags: composer, genre
                    get_genre_composer_tags_from_file,
                    # Final function
                    get_tags
                    )
import re

################################################################################
### Tests for functions associated with
### Create dataframe to store tags
################################################################################

@pytest.fixture
def setup_test_dir(tmp_path):
    test_dir = tmp_path / "test_music"
    test_dir.mkdir()
    test_file = test_dir / "test.flac"
    test_file.write_text('')
    return test_dir, test_file

# Test get_flac_files
def test_get_flac_files_no_flac_files(tmp_path):
    test_dir = tmp_path / "test_music"
    test_dir.mkdir()
    with pytest.raises(ValueError, match="No FLAC files found in the specified directory."):
        get_flac_files(test_dir)

def test_get_flac_files(setup_test_dir):
    test_dir, test_file = setup_test_dir
    flac_files = get_flac_files(test_dir)
    assert flac_files == [str(test_file)]

# Test create_tags_dataframe
def test_create_tags_dataframe(setup_test_dir):
    _, test_file = setup_test_dir
    track_path_list = [str(test_file)]
    tags_df = create_tags_dataframe(track_path_list)
    assert tags_df.index.tolist() == track_path_list
    assert 'Composer' in tags_df.columns

# Integration test: get_tracks_create_dataframe
def test_get_tracks_create_dataframe(setup_test_dir):
    test_dir, test_file = setup_test_dir
    tags_df = get_tracks_create_dataframe(test_dir)
    assert tags_df.index.tolist() == [str(test_file)]
    assert 'Composer' in tags_df.columns

################################################################################
### Tests for functions associated with
### Process track path: get album string, disc number from track path
################################################################################

# Test get_album_string_from_track_path
def test_get_album_string_from_track_path_with_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc 1/01 - Track.flac"
    assert get_album_string_from_track_path(path) == "[2024] Album (Orchestra with Conductor)"

def test_get_album_string_from_track_path_no_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/01 - Track.flac"
    assert get_album_string_from_track_path(path) == "[2024] Album (Orchestra with Conductor)"

# Test get_disc_number_from_track_path
def test_get_disc_number_with_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc 1/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "1"

def test_get_disc_number_with_disk():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disk 2/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "2"

def test_get_disc_number_with_cd():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/CD 3/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "3"

def test_get_disc_number_with_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc4/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "4"

def test_get_disc_number_with_disk():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disk5/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "5"

def test_get_disc_number_with_cd():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/CD6/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "6"

def test_get_disc_number_with_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc 07/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "07"

def test_get_disc_number_with_disk():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disk 08/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "08"

def test_get_disc_number_with_cd():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/CD 09/01 - Track.flac"
    assert get_disc_number_from_track_path(path) == "09"

def test_get_disc_number_no_disc():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/01 - Track.flac"
    assert get_disc_number_from_track_path(path) is None

# Test parse_performer_string
def test_parse_performer_string_with_with():
    result = parse_performer_string("B'Rock Orchestra with Dmitry Sinkovsky")
    assert result == ("B'Rock Orchestra", "Dmitry Sinkovsky")

def test_parse_performer_string_with_comma_orchestra_first():
    result = parse_performer_string("Brandenburg Consort, Goodman")
    assert result == ("Brandenburg Consort", "Goodman")

def test_parse_performer_string_with_comma_conductor_first():
    result = parse_performer_string("Harnoncourt, Concentus Musicus Wien")
    assert result == ("Concentus Musicus Wien", "Harnoncourt")

def test_parse_performer_string_orchestra_only():
    result = parse_performer_string("Capella Savaria")
    assert result == ("Capella Savaria", None)

# Test parse_fields_from_matching_album_string
# Only need one example because parse_performer_string has already been tested
@pytest.fixture
def album_match():
    album_string = "[2024] Album (Orchestra with Conductor)"
    album_pattern = re.compile(r'\[(\d{4})\]\s(.+)')
    match = album_pattern.search(album_string)
    return match

def test_parse_fields_from_matching_album_string(album_match):
    result = parse_fields_from_matching_album_string(album_match)
    assert result == ("Album", "2024", "Orchestra", "Conductor")

# Integration test for get_album_fields_from_track_path
def test_get_album_fields_from_track_path_matching_pattern():    
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/01 - Track.flac"
    result = get_album_fields_from_track_path(path)
    assert result == ("Album", "2024", "Orchestra", "Conductor")

def test_get_tags_from_file_with_unmatched_album_string(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'album': ['Album'],
        'year': ['2024'],
        'orchestra': ['Orchestra'],
        'conductor': ['Conductor']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    result = get_album_fields_from_track_path(path)
    assert result == ("Album", "2024", "Orchestra", "Conductor")

# Integration test for get_album_fields_from_track_path
# Only need to test one matched example because parse_performer_string has already been tested
def test_get_album_fields_from_track_path_matched():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc 1/01 - Track.flac"
    title, year, orchestra, conductor = get_album_fields_from_track_path(path)
    assert title == "Album"
    assert year == "2024"
    assert orchestra == "Orchestra"
    assert conductor == "Conductor"

def test_get_album_fields_from_track_path_unmatched(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'album': ['Album'],
        'year': ['2024'],
        'orchestra': ['Orchestra'],
        'conductor': ['Conductor']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    title, year, orchestra, conductor = get_album_fields_from_track_path(path)
    assert title == "Album"
    assert year == "2024"
    assert orchestra == "Orchestra"
    assert conductor == "Conductor"


################################################################################
### Tests for functions associated with
### Process track string
################################################################################

# Test parse_movement_from_title
# Work, Work Number, in Initial Key, 'Epithet', Catalog #, Opus, Opus Number - I. Movement
# Because movement will always be at the end, only need to test one example
def test_parse_movement_from_title():
    work = "Symphony No 41 in C, 'Jupiter', K 551 - I. Allegro vivace"
    work, movement = parse_movement_from_title(work)
    assert work == "Symphony No 41 in C, 'Jupiter', K 551"
    assert movement == "I. Allegro vivace"

def test_parse_movement_from_title_no_movement():
    work = "Symphony No 41 in C, 'Jupiter', K 551"
    work, movement = parse_movement_from_title(work)
    assert work == "Symphony No 41 in C, 'Jupiter', K 551"
    assert movement is None

# Test parse_epithet_from_title
# Work, Work Number, in Initial Key, 'Epithet', Catalog #, Opus, Opus Number
def test_parse_epithet_from_title_with_epithet():
    work = "Symphony No 41 in C, 'Jupiter', K 551"
    work, epithet = parse_epithet_from_title(work)
    assert work == "Symphony No 41 in C, K 551"
    assert epithet == "Jupiter"

def test_parse_epithet_from_title_without_epithet():
    work = "Symphony No 41 in C, K 551"
    work, epithet = parse_epithet_from_title(work)
    assert work == "Symphony No 41 in C, K 551"
    assert epithet is None

# Test parse_opus_opusnumber_worknumber_from_title
# Work, Work Number in Initial Key, Catalog #, Opus, Opus Number
# Test work number, opus, opus number - with catalog #
def test_parse_opus_opusnumber_worknumber_from_title1():
    work = "String Quartet No 75 in G, Op 76 No 1, Hob.III:75"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G, Hob.III:75"
    assert work_number == "No 75"
    assert opus == "Op 76"
    assert opus_number == "No 1"

# Test work number, opus, opus number - without catalog #
def test_parse_opus_opusnumber_worknumber_from_title2():
    work = "String Quartet No 75 in G, Op 76 No 1"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G,"
    assert work_number == "No 75"
    assert opus == "Op 76"
    assert opus_number == "No 1"

# Test work number, opus, without opus number - with catalog #
def test_parse_opus_opusnumber_worknumber_from_title3():
    work = "String Quartet No 75 in G, Op 76, Hob.III:75"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G, Hob.III:75"
    assert work_number == "No 75"
    assert opus == "Op 76"
    assert opus_number == None

# Test work number, opus, without opus number - without catalog #
def test_parse_opus_opusnumber_worknumber_from_title4():
    work = "String Quartet No 75 in G, Op 76"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G,"
    assert work_number == "No 75"
    assert opus == "Op 76"
    assert opus_number == None

# Test opus, opus number, without work number - with catalog #
def test_parse_opus_opusnumber_worknumber_from_title5():
    work = "String Quartet in G, Op 76 No 1, Hob.III:75"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G, Hob.III:75"
    assert work_number == None
    assert opus == "Op 76"
    assert opus_number == "No 1"

# Test opus, opus number, without work number - without catalog #
def test_parse_opus_opusnumber_worknumber_from_title6():
    work = "String Quartet in G, Op 76 No 1"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G"
    assert work_number == None
    assert opus == "Op 76"
    assert opus_number == "No 1"

# Test opus, without opus number, without work number - with catalog #
def test_parse_opus_opusnumber_worknumber_from_title7():
    work = "String Quartet in G, Op 76, Hob.III:75"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G, Hob.III:75"
    assert work_number == None
    assert opus == "Op 76"
    assert opus_number == None

# Test opus, without opus number, without work number - without catalog #
def test_parse_opus_opusnumber_worknumber_from_title8():
    work = "String Quartet in G, Op 76"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G"
    assert work_number == None
    assert opus == "Op 76"
    assert opus_number == None

# Test work without opus, without opus number, without work number - with catalog #
def test_parse_opus_opusnumber_worknumber_from_title9():
    work = "String Quartet in G, Hob.III:75"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G, Hob.III:75"
    assert work_number == None
    assert opus == None
    assert opus_number == None

# Test work without opus, without opus number, without work number - without catalog #
def test_parse_opus_opusnumber_worknumber_from_title10():
    work = "String Quartet in G"
    work, work_number, opus, opus_number = parse_opus_opusnumber_worknumber_from_title(work)
    assert work == "String Quartet in G"
    assert work_number == None
    assert opus == None
    assert opus_number == None

# Test parse_catalog_from_title
# Work in Initial Key, Catalog #
def test_parse_catalog_from_title_with_catalog():
    work = "Symphony in C, K 551"
    work, catalog_number = parse_catalog_from_title(work)
    assert work == "Symphony in C"
    assert catalog_number == "K 551"

def test_parse_catalog_from_title_without_catalog():
    work = "Symphony in C"
    work, catalog_number = parse_catalog_from_title(work)
    assert work == "Symphony in C"
    assert catalog_number is None

# Test parse_initialkey_from_title
# Work in Initial Key
def test_parse_initialkey_from_title_major():
    work = "Symphony in E-flat"
    work, key = parse_initialkey_from_title(work)
    assert work == "Symphony"
    assert key == "E-flat"

def test_parse_initialkey_from_title_minor():
    work = "Symphony in C minor"
    work, key = parse_initialkey_from_title(work)
    assert work == "Symphony"
    assert key == "C minor"

# Test parse_fields_from_title_tag
def test_parse_fields_from_title_tag1(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ['Concerto Grosso in G, Op 6 No 1, HWV 319 - I. A tempo giusto']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    work, work_number, initial_key, catalog_number, opus, opus_number, \
        epithet, movement = parse_fields_from_title_tag(path)
    assert work == "Concerto Grosso"
    assert work_number is None
    assert initial_key == "G"
    assert catalog_number == "HWV 319"
    assert opus == "Op 6"
    assert opus_number == "No 1"
    assert epithet is None 
    assert movement == "I. A tempo giusto"

def test_parse_fields_from_title_tag2(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ['String Quartet No 75 in G, Op 76 No 1, Hob.III:75 - I. Allegro con spirito']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    work, work_number, initial_key, catalog_number, opus, opus_number, \
        epithet, movement = parse_fields_from_title_tag(path)
    assert work == "String Quartet"
    assert work_number == "No 75"
    assert initial_key == "G"
    assert catalog_number == "Hob.III:75"
    assert opus == "Op 76"
    assert opus_number == "No 1"
    assert epithet is None
    assert movement == "I. Allegro con spirito"

# YOU ARE HERE - NEXT TESTS ARE FAILING
def test_parse_fields_from_title_tag3(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ["Symphony No 41 in C, 'Jupiter', K 551 - I. Allegro vivace"]
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    work, work_number, initial_key, catalog_number, opus, opus_number, \
        epithet, movement = parse_fields_from_title_tag(path)
    assert work == "Symphony"
    assert work_number == "No 41"
    assert initial_key == "C"
    assert catalog_number == "K 551"
    assert opus is None
    assert opus_number is None
    assert epithet == "Jupiter"
    assert movement == "I. Allegro vivace"

def test_parse_fields_from_title_tag4(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ["Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio"]
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    work, work_number, initial_key, catalog_number, opus, opus_number, \
        epithet, movement = parse_fields_from_title_tag(path)
    assert work == "Symphony"
    assert work_number == "No 3"
    assert initial_key == "E-flat"
    assert catalog_number is None
    assert opus == "Op 55"
    assert opus_number is None
    assert epithet == "Eroica"
    assert movement == "I. Allegro con brio"

# Test get_tags_from_file_without_title_tag
def test_get_tags_from_file_without_title_tag(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ['Symphony'],
        'work number': ['No 3'],
        'initialkey': ['E-flat'],
        'catalog #': None,
        'opus': ['Op 55'],
        'opus number': None,
        'epithet': ['Eroica'],
        'movement': ['I. Allegro con brio']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    result = get_tags_from_file_without_title_tag(path)
    assert result == ("Symphony", "No 3", "E-flat", None, "Op 55", None, "Eroica", "I. Allegro con brio")

# Test get_track_fields_from_track_path
# Two examples needed: one with title tag, one without
def test_get_track_fields_from_track_path_without_title_tag(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file with no title tag but other tags present
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {}  # Empty tags dict to simulate missing title tag
    mock_flac.__getitem__.side_effect = lambda x: {
        'tracknumber': ['01'],
        'title': ['Symphony'],
        'work number': ['No 3'],
        'initialkey': ['E-flat'],
        'opus': ['Op 55'],
        'epithet': ['Eroica'],
        'movement': ['I. Allegro con brio']
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    track_number, work, work_number, initial_key, catalog_number, opus, \
        opus_number, epithet, movement = get_track_fields_from_track_path(path)
    
    assert track_number == '01'
    assert work == 'Symphony'
    assert work_number == 'No 3' 
    assert initial_key == 'E-flat'
    assert catalog_number is None
    assert opus == 'Op 55'
    assert opus_number is None
    assert epithet == 'Eroica'
    assert movement == 'I. Allegro con brio'

def test_get_track_fields_from_track_path_with_title_tag(mocker):
    # Mock FLAC audio file with a title tag present
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {'title': ["Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio"]}  # Title tag exists
    mock_flac.__getitem__.side_effect = lambda x: {
        'tracknumber': ['01'],
        'title': ["Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio"]
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    track_number, work, work_number, initial_key, catalog_number, opus, \
        opus_number, epithet, movement = get_track_fields_from_track_path(path)
    
    assert track_number == '01'
    assert work == 'Symphony'
    assert work_number == 'No 3'
    assert initial_key == 'E-flat'
    assert catalog_number is None
    assert opus == 'Op 55'
    assert opus_number is None
    assert epithet == 'Eroica'
    assert movement == 'I. Allegro con brio'

################################################################################
### Tests for functions associated with
### Read remaining tags: composer, genre
################################################################################

def test_get_genre_composer_tags_from_file_both_tags(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'genre': ['Genre'],
        'composer': ['Composer']
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    result = get_genre_composer_tags_from_file(path)
    assert result == ("Genre", "Composer")

def test_get_genre_composer_tags_from_file_genre_only(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'genre': ['Genre'],
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    result = get_genre_composer_tags_from_file(path)
    assert result == ("Genre", None)

def test_get_genre_composer_tags_from_file_composer_only(mocker):
    # Use mocking because 1) test FLAC file doesn't exist, 2) don't want to test mutagen
    # Mock FLAC audio file
    mock_flac = mocker.MagicMock()
    mock_flac.__getitem__.side_effect = lambda x: {
        'composer': ['Composer'],
    }[x]
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)

    path = "/path/to/Genre/Composer/Album/01 - Track.flac"
    result = get_genre_composer_tags_from_file(path)
    assert result == (None, "Composer")


################################################################################
### Tests for master get_tags function
################################################################################

def test_get_tags_1(mocker):
    # Mock FLAC file with Handel Concerto Grosso tags
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {'title': ['Concerto Grosso in G, Op 6 No 1, HWV 319 - I. A tempo giusto']}
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ['Concerto Grosso in G, Op 6 No 1, HWV 319 - I. A tempo giusto'],
        'tracknumber': ['01'],
        'album': ['Concerti Grossi Op 3 & Op 6'],
        'year': ['1971'],
        'orchestra': ['Munchener Bach-Orchester'],
        'conductor': ['Karl Richter'],
        'genre': ['Baroque'],
        'composer': ['Handel, George Frideric'],
        'discnumber': ['2']
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    # Create test dataframe with one track
    path = "/path/to/01 - Baroque/Handel, George Frideric/Concerti Grossi/[1971] Concerti Grossi Op 3 & Op 6 (Munchener Bach-Orchester with Karl Richter)/Disc 2/01 - Concerto Grosso in G, Op 6 No 1, HWV 319 - I. A tempo giusto.flac"
    df = pd.DataFrame(index=[path])
    df = get_tags(df)

    # Test all metadata fields
    assert df.loc[path, 'Work'] == 'Concerto Grosso'
    assert df.loc[path, 'Work Number'] is None
    assert df.loc[path, 'InitialKey'] == 'G'
    assert df.loc[path, 'Catalog #'] == 'HWV 319'
    assert df.loc[path, 'Opus'] == 'Op 6'
    assert df.loc[path, 'Opus Number'] == 'No 1'
    assert df.loc[path, 'Movement'] == 'I. A tempo giusto'
    assert df.loc[path, 'TrackNumber'] == '01'
    assert df.loc[path, 'DiscNumber'] == '2'
    assert df.loc[path, 'Album'] == 'Concerti Grossi Op 3 & Op 6'
    assert df.loc[path, 'Year Recorded'] == '1971'
    assert df.loc[path, 'Orchestra'] == 'Munchener Bach-Orchester'
    assert df.loc[path, 'Conductor'] == 'Karl Richter'
    assert df.loc[path, 'Genre'] == 'Baroque'
    assert df.loc[path, 'Composer'] == 'Handel, George Frideric'

def test_get_tags_2(mocker):
    # Mock FLAC file with Haydn String Quartet tags
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {'title': ['String Quartet No 75 in G, Op 76 No 1, Hob.III:75 - I. Allegro con spirito']}
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ['String Quartet No 75 in G, Op 76 No 1, Hob.III:75 - I. Allegro con spirito'],
        'tracknumber': ['01'],
        'album': ['The Complete String Quartets'],
        'year': ['2009'],
        'orchestra': ['Aeolian String Quartet'],
        'genre': ['Classical'],
        'composer': ['Haydn, Franz Joseph'],
        'discnumber': ['19']
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/02 - Classical/Haydn, Franz Joseph/String Quartets/[2009] The Complete String Quartets (Aeolian String Quartet)/Disc 19/01 - String Quartet No 75 in G, Op 76 No 1, Hob.III:75 - I. Allegro con spirito.flac"
    df = pd.DataFrame(index=[path])
    df = get_tags(df)
    
    assert df.loc[path, 'Work'] == 'String Quartet'
    assert df.loc[path, 'Work Number'] == 'No 75'
    assert df.loc[path, 'InitialKey'] == 'G'
    assert df.loc[path, 'Catalog #'] == 'Hob.III:75'
    assert df.loc[path, 'Opus'] == 'Op 76'
    assert df.loc[path, 'Opus Number'] == 'No 1'
    assert df.loc[path, 'Movement'] == 'I. Allegro con spirito'
    assert df.loc[path, 'TrackNumber'] == '01'
    assert df.loc[path, 'DiscNumber'] == '19'
    assert df.loc[path, 'Album'] == 'The Complete String Quartets'
    assert df.loc[path, 'Year Recorded'] == '2009'
    assert df.loc[path, 'Orchestra'] == 'Aeolian String Quartet'
    assert df.loc[path, 'Genre'] == 'Classical'
    assert df.loc[path, 'Composer'] == 'Haydn, Franz Joseph'

def test_get_tags_3(mocker):
    # Mock FLAC file with Mozart Symphony tags
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {'title': ["Symphony No 41 in C, 'Jupiter', K 551 - I. Allegro vivace"]}
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ["Symphony No 41 in C, 'Jupiter', K 551 - I. Allegro vivace"],
        'tracknumber': ['01'],
        'album': ['Symphonies Nos 35 & 41'],
        'year': ['1960'],
        'orchestra': ['Columbia SO'],
        'conductor': ['Bruno Walter'],
        'genre': ['Classical'],
        'composer': ['Mozart, Wolfgang Amadeus']
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/02 - Classical/Mozart, Wolfgang Amadeus/Symphonies/[1960] Symphonies Nos 35 & 41 (Columbia SO with Bruno Walter)/01 - Symphony No 41 in C, 'Jupiter', K 551 - I. Allegro vivace.flac"
    df = pd.DataFrame(index=[path])
    df = get_tags(df)
    
    assert df.loc[path, 'Work'] == 'Symphony'
    assert df.loc[path, 'Work Number'] == 'No 41'
    assert df.loc[path, 'InitialKey'] == 'C'
    assert df.loc[path, 'Catalog #'] == 'K 551'
    assert df.loc[path, 'Epithet'] == 'Jupiter'
    assert df.loc[path, 'Movement'] == 'I. Allegro vivace'
    assert df.loc[path, 'TrackNumber'] == '01'
    assert df.loc[path, 'Album'] == 'Symphonies Nos 35 & 41'
    assert df.loc[path, 'Year Recorded'] == '1960'
    assert df.loc[path, 'Orchestra'] == 'Columbia SO'
    assert df.loc[path, 'Conductor'] == 'Bruno Walter'
    assert df.loc[path, 'Genre'] == 'Classical'
    assert df.loc[path, 'Composer'] == 'Mozart, Wolfgang Amadeus'

def test_get_tags_4(mocker):
    # Mock FLAC file with Beethoven Symphony tags
    mock_flac = mocker.MagicMock()
    mock_flac.tags = {'title': ["Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio"]}
    mock_flac.__getitem__.side_effect = lambda x: {
        'title': ["Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio"],
        'tracknumber': ['05'],
        'album': ['9 Symphonien'],
        'year': ['1963'],
        'orchestra': ['Berlin'],
        'conductor': ['Karajan'],
        'genre': ['Classical'],
        'composer': ['Beethoven, Ludwig van']
    }[x]
    
    # Mock mutagen.flac.FLAC
    mocker.patch('mutagen.flac.FLAC', return_value=mock_flac)
    
    path = "/path/to/03 - Classical/Beethoven, Ludwig van/Symphonies/[1963] 9 Symphonien (Karajan, Berlin, 1963)/05 - Symphony No 3 in E-flat, 'Eroica', Op 55 - I. Allegro con brio.flac"
    df = pd.DataFrame(index=[path])
    df = get_tags(df)
    
    assert df.loc[path, 'Work'] == 'Symphony'
    assert df.loc[path, 'Work Number'] == 'No 3'
    assert df.loc[path, 'InitialKey'] == 'E-flat'
    assert df.loc[path, 'Opus'] == 'Op 55'
    assert df.loc[path, 'Epithet'] == 'Eroica'
    assert df.loc[path, 'Movement'] == 'I. Allegro con brio'
    assert df.loc[path, 'TrackNumber'] == '05'
    assert df.loc[path, 'Album'] == '9 Symphonien'
    assert df.loc[path, 'Year Recorded'] == '1963'
    assert df.loc[path, 'Orchestra'] == 'Berlin'
    assert df.loc[path, 'Conductor'] == 'Karajan'
    assert df.loc[path, 'Genre'] == 'Classical'
    assert df.loc[path, 'Composer'] == 'Beethoven, Ludwig van'