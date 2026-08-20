################################################################################
### test_catalog.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import csv
import sqlite3
from argparse import Namespace

import pytest

from src.catalog import (
    CATALOG_FIELDS,
    DUPLICATE_REPORT_HEADER,
    MISSING_CHECKSUM_REPORT_HEADER,
    build_track_row,
    find_duplicate_tracks,
    repair_missing_checksum_tracks,
    run,
    scan_tracks,
    to_snake_case,
    write_duplicate_report,
    write_missing_checksum_report,
)
from src.utils import MISSING_CHECKSUM_MD5

from tests.conftest import (
    FakeAudio,
    FakeCompletedProcess,
    SAMPLE_TAGS,
    make_flac_side_effect,
    mock_sox_failure,
    mock_sox_success,
)

################################################################################
### to_snake_case
################################################################################

@pytest.mark.parametrize('display_name, expected', [
    ('Composer', 'composer'),
    ('Album', 'album'),
    ('Year Recorded', 'year_recorded'),
    ('Orchestra', 'orchestra'),
    ('Conductor', 'conductor'),
    ('Soloists', 'soloists'),
    ('Arranger', 'arranger'),
    ('Genre', 'genre'),
    ('DiscNumber', 'disc_number'),
    ('TrackNumber', 'track_number'),
    ('Title', 'title'),
    ('TrackTitle', 'track_title'),
    ('Work', 'work'),
    ('Work Number', 'work_number'),
    ('InitialKey', 'initial_key'),
    ('Catalog #', 'catalog_number'),
    ('Opus', 'opus'),
    ('Opus Number', 'opus_number'),
    ('Epithet', 'epithet'),
    ('Movement', 'movement'),
])
def test_to_snake_case(display_name, expected):
    assert to_snake_case(display_name) == expected

################################################################################
### build_track_row / scan_tracks
################################################################################

def test_build_track_row_reads_canonical_tags(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio(dict(SAMPLE_TAGS), md5_signature=42)
    mocker.patch('src.catalog.FLAC', return_value=audio)

    row = build_track_row(str(track))

    assert row['audio_md5'] == f"{42:032x}"
    assert row['path'] == str(track)
    assert row['composer'] == 'Ludwig van Beethoven'
    assert row['work_number'] == 'No 5'
    assert row['catalog_number'] is None  # empty tag value

def test_scan_tracks_skips_unreadable_and_counts_missing_checksum(tmp_path, mocker):
    good = tmp_path / "01 - Good.flac"
    good.write_text("dummy")
    missing = tmp_path / "02 - Missing.flac"
    missing.write_text("dummy")
    bad = tmp_path / "03 - Bad.flac"
    bad.write_text("dummy")

    audios = {
        str(good): FakeAudio(dict(SAMPLE_TAGS), md5_signature=1),
        str(missing): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
    }

    def fake_flac(path):
        if path == str(bad):
            raise Exception("corrupt file")
        return audios[path]

    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)

    rows, missing_checksum_count, skipped = scan_tracks([str(good), str(missing), str(bad)])

    assert len(rows) == 2
    assert missing_checksum_count == 1
    assert skipped == [str(bad)]

################################################################################
### repair_missing_checksum_tracks
################################################################################

