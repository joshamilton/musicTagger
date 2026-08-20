################################################################################
### test_standardize.py
### Copyright (c) 2026, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import csv
import os
import unicodedata
from argparse import Namespace

import pytest

from src.standardize import (
    CSV_FIELDNAMES,
    add_track_tags_to_uniques,
    album_folder_for_file,
    analyze_album,
    apply_album_rename,
    apply_disc_renames_for_album,
    apply_plan_live_for_albums,
    apply_rename_rows,
    apply_retag_mappings,
    build_disc_mappings,
    build_performance_info,
    build_plan_from_dir,
    collect_track_tags,
    compute_retag_updates,
    detect_file_list_kind,
    earliest_year,
    empty_unique_tag_sets,
    flip_to_last_first,
    format_conductor,
    format_soloists,
    load_retag_mappings,
    normalize_soloists_field,
    parse_disc_number,
    planned_renames_from_dir,
    read_rename_list,
    remap_soloists_field,
    run,
    sanitize_component,
    write_unique_tag_lists,
)

################################################################################
### Helpers
################################################################################

def make_disc_with_flac(parent, name):
    """Create a disc-like folder containing a dummy .flac file."""
    disc_path = parent / name
    disc_path.mkdir()
    (disc_path / "01 - Track.flac").write_text("dummy")
    return disc_path


def tags(**kwargs):
    base = {
        'year': None,
        'album': None,
        'orchestra': None,
        'conductor': None,
        'soloists': None,
    }
    base.update(kwargs)
    return base


def empty_plan_fields(**overrides):
    """Default empty CSV plan fields for file-list fixtures."""
    row = {key: '' for key in CSV_FIELDNAMES}
    row.update(overrides)
    return row

################################################################################
### parse_disc_number
################################################################################

def test_parse_disc_number_variants():
    assert parse_disc_number("Disc 1") == 1
    assert parse_disc_number("CD 10") == 10
    assert parse_disc_number("Disk 03") == 3
    assert parse_disc_number("Disc 1 - Bonus") == 1
    assert parse_disc_number("CD01") == 1
    assert parse_disc_number("Scans") is None
    assert parse_disc_number("Booklet") is None


def test_album_folder_for_file_direct_and_via_disc():
    assert album_folder_for_file("/lib/Composer/Album/track.flac") == "/lib/Composer/Album"
    assert (
        album_folder_for_file("/lib/Composer/Album/Disc 1/track.flac")
        == "/lib/Composer/Album"
    )

################################################################################
### build_disc_mappings
################################################################################

def test_build_mappings_padding_and_stripping(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "CD 1")
    make_disc_with_flac(album, "Disc 10 - Bonus")

    mappings = build_disc_mappings(str(album))
    by_original = {m['original_name']: m for m in mappings}

    assert by_original["CD 1"]["path"] == str(album)
    assert by_original["CD 1"]["new_name"] == "Disc 01"
    assert by_original["CD 1"]["needs_rename"] is True
    assert by_original["CD 1"]["type"] == "disc"
    assert by_original["Disc 10 - Bonus"]["new_name"] == "Disc 10"
    assert by_original["Disc 10 - Bonus"]["needs_rename"] is True


