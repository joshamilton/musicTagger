################################################################################
### predict.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################
import json
import os
from datetime import datetime

################################################################################
### DataManager Class
### This class creates and updates a JSON file to record the initial and
### updated tags. These data will be used later to train a generative model to
### predict updated tags.
################################################################################

class DataManager:
    def __init__(self, data_file="tags.json"):
        self.data_file = data_file
        self._load_or_create()
    
    def _load_or_create(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}
            self._save()
    
    def store_original(self, filepath, tags):
        if filepath not in self.data:
            self.data[filepath] = {
                "original": {
                    "timestamp": datetime.now().isoformat(),
                    "tags": tags
                }
            }
        self._save()
    
    def store_correction(self, filepath, tags):
        if filepath in self.data:
            self.data[filepath]["corrected"] = {
                "timestamp": datetime.now().isoformat(),
                "tags": tags
            }
        self._save()
    
    def _save(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)