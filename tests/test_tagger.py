################################################################################
### test_tagger.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import pytest
import os
from argparse import Namespace
from src.tagger import validate_inputs

################################################################################
### Tests
################################################################################

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
    args = Namespace(mode='read', dir=str(valid_dir), excel_in=None, excel_out=str(output_excel))
    validate_inputs(args)

def test_validate_inputs_read_mode_invalid_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(mode='read', dir='invalid_dir', excel_in=None, excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_read_mode_missing_dir(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(mode='read', dir=None, excel_in=None, excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing directory path containing music files."):
        validate_inputs(args)

def test_validate_inputs_read_mode_invalid_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    args = Namespace(mode='read', dir=str(valid_dir), excel_in=None, excel_out='invalid_path/output.xlsx')
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs(args)

def test_validate_inputs_read_mode_missing_output(setup_directories_and_files):
    valid_dir, _, _ = setup_directories_and_files
    args = Namespace(mode='read', dir=str(valid_dir), excel_in=None, excel_out=None)
    with pytest.raises(ValueError, match="Invalid or missing file path for writing tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_valid(setup_directories_and_files):
    _, input_excel, output_excel = setup_directories_and_files
    args = Namespace(mode='write', dir=None, excel_in=str(input_excel), excel_out=str(output_excel))
    validate_inputs(args)

def test_validate_inputs_write_mode_invalid_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(mode='write', dir=None, excel_in='invalid_input.xlsx', excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_missing_input(setup_directories_and_files):
    _, _, output_excel = setup_directories_and_files
    args = Namespace(mode='write', dir=None, excel_in=None, excel_out=str(output_excel))
    with pytest.raises(ValueError, match="Invalid or missing file path for reading tag information."):
        validate_inputs(args)

def test_validate_inputs_write_mode_invalid_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    args = Namespace(mode='write', dir=None, excel_in=str(input_excel), excel_out='invalid_path/output.xlsx')
    with pytest.raises(ValueError, match="Invalid or missing file path for writing failed tags."):
        validate_inputs(args)

def test_validate_inputs_write_mode_missing_output(setup_directories_and_files):
    _, input_excel, _ = setup_directories_and_files
    args = Namespace(mode='write', dir=None, excel_in=str(input_excel), excel_out=None)
    with pytest.raises(ValueError, match="Invalid or missing file path for writing failed tags."):
        validate_inputs(args)