def test_build_mappings_skip_if_already_correct(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disc 1")
    make_disc_with_flac(album, "Disc 2")

    mappings = build_disc_mappings(str(album))
    assert all(m["needs_rename"] is False for m in mappings)
    assert {m["new_name"] for m in mappings} == {"Disc 1", "Disc 2"}


def test_build_mappings_cd_and_disk_to_disc(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "CD 1")
    make_disc_with_flac(album, "Disk 2")

    mappings = build_disc_mappings(str(album))
    names = {m["new_name"] for m in mappings}
    assert names == {"Disc 1", "Disc 2"}


def test_build_mappings_ignores_non_disc_and_empty_disc(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disc 1")
    (album / "Scans.pdf").write_text("pdf")
    empty_disc = album / "Disc 2"
    empty_disc.mkdir()

    mappings = build_disc_mappings(str(album))
    assert len(mappings) == 1
    assert mappings[0]["original_name"] == "Disc 1"

################################################################################
### Soloists / year / performance templates
################################################################################

def test_format_soloists_flip_sort_join():
    raw = "Ax, Emmanual; Stern, Isaac; Laredo, Jamie; Ma, Yo-Yo"
    result = format_soloists(raw)
    assert result == "Emmanual Ax, Jamie Laredo, Yo-Yo Ma, and Isaac Stern"


def test_format_soloists_one_and_two():
    assert format_soloists("Leonhardt, Gustav") == "Gustav Leonhardt"
    assert format_soloists("Ax, Emmanual; Stern, Isaac") == "Emmanual Ax and Isaac Stern"


def test_flip_to_last_first():
    assert flip_to_last_first("Isaac Stern") == "Stern, Isaac"
    assert flip_to_last_first("Yo-Yo Ma") == "Ma, Yo-Yo"
    assert flip_to_last_first("Jean Pierre Rampal") == "Rampal, Jean Pierre"
    assert flip_to_last_first("Stern, Isaac") == "Stern, Isaac"
    assert flip_to_last_first("Cher") == "Cher"


def test_normalize_soloists_field_flip_sort_join():
    raw = "Isaac Stern; Ax, Emmanual; Yo-Yo Ma"
    assert normalize_soloists_field(raw) == "Ax, Emmanual; Ma, Yo-Yo; Stern, Isaac"


def test_normalize_soloists_field_dedupes_after_flip():
    raw = "Isaac Stern; Stern, Isaac; Stern, Isaac"
    assert normalize_soloists_field(raw) == "Stern, Isaac"


def test_normalize_soloists_field_no_op_when_already_sorted():
    raw = "Ax, Emmanual; Stern, Isaac"
    assert normalize_soloists_field(raw) == raw


def test_normalize_soloists_field_empty_input():
    assert normalize_soloists_field(None) is None
    assert normalize_soloists_field('') == ''


def test_format_conductor_flip():
    assert format_conductor("Ansermet, Ernest") == "Ernest Ansermet"
    assert format_conductor("Trevor Pinnock") == "Trevor Pinnock"
    assert format_conductor(None) is None


def test_sanitize_component_colon_slash():
    assert sanitize_component("Schubert: 'Trout'") == "Schubert - 'Trout'"
    assert sanitize_component("A/B\\C") == "A-B-C"


def test_earliest_year():
    assert earliest_year(["1960-1967", "1970"]) == "1960"
    assert earliest_year(["1978"]) == "1978"
    assert earliest_year([None, ""]) is None


def test_build_performance_info_templates():
    assert build_performance_info("O", None, None) == ("O", None)
    assert build_performance_info("O", "C", None) == ("O with C", None)
    assert build_performance_info("O", None, "S") == ("O with S", None)
    assert build_performance_info(None, None, "S") == ("S", None)
    assert build_performance_info("O", "C", "S") == ("O with C and S", None)
    assert build_performance_info(None, "C", "S") == ("C with S", None)


def test_build_performance_info_flag_cases():
    assert build_performance_info(None, None, None)[1]
    assert build_performance_info(None, "C", None)[1]


def test_analyze_album_planned(tmp_path):
    album = tmp_path / "Old Name"
    album.mkdir()
    track_tags = [
        tags(year="1960", album="Organ Works", soloists="Alain, Marie-Claire"),
        tags(year="1965", album="Organ Works", soloists="Alain, Marie-Claire"),
    ]
    row = analyze_album(str(album), track_tags=track_tags)
    assert row["status"] == "planned"
    assert row["year_chosen"] == "1960"
    assert row["album_chosen"] == "Organ Works"
    assert row["soloist_chosen"] == "Marie-Claire Alain"
    assert row["performance_info"] == "Marie-Claire Alain"
    assert row["path"] == str(tmp_path)
    assert row["original_name"] == "Old Name"
    assert row["new_name"] == "[1960] Organ Works (Marie-Claire Alain)"


def test_analyze_album_orchestra_with_conductor(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[tags(
            year="1982",
            album="Brandenburg Concertos",
            orchestra="English Concert",
            conductor="Pinnock, Trevor",
        )],
    )
    assert row["status"] == "planned"
    assert row["orchestra_chosen"] == "English Concert"
    assert row["conductor_chosen"] == "Trevor Pinnock"
    assert row["soloist_chosen"] == ""
    assert row["performance_info"] == "English Concert with Trevor Pinnock"


def test_analyze_album_skipped_when_names_differ_only_by_normalization(tmp_path):
    # The on-disk folder name is stored decomposed (NFD); the tag-built name
    # comes back precomposed (NFC), the way write.py normalizes tags. Same
    # text, different encoding -- must not be treated as a needed rename.
    canonical_name = "[1959] 46 Symphonies (Berlin Philharmonic with Karl Böhm)"
    on_disk_name = unicodedata.normalize('NFD', canonical_name)
    album = tmp_path / on_disk_name
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[tags(
            year="1959",
            album="46 Symphonies",
            orchestra="Berlin Philharmonic",
            conductor=unicodedata.normalize('NFC', "Karl Böhm"),
        )],
    )
    assert row["status"] == "skipped"


def test_analyze_album_flags_no_perf(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[tags(year="2000", album="Echoes")],
    )
    assert row["status"] == "flagged"
    assert "no Orchestra/Conductor/Soloists" in row["flag_reason"]


def test_analyze_album_conductor_with_soloist(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[tags(
            year="2000",
            album="X",
            conductor="Barbirolli, John",
            soloists="Cortot, Alfred",
        )],
    )
    assert row["status"] == "planned"
    assert row["conductor_chosen"] == "John Barbirolli"
    assert row["soloist_chosen"] == "Alfred Cortot"
    assert row["performance_info"] == "John Barbirolli with Alfred Cortot"
    assert row["new_name"] == "[2000] X (John Barbirolli with Alfred Cortot)"


def test_analyze_album_flags_tie(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[
            tags(year="2000", album="A", orchestra="O1"),
            tags(year="2000", album="A", orchestra="O2"),
        ],
    )
    assert row["status"] == "flagged"
    assert "tie for most common Orchestra" in row["flag_reason"]


def test_analyze_album_flags_conflicting_albums(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    row = analyze_album(
        str(album),
        track_tags=[
            tags(year="2000", album="A", soloists="X, Y"),
            tags(year="2000", album="B", soloists="X, Y"),
        ],
    )
    assert row["status"] == "flagged"
    assert "conflicting Album" in row["flag_reason"]

################################################################################
### disc apply
################################################################################

def test_planned_renames_only_needs_rename(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "CD 1")
    make_disc_with_flac(album, "Disc 2")

    planned = planned_renames_from_dir(str(tmp_path))
    assert len(planned) == 1
    assert planned[0]["type"] == "disc"
    assert planned[0]["path"] == str(album)
    assert planned[0]["original_name"] == "CD 1"
    assert planned[0]["new_name"] == "Disc 1"


def test_apply_disc_renames_already_correct_reports_not_renamed(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disc 1")
    make_disc_with_flac(album, "Disc 2")

    errors, renamed = apply_disc_renames_for_album(str(album))

    assert errors == []
    assert renamed is False
    assert (album / "Disc 1").is_dir()
    assert (album / "Disc 2").is_dir()


def test_apply_duplicate_disc_numbers_error(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disk 03")
    make_disc_with_flac(album, "Disc 3")

    errors, renamed = apply_disc_renames_for_album(str(album))
    assert errors
    assert renamed
    assert (album / "Disk 03").is_dir()
    assert (album / "Disc 3").is_dir()


def test_apply_padding_collision_with_existing(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disc 1")
    make_disc_with_flac(album, "Disc 10")

    errors, renamed = apply_disc_renames_for_album(str(album))
    assert errors == []
    assert renamed
    assert (album / "Disc 01").is_dir()
    assert (album / "Disc 10").is_dir()
    assert not (album / "Disc 1").exists()


def test_apply_two_phase_when_targets_overlap_sources(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    make_disc_with_flac(album, "Disc 1")
    make_disc_with_flac(album, "Disc 2")
    make_disc_with_flac(album, "Disc 10")

    errors, renamed = apply_disc_renames_for_album(str(album))
    assert errors == []
    assert renamed
    assert (album / "Disc 01").is_dir()
    assert (album / "Disc 02").is_dir()
    assert (album / "Disc 10").is_dir()
    assert not (album / "Disc 1").exists()
    assert not (album / "Disc 2").exists()

################################################################################
### album apply
################################################################################

def test_apply_album_rename_noop_when_names_differ_only_by_normalization(tmp_path):
    # Same scenario as the analyze_album regression above, but at the apply
    # layer: on APFS, os.path.exists() finds the source folder itself under
    # its NFC spelling, which used to be misreported as "destination already
    # exists." The rename must be treated as already satisfied instead.
    canonical_name = "[1985] Bruggen Conducts Mozart (Frans Brüggen)"
    on_disk_name = unicodedata.normalize('NFD', canonical_name)
    nfc_name = unicodedata.normalize('NFC', canonical_name)
    album = tmp_path / on_disk_name
    album.mkdir()

    row = {'path': str(tmp_path), 'original_name': on_disk_name, 'new_name': nfc_name}
    errors = apply_album_rename(row)

    assert errors == []
    assert (tmp_path / on_disk_name).is_dir()


def test_apply_album_rename_real_collision_still_errors(tmp_path):
    album = tmp_path / "Old Name"
    album.mkdir()
    (tmp_path / "New Name").mkdir()

    row = {'path': str(tmp_path), 'original_name': "Old Name", 'new_name': "New Name"}
    errors = apply_album_rename(row)

    assert errors == ["destination already exists: " + str(tmp_path / "New Name")]

################################################################################
### Scoped live rename (retag-touched albums)
################################################################################

def test_apply_plan_live_for_albums_scopes_to_given_albums(tmp_path, mocker):
    root = tmp_path / "lib"
    touched = root / "Composer" / "Old Name"
    touched.mkdir(parents=True)
    touched_track = touched / "01 - Track.flac"
    touched_track.write_text("dummy")

    untouched = root / "Composer" / "Untouched Old Name"
    untouched.mkdir(parents=True)
    untouched_track = untouched / "01 - Track.flac"
    untouched_track.write_text("dummy")

    audios = {
        str(touched_track): FakeAudio({
            'Year Recorded': ['1960'],
            'Album': ['Organ Works'],
            'Soloists': ['Alain, Marie-Claire'],
        }),
        str(untouched_track): FakeAudio({
            'Year Recorded': ['1960'],
            'Album': ['Should Not Rename'],
            'Soloists': ['Alain, Marie-Claire'],
        }),
    }
    mocker.patch('src.standardize.FLAC', side_effect=lambda path: audios[path])

    errors = apply_plan_live_for_albums({str(touched)})

    assert errors == []
    assert not touched.exists()
    assert (touched.parent / "[1960] Organ Works (Marie-Claire Alain)").is_dir()
    assert untouched.is_dir()

################################################################################
### Unique tag lists
################################################################################

def test_add_track_tags_splits_soloists():
    uniques = empty_unique_tag_sets()
    add_track_tags_to_uniques(
        [
            tags(
                album="A",
                orchestra="O1",
                conductor="C1",
                soloists="Ax, Emmanual; Stern, Isaac",
            ),
            tags(
                album="A",
                orchestra="O2",
                conductor="C1",
                soloists="Stern, Isaac",
            ),
        ],
        uniques,
    )
    assert uniques['albums'] == {"A"}
    assert uniques['orchestras'] == {"O1", "O2"}
    assert uniques['conductors'] == {"C1"}
    assert uniques['soloists'] == {"Ax, Emmanual", "Stern, Isaac"}


def test_write_unique_tag_lists(tmp_path):
    uniques = empty_unique_tag_sets()
    uniques['albums'].add("Brandenburg")
    uniques['soloists'].update(["Stern, Isaac", "Ax, Emmanual"])
    out = tmp_path / "plan.csv"
    write_unique_tag_lists(uniques, str(out))

    with open(tmp_path / "plan_albums.csv", newline='', encoding='utf-8-sig') as f:
        albums = list(csv.DictReader(f))
    with open(tmp_path / "plan_soloists.csv", newline='', encoding='utf-8-sig') as f:
        soloists = list(csv.DictReader(f))
    assert list(albums[0].keys()) == ['original_album', 'new_album']
    assert [r['original_album'] for r in albums] == ["Brandenburg"]
    assert albums[0]['new_album'] == ''
    assert [r['original_soloist'] for r in soloists] == ["Ax, Emmanual", "Stern, Isaac"]
    assert all(r['new_soloist'] == '' for r in soloists)
    with open(tmp_path / "plan_orchestras.csv", newline='', encoding='utf-8-sig') as f:
        assert list(csv.DictReader(f)) == []
    with open(tmp_path / "plan_conductors.csv", newline='', encoding='utf-8-sig') as f:
        assert list(csv.DictReader(f)) == []


################################################################################
### Retag mappings
################################################################################

class FakeAudio:
    """Minimal stand-in for mutagen FLAC for get_tag / compute_retag_updates."""

    def __init__(self, tags):
        self.tags = tags

    def __setitem__(self, key, value):
        self.tags[key] = [value]

    def save(self):
        pass


################################################################################
### Tag reads (get_tag / collect_track_tags)
################################################################################

def test_collect_track_tags_normalizes_to_nfc(tmp_path, mocker):
    album = tmp_path / "Album"
    album.mkdir()
    track = album / "01 - Track.flac"
    track.write_text("dummy")

    nfd_conductor = unicodedata.normalize('NFD', "Karl Böhm")
    audio = FakeAudio({'Conductor': [nfd_conductor]})
    mocker.patch('src.standardize.FLAC', side_effect=lambda path: audio)

    track_tags = collect_track_tags(str(album))

    assert track_tags[0]['conductor'] == unicodedata.normalize('NFC', "Karl Böhm")


def test_detect_file_list_kind_rename_and_retag(tmp_path):
    rename_csv = tmp_path / "rename.csv"
    with open(rename_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
    assert detect_file_list_kind(str(rename_csv)) == 'rename'

    retag_csv = tmp_path / "conductors.csv"
    with open(retag_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['original_conductor', 'new_conductor'])
        writer.writerow(['A', 'B'])
    assert detect_file_list_kind(str(retag_csv)) == 'retag'

    bad = tmp_path / "bad.csv"
    with open(bad, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['foo', 'bar'])
    with pytest.raises(ValueError, match='Unrecognized'):
        detect_file_list_kind(str(bad))


def test_load_retag_mappings_skips_blank_and_identical(tmp_path):
    path = tmp_path / "map.csv"
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['original_conductor', 'new_conductor'])
        writer.writerow(['Keep Me', ''])
        writer.writerow(['Same', 'Same'])
        writer.writerow(['Old', 'New'])
        writer.writerow(['Böhm, Karl', 'Böhm, Karl'])
    mappings = load_retag_mappings(str(path))
    assert mappings == {
        'conductor': {
            'Old': 'New',
            'Böhm, Karl': 'Böhm, Karl',
        }
    }


def test_remap_soloists_field():
    soloist_map = {'Stern, Isaac': 'Stern, I.', 'Ax, Emmanual': 'Ax, E.'}
    assert remap_soloists_field(
        'Ax, Emmanual; Stern, Isaac', soloist_map
    ) == 'Ax, E.; Stern, I.'
    assert remap_soloists_field('Unmapped, Person', soloist_map) == 'Unmapped, Person'


def test_compute_retag_updates_conductor_and_soloists():
    audio = FakeAudio({
        'Conductor': ['Jochum, Eugene'],
        'Soloists': ['Ax, Emmanual; Stern, Isaac'],
    })
    mappings = {
        'conductor': {'Jochum, Eugene': 'Jochum, Eugen'},
        'soloist': {'Stern, Isaac': 'Stern, I.'},
    }
    updates = compute_retag_updates(audio, mappings)
    assert updates == {
        'Conductor': 'Jochum, Eugen',
        'Soloists': 'Ax, Emmanual; Stern, I.',
    }


def test_compute_retag_updates_soloist_remap_reorders_and_dedupes():
    audio = FakeAudio({
        'Soloists': ['Isaac Stern; Ax, Emmanual; Ax, Emmanual'],
    })
    mappings = {
        'soloist': {'Isaac Stern': 'Zimmer, Isaac'},
    }
    updates = compute_retag_updates(audio, mappings)
    assert updates == {
        'Soloists': 'Ax, Emmanual; Zimmer, Isaac',
    }


def test_compute_retag_updates_no_soloist_mapping_leaves_soloists_untouched():
    audio = FakeAudio({
        'Album': ['Old Album'],
        'Soloists': ['Isaac Stern; Ax, Emmanual'],
    })
    mappings = {
        'album': {'Old Album': 'New Album'},
    }
    updates = compute_retag_updates(audio, mappings)
    assert updates == {'Album': 'New Album'}


def test_apply_retag_mappings_reports_touched_albums(tmp_path, mocker):
    root = tmp_path / "lib"
    touched_album = root / "Composer" / "Old Album"
    touched_album.mkdir(parents=True)
    touched_track = touched_album / "01 - Track.flac"
    touched_track.write_text("dummy")

    untouched_album = root / "Composer" / "Other Album"
    untouched_album.mkdir(parents=True)
    untouched_track = untouched_album / "01 - Track.flac"
    untouched_track.write_text("dummy")

    audios = {
        str(touched_track): FakeAudio({'Album': ['Old Album']}),
        str(untouched_track): FakeAudio({'Album': ['Other Album']}),
    }
    mocker.patch('src.standardize.FLAC', side_effect=lambda path: audios[path])

    errors, touched_albums = apply_retag_mappings(
        str(root), {'album': {'Old Album': 'New Album'}}
    )

    assert errors == []
    assert touched_albums == {str(touched_album)}
    assert audios[str(touched_track)].tags['Album'] == ['New Album']
    assert audios[str(untouched_track)].tags['Album'] == ['Other Album']


def test_run_retag_requires_dir(tmp_path):
    map_csv = tmp_path / "conductors.csv"
    with open(map_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['original_conductor', 'new_conductor'])
        writer.writerow(['Old', 'New'])

    with pytest.raises(ValueError, match='requires --dir'):
        run(Namespace(
            dir=None,
            dry_run=False,
            output_file=None,
            file_list=str(map_csv),
        ))


def test_run_retag_no_mappings_is_noop(tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    map_csv = tmp_path / "conductors.csv"
    with open(map_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['original_conductor', 'new_conductor'])
        writer.writerow(['Keep', ''])

    run(Namespace(
        dir=str(root),
        dry_run=False,
        output_file=None,
        file_list=str(map_csv),
    ))


def test_run_retag_renames_touched_album_only(tmp_path, mocker):
    root = tmp_path / "lib"
    touched = root / "Composer" / "Old Album"
    touched.mkdir(parents=True)
    touched_track = touched / "01 - Track.flac"
    touched_track.write_text("dummy")

    untouched = root / "Composer" / "Untouched Album"
    untouched.mkdir(parents=True)
    untouched_track = untouched / "01 - Track.flac"
    untouched_track.write_text("dummy")

    audios = {
        str(touched_track): FakeAudio({
            'Year Recorded': ['1960'],
            'Album': ['Old Album'],
            'Soloists': ['Alain, Marie-Claire'],
        }),
        str(untouched_track): FakeAudio({
            'Year Recorded': ['1960'],
            'Album': ['Some Other Album'],
            'Soloists': ['Alain, Marie-Claire'],
        }),
    }
    mocker.patch('src.standardize.FLAC', side_effect=lambda path: audios[path])

    map_csv = tmp_path / "albums.csv"
    with open(map_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['original_album', 'new_album'])
        writer.writerow(['Old Album', 'New Album'])

    run(Namespace(dir=str(root), dry_run=False, output_file=None, file_list=str(map_csv)))

    assert not touched.exists()
    assert (touched.parent / "[1960] New Album (Marie-Claire Alain)").is_dir()
    assert untouched.is_dir()


################################################################################
### run / CSV
################################################################################

def test_run_dry_run_writes_schema(tmp_path):
    root = tmp_path / "lib"
    album = root / "Composer" / "Album"
    album.mkdir(parents=True)
    make_disc_with_flac(album, "CD 1")
    make_disc_with_flac(album, "Disc 10")

    out = tmp_path / "report.csv"
    run(Namespace(dir=str(root), dry_run=True, output_file=str(out), file_list=None))

    with open(out, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0].keys()) == CSV_FIELDNAMES
    disc_rows = [r for r in rows if r["type"] == "disc"]
    album_rows = [r for r in rows if r["type"] == "album"]
    assert len(disc_rows) == 1
    assert disc_rows[0]["status"] == "planned"
    assert disc_rows[0]["path"] == str(album)
    assert disc_rows[0]["original_name"] == "CD 1"
    assert disc_rows[0]["new_name"] == "Disc 01"
    assert len(album_rows) == 1
    assert album_rows[0]["status"] == "flagged"  # dummy flacs have no tags
    assert (tmp_path / "report_albums.csv").is_file()
    assert (tmp_path / "report_soloists.csv").is_file()


def test_run_applies_file_list_disc_then_album(tmp_path):
    root = tmp_path / "lib"
    parent = root / "Composer"
    parent.mkdir(parents=True)
    album = parent / "Old Album"
    album.mkdir()
    make_disc_with_flac(album, "CD 1")
    make_disc_with_flac(album, "Disc 10")

    plan = tmp_path / "plan.csv"
    new_album_name = "[1960] Organ Works (Marie-Claire Alain)"
    with open(plan, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerow(empty_plan_fields(
            path=str(album),
            original_name="CD 1",
            new_name="Disc 01",
            type='disc',
            status='planned',
        ))
        writer.writerow(empty_plan_fields(
            path=str(parent),
            original_name="Old Album",
            new_name=new_album_name,
            type='album',
            status='planned',
            year_chosen='1960',
            album_chosen='Organ Works',
            soloist_chosen='Marie-Claire Alain',
            performance_info='Marie-Claire Alain',
        ))
        writer.writerow(empty_plan_fields(
            path=str(parent),
            original_name="Skip Me",
            new_name="Nope",
            type='album',
            status='flagged',
            flag_reason='test',
        ))

    run(Namespace(dir=None, dry_run=False, output_file=None, file_list=str(plan)))

    new_album = parent / new_album_name
    assert new_album.is_dir()
    assert (new_album / "Disc 01").is_dir()
    assert (new_album / "Disc 10").is_dir()
    assert not album.exists()
    assert not (parent / "Nope").exists()


def test_read_rename_list_skips_flagged_and_empty_status(tmp_path):
    csv_path = tmp_path / "plan.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerow(empty_plan_fields(
            path='/a',
            original_name='CD 1',
            new_name='Disc 1',
            type='disc',
            status='planned',
        ))
        writer.writerow(empty_plan_fields(
            path='/parent',
            original_name='Album',
            new_name='New',
            type='album',
            status='flagged',
            flag_reason='x',
        ))
        writer.writerow(empty_plan_fields(
            path='/parent',
            original_name='Other',
            new_name='Fixed',
            type='album',
            status='',
        ))

    rows = read_rename_list(str(csv_path))
    assert len(rows) == 1
    assert rows[0]['type'] == 'disc'
    assert rows[0]['path'] == '/a'
    assert rows[0]['original_name'] == 'CD 1'
    assert rows[0]['new_name'] == 'Disc 1'


def test_apply_rename_rows_disc_before_album(tmp_path):
    parent = tmp_path / "Composer"
    parent.mkdir()
    album = parent / "Old"
    album.mkdir()
    make_disc_with_flac(album, "CD 1")
    new_album = parent / "New"

    errors = apply_rename_rows([
        {
            'path': str(album),
            'original_name': 'CD 1',
            'new_name': 'Disc 1',
            'type': 'disc',
        },
        {
            'path': str(parent),
            'original_name': 'Old',
            'new_name': 'New',
            'type': 'album',
        },
    ])
    assert errors == []
    assert new_album.is_dir()
    assert (new_album / "Disc 1").is_dir()
