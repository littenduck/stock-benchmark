"""Move generated files from data/ into data/runtime/, so data/ can also hold the hand-edited content.

Usage (from the project root):
    .venv/bin/python scripts/migrate_runtime_directory.py --dry-run     # print what would move
    .venv/bin/python scripts/migrate_runtime_directory.py               # move
    .venv/bin/python scripts/migrate_runtime_directory.py --reverse     # move back

Nothing is overwritten: if a destination already exists the script stops before moving anything.
The moves stay on one disk, so they are renames and cost no copying.
"""
import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_NAME_LIST = ["symbols", "market", "cache", "logs", "latest_snapshot.json"]


def move_pair_list(reverse: bool) -> list:
    pair_list = []
    for name in RUNTIME_NAME_LIST:
        old = os.path.join(PROJECT_ROOT, "data", name)
        new = os.path.join(PROJECT_ROOT, "data", "runtime", name)
        pair_list.append((new, old) if reverse else (old, new))
    return pair_list


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    args = parser.parse_args()

    pair_list = [(src, dst) for src, dst in move_pair_list(args.reverse) if os.path.exists(src)]
    if not pair_list:
        print("nothing to move")
        return 0
    blocked = [dst for _, dst in pair_list if os.path.exists(dst)]
    if blocked:
        print("refusing to overwrite:", *blocked, sep="\n  ")
        return 1
    for src, dst in pair_list:
        print("{} -> {}".format(os.path.relpath(src, PROJECT_ROOT), os.path.relpath(dst, PROJECT_ROOT)))
    if args.dry_run:
        return 0
    os.makedirs(os.path.join(PROJECT_ROOT, "data", "runtime"), exist_ok=True)
    for src, dst in pair_list:
        os.rename(src, dst)
    print("moved {} item(s)".format(len(pair_list)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
