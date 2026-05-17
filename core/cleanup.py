"""
core/cleanup.py
---------------
Utility for cleaning up old uploaded files and generated outputs.
"""

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

def cleanup_old_files(directory: str, max_age_seconds: int = 3600) -> int:
    """
    Deletes files in the specified directory that are older than max_age_seconds.

    Args:
        directory: Path to the directory to clean.
        max_age_seconds: Maximum age of files in seconds (default: 1 hour).

    Returns:
        Number of files deleted.
    """
    path = Path(directory)
    if not path.exists() or not path.is_dir():
        logger.warning(f"Cleanup: Directory {directory} does not exist.")
        return 0

    count = 0
    now = time.time()
    for file_path in path.iterdir():
        if file_path.is_file():
            file_age = now - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"Cleanup: Failed to delete {file_path}: {e}")

    if count > 0:
        logger.info(f"Cleanup: Deleted {count} old files from {directory}.")
    return count
