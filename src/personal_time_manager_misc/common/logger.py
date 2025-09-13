'''
Universal Logger logic for all the application. it will print into terminal and a seperate log_file.log
'''
import logging
import sys

# 1. Create a logger instance
logger = logging.getLogger('personal_time_manager_misc')
logger.setLevel(logging.INFO) # Set the lowest level of messages to handle

# 2. Create a formatter to define the log message structure
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 3. Create a handler to write logs to a file
file_handler = logging.FileHandler('log_file.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# 4. Create a handler to write logs to the standard output (console)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# 5. Add both handlers to the logger
# Avoid adding handlers multiple times if this module is imported more than once
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
