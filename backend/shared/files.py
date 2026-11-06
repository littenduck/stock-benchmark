"""Write files so a crash never leaves half a file behind."""
import os
from typing import Callable


def files_write_atomically(file_path: str, write_to_path: Callable[[str], None]) -> None:
    """Write to file_path + ".tmp" first, then rename it over file_path in one step."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temporary_file_path = file_path + ".tmp"
    write_to_path(temporary_file_path)
    os.replace(temporary_file_path, file_path)
