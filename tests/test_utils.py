################################################################################
### test_utils.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import unicodedata

from src.utils import filenames_match, get_audio_md5, is_missing_checksum, normalize_nfc, repair_missing_checksum

from tests.conftest import FakeAudio, FakeCompletedProcess, make_flac_side_effect, mock_sox_failure, mock_sox_success

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
