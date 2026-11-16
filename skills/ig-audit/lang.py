"""
lang.py - the language layer shared by every script in this pack.

Canonical copy: shared/lang.py. A copy sits next to each script that uses it,
so every skill folder still installs on its own. Do not edit the copies: edit
this file and run `python3 tools/sync_lang.py`. tests/test_pack.py checks they
are equal.

What it does, and nothing more:
  - count words in English, French, Arabic script and arabizi (Latin-script
    Darija with digits for sounds: 3, 7, 9, 5...);
  - read "18 000", "18,000" and "18 000" as one number;
  - decide which language a text is in: --lang first, then the `language:`
    line in ~/.claude/instagram/voice.md, then a guess. A guess without real
    evidence returns "und" (unknown), which never gets a calibrated verdict;
  - say which invisible or typographic characters are legitimate, so no script
    deletes French spacing, Arabic direction marks or the joiner inside an emoji;
  - read files and stdin whatever their encoding (UTF-8, UTF-8 with BOM, UTF-16
    from PowerShell) and make stdout and stderr UTF-8, so Windows consoles do
    not crash on Arabic.

English keeps its own counting rules in each script, so its calibrated scores
stay exactly as they are. Scores are calibrated in English
only: every script asks `calibrated(lang)` before printing a global verdict.
"""

import os
import re
import sys

LANGS = ("en", "fr", "ar", "aeb-latn")
UNKNOWN = "und"
CALIBRATED = {"en"}
LANG_NAMES = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic script (MSA or Darija)",
    "aeb-latn": "arabizi (Darija in Latin letters)",
    "und": "unknown language (pass --lang)",
}
DIALECT_ALIASES = {"darija", "derja", "tounsi", "tunsi", "tunisien", "tunisienne", "tunisian",
                   "aeb", "aeb-arab"}
ALIASES = {
    "english": "en", "anglais": "en",
    "french": "fr", "francais": "fr", "français": "fr",
    "arabic": "ar", "arabe": "ar", "msa": "ar", "ar-tn": "ar",
    "arabizi": "aeb-latn", "aeb_latn": "aeb-latn", "darija-latn": "aeb-latn",
    "franco": "aeb-latn", "aeb-latn": "aeb-latn",
}
ALIASES.update({d: "ar" for d in DIALECT_ALIASES})

VOICE_FILE = os.path.join(os.path.expanduser("~"), ".claude", "instagram", "voice.md")

# Letters: Latin with accents, Arabic with its supplements and presentation
# forms. Harakat (U+064B-U+065F) and tatweel sit inside U+0600-U+06FF.
_LATIN = "A-Za-zÀ-ÖØ-öø-ɏḀ-ỿ"
_ARABIC = "؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"
_ARABIC_LETTERS = re.compile(f"[{_ARABIC}]")
_LATIN_LETTERS = re.compile(f"[{_LATIN}]")
_DIGITS = "0-9٠-٩۰-۹"
# A word may hold an apostrophe or a hyphen inside it, not at its ends.
WORD_RE = re.compile(
    f"[{_LATIN}{_ARABIC}{_DIGITS}$€£%]"
    f"(?:[{_LATIN}{_ARABIC}{_DIGITS}$€£%'’\\-]*[{_LATIN}{_ARABIC}{_DIGITS}$€£%])?")
_ARABIC_PUNCT = set("،؛؟٪٫٬۔")

# Thousands groups: 1 to 3 digits, then groups of exactly 3 after a comma or a
# space (plain, no-break, narrow, thin). "2024 300" and "0612 345 678" are not
# one number, and a dot is left alone on purpose: "18.000" is eighteen in
# Tunisian dinars and eighteen thousand in German.
_SEP = ",    "
_THOUSANDS = re.compile(f"(?<![\\d.,])(?<!\\d[{_SEP}])(\\d{{1,3}})((?:[{_SEP}]\\d{{3}})+)(?![\\d-])")


def setup_stdout():
    """UTF-8 out, whatever the console. Call once at the top of main()."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def decode(data):
    """Bytes -> text: UTF-16 with a BOM (PowerShell 5 `>`), else UTF-8 (BOM dropped)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig", errors="replace")


