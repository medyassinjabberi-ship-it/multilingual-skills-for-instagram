#!/usr/bin/env python3
"""
journal.py - the pack's memory of what was written, shot and posted.

One JSON object per line in ~/.claude/instagram/journal.jsonl. Every skill can
read it; ig-reel and ig-carousel add to it, ig-plan reads it to avoid repeating
itself, and ig-audit joins it with the Insights so a result can be traced back
to the hook and the formula that produced it.

A post enters the journal as "ready" when the user approves the script, and
becomes "posted" only when the user says it went out (with the date, and the
link if they have it). Nothing here is guessed: a post the user never confirms
stays "ready".

Fields
  id         20261116-1          made by `add`
  created    2026-11-16          the day it was approved
  status     ready | posted | dropped
  format     reel | carousel | story | photo
  hook       the first spoken line, or the cover text
  formula    id from ig-reel/hooks.json ("5"), or null
  lang       en | fr | ar | aeb-latn
  theme      free text, short ("pricing")
  type       proof | teach | opinion | story | offer, or null
  hookscore  hookscore.py overall (English only), or null
  length_s   planned length in seconds, or null
  posted     2026-11-18, or null
  permalink  https://www.instagram.com/reel/..., or null

Usage
  python3 journal.py add --format reel --hook "Proposals took me five hours." \
          --formula 5 --lang en --theme proposals --type proof --hookscore 51.2 --length 28
  python3 journal.py posted 20261116-1 --date 2026-11-18 --permalink https://...
  python3 journal.py drop 20261116-1
  python3 journal.py recent --days 14       # what was made lately, and what repeats
  python3 journal.py list [--status posted] [--json]

The file can be overridden with --file or the IG_JOURNAL environment variable.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter

DEFAULT = os.path.join(os.path.expanduser("~"), ".claude", "instagram", "journal.jsonl")
FORMATS = ("reel", "carousel", "story", "photo")
TYPES = ("proof", "teach", "opinion", "story", "offer")
STATUSES = ("ready", "posted", "dropped")
FIELDS = ("id", "created", "status", "format", "hook", "formula", "lang", "theme", "type",
          "hookscore", "length_s", "posted", "permalink")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def path_from(arg=None):
    return arg or os.environ.get("IG_JOURNAL") or DEFAULT


def parse_date(s):
    if s is None:
        return None
    if not DATE_RE.match(s):
        raise ValueError(f"date must be YYYY-MM-DD, got {s!r}")
    return dt.date.fromisoformat(s)


def load(path=None):
    """Every entry in the journal, oldest first. A broken line is skipped and reported."""
    path = path_from(path)
    entries, bad = [], 0
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if isinstance(row, dict) and row.get("id"):
                entries.append({k: row.get(k) for k in FIELDS} | {k: v for k, v in row.items() if k not in FIELDS})
            else:
                bad += 1
    if bad:
        print(f"journal: skipped {bad} unreadable line(s) in {path}", file=sys.stderr)
    return entries


def save(entries, path=None):
    path = path_from(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def norm_link(url):
    """Compare permalinks without the query string, the scheme, www or a trailing slash.
    The host is case-insensitive; the path is not (Instagram shortcodes are case-sensitive)."""
    if not url:
        return None
    url = url.strip().split("?")[0].split("#")[0].rstrip("/")
    url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    host, _, path = url.partition("/")
    host = re.sub(r"^www\.", "", host.lower())
    return host + ("/" + path if path else "")


_FORMULA = re.compile(r"^(?:#|formula\s*|formule\s*|n°\s*)?0*(\d{1,3})\.?$", re.IGNORECASE)


def norm_formula(value):
    """'#05', 'formula 5', '5.' -> '5'. Anything else comes back stripped, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = _FORMULA.match(s)
    return m.group(1) if m else s


def safe_date(s):
    """parse_date that returns None instead of raising, for hand-edited lines."""
    try:
        return parse_date(s) if s else None
    except ValueError:
        return None


def new_id(entries, today):
    stem = today.strftime("%Y%m%d")
    taken = {e["id"] for e in entries}
    n = 1
    while f"{stem}-{n}" in taken:
        n += 1
    return f"{stem}-{n}"


def add(entries, fmt, hook, today, **extra):
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {', '.join(FORMATS)}")
    if extra.get("type") and extra["type"] not in TYPES:
        raise ValueError(f"type must be one of {', '.join(TYPES)}")
    entry = {k: None for k in FIELDS}
    entry.update({k: v for k, v in extra.items() if k in FIELDS})
    entry["formula"] = norm_formula(entry.get("formula"))
    if entry["formula"] and not entry["formula"].isdigit():
        print(f"journal: formula {entry['formula']!r} is not an id from ig-reel/hooks.json; "
              "kept as written", file=sys.stderr)
    entry.update(id=new_id(entries, today), created=today.isoformat(), status="ready",
                 format=fmt, hook=hook.strip())
    entries.append(entry)
    return entry


def find(entries, entry_id):
    for e in entries:
        if e["id"] == entry_id:
            return e
    raise KeyError(f"no entry {entry_id!r} in the journal (see: journal.py list)")


