#!/usr/bin/env python3
"""
detect.py - a five-check panel that scores how machine-written a draft looks.

What this is:  five local heuristics modelled on the signals public AI
detectors actually measure - sentence-length variation, concreteness, stock
vocabulary, typographic fingerprint, and voice. Every score is computed on
your machine from the text alone. Nothing is uploaded.

What this is NOT:  GPTZero, Originality, Copyleaks, Winston or Turnitin.
It does not call their APIs and it cannot promise their verdict. It catches
the things they all key on, which is why fixing them tends to move their
numbers too - but the only honest claim is the one on this line.

Languages:  the thresholds were set on English. In English the panel gives a
HUMAN SCORE and a verdict. In French, Arabic script and arabizi it prints each
signal on its own, marked "not calibrated", and no global verdict: a number
that looks precise and is not would be worse than none. A check that cannot
be measured in a language (no word list yet, pronouns written as suffixes)
says "n/a" instead of guessing.

Each check returns a HUMAN score from 0 to 100. Higher is better.

Usage
  python3 detect.py draft.txt
  python3 detect.py draft.txt --lang fr
  pbpaste | python3 detect.py -
  python3 detect.py draft.txt --json
  python3 detect.py before.txt after.txt      # compare two drafts
"""

import argparse
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402

LEX = os.path.join(HERE, "slop.json")
LEX_DIR = os.path.join(HERE, "lex")