def test_repair_missing_checksum_tracks_mutates_successful_rows_in_place(mocker):
    rows = [
        {'audio_md5': f"{1:032x}", 'path': '/music/a.flac'},
        {'audio_md5': MISSING_CHECKSUM_MD5, 'path': '/music/b.flac'},
        {'audio_md5': MISSING_CHECKSUM_MD5, 'path': '/music/c.flac'},
    ]

    def fake_repair(path):
        if path == '/music/b.flac':
            return f"{555:032x}", None
        return None, "sox exited with code 1"

    mocker.patch('src.catalog.repair_missing_checksum', side_effect=fake_repair)

    report = repair_missing_checksum_tracks(rows)

    assert rows[0]['audio_md5'] == f"{1:032x}"  # untouched, checksum wasn't missing
    assert rows[1]['audio_md5'] == f"{555:032x}"  # repaired in place
    assert rows[2]['audio_md5'] == MISSING_CHECKSUM_MD5  # left missing, repair failed

    assert len(report) == 2
    by_path = {entry['path']: entry for entry in report}
    assert by_path['/music/b.flac'] == {
        'path': '/music/b.flac', 'status': 'repaired',
        'new_audio_md5': f"{555:032x}", 'reason': '',
    }
    assert by_path['/music/c.flac'] == {
        'path': '/music/c.flac', 'status': 'failed',
        'new_audio_md5': '', 'reason': 'sox exited with code 1',
    }

def test_repair_missing_checksum_tracks_none_missing_returns_empty(mocker):
    repair_mock = mocker.patch('src.catalog.repair_missing_checksum')
    rows = [{'audio_md5': f"{1:032x}", 'path': '/music/a.flac'}]

    report = repair_missing_checksum_tracks(rows)

    assert report == []
    repair_mock.assert_not_called()

################################################################################
### write_missing_checksum_report
################################################################################

def test_write_missing_checksum_report_writes_header_and_rows(tmp_path):
    report = [
        {'path': '/music/a.flac', 'status': 'repaired', 'new_audio_md5': f"{555:032x}", 'reason': ''},
        {'path': '/music/b.flac', 'status': 'failed', 'new_audio_md5': '', 'reason': 'sox exited with code 1'},
    ]
    csv_path = tmp_path / "missing_checksums.csv"

    write_missing_checksum_report(report, str(csv_path))

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == MISSING_CHECKSUM_REPORT_HEADER
    assert rows[1] == ['/music/a.flac', 'repaired', f"{555:032x}", '']
    assert rows[2] == ['/music/b.flac', 'failed', '', 'sox exited with code 1']

################################################################################
### find_duplicate_tracks
################################################################################

def test_find_duplicate_tracks_last_path_in_group_is_kept():
    rows = [
        {'audio_md5': 'aaa', 'path': '/music/a1.flac'},
        {'audio_md5': 'aaa', 'path': '/music/a2.flac'},
        {'audio_md5': 'aaa', 'path': '/music/a3.flac'},
        {'audio_md5': 'bbb', 'path': '/music/b.flac'},
    ]

    report = find_duplicate_tracks(rows)

    by_path = {entry['path']: entry for entry in report}
    assert by_path['/music/a1.flac']['status'] == 'shadowed'
    assert by_path['/music/a2.flac']['status'] == 'shadowed'
    assert by_path['/music/a3.flac']['status'] == 'kept'
    assert '/music/b.flac' not in by_path  # unique checksum, not a duplicate
    assert all(entry['audio_md5'] == 'aaa' for entry in report)

def test_find_duplicate_tracks_no_duplicates_returns_empty():
    rows = [
        {'audio_md5': 'aaa', 'path': '/music/a.flac'},
        {'audio_md5': 'bbb', 'path': '/music/b.flac'},
    ]

    assert find_duplicate_tracks(rows) == []

def test_find_duplicate_tracks_excludes_missing_checksum_group():
    rows = [
        {'audio_md5': MISSING_CHECKSUM_MD5, 'path': '/music/a.flac'},
        {'audio_md5': MISSING_CHECKSUM_MD5, 'path': '/music/b.flac'},
    ]

    assert find_duplicate_tracks(rows) == []

################################################################################
### write_duplicate_report
################################################################################

def test_write_duplicate_report_writes_header_and_rows(tmp_path):
    report = [
        {'audio_md5': 'aaa', 'path': '/music/a1.flac', 'status': 'shadowed'},
        {'audio_md5': 'aaa', 'path': '/music/a2.flac', 'status': 'kept'},
    ]
    csv_path = tmp_path / "duplicates.csv"

    write_duplicate_report(report, str(csv_path))

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == DUPLICATE_REPORT_HEADER
    assert rows[1] == ['aaa', '/music/a1.flac', 'shadowed']
    assert rows[2] == ['aaa', '/music/a2.flac', 'kept']

