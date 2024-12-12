import pytest
import os
from src.tagger import validate_inputs

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
    validate_inputs('read', str(valid_dir), None, str(output_excel))

def test_validate_inputs_read_mode_invalid_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs('read', 'invalid_dir', None, str(output_excel))

def test_validate_inputs_read_mode_missing_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs('read', None, None, str(output_excel))

def test_validate_inputs_read_mode_invalid_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs('read', str(valid_dir), None, 'invalid_path/output.xlsx')

def test_validate_inputs_read_mode_missing_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs('read', str(valid_dir), None, None)

def test_validate_inputs_write_mode_valid(setup_directories_and_files):
    _, input_excel, output_excel = setup_directories_and_files
    validate_inputs('write', None, str(input_excel), str(output_excel))

def test_validate_inputs_write_mode_invalid_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs('write', None, 'invalid_input.xlsx', str(output_excel))

def test_validate_inputs_write_mode_missing_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs('write', None, None, str(output_excel))

def test_validate_inputs_write_mode_invalid_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing directory path for writing failed tags."):
        validate_inputs('write', None, str(input_excel), 'invalid_path/output.xlsx')

def test_validate_inputs_write_mode_missing_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    with pytest.raises(ValueError, match="Invalid or missing directory path for writing failed tags."):
        validate_inputs('write', None, str(input_excel), None)