SENT_RE = re.compile(r"[^.!?؟\n]+[.!?؟]*")
CONTRACTIONS = re.compile(r"\b\w+['’](?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS = {
    "en": re.compile(r"\b(i|me|my|mine|we|us|our|you|your)\b", re.IGNORECASE),
    "fr": re.compile(r"(?<!\w)(?:je|j['’]|me|m['’]|moi|mon|ma|mes|nous|notre|nos|tu|t['’]|te|toi|"
                     r"ton|ta|tes|vous|votre|vos)(?!\w)", re.IGNORECASE),
    "aeb-latn": re.compile(r"\b(ena|enti|inti|enta|inta|a7na|ahna|entouma|intouma|"
                           r"mte3i|mta3i|mte3ek|mta3ek|mte3na|mta3na|3andi|3andek)\b",
                           re.IGNORECASE),
    # Arabic script: pronouns are mostly suffixes on the verb or noun, so a
    # word list counts almost nothing. Not measured rather than measured wrong.
}
NUMBERS = re.compile(r"(?<!\w)[\d٠-٩۰-۹][\d٠-٩۰-۹,.]*%?"
                     r"|[$€£]\s?\d")
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿ]{2,}\b", re.MULTILINE)
# English keeps its own rules, so its calibration still holds.
WORD_RE_EN = re.compile(r"[A-Za-z']+")
NUMBERS_EN = re.compile(r"\b\d[\d,.]*%?\b|\$\d")
PROPER_EN = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b", re.MULTILINE)


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, human, machine):
    """Map value onto 0-100 where `human` -> 100 and `machine` -> 0."""
    if human == machine:
        return 50.0
    return clamp((value - machine) / (human - machine) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def words(text, lang="en"):
    if lang == "en":
        return WORD_RE_EN.findall(text)
    return L.words(text)


def check_burstiness(text, lang="en"):
    """Humans vary sentence length hard. Models write even."""
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < 4:
        return 50.0, "too short to judge"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    score = scale(cv, human=0.70, machine=0.22)
    return score, f"variation {cv:.2f} across {len(lens)} sentences (want 0.55+)"


def check_specificity(text, lang="en"):
    """Numbers, names and concrete nouns. Slop is abstract."""
    w = words(text, lang)
    if len(w) < 25:
        return 50.0, "too short to judge"
    per100 = 100 / len(w)
    if lang == "en":
        hits = len(NUMBERS_EN.findall(text)) + len(set(PROPER_EN.findall(text)))
    else:
        merged = L.merge_thousands(text)
        names = set(PROPER.findall(text)) if lang != "ar" else set()
        hits = len(NUMBERS.findall(merged)) + len(names)
    density = hits * per100
    score = scale(density, human=6.0, machine=0.5)
    detail = f"{hits} concrete markers, {density:.1f} per 100 words (want 4+)"
    if lang == "ar":
        detail += "; numbers only, Arabic script has no capitals to find names by"
    return score, detail


def check_slop(text, lang_lex, lang="en"):
    """Stock vocabulary density against the language's own lexicon."""
    if not lang_lex:
        return None, f"n/a - no word list for {L.LANG_NAMES.get(lang, lang)} yet"
    w = words(text, lang)
    if not w:
        return 50.0, "empty"
    hits, found = 0, []
    body = L.strip_protected(text)        # a slop word inside a URL or a handle is not slop
    entries = lang_lex.get("words", []) + lang_lex.get("phrases", [])
    if lang != "en":                      # longest first, each span counted once
        entries = sorted(entries, key=lambda e: -len(e["find"]))
    for entry in entries:
        pattern = re.compile(r"(?<!\w)" + re.escape(entry["find"]).replace(r"\ ", r"\s+") + r"(?!\w)",
                             re.IGNORECASE)
        n = len(pattern.findall(body))
        if lang != "en":
            body = pattern.sub(" ", body)
        if n:
            hits += n
            found.append(entry["find"])
    density = hits * 100 / len(w)
    score = scale(density, human=0.0, machine=4.0)
    detail = f"{hits} stock terms, {density:.1f} per 100 words"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return score, detail


def check_fingerprint(text, lang="en"):
    """Characters a phone keyboard does not produce.

    ’ is never counted: iPhone and Android type it by default. Characters a
    language really uses (French no-break spaces, Arabic direction marks, the
    joiner inside an emoji) are not counted either. Outside English only the
    true invisibles and the em dash count.
    """
    invisible = len(L.machine_invisibles(text, lang))
    em = text.count("—")
    if lang == "en":
        curly = sum(text.count(c) for c in "‘“”")
        ellip = text.count("…")
        nbsp = sum(text.count(c) for c in "   ")
    else:
        curly = ellip = nbsp = 0
    total = invisible * 4 + em * 2 + curly + ellip + nbsp
    per1k = total * 1000 / max(len(text), 1)
    score = scale(per1k, human=0.0, machine=12.0)
    if lang == "en":
        detail = (f"{invisible} invisible, {em} em dash, {curly} curly quote, "
                  f"{ellip} ellipsis, {nbsp} hard space")
    else:
        detail = f"{invisible} invisible, {em} em dash (this language's typography is not counted)"
    return score, detail


def check_voice(text, lex, lang_lex=None, lang="en"):
    """Contractions, person, and the shapes models default to."""
    w = words(text, lang)
    if len(w) < 25:
        return 50.0, "too short to judge"
    per100 = 100 / len(w)
    tells = 0
    names = []
    for s in lex.get("structures", []) + ((lang_lex or {}).get("structures", [])):
        try:
            n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
        except re.error:
            continue
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = (len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6)
    tell_score = clamp(100 - tells * 22)
    parts = []
    pron = PRONOUNS.get(lang)
    person = len(pron.findall(text)) * per100 if pron else None
    if lang == "en":
        contractions = len(CONTRACTIONS.findall(text)) * per100
        score = (scale(contractions, human=3.0, machine=0.0) * 0.35
                 + scale(person, human=8.0, machine=1.0) * 0.35
                 + tell_score * 0.30)
        parts.append(f"{contractions:.1f} contractions")
    elif person is not None:
        # No contractions sub-signal: French elision is grammar, not voice.
        score = scale(person, human=8.0, machine=1.0) * 0.5 + tell_score * 0.5
    else:
        score = tell_score
        parts.append("pronouns n/a (suffixes in Arabic script)")
    if person is not None:
        parts.append(f"{person:.1f} personal pronouns per 100 words")
    if uniform:
        score -= 12
        names.append("uniform-bullets")
    detail = ", ".join(parts) + f", {tells} structural tell(s)"
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


CHECKS = ["BURSTINESS", "SPECIFICITY", "SLOP DENSITY", "FINGERPRINT", "VOICE"]


def run(text, lex, lang="en", lang_lex=None):
    results = {}
    results["BURSTINESS"] = check_burstiness(text, lang)
    results["SPECIFICITY"] = check_specificity(text, lang)
    results["SLOP DENSITY"] = check_slop(text, lang_lex, lang)
    results["FINGERPRINT"] = check_fingerprint(text, lang)
    results["VOICE"] = check_voice(text, lex, lang_lex, lang)
    scores = [results[c][0] for c in CHECKS if results[c][0] is not None]
    if not L.calibrated(lang) or len(scores) < len(CHECKS):
        return results, None, "NOT CALIBRATED"
    # The weakest check drags the verdict: a detector only needs one signal.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    verdict = "PASS" if overall >= 70 and min(scores) >= 55 else (
        "REVIEW" if overall >= 50 else "FLAGGED")
    return results, overall, verdict