################################################################################
### run
################################################################################

def test_run_happy_path_writes_db_and_csv(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audio = FakeAudio(dict(SAMPLE_TAGS), md5_signature=1)
    mocker.patch('src.catalog.FLAC', return_value=audio)
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5, path, composer, work_number FROM tracks").fetchall()
    conn.close()
    assert rows == [(f"{1:032x}", str(track), 'Ludwig van Beethoven', 'No 5')]

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        data_rows = list(reader)
    assert header == ['Audio MD5', 'Path', 'Last Seen'] + CATALOG_FIELDS
    assert data_rows[0][0] == f"{1:032x}"
    assert data_rows[0][1] == str(track)
    assert data_rows[0][3] == 'Ludwig van Beethoven'  # first CATALOG_FIELDS column


def test_run_upserts_on_second_run(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(
        {**SAMPLE_TAGS, 'Composer': ['Original Composer']}, md5_signature=7))
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(
        {**SAMPLE_TAGS, 'Composer': ['Updated Composer']}, md5_signature=7))
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT composer FROM tracks").fetchall()
    conn.close()
    assert rows == [('Updated Composer',)]


def test_run_prune_removes_stale_rows(tmp_path, mocker):
    track_a = tmp_path / "01 - A.flac"
    track_a.write_text("dummy")
    track_b = tmp_path / "02 - B.flac"
    track_b.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(track_a): FakeAudio(dict(SAMPLE_TAGS), md5_signature=1),
        str(track_b): FakeAudio(dict(SAMPLE_TAGS), md5_signature=2),
    }
    mocker.patch('src.catalog.FLAC', side_effect=lambda path: audios[path])
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    track_b.unlink()
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=True))

    conn = sqlite3.connect(str(db_path))
    remaining = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert remaining == [(f"{1:032x}",)]


def test_run_without_prune_leaves_stale_rows(tmp_path, mocker):
    track_a = tmp_path / "01 - A.flac"
    track_a.write_text("dummy")
    track_b = tmp_path / "02 - B.flac"
    track_b.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(track_a): FakeAudio(dict(SAMPLE_TAGS), md5_signature=1),
        str(track_b): FakeAudio(dict(SAMPLE_TAGS), md5_signature=2),
    }
    mocker.patch('src.catalog.FLAC', side_effect=lambda path: audios[path])
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    first_seen = dict(conn.execute("SELECT audio_md5, last_seen FROM tracks").fetchall())
    conn.close()

    track_b.unlink()
    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = dict(conn.execute("SELECT audio_md5, last_seen FROM tracks").fetchall())
    conn.close()
    assert set(rows.keys()) == {f"{1:032x}", f"{2:032x}"}
    assert rows[f"{2:032x}"] == first_seen[f"{2:032x}"]  # not rescanned, timestamp unchanged
    assert rows[f"{1:032x}"] != first_seen[f"{1:032x}"]  # rescanned, timestamp advanced