def read_input(path):
    """A file path, or '-' for stdin, read as text whatever the encoding."""
    if path == "-":
        return decode(sys.stdin.buffer.read())
    with open(path, "rb") as fh:
        return decode(fh.read())


def merge_thousands(text):
    """'18 000' and '18,000' -> '18000', so one spoken number counts once."""
    return _THOUSANDS.sub(lambda m: m.group(1) + re.sub(f"[{_SEP}]", "", m.group(2)), text)


def words(text):
    """Words in any of the four languages. Numbers count as one word each."""
    return [w for w in WORD_RE.findall(merge_thousands(text))
            if any(ch not in _ARABIC_PUNCT for ch in w)]


def arabic_ratio(text):
    a = len(_ARABIC_LETTERS.findall(text))
    l = len(_LATIN_LETTERS.findall(text))
    return a / (a + l) if a + l else 0.0


# --- guessing: a fallback, and a cautious one -----------------------------

_EN = {"the", "and", "is", "you", "your", "to", "of", "it", "that", "for", "this",
       "with", "are", "was", "my", "not", "on", "what", "how", "i", "they", "do",
       "a", "an", "at", "in", "be", "will", "can", "we", "me", "if", "why", "from",
       "just", "about", "have", "has", "don't", "it's", "i'm", "you're", "nobody",
       "never", "every", "before", "after", "when", "here's", "there"}
_FR = {"le", "la", "les", "des", "est", "pas", "une", "du", "et", "que", "qui",
       "pour", "dans", "vous", "je", "tu", "ce", "sur", "avec", "ne", "au", "mais",
       "mon", "ton", "votre", "c'est", "j'ai", "il", "elle", "on", "en", "un",
       "à", "ça", "mes", "tes", "nos", "sont", "fait", "plus", "comme", "quand"}
_AEB = {"fel", "fi", "w", "men", "menhom", "enti", "inti", "bech", "bch", "mte3",
        "mta3", "3la", "3al", "barcha", "kifech", "chnowa", "chnoua", "chnouwa", "chnia",
        "chniya", "ya3ni", "5ater", "khater", "tawa", "taw", "sahbi", "brabi", "3andek",
        "3andi", "nheb", "n7eb", "najem", "najjem", "kif", "famma", "fama", "ena",
        "howa", "heya", "ma3", "m3a", "yesser", "akahaw", "mouch", "mich", "wela",
        "walla", "zeda", "zada", "lel", "bel", "yji", "wa9t", "9a3ed", "chbik", "chbih",
        "chouf", "choufou", "sar", "sayer", "kima", "hedha", "hedhi", "hedheka", "eli",
        "illi", "aslema", "3aslema", "ahla", "nchallah", "inchallah", "lyoum", "ghodwa"}
# Arabizi spells sounds with digits inside words: 3la, n7eb, 9a3ed, tarte7.
# English and French have digit-letter tokens too (3x, 7am, 2nd, b2b, mp3, q4,
# 5k), so a digit token counts only if it is not one of those shapes.
_ARABIZI_TOKEN = re.compile(r"^(?:[2-9][a-z]{2,}[a-z0-9]*|[a-z]+[2-9][a-z]+[a-z0-9]*|[a-z]{3,}[2-9])$")
_NOT_ARABIZI = re.compile(r"^(?:\d+(?:x|k|m|b|am|pm|st|nd|rd|th|h|hr|hrs|min|mins|s|d|w|y|yo|p|fps"
                          r"|gb|mb|eme|ème|e|er|ère)|[a-z]\d[a-z]|[a-z]{1,2}\d+)$")


def _scores(text):
    toks = [t.lower().replace("’", "'") for t in words(text)]
    en = sum(1 for t in toks if t in _EN)
    fr = sum(1 for t in toks if t in _FR) + 0.5 * len(re.findall(r"[àâçéèêëîïôûùüÿœ]", text.lower()))
    aeb_words = sum(1 for t in toks if t in _AEB)
    aeb_digits = sum(1 for t in toks
                     if _ARABIZI_TOKEN.match(t) and not _NOT_ARABIZI.match(t))
    aeb = aeb_words + 1.5 * aeb_digits if (aeb_words or aeb_digits >= 2) else 0.0
    return {"en": float(en), "fr": float(fr), "aeb-latn": aeb,
            "ar": arabic_ratio(text) * max(len(toks), 1)}