def mark_posted(entries, entry_id, date, permalink=None, today=None):
    if today and date > today + dt.timedelta(days=1):
        raise ValueError(f"posted date {date} is in the future")
    e = find(entries, entry_id)
    e["status"] = "posted"
    e["posted"] = date.isoformat()
    if permalink:
        e["permalink"] = permalink.strip()
    return e


def recent(entries, today, days=14):
    """What was made in the window, and what repeats inside it."""
    start = today - dt.timedelta(days=days)

    def when(e):
        return safe_date(e.get("posted")) or safe_date(e.get("created"))

    notes = [f"{e['id']} has a date this script cannot read ({e.get('posted') or e.get('created')!r}): "
             "fix it as YYYY-MM-DD" for e in entries
             if (e.get("posted") and not safe_date(e["posted"])) or not safe_date(e.get("created"))]
    window = [e for e in entries if e.get("status") != "dropped" and when(e) and when(e) >= start]
    window.sort(key=when)
    for field, label in (("formula", "formula"), ("theme", "theme")):
        key = norm_formula if field == "formula" else (lambda v: str(v).strip().lower())
        counts = Counter(key(e[field]) for e in window if e.get(field))
        for value, n in counts.most_common():
            if n >= 2:
                notes.append(f"{label} {value!r} used {n} times in {days} days")
    posted = [e for e in window if e.get("status") == "posted"]
    for a, b in zip(posted, posted[1:]):
        if a.get("type") and a.get("type") == b.get("type"):
            notes.append(f"two {a['type']} posts back to back ({a['posted']}, {b['posted']})")
    stale = [e for e in entries if e.get("status") == "ready" and safe_date(e.get("created"))
             and safe_date(e["created"]) <= today - dt.timedelta(days=7)]
    for e in stale:
        notes.append(f"{e['id']} approved on {e['created']} and never marked posted: posted, or drop it?")
    return window, notes


def row(e):
    when = e.get("posted") or e.get("created") or ""
    formula = f"#{e['formula']}" if e.get("formula") else "-"
    return (f"{e['id']:<12} {e.get('status', ''):<7} {when:<10} {e.get('format') or '':<8} "
            f"{formula:<4} {(e.get('type') or '-'):<7} {(e.get('theme') or '-')[:14]:<14} "
            f"{(e.get('hook') or '')[:60]}")


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    setup_stdout()
    ap = argparse.ArgumentParser(description="The pack's journal of posts.")
    ap.add_argument("--file", help="journal path (default ~/.claude/instagram/journal.jsonl)")
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="log an approved post")
    a.add_argument("--format", required=True, choices=FORMATS)
    a.add_argument("--hook", required=True)
    a.add_argument("--formula")
    a.add_argument("--lang")
    a.add_argument("--theme")
    a.add_argument("--type", choices=TYPES)
    a.add_argument("--hookscore", type=float)
    a.add_argument("--length", type=float, dest="length_s")

    p = sub.add_parser("posted", help="the user says it went out")
    p.add_argument("id")
    p.add_argument("--date", help="YYYY-MM-DD, default today")
    p.add_argument("--permalink")

    d = sub.add_parser("drop", help="approved but never going out")
    d.add_argument("id")

    r = sub.add_parser("recent", help="what was made lately, and what repeats")
    r.add_argument("--days", type=int, default=14)

    ls = sub.add_parser("list")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    try:
        today = parse_date(args.today) if args.today else dt.date.today()
        entries = load(args.file)
        if args.cmd == "add":
            formula = args.formula.lstrip("#") if args.formula else None
            e = add(entries, args.format, args.hook, today, formula=formula, lang=args.lang,
                    theme=args.theme, type=args.type, hookscore=args.hookscore, length_s=args.length_s)
            save(entries, args.file)
            print(f"logged {e['id']} as ready. When it is posted: journal.py posted {e['id']} --date YYYY-MM-DD")
        elif args.cmd == "posted":
            date = parse_date(args.date) if args.date else today
            e = mark_posted(entries, args.id, date, args.permalink, today)
            save(entries, args.file)
            print(f"{e['id']} posted on {e['posted']}" + ("" if e.get("permalink") else " (no link: the audit will match it by date)"))
        elif args.cmd == "drop":
            find(entries, args.id)["status"] = "dropped"
            save(entries, args.file)
            print(f"{args.id} dropped")
        elif args.cmd == "recent":
            window, notes = recent(entries, today, args.days)
            print(f"JOURNAL  ·  last {args.days} days  ·  {len(window)} post(s)")
            for e in window:
                print("  " + row(e))
            print("\nREPEATS" if notes else "\nNo repeats in the window.")
            for n in notes:
                print("  - " + n)
        elif args.cmd == "list":
            rows = [e for e in entries if not args.status or e.get("status") == args.status]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for e in rows:
                    print(row(e))
                if not rows:
                    print("journal is empty")
    except (ValueError, KeyError) as exc:
        print(f"journal: {exc.args[0] if exc.args else exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