def bar(score, width=24):
    if score is None:
        return " " * width
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render(results, overall, verdict, label=None, lang="en", source="declared", out=sys.stdout):
    title = "AI DETECTION PANEL" + (f"  -  {label}" if label else "")
    print("\n" + title, file=out)
    print("=" * max(len(title), 62), file=out)
    print(f"  language: {L.LANG_NAMES.get(lang, lang)} ({source})", file=out)
    for name in CHECKS:
        score, detail = results[name]
        shown = f"{score:5.1f}" if score is not None else "  n/a"
        print(f"  {name:<13} {bar(score)} {shown}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    if overall is None:
        print(f"  {L.uncalibrated_note(lang)}", file=out)
        measured = {c: results[c][0] for c in CHECKS if results[c][0] is not None}
        if measured:
            weakest = min(measured, key=measured.get)
            print(f"\n  Weakest signal measured: {weakest}. Look at that first.", file=out)
    else:
        print(f"  {'HUMAN SCORE':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
        if verdict != "PASS":
            weakest = min(CHECKS, key=lambda c: results[c][0])
            print(f"\n  Weakest signal: {weakest}. Fix that first.", file=out)
    print("", file=out)


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Score how machine-written a draft looks.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("compare", nargs="?", help="second file, to show before/after")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lexicon", default=LEX)
    ap.add_argument("--lex-dir", default=LEX_DIR)
    L.add_lang_arg(ap)
    args = ap.parse_args()

    lex = json.load(open(args.lexicon, encoding="utf-8"))

    targets = [(args.input, L.read_input(args.input))]
    if args.compare:
        targets.append((args.compare, L.read_input(args.compare)))
    if not all(t.strip() for _, t in targets):
        print("empty input: nothing to score", file=sys.stderr)
        sys.exit(2)

    lang, source = L.resolve(targets[0][1], args.lang)
    path = os.path.join(args.lex_dir, f"{lang}.json")
    lang_lex = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None

    payload, runs = [], []
    for name, text in targets:
        results, overall, verdict = run(text, lex, lang, lang_lex)
        runs.append((results, overall, verdict))
        payload.append({
            "source": name,
            "lang": lang,
            "lang_source": source,
            "calibrated": L.calibrated(lang),
            "checks": {k: {"score": None if v[0] is None else round(v[0], 1), "detail": v[1]}
                       for k, v in results.items()},
            "human_score": None if overall is None else round(overall, 1),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2, ensure_ascii=False))
        return

    for (name, _), (results, overall, verdict) in zip(targets, runs):
        render(results, overall, verdict, label=os.path.basename(name) if args.compare else None,
               lang=lang, source=source)
    if args.compare:
        a, b = payload
        if a["human_score"] is not None:
            delta = b["human_score"] - a["human_score"]
            print(f"  {a['human_score']:.1f} {a['verdict']}  ->  "
                  f"{b['human_score']:.1f} {b['verdict']}   ({delta:+.1f})\n")
        else:
            for k in CHECKS:
                sa, sb = a["checks"][k]["score"], b["checks"][k]["score"]
                if sa is not None and sb is not None:
                    print(f"  {k:<13} {sa:5.1f} -> {sb:5.1f}   ({sb - sa:+.1f})")
            print("")

    if payload[-1]["human_score"] is None:
        sys.exit(0)
    sys.exit(0 if payload[-1]["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
