################################################################################
### conftest.py
### Copyright (c) 2026, Joshua J Hamilton
### Shared test doubles for mutagen FLAC objects and sox subprocess calls,
### used by tests exercising the missing-checksum repair machinery across
### src/utils.py, src/catalog.py, and src/write.py.
################################################################################

################################################################################
### Fake mutagen FLAC objects
################################################################################

class FakeInfo:
    def __init__(self, md5_signature):
        self.md5_signature = md5_signature

class FakeAudio:
    """Minimal stand-in for mutagen FLAC for catalog scanning."""

    def __init__(self, tags, md5_signature=1):
        self.tags = tags
        self.info = FakeInfo(md5_signature)
        self.saved = False

    def save(self):
        self.saved = True

SAMPLE_TAGS = {
    'Composer': ['Ludwig van Beethoven'],
    'Album': ['Symphony No 5'],
    'Year Recorded': ['1963'],
    'Orchestra': ['Berlin Philharmonic'],
    'Conductor': ['Herbert von Karajan'],
    'Soloists': [''],
    'Arranger': [''],
    'Genre': ['Classical'],
    'DiscNumber': ['1'],
    'TrackNumber': ['1'],
    'Title': ['Symphony No 5, Op 67, in C minor - I. Allegro con brio'],
    'TrackTitle': [''],
    'Work': ['Symphony'],
    'Work Number': ['No 5'],
    'InitialKey': ['C minor'],
    'Catalog #': [''],
    'Opus': ['Op 67'],
    'Opus Number': [''],
    'Epithet': [''],
    'Movement': ['I. Allegro con brio'],
}

################################################################################
### Fake sox subprocess calls
################################################################################

class FakeCompletedProcess:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode=0, stdout=b'', stderr=b''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def fake_sox_run(command, capture_output=True):
    """
    Fake subprocess.run for a successful sox re-encode: writes the source
    path (command[1]) as bytes into the destination temp file (command[-1]),
    so a paired FLAC fake can tell which original file a given temp file
    came from. Mirrors real sox, which must write to a real (seekable)
    file, not a pipe, to compute a correct checksum -- see
    repair_missing_checksum's docstring.
    """
    source_path = command[1]
    dest_path = command[-1]
    with open(dest_path, 'wb') as f:
        f.write(f"REENCODED:{source_path}".encode())
    return FakeCompletedProcess(returncode=0)

def mock_sox_success(mocker):
    """Mock subprocess.run to simulate sox successfully re-encoding any input."""
    return mocker.patch('src.utils.subprocess.run', side_effect=fake_sox_run)

def mock_sox_failure(mocker, stderr=b'sox FAIL formats: could not decode file'):
    """Mock subprocess.run to simulate sox failing on any input (no output file written)."""
    return mocker.patch(
        'src.utils.subprocess.run',
        return_value=FakeCompletedProcess(returncode=1, stdout=b'', stderr=stderr),
    )

def make_flac_side_effect(audios, reencoded_md5_by_path=None):
    """
    Build a FLAC(...) side_effect for tests: dispatches on path for
    original-file reads (via `audios`), and on the source path marker
    written into a temp file by fake_sox_run (via `reencoded_md5_by_path`)
    for re-encoded-file reads.
    """
    def fake_flac(path):
        if path in audios:
            return audios[path]
        with open(path, 'rb') as f:
            marker = f.read().decode()
        original_path = marker.split("REENCODED:", 1)[1]
        return FakeAudio(dict(SAMPLE_TAGS), md5_signature=reencoded_md5_by_path[original_path])
    return fake_flac
