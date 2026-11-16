#!/usr/bin/env python3
"""
voice.py - check a draft against the user's own voice.md, in any language.

The slop lexicon knows what a machine sounds like. It does not know what THIS
person would never say. voice.md does, in two fields the user fills in
themselves:

  - **Words I would never say out loud:**   -> NEVER SAYS
  - **Clients, numbers or names I cannot say publicly:**   -> CANNOT SAY

Every entry is matched as a whole word or phrase, case and accents ignored,
in Latin or Arabic script (Arabic diacritics and tatweel ignored, and the
attached prefixes و ف ب ل ك ال allowed in front). The words come from the user,
so this works in Darija and arabizi too: nothing here is invented.

Entries are separated by commas, semicolons or new bullet lines, and may sit on
the same line as the field or on the lines under it.

Usage
  python3 voice.py draft.txt                    # reads ~/.claude/instagram/voice.md
  python3 voice.py draft.txt --voice path/to/voice.md
  python3 voice.py draft.txt --never "game changer,bro" --private "Acme,18 400"
  python3 voice.py draft.txt --json

Exit code: 0 clean, 1 something to fix, 2 nothing to check against.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402

FIELDS = {
    "never": r"words i would never say(?: out loud)?",
    "private": r"clients, numbers or names i cannot say publicly",
}
LABELS = {"never": "NEVER SAYS", "private": "CANNOT SAY"}
_HARAKAT = re.compile("[ً-ٰٟـ]")
_AR = re.compile("[؀-ۿ]")
_PLACEHOLDER = re.compile(r"^\(.*\)$")
_NUMBERING = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•])\s+")
_EXAMPLE = re.compile(r"^(?:e\.?\s?g\.?|ex\.?|par ex(?:emple)?\.?|for example|like)\s*:?\s*", re.IGNORECASE)
_NOTHING = {"none", "n/a", "na", "nothing", "aucun", "aucune", "rien", "-", "—", "no", "non", "nope"}


def fold(text):
    """Case, accents, Arabic diacritics and tatweel out; same length kept is not needed."""
    t = unicodedata.normalize("NFKC", text)
    t = _HARAKAT.sub("", t)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)
                or _AR.match(c))
    return t.casefold().replace("’", "'")


def split_entries(value):
    """'1. Acme (the logistics one)', '- "booster"', 'e.g. "unlock"' -> 'Acme', 'booster', 'unlock'."""
    out = []
    for part in re.split(r"[,;\n]|\s+/\s+", value):
        part = _NUMBERING.sub("", part.strip())
        if _PLACEHOLDER.match(part.strip()):
            continue
        part = re.sub(r"\s*\([^)]*\)", "", part)          # a note in brackets is not part of the word
        part = _EXAMPLE.sub("", part.strip())
        part = part.strip().strip("\"'«»“”`").strip().rstrip(".:").strip()
        if part and part.lower() not in _NOTHING and len(part) <= 80:
            out.append(part)
    return out


def read_voice(path):
    """{'never': [...], 'private': [...]} from voice.md. Missing file -> None."""
    try:
        with open(path, "rb") as fh:
            body = L.decode(fh.read())
    except OSError:
        return None
    found = {k: [] for k in FIELDS}
    lines = body.splitlines()
    for key, label in FIELDS.items():
        for i, line in enumerate(lines):
            m = re.match(rf"^\s*[-*]?\s*\**\s*{label}\s*:?\s*\**\s*:?\s*(.*)$", line, re.IGNORECASE)
            if not m:
                continue
            chunk = [m.group(1)]
            for nxt in lines[i + 1:]:
                # the field runs until the next bold field or heading; blank lines inside are fine
                if re.match(r"^\s*(#|[-*]?\s*\*\*[^*]+\*\*)", nxt):
                    break
                chunk.append(nxt)
            found[key] += split_entries("\n".join(chunk))
    return found


def pattern(entry):
    folded = fold(entry)
    digits = re.sub(r"[\s.,'  ]", "", folded)
    if digits.isdigit() and len(digits) >= 3:
        # "18 400" also finds 18,400 / 18400 / 18.400 / 18 400 with a narrow space
        e = r"[\s.,'  ]?".join(digits)
        return re.compile(rf"(?<![\d]){e}(?![\d])")
    e = re.escape(folded).replace(r"\ ", r"[\s\-‑]+").replace(r"\.", r"\.?")
    prefix = r"(?:[وفبلك]{0,2}(?:ال)?)?" if _AR.search(entry) else ""
    return re.compile(rf"(?<![\w]){prefix}{e}(?![\w])")


def check(text, lists):
    hits = []
    folded_lines = [fold(l) for l in text.splitlines()]
    for key, entries in lists.items():
        for entry in entries:
            rx = pattern(entry)
            for n, line in enumerate(folded_lines, 1):
                if rx.search(line):
                    hits.append({"kind": key, "entry": entry, "line": n,
                                 "text": text.splitlines()[n - 1].strip()})
    return hits


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Check a draft against the user's voice.md.")
    ap.add_argument("input", nargs="?", default="-", help="draft file, or - for stdin")
    ap.add_argument("--voice", default=os.path.join(os.path.dirname(L.VOICE_FILE), "voice.md"))
    ap.add_argument("--never", help="extra words the user never says, comma-separated")
    ap.add_argument("--private", help="extra names or numbers that cannot be said, comma-separated")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    lists = read_voice(args.voice) or {k: [] for k in FIELDS}
    for key in FIELDS:
        extra = getattr(args, key)
        if extra:
            lists[key] += split_entries(extra)
    if not any(lists.values()):
        print("voice: nothing to check against. Fill 'Words I would never say out loud' in "
              f"{args.voice}, or pass --never.", file=sys.stderr)
        return 2
    text = L.read_input(args.input)
    hits = check(text, lists)
    if args.json:
        print(json.dumps({"lists": lists, "hits": hits}, ensure_ascii=False, indent=2))
    else:
        print(f"VOICE CHECK  ·  {sum(len(v) for v in lists.values())} entries from the user  ·  "
              f"{len(hits)} hit(s)")
        for key in FIELDS:
            if lists[key]:
                print(f"  read {LABELS[key]:<11} " + ", ".join(f'"{e}"' for e in lists[key]))
        for h in hits:
            print(f"  {LABELS[h['kind']]:<11} line {h['line']:<3} \"{h['entry']}\"  in: {h['text'][:80]}")
        if not hits:
            print("  clean for the entries read above. Check that list: an entry missing from it was not checked.")
        elif any(h["kind"] == "private" for h in hits):
            print("  CANNOT SAY entries must come out before anything is shown as ready.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
