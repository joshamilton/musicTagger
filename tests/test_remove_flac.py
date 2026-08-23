################################################################################
### test_remove_flac.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

from argparse import Namespace

from src.remove_flac import find_files_to_remove, remove_files, run

################################################################################
### find_files_to_remove
################################################################################

def test_find_files_to_remove_matches_case_insensitive(tmp_path):
    to_remove = [
        "01 - Track.flac",
        "EAC.LOG",
        "album.Cue",
        "rip.accurip",
        "playlist.m3u8",
        "cover.JPG",
        "back.png",
        "booklet.TIF",
        "scan.bmp",
    ]
    to_keep = ["01 - Track.mp3", "notes.txt"]
    for name in to_remove + to_keep:
        (tmp_path / name).write_text("dummy")

    found = find_files_to_remove(str(tmp_path))

    expected = sorted(str(tmp_path / name) for name in to_remove)
    assert found == expected

def test_find_files_to_remove_recurses_subdirectories(tmp_path):
    subdir = tmp_path / "Disc 1"
    subdir.mkdir()
    flac = subdir / "01 - Track.flac"
    flac.write_text("dummy")

    found = find_files_to_remove(str(tmp_path))

    assert found == [str(flac)]

################################################################################
### remove_files
################################################################################

def test_remove_files_deletes_files(tmp_path):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")

    busy_files = remove_files([str(track)])

    assert busy_files == []
    assert not track.exists()

def test_remove_files_reports_busy_files(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch('src.remove_flac.os.remove', side_effect=OSError(16, "Resource busy"))

    busy_files = remove_files([str(track)])

    assert busy_files == [str(track)]

################################################################################
### run
################################################################################

def test_run_removes_matching_files_keeps_others(tmp_path):
    flac = tmp_path / "01 - Track.flac"
    flac.write_text("dummy")
    mp3 = tmp_path / "01 - Track.mp3"
    mp3.write_text("dummy")

    run(Namespace(dir=str(tmp_path)))

    assert not flac.exists()
    assert mp3.exists()