def detect(text, among=None):
    """(best, confidence 0-1). Raw guess, used by resolve() under conditions."""
    among = [l for l in (among or LANGS) if l in LANGS] or list(LANGS)
    if arabic_ratio(text) >= 0.5 and "ar" in among:
        return "ar", 0.95
    sc = _scores(text)
    ranked = sorted(among, key=lambda l: -sc[l])
    best = ranked[0]
    total = sum(sc[l] for l in among)
    return best, (round(sc[best] / total, 2) if total else 0.0)


def guess(text, among=None):
    """A language only if the text shows real evidence for it, else None.

    Evidence: two or more marker words for the language, and at least twice
    the score of the runner-up. Arabic script needs half the letters.
    """
    among = [l for l in (among or LANGS) if l in LANGS] or list(LANGS)
    if arabic_ratio(text) >= 0.5:
        return "ar" if "ar" in among else None
    sc = _scores(text)
    ranked = sorted((l for l in among if l != "ar"), key=lambda l: -sc[l])
    if not ranked:
        return None
    best = ranked[0]
    runner = sc[ranked[1]] if len(ranked) > 1 else 0.0
    if sc[best] >= 2 and sc[best] >= 2 * runner:
        return best
    return None


def normalise(code):
    if not code:
        return None
    c = code.strip().strip("`*_[]().,;:").lower()
    if c in LANGS:
        return c
    if c in ALIASES:
        return ALIASES[c]
    base = c.split("-")[0].split("_")[0]
    return base if base in ("en", "fr", "ar") else None


def voice_langs(path=VOICE_FILE, warn=True):
    """Languages declared in voice.md, e.g. `language: fr, en`. [] if none."""
    try:
        with open(path, "rb") as fh:
            body = decode(fh.read())
    except OSError:
        return []
    m = re.search(r"(?im)^\s*[-*]?\s*\**\s*(?:language|languages|langue|langues)\s*"
                  r"(?::\**|\**\s*:)[ \t]*(.*)$", body)
    if not m:
        return []
    value = m.group(1).split("#")[0].strip().strip("`")
    if not value:
        return []
    tokens = re.findall(r"[a-zà-ÿ]+(?:[-_][a-z]+)?", value.lower())
    codes, ar_from_dialect, ar_explicit = [], False, False
    for t in tokens:
        c = normalise(t)
        if not c:
            continue
        if c == "ar":
            if t in DIALECT_ALIASES:
                ar_from_dialect = True
            else:
                ar_explicit = True
        if c not in codes:
            codes.append(c)
    # "Darija (arabizi)" means arabizi, not Arabic script plus arabizi.
    if "aeb-latn" in codes and ar_from_dialect and not ar_explicit:
        codes.remove("ar")
    if not codes and warn:
        print(f"note: voice.md has `language: {value}`, which this pack does not read. "
              "Use en, fr, ar or aeb-latn.", file=sys.stderr)
    return codes


def resolve(text, declared=None, voice_path=VOICE_FILE):
    """(lang, source). lang may be 'und' when nothing was declared and the guess is weak.

    An unknown --lang is an error, not a silent fallback. The script of the text
    settles the one thing a declaration cannot: "Darija" written in Latin
    letters is arabizi, and Arabic letters are Arabic script.
    """
    latin_only = not _ARABIC_LETTERS.search(text) and bool(_LATIN_LETTERS.search(text))

    def by_script(code, source):
        if code == "ar" and latin_only:
            return "aeb-latn", source + " (Latin letters: arabizi)"
        return code, source

    if declared:
        code = normalise(declared)
        if not code:
            raise SystemExit(f"--lang {declared!r} is not a language this pack knows. "
                             "Use en, fr, ar (Arabic script, Darija included) or aeb-latn (arabizi).")
        if declared.strip().lower() in DIALECT_ALIASES:
            return by_script(code, "declared")
        return code, "declared"
    vl = voice_langs(voice_path)
    if vl:
        if arabic_ratio(text) >= 0.5 and "ar" not in vl:
            return "ar", "script (voice.md says " + ", ".join(vl) + ")"
        if len(vl) == 1:
            return by_script(vl[0], "voice.md")
        return by_script(guess(text, among=vl) or vl[0], "voice.md + guessed")
    g = guess(text)
    if g:
        return g, "guessed"
    return UNKNOWN, "not declared, guess too weak"


