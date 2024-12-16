import os
import pytest
import pandas as pd
from read import get_flac_files, create_tags_dataframe, get_tracks_create_dataframe

@pytest.fixture
def setup_test_dir(tmp_path):
    test_dir = tmp_path / "test_music"
    test_dir.mkdir()
    test_file = test_dir / "test.flac"
    test_file.write_text('')
    return test_dir, test_file

def test_get_flac_files_no_flac_files(tmp_path):
    test_dir = tmp_path / "test_music"
    test_dir.mkdir()
    with pytest.raises(ValueError, match="No FLAC files found in the specified directory."):
        get_flac_files(test_dir)

def test_get_flac_files(setup_test_dir):
    test_dir, test_file = setup_test_dir
    flac_files = get_flac_files(test_dir)
    assert flac_files == [str(test_file)]

def test_create_tags_dataframe(setup_test_dir):
    _, test_file = setup_test_dir
    track_path_list = [str(test_file)]
    tags_df = create_tags_dataframe(track_path_list)
    assert tags_df.index.tolist() == track_path_list
    assert 'Composer' in tags_df.columns

def test_get_tracks_create_dataframe(setup_test_dir):
    test_dir, test_file = setup_test_dir
    tags_df = get_tracks_create_dataframe(test_dir)
    assert tags_df.index.tolist() == [str(test_file)]
    assert 'Composer' in tags_df.columns