def test_run_missing_checksum_repair_fails_falls_back_to_shared_row(tmp_path, mocker, capsys):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(dict(SAMPLE_TAGS), md5_signature=0))
    mock_sox_failure(mocker)  # sox fails before repair ever calls FLAC again, so no utils.FLAC patch needed
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert rows == [('0' * 32,)]

    with open(tmp_path / "missing_checksums.csv", newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        report_rows = list(reader)
    assert report_rows[0] == MISSING_CHECKSUM_REPORT_HEADER
    assert report_rows[1][0] == str(track)
    assert report_rows[1][1] == 'failed'

    out = capsys.readouterr().out.lower()
    assert "missing" in out
    assert "could not be repaired" in out


def test_run_missing_checksum_repair_succeeds_gets_own_row(tmp_path, mocker, capsys):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {str(track): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0)}
    mock_sox_success(mocker)
    fake_flac = make_flac_side_effect(audios, reencoded_md5_by_path={str(track): 555})
    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)  # build_track_row's own read
    mocker.patch('utils.FLAC', side_effect=fake_flac)        # repair_missing_checksum's reads

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert rows == [(f"{555:032x}",)]

    with open(tmp_path / "missing_checksums.csv", newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        report_rows = list(reader)
    assert report_rows[1][1] == 'repaired'
    assert report_rows[1][2] == f"{555:032x}"

    assert "repaired" in capsys.readouterr().out.lower()


def test_run_two_missing_checksum_files_get_separate_rows_after_repair(tmp_path, mocker):
    track_a = tmp_path / "01 - A.flac"
    track_a.write_text("dummy")
    track_b = tmp_path / "02 - B.flac"
    track_b.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(track_a): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
        str(track_b): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
    }
    mock_sox_success(mocker)
    fake_flac = make_flac_side_effect(audios, reencoded_md5_by_path={str(track_a): 111, str(track_b): 222})
    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)
    mocker.patch('utils.FLAC', side_effect=fake_flac)

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks ORDER BY audio_md5").fetchall()
    conn.close()
    assert rows == [(f"{111:032x}",), (f"{222:032x}",)]


def test_run_two_missing_checksum_files_both_fail_repair_still_collapse(tmp_path, mocker):
    track_a = tmp_path / "01 - A.flac"
    track_a.write_text("dummy")
    track_b = tmp_path / "02 - B.flac"
    track_b.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(track_a): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
        str(track_b): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
    }
    mocker.patch('src.catalog.FLAC', side_effect=lambda path: audios[path])
    mock_sox_failure(mocker)  # sox fails before repair ever calls FLAC again, so no utils.FLAC patch needed

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert rows == [('0' * 32,)]

    # Both files share the missing-checksum key, not genuinely identical audio --
    # already reported in missing_checksums.csv, so duplicates.csv must stay empty.
    assert not (tmp_path / "duplicates.csv").exists()


