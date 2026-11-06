"""Compare two golden captures byte for byte.

Usage:
    .venv/bin/python scripts/golden/compare.py ~/stock-benchmark-golden/p0 ~/stock-benchmark-golden/p1 [--allow NAME ...]

Every file in both trees must be identical. --allow takes a relative path, and that path may differ
(for example a version string that is expected to change in a release phase). The exit code is 0
only when nothing outside --allow differs and no file is missing or new.
"""
import argparse
import filecmp
import os
import sys


def file_list(root: str) -> set:
    found = set()
    for folder, _, names in os.walk(root):
        for name in names:
            found.add(os.path.relpath(os.path.join(folder, name), root))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--allow", action="append", default=[], help="relative path allowed to differ")
    args = parser.parse_args()

    before = os.path.expanduser(args.before)
    after = os.path.expanduser(args.after)
    before_files, after_files = file_list(before), file_list(after)
    problems = []
    allowed = []
    for name in sorted(before_files | after_files):
        if name not in after_files:
            problems.append("missing in after: " + name)
        elif name not in before_files:
            problems.append("new in after: " + name)
        elif not filecmp.cmp(os.path.join(before, name), os.path.join(after, name), shallow=False):
            (allowed if name in args.allow else problems).append(
                ("differs (allowed): " if name in args.allow else "differs: ") + name)

    for line in allowed:
        print(line)
    for line in problems:
        print(line)
    print("{} files compared, {} problem(s), {} allowed difference(s)".format(
        len(before_files | after_files), len(problems), len(allowed)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
