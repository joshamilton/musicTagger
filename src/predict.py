################################################################################
### predict.py
### Copyright (c) 2025, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import sqlite3

################################################################################
### DataManager Class
### This class creates and updates a JSON file to record the initial and
### updated tags. These data will be used later to test and/or train a generative 
### model to predict updated tags.
################################################################################

class DataManager:
    def __init__(self, db_file="tags.db"):
        self.db_file = db_file
        self._connect_db()

    def _connect_db(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS filename (
                id INTEGER PRIMARY KEY,
                filepath TEXT UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS original_tags (
                filename_id INTEGER,
                tag_key TEXT,
                tag_value TEXT,
                FOREIGN KEY (filename_id) REFERENCES filename (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS updated_tags (
                filename_id INTEGER,
                tag_key TEXT,
                tag_value TEXT,
                FOREIGN KEY (filename_id) REFERENCES filename (id)
            )
        ''')
        self.conn.commit()

    def _get_filename_id(self, filepath):
        self.cursor.execute('SELECT id FROM filename WHERE filepath = ?', (filepath,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            self.cursor.execute('INSERT INTO filename (filepath) VALUES (?)', (filepath,))
            self.conn.commit()
            return self.cursor.lastrowid

    def save_original_tags(self, filepath, tags):
        filename_id = self._get_filename_id(filepath)
        for key, value in tags.items():
            value = value[0]
            # Check if the tag already exists
            self.cursor.execute('''
                SELECT COUNT(*) FROM original_tags WHERE filename_id = ? AND tag_key = ?
            ''', (filename_id, key))
            if self.cursor.fetchone()[0] == 0:
                # Insert only if the tag does not exist
                self.cursor.execute('''
                    INSERT INTO original_tags (filename_id, tag_key, tag_value)
                    VALUES (?, ?, ?)
                ''', (filename_id, key, value))
        self.conn.commit()

    def save_updated_tags(self, filepath, tags):
        filename_id = self._get_filename_id(filepath)
        for key, value in tags.items():
            value = value[0]
            self.cursor.execute('''
                INSERT INTO updated_tags (filename_id, tag_key, tag_value)
                VALUES (?, ?, ?)
            ''', (filename_id, key, value))
        self.conn.commit()

    def get_tags(self, filepath):
        filename_id = self._get_filename_id(filepath)
        self.cursor.execute('SELECT tag_key, tag_value FROM original_tags WHERE filename_id = ?', (filename_id,))
        original_tags = {row[0]: row[1] for row in self.cursor.fetchall()}
        self.cursor.execute('SELECT tag_key, tag_value FROM updated_tags WHERE filename_id = ?', (filename_id,))
        updated_tags = {row[0]: row[1] for row in self.cursor.fetchall()}
        return original_tags, updated_tags

    def close(self):
        self.conn.close()