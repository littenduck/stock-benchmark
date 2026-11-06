"""Save and load the dashboard snapshot as JSON."""
import json
import os
from typing import Optional

from backend.shared.files import files_write_atomically


def snapshot_storage_save_snapshot_to_json_file(snapshot: dict, snapshot_file_path: str) -> None:
    def write(temporary_file_path: str) -> None:
        with open(temporary_file_path, "w") as temporary_file:
            json.dump(snapshot, temporary_file, default=str)
    files_write_atomically(snapshot_file_path, write)


def snapshot_storage_load_snapshot_from_json_file(snapshot_file_path: str) -> Optional[dict]:
    if not os.path.exists(snapshot_file_path):
        return None
    with open(snapshot_file_path) as snapshot_file:
        return json.load(snapshot_file)
