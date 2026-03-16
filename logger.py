from loguru import logger
import sys

def setup_logging():
    logger.remove()
    
    custom_format = (
        "<green>{file}</green>:"
        "<cyan>{line}</cyan>:"
        "<level>{level}</level> - "
        "<level>{message}</level>"
    )
    EXCLUDED_FILES = ["alt_tab.py"]

    logger.add(sys.stderr, format=custom_format, colorize=True,filter=lambda record: record["file"].name not in EXCLUDED_FILES)
    return logger