def add_lang_arg(ap):
    ap.add_argument("--lang", default=None,
                    help="language of the text: en, fr, ar (Arabic script, Darija included) "
                         "or aeb-latn (arabizi). Default: the `language:` line in "
                         "~/.claude/instagram/voice.md, then a cautious guess.")


def calibrated(lang):
    return lang in CALIBRATED


def uncalibrated_note(lang):
    if lang == UNKNOWN:
        return ("Language not declared and not recognised with confidence: no verdict. "
                "Pass --lang en|fr|ar|aeb-latn, or set `language:` in voice.md.")
    return (f"{LANG_NAMES.get(lang, lang)}: these scores are not calibrated for this "
            "language. Read each signal on its own; there is no overall verdict.")


# --- characters that are legitimate --------------------------------------

# French typography: no-break space before ; : ! ? and inside « », thin and
# narrow spaces in numbers, the typographic apostrophe, guillemets.
FR_KEEP = {" ", " ", " ", "’", "«", "»"}
# Arabic script: direction marks, embeddings and isolates, the Arabic letter
# mark, and the joiners that shape letters. Kept whenever the text holds
# Arabic letters, whatever language was declared: a French caption can quote
# a Darija phrase.
BIDI = {"‎", "‏", "؜", "‪", "‫", "‬", "‭", "‮",
        "⁦", "⁧", "⁨", "⁩"}
AR_KEEP = BIDI | {"‌", "‍", " "}
# Phones type ’ by default. English keeps its calibrated behaviour (it is replaced
# there); every other language keeps it.
APOSTROPHE = {"’"}

ZWJ = "‍"
VS16 = "️"
_TAG_LO, _TAG_HI = 0xE0020, 0xE007F
_BLACK_FLAG = 0x1F3F4


def is_emoji(ch):
    cp = ord(ch)
    return (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF
            or 0x2190 <= cp <= 0x21FF or 0x2300 <= cp <= 0x23FF
            or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139))


def _emoji_before(text, i):
    j = i - 1
    while j >= 0 and (text[j] == VS16 or 0x1F3FB <= ord(text[j]) <= 0x1F3FF):
        j -= 1
    return j >= 0 and is_emoji(text[j])


def in_emoji_sequence(text, i):
    """True for a ZWJ inside 👨‍👩‍👧, or a tag char inside a subdivision flag."""
    ch = text[i]
    if ch == ZWJ:
        return _emoji_before(text, i) and i + 1 < len(text) and is_emoji(text[i + 1])
    if _TAG_LO <= ord(ch) <= _TAG_HI:
        j = i - 1
        while j >= 0 and _TAG_LO <= ord(text[j]) <= _TAG_HI:
            j -= 1
        return j >= 0 and ord(text[j]) == _BLACK_FLAG
    return False


def keep_chars(lang):
    if lang == "fr":
        return FR_KEEP
    if lang == "ar":
        return AR_KEEP | APOSTROPHE
    if lang == "en":
        return set()
    return APOSTROPHE


def legitimate(text, i, lang):
    """Is the character at text[i] something a person really types here?"""
    ch = text[i]
    if ch in keep_chars(lang):
        return True
    if ch in AR_KEEP and _ARABIC_LETTERS.search(text):
        return True
    return in_emoji_sequence(text, i)


def machine_invisibles(text, lang):
    """Format (Cf) characters that no keyboard produced for this text."""
    import unicodedata
    return [i for i, c in enumerate(text)
            if unicodedata.category(c) == "Cf" and not legitimate(text, i, lang)]


# --- spans no pass may rewrite ---------------------------------------------

PROTECT_RE = re.compile(
    r"https?://\S+|www\.\S+|\S+@\S+\.\S+"                 # URLs and e-mails
    r"|(?<![\w@#])[@#][^\W][\w.ً-ٰٟ]*"       # @handles, #hashtags
    r"|\b[\w-]+\.(?:com|fr|tn|io|co|net|org|ai|app|ly|me|dev|link|page|shop|store)\b(?:/\S*)?")


def strip_protected(text):
    """Text with URLs, handles, hashtags and domains blanked, for counting."""
    return PROTECT_RE.sub(" ", text)
