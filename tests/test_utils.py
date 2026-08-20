################################################################################
### test_utils.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import logging
import os
import unicodedata

import pytest

from src.utils import (
    filenames_match, get_audio_md5, get_repo_root, is_missing_checksum,
    normalize_nfc, repair_missing_checksum, setup_logging, walk_with_progress,
)

from tests.conftest import FakeAudio, FakeCompletedProcess, make_flac_side_effect, mock_sox_failure, mock_sox_success

@pytest.fixture(autouse=True)
def reset_root_logger():
    """Restore the root logger's handlers/level after each test, since
    setup_logging (like logging.basicConfig) mutates global state."""
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    yield
    logging.root.handlers = original_handlers
    logging.root.level = original_level

################################################################################
### get_audio_md5 / is_missing_checksum
################################################################################

def test_get_audio_md5_formats_as_32_char_hex():
    audio = FakeAudio({}, md5_signature=305441741)
    assert get_audio_md5(audio) == f"{305441741:032x}"
    assert len(get_audio_md5(audio)) == 32

def test_is_missing_checksum():
    assert is_missing_checksum('0' * 32) is True
    assert is_missing_checksum('a' * 32) is False

################################################################################
### filenames_match / normalize_nfc
################################################################################

def test_filenames_match_nfc_vs_nfd():
    nfc_name = unicodedata.normalize('NFC', "Böhm")
    nfd_name = unicodedata.normalize('NFD', "Böhm")
    assert nfc_name != nfd_name  # sanity check: genuinely different byte sequences
    assert filenames_match(nfc_name, nfd_name) is True

def test_filenames_match_different_names():
    assert filenames_match("Böhm", "Karajan") is False

def test_normalize_nfc_normalizes_string():
    nfd_name = unicodedata.normalize('NFD', "Böhm")
    assert normalize_nfc(nfd_name) == unicodedata.normalize('NFC', "Böhm")

def test_normalize_nfc_passes_through_non_string():
    assert normalize_nfc(None) is None

################################################################################
### repair_missing_checksum
################################################################################

def test_repair_missing_checksum_success(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mock_sox_success(mocker)
    original_audio = FakeAudio({}, md5_signature=0)
    mocker.patch('src.utils.FLAC', side_effect=make_flac_side_effect(
        {str(track): original_audio}, reencoded_md5_by_path={str(track): 555}))

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 == f"{555:032x}"
    assert error is None
    assert original_audio.info.md5_signature == 555
    assert original_audio.saved is True

def test_repair_missing_checksum_sox_nonzero_exit(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mock_sox_failure(mocker, stderr=b'sox FAIL formats: no handler for file extension')
    flac_mock = mocker.patch('src.utils.FLAC')

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 is None
    assert 'no handler' in error
    flac_mock.assert_not_called()

def test_repair_missing_checksum_sox_empty_output(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch(
        'src.utils.subprocess.run',
        return_value=FakeCompletedProcess(returncode=0, stdout=b'', stderr=b''),
    )
    flac_mock = mocker.patch('src.utils.FLAC')

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 is None
    assert error == "sox produced no output file"
    flac_mock.assert_not_called()

def test_repair_missing_checksum_sox_missing_binary(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch('src.utils.subprocess.run', side_effect=FileNotFoundError("no sox"))

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 is None
    assert "could not run sox" in error

def test_repair_missing_checksum_reencoded_stream_still_missing(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mock_sox_success(mocker)
    mocker.patch('src.utils.FLAC', side_effect=make_flac_side_effect(
        {}, reencoded_md5_by_path={str(track): 0}))

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 is None
    assert "missing" in error

def test_repair_missing_checksum_write_back_fails(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mock_sox_success(mocker)

    def fake_flac(path):
        if path == str(track):
            raise Exception("cannot open original file")
        return FakeAudio({}, md5_signature=555)

    mocker.patch('src.utils.FLAC', side_effect=fake_flac)

    new_md5, error = repair_missing_checksum(str(track))

    assert new_md5 is None
    assert "could not write it back" in error

################################################################################
### get_repo_root
################################################################################

def test_get_repo_root_points_at_the_repository_root():
    root = get_repo_root()
    assert os.path.isfile(os.path.join(root, 'src', 'utils.py'))

################################################################################
### setup_logging
################################################################################

def test_setup_logging_console_only_when_no_log_file():
    setup_logging('INFO', None)

    assert len(logging.root.handlers) == 1
    assert isinstance(logging.root.handlers[0], logging.StreamHandler)
    assert logging.root.handlers[0].level == logging.INFO

def test_setup_logging_adds_file_handler_always_at_debug(tmp_path):
    log_file = tmp_path / "run.log"
    setup_logging('WARNING', str(log_file))

    console_handlers = [h for h in logging.root.handlers if isinstance(h, logging.StreamHandler)
                         and not isinstance(h, logging.FileHandler)]
    file_handlers = [h for h in logging.root.handlers if isinstance(h, logging.FileHandler)]

    assert len(console_handlers) == 1
    assert console_handlers[0].level == logging.WARNING
    assert len(file_handlers) == 1
    assert file_handlers[0].level == logging.DEBUG

def test_setup_logging_file_captures_debug_regardless_of_console_level(tmp_path, capsys):
    log_file = tmp_path / "run.log"
    setup_logging('INFO', str(log_file))
    logger = logging.getLogger('test_setup_logging_module')

    logger.debug("only for the file")
    logger.info("visible on console too")

    console_output = capsys.readouterr().err
    assert "visible on console too" in console_output
    assert "only for the file" not in console_output

    file_contents = log_file.read_text()
    assert "only for the file" in file_contents
    assert "visible on console too" in file_contents
    assert "test_setup_logging_module" in file_contents  # detailed format includes the logger name

################################################################################
### walk_with_progress
################################################################################

def test_walk_with_progress_yields_same_tuples_as_os_walk(tmp_path):
    (tmp_path / "album_a").mkdir()
    (tmp_path / "album_a" / "track.flac").write_text("dummy")
    (tmp_path / "album_b").mkdir()

    expected = sorted(os.walk(str(tmp_path)))
    actual = sorted(walk_with_progress(str(tmp_path), desc="Testing"))

    assert actual == expected

def test_walk_with_progress_dirnames_pruning_still_works(tmp_path):
    (tmp_path / "keep").mkdir()
    (tmp_path / "skip").mkdir()
    (tmp_path / "skip" / "nested").mkdir()

    visited = []
    for dirpath, dirnames, _ in walk_with_progress(str(tmp_path), desc="Testing"):
        visited.append(dirpath)
        if os.path.basename(dirpath) == "skip":
            dirnames[:] = []  # prune: do not descend into skip/nested

    assert str(tmp_path / "skip" / "nested") not in visited