def test_run_duplicate_nonzero_hash_collapses_to_one_row_and_is_reported(tmp_path, mocker):
    track_a = tmp_path / "01 - A.flac"
    track_a.write_text("dummy")
    track_b = tmp_path / "02 - B.flac"
    track_b.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(track_a): FakeAudio(dict(SAMPLE_TAGS), md5_signature=99),
        str(track_b): FakeAudio(dict(SAMPLE_TAGS), md5_signature=99),
    }
    mocker.patch('src.catalog.FLAC', side_effect=lambda path: audios[path])

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert rows == [(f"{99:032x}",)]

    with open(tmp_path / "duplicates.csv", newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        report_rows = list(reader)
    assert report_rows[0] == DUPLICATE_REPORT_HEADER
    statuses = {row[1]: row[2] for row in report_rows[1:]}
    assert statuses[str(track_a)] == 'shadowed'
    assert statuses[str(track_b)] == 'kept'


def test_run_unreadable_file_is_skipped_not_aborted(tmp_path, mocker, capsys):
    good = tmp_path / "01 - Good.flac"
    good.write_text("dummy")
    bad = tmp_path / "02 - Bad.flac"
    bad.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    good_audio = FakeAudio(dict(SAMPLE_TAGS), md5_signature=1)

    def fake_flac(path):
        if path == str(bad):
            raise Exception("corrupt file")
        return good_audio

    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert rows == [(f"{1:032x}",)]
    assert str(bad) in capsys.readouterr().out


def test_run_mixed_normal_repaired_failed_and_unreadable(tmp_path, mocker):
    normal = tmp_path / "01 - Normal.flac"
    normal.write_text("dummy")
    repaired = tmp_path / "02 - Repaired.flac"
    repaired.write_text("dummy")
    failed = tmp_path / "03 - Failed.flac"
    failed.write_text("dummy")
    unreadable = tmp_path / "04 - Unreadable.flac"
    unreadable.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    audios = {
        str(normal): FakeAudio(dict(SAMPLE_TAGS), md5_signature=1),
        str(repaired): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
        str(failed): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0),
    }

    def fake_run(command, capture_output=True):
        source_path = command[1]
        dest_path = command[-1]
        if source_path == str(failed):
            return FakeCompletedProcess(returncode=1, stdout=b'', stderr=b'sox: could not decode')
        with open(dest_path, 'wb') as f:
            f.write(f"REENCODED:{source_path}".encode())
        return FakeCompletedProcess(returncode=0)

    mocker.patch('utils.subprocess.run', side_effect=fake_run)

    def fake_flac(path):
        if path in audios:
            return audios[path]
        if path == str(unreadable):
            raise Exception("corrupt file")
        with open(path, 'rb') as f:
            marker = f.read().decode()
        assert marker.startswith("REENCODED:")
        return FakeAudio(dict(SAMPLE_TAGS), md5_signature=555)

    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)  # build_track_row's own reads
    mocker.patch('utils.FLAC', side_effect=fake_flac)        # repair_missing_checksum's reads

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT audio_md5 FROM tracks").fetchall()
    conn.close()
    assert len(rows) == 3
    md5s = {row[0] for row in rows}
    assert f"{1:032x}" in md5s
    assert f"{555:032x}" in md5s
    assert '0' * 32 in md5s

    with open(tmp_path / "missing_checksums.csv", newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        report_rows = list(reader)
    assert len(report_rows) == 3  # header + repaired + failed
    statuses = {row[0]: row[1] for row in report_rows[1:]}
    assert statuses[str(repaired)] == 'repaired'
    assert statuses[str(failed)] == 'failed'


def test_run_no_missing_checksums_does_not_write_report(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(dict(SAMPLE_TAGS), md5_signature=1))
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    assert not (tmp_path / "missing_checksums.csv").exists()


def test_run_no_duplicates_does_not_write_report(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(dict(SAMPLE_TAGS), md5_signature=1))
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    assert not (tmp_path / "duplicates.csv").exists()


def test_run_report_paths_next_to_csv_output(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    audios = {str(track): FakeAudio(dict(SAMPLE_TAGS), md5_signature=0)}
    mock_sox_success(mocker)
    fake_flac = make_flac_side_effect(audios, reencoded_md5_by_path={str(track): 555})
    mocker.patch('src.catalog.FLAC', side_effect=fake_flac)
    mocker.patch('utils.FLAC', side_effect=fake_flac)

    db_path = tmp_path / "catalog.db"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    csv_path = output_dir / "catalog.csv"

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    assert (output_dir / "missing_checksums.csv").exists()
    assert not (tmp_path / "missing_checksums.csv").exists()


def test_run_removes_stale_missing_checksum_report_when_none_remain(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"
    report_path = tmp_path / "missing_checksums.csv"
    report_path.write_text("stale report from a previous run")

    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(dict(SAMPLE_TAGS), md5_signature=1))

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    assert not report_path.exists()


def test_run_removes_stale_duplicate_report_when_none_remain(tmp_path, mocker):
    track = tmp_path / "01 - Track.flac"
    track.write_text("dummy")
    db_path = tmp_path / "catalog.db"
    csv_path = tmp_path / "catalog.csv"
    report_path = tmp_path / "duplicates.csv"
    report_path.write_text("stale report from a previous run")

    mocker.patch('src.catalog.FLAC', return_value=FakeAudio(dict(SAMPLE_TAGS), md5_signature=1))

    run(Namespace(dir=str(tmp_path), db=str(db_path), csv=str(csv_path), prune=False))

    assert not report_path.exists()
