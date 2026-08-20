################################################################################
### test_write.py
### Copyright (c) 2026, Joshua J Hamilton
### Covers the missing-checksum repair integration in update_tags. Does
### not attempt a full retrofit of write.py's other, previously-untested
### logic (title-building, filename-safety, etc.).
################################################################################

################################################################################
### Import packages
################################################################################

import shutil
from pathlib import Path

import mutagen.flac
import pandas as pd

from src.write import update_tags

################################################################################
### Helpers
################################################################################

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample.flac"

def make_track_copy(tmp_path, name="01 - Track.flac"):
    """Copy the fixture FLAC to a temp path so each test gets an independent file."""
    dest = tmp_path / name
    shutil.copy(FIXTURE_PATH, dest)
    return dest

def force_missing_checksum(path):
    """Set a real FLAC file's STREAMINFO checksum to all zeros, as if never computed."""
    audio = mutagen.flac.FLAC(str(path))
    audio.info.md5_signature = 0
    audio.save()

################################################################################
### update_tags: missing-checksum repair integration
################################################################################

def test_update_tags_repairs_missing_checksum_before_saving_tags(tmp_path, mocker):
    """
    Regression test for the staleness bug: if repair ran after write.py's own
    tag-editing FLAC object were opened (or wrote through a stale cached
    object), the later tag save would silently overwrite a same-iteration
    repair back to all zeros. This uses a real fixture file and a real
    mutagen write inside the mocked repair function specifically so this
    checksum assertion is a faithful check of mutagen's real object-caching
    behavior, not of a hand-rolled double's assumptions about it.
    """
    track = make_track_copy(tmp_path)
    force_missing_checksum(track)

    def fake_repair(path):
        audio = mutagen.flac.FLAC(path)
        audio.info.md5_signature = 0xDEADBEEF
        audio.save()
        return f"{0xDEADBEEF:032x}", None

    mocker.patch('src.write.repair_missing_checksum', side_effect=fake_repair)

    tags_df = pd.DataFrame({'Work': ['Test Work'], 'TrackNumber': ['1']}, index=[str(track)])
    successful_df, failed_df = update_tags(tags_df)

    assert str(track) in successful_df.index
    assert failed_df.empty

    final_files = list(tmp_path.glob("*.flac"))
    assert len(final_files) == 1
    reopened = mutagen.flac.FLAC(str(final_files[0]))
    assert reopened.info.md5_signature == 0xDEADBEEF  # not clobbered back to 0 by the tag save
    assert reopened['Title'][0] == 'Test Work'  # tags were actually written

def test_update_tags_writes_tags_even_if_repair_fails(tmp_path, mocker):
    track = make_track_copy(tmp_path)
    force_missing_checksum(track)
    mocker.patch('src.write.repair_missing_checksum', return_value=(None, "sox exited with code 1"))

    tags_df = pd.DataFrame({'Work': ['Test Work'], 'TrackNumber': ['1']}, index=[str(track)])
    successful_df, failed_df = update_tags(tags_df)

    assert str(track) in successful_df.index
    assert failed_df.empty

    final_files = list(tmp_path.glob("*.flac"))
    assert len(final_files) == 1
    reopened = mutagen.flac.FLAC(str(final_files[0]))
    assert reopened.info.md5_signature == 0  # still missing, repair failed but tags still written
    assert reopened['Title'][0] == 'Test Work'

def test_update_tags_skips_repair_when_checksum_already_real(tmp_path, mocker):
    track = make_track_copy(tmp_path)  # fixture's own real, encoder-computed checksum
    repair_mock = mocker.patch('src.write.repair_missing_checksum')

    tags_df = pd.DataFrame({'Work': ['Test Work'], 'TrackNumber': ['1']}, index=[str(track)])
    update_tags(tags_df)

    repair_mock.assert_not_called()

def test_update_tags_unreadable_file_reported_not_fatal(tmp_path):
    bad = tmp_path / "01 - Bad.flac"
    bad.write_text("not a flac file")
    good = make_track_copy(tmp_path, name="02 - Good.flac")

    tags_df = pd.DataFrame(
        {'Work': ['Bad Work', 'Good Work'], 'TrackNumber': ['1', '2']},
        index=[str(bad), str(good)],
    )
    successful_df, failed_df = update_tags(tags_df)

    assert str(bad) in failed_df.index
    assert str(good) in successful_df.index
