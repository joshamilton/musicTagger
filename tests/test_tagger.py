################################################################################
### test_tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import logging
import pytest
import os
from argparse import Namespace
from src.tagger import main, validate_inputs

################################################################################
### Tests
################################################################################

@pytest.fixture(autouse=True)
def reset_root_logger():
    """Restore the root logger's handlers/level after each test, since
    main() configures logging as a side effect (like logging.basicConfig,
    it mutates global state)."""
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    yield
    logging.root.handlers = original_handlers
    logging.root.level = original_level

def test_main_writes_log_file_at_explicit_log_file_path(tmp_path, monkeypatch):
    """An end-to-end check that main() centralizes logging correctly: a
    subcommand run with --log-file produces a non-empty log file at that
    exact path (not the real repo's logs/ directory), containing the same
    text the command prints to the console."""
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    log_file = tmp_path / "custom.log"

    monkeypatch.setattr(
        'sys.argv',
        ['tagger.py', 'cleanup', '--dir', str(music_dir), '--log-file', str(log_file)],
    )

    main()

    assert log_file.is_file()
    content = log_file.read_text()
    assert "Scanning directory for files to process..." in content
    assert "Tag cleanup complete." in content

@pytest.fixture
# Create a temporary directory, input Excel file, and output Excel file path
# Used to test the validate_inputs function
def setup_directories_and_files(tmp_path):
    # Create a temporary directory
    valid_dir = tmp_path / "valid_dir"
    valid_dir.mkdir()

    # Create a temporary input Excel file
    input_excel = tmp_path / "input.xlsx"
    input_excel.touch()

    # Create a temporary output directory
    output_dir = tmp_path / "output_dir"
    output_dir.mkdir()

    # Create a temporary output Excel file path
    output_excel = output_dir / "output.xlsx"

    return valid_dir, input_excel, output_excel

# Test cases for validate_inputs
def test_validate_inputs_read_mode_valid(setup_directories_and_files):
    valid_dir, _, output_excel = setup_directories_and_files
    args = Namespace(command='read', dir=str(valid_dir), excel_out=str(output_excel))
    validate_inputs(args)

def test_validate_inputs_read_mode_invalid_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(command='read', dir='invalid_dir', excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_read_mode_missing_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(command='read', dir=None, excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_read_mode_invalid_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    args = Namespace(command='read', dir=str(valid_dir), excel_out='invalid_path/output.xlsx')
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs(args)

def test_validate_inputs_read_mode_missing_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    args = Namespace(command='read', dir=str(valid_dir), excel_out=None)
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_valid(setup_directories_and_files):
    _, input_excel, output_excel = setup_directories_and_files
    args = Namespace(command='write', excel_in=str(input_excel), excel_out=str(output_excel))
    validate_inputs(args)

def test_validate_inputs_write_mode_invalid_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(command='write', excel_in='invalid_input.xlsx', excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_missing_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(command='write', excel_in=None, excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_invalid_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    args = Namespace(command='write', excel_in=str(input_excel), excel_out='invalid_path/output.xlsx')
    with pytest.raises(ValueError, match="Invalid or missing file path for writing failed tags."):
        validate_inputs(args)

def test_validate_inputs_write_mode_missing_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    args = Namespace(command='write', excel_in=str(input_excel), excel_out=None)
    with pytest.raises(ValueError, match="Invalid or missing file path for writing failed tags."):
        validate_inputs(args)

def test_validate_inputs_catalog_mode_valid(setup_directories_and_files):
    valid_dir, _, output_excel = setup_directories_and_files
    output_dir = output_excel.parent
    args = Namespace(command='catalog', dir=str(valid_dir),
                      db=str(output_dir / "catalog.db"),
                      prune=False)
    validate_inputs(args)

def test_validate_inputs_catalog_mode_invalid_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    output_dir = output_excel.parent
    args = Namespace(command='catalog', dir='invalid_dir',
                      db=str(output_dir / "catalog.db"),
                      prune=False)
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_catalog_mode_missing_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    output_dir = output_excel.parent
    args = Namespace(command='catalog', dir=None,
                      db=str(output_dir / "catalog.db"),
                      prune=False)
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_catalog_mode_invalid_db(setup_directories_and_files):
    valid_dir, _, output_excel = setup_directories_and_files
    output_dir = output_excel.parent
    args = Namespace(command='catalog', dir=str(valid_dir),
                      db='invalid_path/catalog.db',
                      prune=False)
    with pytest.raises(ValueError, match="Invalid or missing path for the catalog database."):
        validate_inputs(args)
