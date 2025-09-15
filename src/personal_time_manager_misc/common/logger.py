'''
Universal Logger logic for all the application. it will print into terminal and a seperate log_file.log
'''
import logging
import sys
import os
from pathlib import Path

class DirectoryFormatter(logging.Formatter):
    def format(self, record):
        # Extract the directory name from the path
        if hasattr(record, 'pathname') and record.pathname:
            # Get the parent directory name of the file
            file_path = Path(record.pathname)
            # Get the immediate parent directory name
            directory_name = file_path.parent.name
            record.directory = directory_name
        else:
            record.directory = 'Unknown'
        
        return super().format(record)

# 1. Create a logger instance with the desired name
logger = logging.getLogger('ptm-misc')
logger.setLevel(logging.INFO)

# 2. Create a custom formatter with directory information
formatter = DirectoryFormatter(
    '%(asctime)s - %(name)s - %(directory)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# 3. Create a handler to write logs to a file
file_handler = logging.FileHandler('log_file.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# 4. Create a handler to write logs to the standard output (console)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# 5. Add both handlers to the logger
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
