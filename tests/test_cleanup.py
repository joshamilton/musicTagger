################################################################################
### test_cleanup.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import csv
from argparse import Namespace

from src.cleanup import (
    apply_tag_actions,
    find_disallowed_tags,
    run,
    write_tag_report,
)

################################################################################
### Helpers
################################################################################

class FakeAudio:
    """Minimal stand-in for mutagen FLAC for find_disallowed_tags / apply_tag_actions."""

    def __init__(self, tags):
        self.tags = tags

    def __setitem__(self, key, value):
        self.tags[key] = value

    def delete(self):
        self.tags = {}

    def save(self):
        pass

################################################################################
### find_disallowed_tags
################################################################################

def test_find_disallowed_tags_flags_unrecognized(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio({'Album': ['Test Album'], 'ENCODER': ['some ripper']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    actions, errors = find_disallowed_tags(str(tmp_path))

    assert errors == []
    assert actions == [{'path': str(track), 'tag': 'ENCODER'}]


def test_find_disallowed_tags_case_insensitive_keeps_allowed(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio({'album': ['Test Album']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    actions, errors = find_disallowed_tags(str(tmp_path))

    assert errors == []
    assert actions == []

################################################################################
### write_tag_report
################################################################################

def test_write_tag_report_writes_csv(tmp_path):
    actions = [{'path': '/a/track.flac', 'tag': 'ENCODER'}]
    write_tag_report(actions, str(tmp_path))

    with open(tmp_path / "tags.csv", newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    assert rows == [{'path': '/a/track.flac', 'tag': 'ENCODER'}]

################################################################################
### apply_tag_actions
################################################################################

def test_apply_tag_actions_removes_disallowed_keeps_allowed(mocker):
    audio = FakeAudio({'Album': ['Keep'], 'ENCODER': ['Remove me']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    errors = apply_tag_actions([{'path': 'somepath.flac', 'tag': 'ENCODER'}])

    assert errors == []
    assert audio.tags == {'Album': ['Keep']}

################################################################################
### run
################################################################################

def test_run_dry_run_writes_tags_csv_without_modifying(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio({'Album': ['Keep'], 'ENCODER': ['Remove me']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    run(Namespace(dir=str(tmp_path), dry_run=True))

    with open(tmp_path / "tags.csv", newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    assert rows == [{'path': str(track), 'tag': 'ENCODER'}]
    assert audio.tags == {'Album': ['Keep'], 'ENCODER': ['Remove me']}


def test_run_live_removes_disallowed_tags(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio({'Album': ['Keep'], 'ENCODER': ['Remove me']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    run(Namespace(dir=str(tmp_path), dry_run=False))

    assert audio.tags == {'Album': ['Keep']}


def test_run_does_not_write_missing_files_report(tmp_path, mocker):
    # The missing LOG/CUE report was removed: albums added from streaming
    # sources have no LOG or CUE file, so the report was just noise.
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio({'Album': ['Keep']})
    mocker.patch('src.cleanup.FLAC', return_value=audio)

    run(Namespace(dir=str(tmp_path), dry_run=True))
    assert not (tmp_path / "missing.csv").exists()

    run(Namespace(dir=str(tmp_path), dry_run=False))
    assert not (tmp_path / "missing.csv").exists()
