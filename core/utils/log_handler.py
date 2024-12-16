import os
import logging

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()


def rotating_file_logger(app_name: str, max_bytes=1024 * 1024 * 10, backup_count=1):
    """
    Rotating file logger
    """

    # Get the log level from the environment variable or use the default log level
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    # Create logging
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)

    # Get the log directory from the environment variable or use the default log directory of os
    log_dir = os.environ.get("LOG_DIR")
    # get default log directory of the os
    if not log_dir:
        log_dir = os.path.join(os.path.expanduser("~"), "Logs", "AeonIntelligence")

    # Create the log directory if it does not exist
    os.makedirs(log_dir, exist_ok=True)

    # Create the log file
    log_file = os.path.join(log_dir, f"{app_name}.log")

    # Create a file handler with a maximum file size of 10MB and 5 backup files
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)

    return logger
