import os
import pytest
from src.read import (
                    # Create dataframe to store tags
                    get_flac_files, create_tags_dataframe, get_tracks_create_dataframe,
                    # Process track path: get album string, disc number from track path
                    get_album_string_from_track_path, get_disc_number_from_track_path,
                    parse_performer_string, parse_fields_from_matching_album_string,
                    get_tags_from_file_with_unmatched_album_string, 
                    get_fields_from_album_string
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

# Integration test for get_fields_from_album_string
def test_get_fields_from_album_string_matching_pattern():    
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/01 - Track.flac"
    result = get_fields_from_album_string(path)
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
    result = get_fields_from_album_string(path)
    assert result == ("Album", "2024", "Orchestra", "Conductor")

# Integration test for get_fields_from_album_string
# Only need to test one matched example because parse_performer_string has already been tested
def test_get_fields_from_album_string_matched():
    path = "/path/to/Genre/Composer/[2024] Album (Orchestra with Conductor)/Disc 1/01 - Track.flac"
    title, year, orchestra, conductor = get_fields_from_album_string(path)
    assert title == "Album"
    assert year == "2024"
    assert orchestra == "Orchestra"
    assert conductor == "Conductor"

def test_get_fields_from_album_string_unmatched(mocker):
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
    title, year, orchestra, conductor = get_fields_from_album_string(path)
    assert title == "Album"
    assert year == "2024"
    assert orchestra == "Orchestra"
    assert conductor == "Conductor"