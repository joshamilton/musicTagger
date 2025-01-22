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
import sqlite3
from datetime import datetime
from src.predict import DataManager

################################################################################
### Tests for functions associated with DataManager class
################################################################################
@pytest.fixture
def temp_db_file_path(tmp_path):
    """Path to a a temporary SQLite database file"""
    db_file = tmp_path / "test_tags.db"
    return str(db_file)

@pytest.fixture
def temp_db_file(temp_db_file_path):
    """Initialize the database and add data to it"""
    # Initialize the database using DataManager to create the schema
    manager = DataManager(temp_db_file_path)
    manager.close()

    # Manually insert data into the database
    conn = sqlite3.connect(temp_db_file_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO filename (filepath) VALUES (?)', ("/path/to/test.flac",))
    filename_id = cursor.lastrowid
    cursor.execute('INSERT INTO original_tags (filename_id, tag_key, tag_value) VALUES (?, ?, ?)',
                   (filename_id, "title", "Title"))
    conn.commit()
    conn.close()
    return temp_db_file_path, filename_id

@pytest.fixture
def temp_db_file(temp_db_file_path):
    """Initialize the database and add data to it"""
    # Initialize the database using DataManager to create the schema
    manager = DataManager(temp_db_file_path)
    manager.close()

    # Manually insert data into the database
    conn = sqlite3.connect(temp_db_file_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO filename (filepath) VALUES (?)', ("/path/to/test.flac",))
    filename_id = cursor.lastrowid
    cursor.execute('INSERT INTO original_tags (filename_id, tag_key, tag_value) VALUES (?, ?, ?)',
                   (filename_id, "title", "Title"))
    conn.commit()
    conn.close()
    return temp_db_file_path, filename_id

def test_init_new_db(temp_db_file_path):
    """Test initializing with a new database"""
    manager = DataManager(temp_db_file_path)
    assert os.path.exists(temp_db_file_path)
    manager.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = manager.cursor.fetchall()
    assert len(tables) == 3  # filename, original_tags, updated_tags
    table_names = [table[0] for table in tables]
    assert "filename" in table_names
    assert "original_tags" in table_names
    assert "updated_tags" in table_names
    manager.close()

def test_init_existing_db(temp_db_file):
    """Test initializing with an existing database"""
    temp_db_file_path, filename_id = temp_db_file

    # Re-initialize the DataManager with the existing database
    manager = DataManager(temp_db_file_path)
    manager.cursor.execute('SELECT tag_key, tag_value FROM original_tags WHERE filename_id = ?', (filename_id,))
    original_tags = {row[0]: row[1] for row in manager.cursor.fetchall()}
    assert original_tags["title"] == "Title"
    manager.close()

def test_save_original_tags_new_entry(temp_db_file_path):
    """Test saving original tags for new file"""
    manager = DataManager(temp_db_file_path)
    test_tags = {"title": ["Title"]}
    test_path = "/path/to/new.flac"
    
    manager.save_original_tags(test_path, test_tags)
    
    original_tags, _ = manager.get_tags(test_path)
    assert original_tags["title"] == "Title"
    manager.close()

def test_save_original_tags_existing_entry(temp_db_file_path):
    """Test that save_original_tags doesn't overwrite existing data"""
    manager = DataManager(temp_db_file_path)
    test_path = "/path/to/test.flac"
    original_tags = {"title": ["Title"]}
    new_tags = {"title": ["Different Title"]}
    
    manager.save_original_tags(test_path, original_tags)
    manager.save_original_tags(test_path, new_tags)
    
    original_tags, _ = manager.get_tags(test_path)
    assert original_tags["title"] == "Title"
    manager.close()

def test_save_updated_tags_existing_entry(temp_db_file_path):
    """Test saving updated tags"""
    manager = DataManager(temp_db_file_path)
    test_path = "/path/to/test.flac"
    original_tags = {"title": ["Original"]}
    updated_tags = {"title": ["Updated"]}
    
    manager.save_original_tags(test_path, original_tags)
    manager.save_updated_tags(test_path, updated_tags)
    
    _, updated_tags = manager.get_tags(test_path)
    assert updated_tags["title"] == "Updated"
    manager.close()

def test_save_updated_tags_nonexistent_entry(temp_db_file_path):
    """Test that save_updated_tags only updates existing entries"""
    manager = DataManager(temp_db_file_path)
    test_path = "/path/to/test.flac"
    another_path = "/path/to/another.flac"
    original_tags = {"title": ["Original"]}
    updated_tags = {"title": ["Updated"]}
    
    # Setup initial data
    manager.save_original_tags(test_path, original_tags)
    
    # Try to store updated tags for non-existent path
    manager.save_updated_tags(another_path, updated_tags)
    
    original_tags, updated_tags = manager.get_tags(test_path)
    assert updated_tags == {}
    manager.close()