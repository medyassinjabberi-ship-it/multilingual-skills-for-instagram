#!/usr/bin/env python3
"""
hookscore.py - score the first line of a Reel on the five things strong hooks
have in common, and rank a batch of them against each other.

What this is:  five local heuristics, computed on your machine from the text
alone. They measure properties that hooks which hold attention tend to share -
a length you can say in under three seconds, a concrete marker, something at stake,
the payload at the front rather than the back, and a viewer to aim it at.

What this is NOT:  a view predictor. It was tested against 74 real short-form
hooks, transcribed from the first three seconds of the top eight and bottom
eight performers on five channels. Separating a real hook from a deliberately
bad one it does well: AUC 0.83, and 9 of 10 written-to-be-bad hooks scored
below the real median. Separating a good creator's hits from that same
creator's misses it barely does at all: AUC 0.56, where 0.50 is a coin flip.

So use it for what it measured well. It catches greetings, preambles, hooks
with nothing concrete in them and hooks that take five seconds to say. It will
not tell you which of two decent hooks will travel, and nothing that reads text
can, because that is decided by your face, your edit, your audio and who
Instagram shows it to. Trust the retention graph over this script.

Languages:  that test was run on English hooks, and STAKES and ADDRESS are
English word lists. In French, Arabic script and arabizi the script measures
only the mechanics - LENGTH, SPECIFICITY (numbers and names), FRONTLOAD and the
dealbreakers - and leaves STAKES and ADDRESS to Claude, who reads them with the
grid in SKILL.md. There is no verdict outside English. Hooks are still ranked,
on the mechanics alone, so you can see which ones break a rule.

Each check returns 0 to 100. Higher is better.

Usage
  python3 hookscore.py hooks.txt              # one hook per line, ranked
  python3 hookscore.py --hook "I lost $18,000 on one missing contract."
  python3 hookscore.py hooks.txt --lang fr
  pbpaste | python3 hookscore.py -
  python3 hookscore.py hooks.txt --json
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

NUMBER_RE = re.compile(
    r"[$€£]\s?\d[\d,]*(?:\.\d+)?"                    # money, whole
    r"|\b\d[\d,]*(?:[.,]\d+)?\s?(?:€|£)?\s?"         # a figure, with or
    r"(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b"  # without a unit
    r"|days?\b|weeks?\b|months?\b|years?\b"
    r"|h\b|jours?\b|semaines?\b|mois\b|ans?\b|années?\b)?"
    r"|[٠-٩۰-۹]+",
    re.IGNORECASE)
PROPER_RE = re.compile(r"(?<!^)\b[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿ]{2,}\b")
# English keeps its own rules exactly, so its calibration still holds.
WORD_RE_EN = re.compile(r"[A-Za-z0-9$%'’-]+")
NUMBER_RE_EN = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?"
    r"(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b"
    r"|days?\b|weeks?\b|months?\b|years?\b)?",
    re.IGNORECASE)
PROPER_RE_EN = re.compile(r"(?<!^)\b[A-Z][a-z]{2,}\b")
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

# Spoken hooks say their numbers out loud. "Zero dollars" and "twenty grand"
# are as concrete as "$0" and "$20,000", and counting only digits missed them.
# "one" and "first" are deliberately absent: they are filler far more often
# than they are a quantity.
SPOKEN_NUMBERS = {
    "en": {
        "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "fifteen", "twenty", "thirty", "forty", "fifty",
        "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
        "billion", "dozen", "half", "twice", "triple",
    },
    # "un", "une" and "premier" are left out for the same reason as "one".
    "fr": {
        "zéro", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
        "dix", "onze", "douze", "quinze", "vingt", "trente", "quarante", "cinquante",
        "soixante", "cent", "cents", "mille", "million", "millions", "milliard",
        "milliards", "douzaine", "moitié", "double", "triple",
    },
}
MONEY_WORDS = {
    "en": {
        "dollars", "dollar", "bucks", "grand", "percent", "cents",
        "millionaire", "billionaire", "revenue", "profit", "salary", "rent",
    },
    "fr": {
        "euros", "euro", "dollars", "balles", "pourcent", "salaire", "loyer",
        "bénéfice", "bénéfices", "millionnaire", "smic",
    },
}

# Words that put something on the line. A hook with none of these is a
# statement; a hook with one is a reason to keep watching. English only:
# in other languages Claude judges the stakes (SKILL.md, judgement grid).
STAKES = {
    "stop", "never", "wrong", "mistake", "mistakes", "lost", "lose", "losing",
    "cost", "costs", "broke", "broken", "failed", "failure", "fail", "nobody",
    "no", "not", "don't", "dont", "doesn't", "didn't", "can't", "won't",
    "quit", "quitting", "fired", "deleted", "delete", "killed", "kills", "kill",
    "replaced", "replaces", "cut", "beat", "free", "paid", "charged", "hired",
    "saved", "first",
    "banned", "illegal", "worst", "hate", "hated", "wasted", "waste", "scam",
    "lie", "lied", "lying", "truth", "secret", "hidden", "stole", "stolen",
    "before", "until", "instead", "but", "except", "unless", "problem",
    "risk", "danger", "warning", "regret", "wish", "should", "shouldn't",
    "still", "already", "only", "without", "versus", "vs", "actually",
}

# Openers that spend the first second saying nothing.
WEAK_OPENERS = {
    "en": [
        "so", "ok", "okay", "hey", "hi", "hello", "guys", "yo", "alright",
        "welcome", "today", "basically", "honestly", "look", "listen", "um",
        "just", "let", "lets", "let's", "i wanted", "i want", "one of",
        "have you", "did you", "do you", "are you", "in this", "in today",
        "the thing", "a lot", "there is", "there are", "this is", "it is",
        "as a", "when it", "if you've", "you know",
    ],
    "fr": [
        "alors", "bon", "donc", "ok", "okay", "salut", "coucou", "bonjour", "hello",
        "hey", "yo", "bref", "voilà", "euh", "aujourd'hui", "en fait", "du coup",
        "dans cette", "dans ce", "je vais", "on va", "je voulais", "vous savez",
        "tu sais", "il y", "c'est", "est-ce que", "est ce", "avez-vous", "as-tu",
    ],
    "aeb-latn": [
        "ahla", "aslema", "3aslema", "salam", "salem", "ya jme3a", "lyoum", "lyouma",
        "taw", "tawa", "ok", "okay", "hey", "hello", "bon", "alors", "donc",
    ],
    "ar": [
        "السلام", "عسلامة", "أهلا", "اهلا", "مرحبا", "اليوم", "توا", "تو", "يا جماعة",
    ],
}

# Imperatives that earn the front position.
IMPERATIVES = {
    "stop", "steal", "copy", "delete", "try", "watch", "read", "save",
    "use", "build", "make", "write", "send", "take", "start", "quit",
    "never", "always", "don't", "dont", "do", "put", "run", "check",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:stop scrolling|don'?t scroll)"),
     "Opens with \"stop scrolling\". Asking for attention proves you have not earned it."),
    (re.compile(r"(?i)\b(?:in (?:this|today'?s) (?:video|reel)|i'?m going to show you|i'?ll show you how)\b"),
     "Video preamble. Delete it and open on the payoff."),
    (re.compile(r"(?i)^\s*(?:hey |hi |what'?s up |welcome )"),
     "Greeting. Nobody came to the feed to be greeted."),
    (HASHTAG_RE,
     "Hashtag in the hook. Hashtags belong at the bottom of the caption, if anywhere."),
    (EMOJI_RE,
     "Emoji in the hook. On-screen text at hook size has room for words or for an emoji, not both."),
]
DEALBREAKERS_BY_LANG = {
    "fr": [
        (re.compile(r"(?i)^\s*(?:arr[êe]te de scroller|ne scrolle pas|ne scrollez pas)"),
         "Ouvre sur « arrête de scroller ». Demander l'attention prouve qu'on ne l'a pas gagnée."),
        (re.compile(r"(?i)\b(?:dans (?:cette|la) (?:vidéo|video|reel)|aujourd['’]hui je vais "
                    r"(?:te|vous) (?:montrer|expliquer)|je vais (?:te|vous) montrer)\b"),
         "Préambule vidéo. Supprime-le et ouvre sur le résultat."),
        (re.compile(r"(?i)^\s*(?:salut|coucou|bonjour|bonsoir|hello)\b"),
         "Salutation. Personne n'est venu dans le feed pour être salué."),
    ],
    "aeb-latn": [
        (re.compile(r"(?i)^\s*(?:ahla|aslema|3aslema|salam|salem|marhba)\b"),
         "Greeting. Nobody came to the feed to be greeted."),
    ],
    "ar": [
        (re.compile(r"^\s*(?:السلام عليكم|سلام|عسلامة|أهلا|اهلا|مرحبا)(?![ء-يٱ-ۓ])"),
         "Greeting. Nobody came to the feed to be greeted."),
    ],
}

JUDGE = "not measured in this language - Claude judges it (SKILL.md grid)"


def clamp(n):
    return max(0.0, min(100.0, n))


def words(text, lang="en"):
    # "$18,000" and "18 000 €" are one number when spoken, so one word here too.
    if lang == "en":
        return WORD_RE_EN.findall(re.sub(r"(?<=\d),(?=\d)", "", text))
    return L.words(text)


def _numbers(text, lang):
    if lang == "en":
        return NUMBER_RE_EN
    return NUMBER_RE


def _proper(lang):
    return PROPER_RE_EN if lang == "en" else PROPER_RE


def check_length(text, lang="en"):
    """A hook has to land before the thumb moves. Roughly two seconds."""
    w = words(text, lang)
    n = len(w)
    secs = n / 2.75                      # ~165 words per minute, spoken
    chars = len(text.strip())
    if 5 <= n <= 12:
        score = 100.0
    elif n < 5:
        score = clamp(100 - (5 - n) * 20)
    else:
        score = clamp(100 - (n - 12) * 11)
    if chars > 60:                       # two lines of big on-screen text
        score -= 12
    detail = f"{n} words, {chars} chars, ~{secs:.1f}s spoken (want 5-12 words)"
    if lang != "en":
        detail += "; window set on English, time it out loud"
    return clamp(score), detail


def check_specificity(text, lang="en"):
    """One concrete thing beats three abstract ones."""
    source = text if lang == "en" else L.merge_thousands(text)
    nums = [n.strip() for n in _numbers(text, lang).findall(source) if n.strip()]
    propers = set(_proper(lang).findall(text)) if lang != "ar" else set()
    low = [w.lower().strip("'’") for w in words(text, lang)]
    spoken_set = SPOKEN_NUMBERS.get(lang, set()) | MONEY_WORDS.get(lang, set())
    spoken = [w for w in low if w in spoken_set]
    hits = len(nums) + len(propers) + len(spoken)
    score = 15.0 if hits == 0 else clamp(45 + hits * 30)
    found = ", ".join(nums[:2] + sorted(propers)[:2] + spoken[:2])
    return score, (f"{hits} concrete marker(s)" + (f": {found}" if found else
                   " - no number, no name, nothing checkable"))


def check_stakes(text, lang="en"):
    """Tension, cost, negation. Something the viewer might lose."""
    if lang != "en":
        return None, JUDGE
    w = [x.lower().strip("'’") for x in words(text, lang)]
    hits = [x for x in w if x in STAKES]
    markers = sorted(set(hits))
    if re.search(r"\$\s?\d", text):
        markers.append("a price")
    n = len(markers)
    score = {0: 20.0, 1: 70.0}.get(n, 100.0)
    detail = f"{n} tension marker(s)" + (f": {', '.join(markers[:4])}" if markers else
                                         " - nothing is at stake in this line")
    return clamp(score), detail


def _is_payload(token, raw, i, lang):
    if lang == "en" and token in STAKES:
        return True
    if token in SPOKEN_NUMBERS.get(lang, ()) or token in MONEY_WORDS.get(lang, ()):
        return True
    if lang == "en":                      # calibrated English rule
        return bool(NUMBER_RE_EN.match(raw) or (i and PROPER_RE_EN.match(raw)))
    if NUMBER_RE.match(raw) and any(ch.isdigit() for ch in raw):
        return True
    return bool(i and lang != "ar" and PROPER_RE.match(raw))


def check_frontload(text, lang="en"):
    """The interesting word cannot be in position nine."""
    w = words(text, lang)
    if not w:
        return 0.0, "empty"
    if lang == "en":
        low = [x.lower().strip("'’") for x in w]
    else:
        low = [x.lower().replace("’", "'").strip("'") for x in w]
    opener = " ".join(low[:2])
    penalty = 0
    hit_opener = None
    for weak in WEAK_OPENERS.get(lang, []):
        if lang == "en":
            hit = opener.startswith(weak) or low[0] == weak       # calibrated English rule
        else:
            hit = low[:len(weak.split())] == weak.split()          # whole words only
        if hit:
            penalty, hit_opener = 30, weak
            break
    payload = None
    for i, token in enumerate(low):
        if _is_payload(token, w[i], i, lang):
            payload = i
            break
    if payload is None:
        base = 30.0
        where = "no payload word anywhere in the line"
        if lang != "en":
            where = "no number or name in the line (other payloads: Claude judges)"
    elif payload <= 3:
        base = 100.0
        where = f"payload at word {payload + 1}"
    elif payload <= 6:
        base = 70.0
        where = f"payload at word {payload + 1}, could move forward"
    else:
        base = 40.0
        where = f"payload at word {payload + 1}, too late"
    if lang != "en" and payload is None:
        base = 50.0                      # absence of a number is not proof here
    detail = where + (f"; weak opener \"{hit_opener}\"" if hit_opener else "")
    return clamp(base - penalty), detail


def check_address(text, lang="en"):
    """Aimed at one viewer, or floating in the air."""
    if lang != "en":
        return None, JUDGE
    low = text.lower()
    w = [x.lower().strip("'’") for x in words(text, lang)]
    if re.search(r"\b(you|your|you're|youre|yourself)\b", low):
        return 100.0, "speaks to the viewer"
    if w and w[0] in IMPERATIVES:
        return 90.0, f"imperative opener (\"{w[0]}\")"
    if re.search(r"\b(i|my|me|we|our)\b", low):
        return 70.0, "first person, no viewer named"
    return 35.0, "third person, nobody in the room"


CHECKS = ["LENGTH", "SPECIFICITY", "STAKES", "FRONTLOAD", "ADDRESS"]


PENDING = re.compile(r"\{\{[^{}]*\}\}")


def run(text, lang="en"):
    """(results, overall, verdict, flags).

    In English `overall` is the calibrated hook score. In any other language
    `overall` is None and the verdict NOT CALIBRATED: there is no number to
    relay. Rank those hooks with issues() instead.
    """
    # {{your number}} is a number the user still has to give: score the line as it
    # will be said, with a number in that place. The report says it is pending.
    text = PENDING.sub("100", text)
    results = {
        "LENGTH": check_length(text, lang),
        "SPECIFICITY": check_specificity(text, lang),
        "STAKES": check_stakes(text, lang),
        "FRONTLOAD": check_frontload(text, lang),
        "ADDRESS": check_address(text, lang),
    }
    rules = DEALBREAKERS + DEALBREAKERS_BY_LANG.get(lang, [])
    flags = []
    for pattern, msg in rules:
        if pattern.search(text) and msg not in flags:
            flags.append(msg)
    if not L.calibrated(lang):
        return results, None, "NOT CALIBRATED", flags
    scores = [results[c][0] for c in CHECKS]
    # The weakest property caps the hook, same logic as detect.py: one bad
    # property is enough for the thumb to keep moving.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4 - len(flags) * 15
    overall = clamp(overall)
    verdict = "STRONG" if overall >= 70 and min(scores) >= 55 and not flags else (
        "OK" if overall >= 50 else "WEAK")
    return results, overall, verdict, flags


def bar(score, width=24):
    if score is None:
        return " " * width
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def issues(results, flags):
    """Rules a hook breaks: each measured check under 70, each dealbreaker."""
    return [c for c in CHECKS if results[c][0] is not None and results[c][0] < 70] + list(flags)


def _weakest(results):
    measured = {c: results[c][0] for c in CHECKS if results[c][0] is not None}
    return min(measured, key=measured.get)


def render_one(text, results, overall, verdict, flags, lang="en", out=sys.stdout):
    print("\nHOOK SCORE", file=out)
    print("=" * 62, file=out)
    print(f"  \"{text.strip()}\"", file=out)
    if PENDING.search(text):
        print("  pending: {{...}} scored as a number. Fill it with the real one before shooting.", file=out)
    print(f"  language: {L.LANG_NAMES.get(lang, lang)}\n", file=out)
    for name in CHECKS:
        score, detail = results[name]
        shown = f"{score:5.1f}" if score is not None else "  n/a"
        print(f"  {name:<13} {bar(score)} {shown}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    if L.calibrated(lang):
        print(f"  {'HOOK SCORE':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    else:
        n = len(issues(results, flags))
        print(f"  {'RULES BROKEN':<13} {n}   (no overall score in this language)", file=out)
        print(f"  {L.uncalibrated_note(lang)}", file=out)
    for f in flags:
        print(f"\n  DEALBREAKER  {f}", file=out)
    weakest = _weakest(results)
    if verdict == "WEAK" or verdict == "OK" or (
            not L.calibrated(lang) and (results[weakest][0] < 70 or flags)):
        print(f"\n  Weakest property measured: {weakest}. Fix that one and re-run.", file=out)
    print("", file=out)


def render_table(rows, lang="en", out=sys.stdout):
    title = "HOOK GATE" if L.calibrated(lang) else "HOOK GATE  (mechanics only, not calibrated)"
    print(f"\n{title}\n" + "=" * 78, file=out)
    for i, r in enumerate(rows, 1):
        if L.calibrated(lang):
            mark = "ok " if r["score"] >= 50 and not r["flags"] else "out"
        else:
            mark = "ok " if not r["issues"] else "out"
        hook = r["hook"] if len(r["hook"]) <= 62 else r["hook"][:59] + "..."
        if L.calibrated(lang):
            print(f"{mark} {r['score']:5.1f} {r['verdict']:<7} {hook}", file=out)
        else:
            print(f"{mark} {len(r['issues'])} rule(s) broken   {hook}", file=out)
        print(f"        weakest: {r['weakest']} ({r['checks'][r['weakest']]['score']:.0f})", file=out)
        for f in r["flags"]:
            print(f"        dealbreaker: {f}", file=out)
        if PENDING.search(r["hook"]):
            print("        pending: {{...}} scored as a number. Fill it with the real one before shooting.", file=out)
    if L.calibrated(lang):
        print("\nHooks marked out are out: under 50 or a dealbreaker. Between the ones marked ok,"
              "\nthe score does not pick the winner (AUC 0.56 within one creator's own hooks): choose"
              "\non stakes, the user's real proof and what worked on this account.\n", file=out)
    else:
        print(f"\n{L.uncalibrated_note(lang)}\nRanked by rules broken (length, no number, "
              "late payload, greeting), fewest first.\nIt does not say which hook is good. "
              "Stakes and who it speaks to: read them with the grid in SKILL.md before "
              "you pick.\n", file=out)


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Score a Reel hook on five properties.")
    ap.add_argument("input", nargs="?", default="-", help="file with one hook per line, or -")
    ap.add_argument("--hook", help="score a single hook given on the command line")
    ap.add_argument("--json", action="store_true")
    L.add_lang_arg(ap)
    args = ap.parse_args()

    if args.hook:
        lines = [args.hook]
    else:
        raw = L.read_input(args.input)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        print("nothing to score", file=sys.stderr)
        sys.exit(2)
    lang, _ = L.resolve("\n".join(lines), args.lang)

    payload = []
    for line in lines:
        results, overall, verdict, flags = run(line, lang)
        payload.append({
            "hook": line,
            "lang": lang,
            "checks": {k: {"score": None if v[0] is None else round(v[0], 1), "detail": v[1]}
                       for k, v in results.items()},
            "weakest": _weakest(results),
            "flags": flags,
            "issues": issues(results, flags),
            "score": None if overall is None else round(overall, 1),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if len(payload) > 1 else payload[0], indent=2, ensure_ascii=False))
        return

    if len(payload) == 1:
        results, overall, verdict, flags = run(lines[0], lang)
        render_one(lines[0], results, overall, verdict, flags, lang)
    else:
        if L.calibrated(lang):
            render_table(sorted(payload, key=lambda r: -r["score"]), lang)
        else:
            render_table(sorted(payload, key=lambda r: len(r["issues"])), lang)

    if not L.calibrated(lang):
        sys.exit(0)
    sys.exit(0 if max(p["score"] for p in payload) >= 70 else 1)


if __name__ == "__main__":
    main()
