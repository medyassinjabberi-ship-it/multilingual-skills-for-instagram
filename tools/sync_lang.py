#!/usr/bin/env python3
"""
sync_lang.py - copy every shared module next to the scripts that import it.

Each skill folder has to install on its own, so each one carries its own copy
of the modules in shared/. This keeps the copies identical. Run it after any
edit in shared/; tests/test_pack.py (SharedSync) fails if you forget.

Usage
  python3 tools/sync_lang.py          # copy
  python3 tools/sync_lang.py --check  # exit 1 if any copy differs
"""

import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# shared module -> the skill folders that carry a copy of it
SHARED = {
    "lang.py": ["ig-human", "ig-caption", "ig-reel", "ig-viral", "ig-audit", "ig-carousel"],
    "journal.py": ["ig-reel", "ig-carousel", "ig-audit"],
}


def pairs():
    for name, skills in SHARED.items():
        src = os.path.join(ROOT, "shared", name)
        for skill in skills:
            yield src, os.path.join(ROOT, "skills", skill, name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = [(s, t) for s, t in pairs() if not os.path.exists(t) or not filecmp.cmp(s, t, shallow=False)]
    if args.check:
        for _, t in stale:
            print(f"out of date: {os.path.relpath(t, ROOT)}")
        sys.exit(1 if stale else 0)
    for s, t in stale:
        shutil.copyfile(s, t)
        print(f"copied -> {os.path.relpath(t, ROOT)}")
    if not stale:
        print("all copies up to date")


if __name__ == "__main__":
    main()
