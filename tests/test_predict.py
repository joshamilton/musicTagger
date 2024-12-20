################################################################################
### test_predict.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import pytest
import json
import os
from datetime import datetime
from src.predict import DataManager

################################################################################
### Tests for functions associated with DataManager class
################################################################################
@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing"""
    json_file = tmp_path / "test_tags.json"
    return str(json_file)

@pytest.fixture
def existing_data(temp_json_file):
    """Create a JSON file with existing data"""
    test_data = {
        "/path/to/test.flac": {
            "original": {
                "timestamp": "2024-01-01T00:00:00",
                "tags": {"title": "Title"}
            }
        }
    }
    with open(temp_json_file, 'w') as f:
        json.dump(test_data, f)
    return temp_json_file, test_data

def test_init_new_file(temp_json_file):
    """Test initializing with a new file"""
    manager = DataManager(temp_json_file)
    assert os.path.exists(temp_json_file)
    assert manager.data == {}

def test_init_existing_file(existing_data):
    """Test initializing with existing file"""
    json_file, test_data = existing_data
    manager = DataManager(json_file)
    assert manager.data == test_data

def test_store_original_new_entry(temp_json_file):
    """Test storing original tags for new file"""
    manager = DataManager(temp_json_file)
    test_tags = {"title": "Title"}
    test_path = "/path/to/new.flac"
    
    manager.store_original(test_path, test_tags)
    
    with open(temp_json_file, 'r') as f:
        saved_data = json.load(f)
    
    assert test_path in saved_data
    assert saved_data[test_path]["original"]["tags"] == test_tags
    assert "timestamp" in saved_data[test_path]["original"]

def test_store_original_existing_entry(existing_data):
    """Test that store_original doesn't overwrite existing data"""
    json_file, original_data = existing_data
    manager = DataManager(json_file)
    test_path = "/path/to/test.flac"
    new_tags = {"title": "Different Title"}
    
    manager.store_original(test_path, new_tags)
    
    with open(json_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data == original_data

def test_store_correction_existing_entry(temp_json_file):
    """Test storing correction tags"""
    manager = DataManager(temp_json_file)
    test_path = "/path/to/test.flac"
    original_tags = {"title": "Original"}
    corrected_tags = {"title": "Corrected"}
    
    manager.store_original(test_path, original_tags)
    manager.store_correction(test_path, corrected_tags)
    
    with open(temp_json_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data[test_path]["original"]["tags"] == original_tags
    assert saved_data[test_path]["corrected"]["tags"] == corrected_tags
    assert "timestamp" in saved_data[test_path]["corrected"]

def test_store_correction_nonexistent_entry(temp_json_file):
    """Test that store_correction only updates existing entries"""
    manager = DataManager(temp_json_file)
    test_path = "/path/to/test.flac"
    another_path = "/path/to/another.flac"
    original_tags = {"title": "Original"}
    corrected_tags = {"title": "Corrected"}
    
    # Setup initial data
    manager.store_original(test_path, original_tags)
    
    # Try to store correction for non-existent path
    manager.store_correction(another_path, corrected_tags)
    
    with open(temp_json_file, 'r') as f:
        saved_data = json.load(f)
    
    # Verify only original entry exists and wasn't modified
    assert len(saved_data) == 1
    assert test_path in saved_data
    assert "corrected" not in saved_data[test_path]
    assert saved_data[test_path]["original"]["tags"] == original_tags
    assert another_path not in saved_data