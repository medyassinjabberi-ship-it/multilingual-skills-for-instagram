#!/usr/bin/env python3
"""
beats.py - turn a Reel script into a timed beat sheet before you record it.

Estimates how long each line takes to say, stacks them into timecodes, and
flags the four things that kill a Reel in the edit: a hook that runs past the
three-second mark, a beat long enough for the viewer to leave, a run of lines
with nothing concrete in them, and a total length that does not match what you
said you were making.

The timings are an estimate from word count at a words-per-minute rate. They
are close enough to plan an edit and not a substitute for recording it. Set
your own rate with --wpm once you have timed yourself reading a script out
loud: most people land between 150 and 200, and the default here is 165.

Languages: words are counted in English, French, Arabic script and arabizi.
The 165 wpm default was set on English. Arabic script packs prefixes into one
word ("وبالفلوس" is one word, four in English), so the same script reads as
fewer, longer words: time yourself once and pass --wpm. Until then the report
says the timing is an English-rate estimate.

On-screen text: a line starting with [on-screen] (or [screen], [écran]) is a
text card, not speech. It is not timed as words; it goes up with the next
spoken line and stays until the next card. The report lists the cards with
their estimated timecodes, ready for the edit. A script with no such line
gives exactly the same report as before.

    [on-screen] 5 HOURS -> 20 MIN
    Proposals used to take me five hours.

Usage
  python3 beats.py script.txt
  python3 beats.py script.txt --target 30
  python3 beats.py script.txt --wpm 185 --target 45
  pbpaste | python3 beats.py -
  python3 beats.py script.txt --json
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402

SENT_RE = re.compile(r"[^.!?؟]+[.!?؟]*")
CONCRETE_RE = re.compile(r"[$€£]\s?\d|(?<!\w)[\d٠-٩۰-۹][\d٠-٩۰-۹,.]*"
                         r"|(?<!^)\b[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿ]{2,}\b", re.MULTILINE)
STOPWORDS_FR = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "mais", "si", "à", "au",
    "aux", "en", "dans", "sur", "pour", "par", "avec", "que", "qui", "ce", "cet", "cette",
    "il", "elle", "on", "je", "tu", "nous", "vous", "ils", "mon", "ma", "mes", "ton", "ta",
    "tes", "est", "sont", "pas", "ne", "plus", "c'est", "j'ai", "a", "y",
}
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "that", "this", "it", "is", "are", "was", "were", "be", "been",
    "you", "your", "i", "my", "me", "we", "our", "they", "them", "he", "she",
    "so", "just", "not", "no", "do", "did", "does", "have", "has", "had",
    "will", "can", "at", "as", "by", "from", "out", "up", "off", "one", "all",
}

CARD_RE = re.compile(r"^\[(?:on[\s-]?screen|screen|écran|ecran)\]\s*:?\s*(.*)$", re.IGNORECASE)
CARD_WORDS = 6           # words a card can hold and still be read at arm's length
HOOK_WINDOW = 3.0        # seconds. Past this, the thumb has already decided.
MAX_BEAT = 4.0           # seconds on one idea with no change on screen.
ABSTRACT_RUN = 3         # beats in a row with nothing checkable in them.


# English keeps its calibrated rules exactly.
WORD_RE_EN = re.compile(r"[A-Za-z0-9$%'’-]+")
CONCRETE_RE_EN = re.compile(r"\$\s?\d|\b\d[\d,.]*\b|(?<!^)\b[A-Z][a-z]{2,}\b", re.MULTILINE)


def words(text, lang="en"):
    # "$18,000" and "18 000 €" are one number when spoken, so one word here too.
    if lang == "en":
        return WORD_RE_EN.findall(re.sub(r"(?<=\d),(?=\d)", "", text))
    return L.words(text)


PENDING = re.compile(r"\{\{[^{}]*\}\}")


def concrete(text, lang="en"):
    text = PENDING.sub("100", text)       # {{your number}} will be a number when it is said
    if lang == "en":
        return len(CONCRETE_RE_EN.findall(text))
    return len(CONCRETE_RE.findall(L.merge_thousands(text)))


def pretty(token):
    """Put the thousands separator back for display."""
    return re.sub(r"(\d)(?=(\d{3})+$)", r"\1,", token)


def tc(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}"


def split_beats(raw, wps, lang="en"):
    """One line is one beat, unless a line is too long to be one."""
    beats = []
    for line in [l.strip() for l in raw.splitlines()]:
        if not line:
            continue
        if len(words(line, lang)) / wps <= MAX_BEAT * 1.5:
            beats.append(line)
            continue
        # Long paragraph: break it at sentence ends so the timings mean
        # something, and let the report say it was split.
        parts = [p.strip() for p in SENT_RE.findall(line) if p.strip()]
        buf = ""
        for part in parts:
            candidate = (buf + " " + part).strip()
            if buf and len(words(candidate, lang)) / wps > MAX_BEAT:
                beats.append(buf)
                buf = part
            else:
                buf = candidate
        if buf:
            beats.append(buf)
    return beats


def split_cards(raw, wps, lang="en"):
    """Separate [on-screen] lines from speech. Returns the spoken beats and, for
    each card, the index of the beat it goes up with."""
    beats, cards, pending = [], [], []
    for line in raw.splitlines():
        m = CARD_RE.match(line.strip())
        if m:
            if m.group(1).strip():
                pending.append(m.group(1).strip())
            continue
        part = split_beats(line, wps, lang)
        if part:
            cards += [(text, len(beats)) for text in pending]
            pending = []
            beats += part
    cards += [(text, max(len(beats) - 1, 0)) for text in pending]
    return beats, cards


def analyse(raw, wpm=165, target=None, lang="en", wpm_given=True):
    wps = wpm / 60.0
    beats, cards = split_cards(raw, wps, lang)
    if not beats:
        return None

    rows, clock = [], 0.0
    for i, text in enumerate(beats):
        n = len(words(text, lang))
        dur = n / wps
        rows.append({
            "n": i + 1,
            "start": round(clock, 2),
            "dur": round(dur, 2),
            "words": n,
            "text": text,
            "concrete": concrete(text, lang),
            "label": "",
            "flags": [],
        })
        clock += dur
    total = clock

    # Label the structural positions a Reel is actually built around.
    for r in rows:
        if r["n"] == 1 or r["start"] + r["dur"] <= HOOK_WINDOW:
            r["label"] = "HOOK"
    rows[-1]["label"] = "CTA" if rows[-1]["label"] != "HOOK" else "HOOK/CTA"
    half = total / 2
    for r in rows:
        if not r["label"] and r["start"] <= half < r["start"] + r["dur"]:
            r["label"] = "MID"

    notes = []
    if rows[0]["dur"] > HOOK_WINDOW:
        rows[0]["flags"].append(f"hook runs {rows[0]['dur']:.1f}s, past the {HOOK_WINDOW:.0f}s mark")
        notes.append(f"Beat 1 takes {rows[0]['dur']:.1f}s to say. Cut it to "
                     f"{int(HOOK_WINDOW * wps)} words or fewer, or the hook lands after "
                     "the decision has been made.")
    if rows[0]["concrete"] == 0:
        notes.append("Beat 1 has no number and no name in it. Hooks without something "
                     "checkable are the ones that get scrolled.")

    for r in rows:
        if r["dur"] > MAX_BEAT:
            r["flags"].append(f"{r['dur']:.1f}s on one beat")
    long_beats = [r["n"] for r in rows if r["dur"] > MAX_BEAT]
    if long_beats:
        notes.append(f"Beat(s) {', '.join(map(str, long_beats))} run past {MAX_BEAT:.0f}s. "
                     "Either split the line or change what is on screen inside it. "
                     "A static frame is where people leave.")

    run, start = 0, None
    for r in rows:
        if r["concrete"] == 0:
            run += 1
            start = start if start is not None else r["n"]
            if run == ABSTRACT_RUN:
                notes.append(f"Beats {start}-{r['n']} have nothing concrete in them. "
                             "Put a number, a name or a price in one of them.")
        else:
            run, start = 0, None

    # Does the last line hand you back to the first one?
    stop = STOPWORDS | (STOPWORDS_FR if lang == "fr" else set())
    first = {w.lower().replace("’", "'") for w in words(rows[0]["text"], lang)} - stop
    last = {w.lower().replace("’", "'") for w in words(rows[-1]["text"], lang)} - stop
    loop = sorted(pretty(w) for w in first & last)
    if loop:
        notes.append(f"Loops: the last beat repeats \"{', '.join(loop[:3])}\" from the hook. "
                     "Second watches are free reach.")
    else:
        notes.append("No loop. The last beat shares no word with the hook, so the video "
                     "ends flat. Echoing one word from beat 1 is the cheapest replay you get.")

    if target:
        delta = total - target
        if abs(delta) <= target * 0.1:
            notes.append(f"Length is on target ({total:.1f}s against {target}s).")
        elif delta > 0:
            notes.append(f"{delta:.1f}s over target. Cut about {int(delta * wps)} words.")
        else:
            notes.append(f"{-delta:.1f}s under target. Either add {int(-delta * wps)} words "
                         "or shoot it short. Short is usually right.")

    pending = sorted({m.group(0) for r in rows for m in PENDING.finditer(r["text"])})
    if pending:
        notes.append(f"Pending: {', '.join(pending)} still to fill. Not ready to shoot until it is a real number.")

    if lang != "en" and not wpm_given:
        notes.append(f"Timing uses the English rate ({wpm:.0f} wpm). In "
                     f"{L.LANG_NAMES.get(lang, lang)} words are not the same length: "
                     "read one script out loud with a timer and pass --wpm.")

    result = {
        "lang": lang,
        "wpm": wpm, "target": target,
        "total_seconds": round(total, 2),
        "total_words": sum(r["words"] for r in rows),
        "beats": rows,
        "notes": notes,
    }
    if cards:
        result["cards"] = []
        for i, (text, beat) in enumerate(cards):
            start = rows[beat]["start"]
            end = rows[cards[i + 1][1]]["start"] if i + 1 < len(cards) else total
            n = len(words(text, lang))
            flags = [f"{n} words: {CARD_WORDS} or fewer reads at arm's length"] if n > CARD_WORDS else []
            result["cards"].append({"text": text, "beat": beat + 1, "start": round(start, 2),
                                    "end": round(max(end, start), 2), "words": n, "flags": flags})
        if cards[0][1] != 0:
            notes.append("No card goes up with the hook. The hook card belongs at frame 1: "
                         "people read before they listen.")
        if any(c["end"] - c["start"] < 1.0 for c in result["cards"]):
            notes.append("A card is up for under a second: nobody reads it. Merge it with the next one.")
    return result


def render(a, out=sys.stdout):
    head = (f"BEAT SHEET  ·  {a['total_words']} words  ·  ~{a['total_seconds']:.1f}s "
            f"at {a['wpm']} wpm" + (f"  ·  target {a['target']}s" if a["target"] else ""))
    print("\n" + head, file=out)
    print("=" * max(len(head), 72), file=out)
    for r in a["beats"]:
        label = f"{r['label']:<8}" if r["label"] else " " * 8
        print(f"  {tc(r['start'])}  {r['dur']:4.1f}s  {label}{r['text']}", file=out)
        for f in r["flags"]:
            print(f"  {'':>6}  {'':>5}  {'':<8}^ {f}", file=out)
    if a.get("cards"):
        print("-" * max(len(head), 72), file=out)
        print("  ON-SCREEN CARDS  (estimated from the word count: retime them in the edit)", file=out)
        for c in a["cards"]:
            print(f"  {tc(c['start'])} - {tc(c['end'])}  beat {c['beat']:<2}  {c['text']}", file=out)
            for f in c["flags"]:
                print(f"  {'':>15}  {'':<7}  ^ {f}", file=out)
    print("-" * max(len(head), 72), file=out)
    for n in a["notes"]:
        print(f"  - {n}", file=out)
    print("", file=out)


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Time a Reel script into a beat sheet.")
    ap.add_argument("input", nargs="?", default="-", help="script file, or - for stdin")
    ap.add_argument("--wpm", type=float, default=None, help="speaking rate (default 165)")
    ap.add_argument("--target", type=float, help="target length in seconds")
    ap.add_argument("--json", action="store_true")
    L.add_lang_arg(ap)
    args = ap.parse_args()

    raw = L.read_input(args.input)
    lang, _ = L.resolve(raw, args.lang)
    a = analyse(raw, wpm=args.wpm or 165, target=args.target, lang=lang,
                wpm_given=args.wpm is not None)
    if not a:
        only_cards = any(CARD_RE.match(line.strip()) for line in raw.splitlines())
        print("only [on-screen] cards, no spoken line" if only_cards else "empty script", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0)


if __name__ == "__main__":
    main()
