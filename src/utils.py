################################################################################
### utils.py
### Copyright (c) 2024, Joshua J Hamilton
################################################################################

################################################################################
### Import packages
################################################################################

import os
import logging
from datetime import datetime

################################################################################
### Define functions
################################################################################

def setup_logging(path_to_run_data):
    """
    Set up logging to a file.

    Args:
        path_to_run_data (str): Path to the run data directory

    Returns:
        logging.Logger: Configured logger object
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(path_to_run_data, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'{timestamp}.log')

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file)
        ]
    )

    return logging.getLogger(__name__)