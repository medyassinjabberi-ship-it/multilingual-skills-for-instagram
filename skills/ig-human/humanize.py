#!/usr/bin/env python3
"""
humanize.py - strip the machine fingerprint out of a draft.

Three passes, in this order:

  1. INVISIBLE   delete or normalise the characters a keyboard never
                 produces: zero-width spaces, word joiners, soft hyphens,
                 BOMs, Unicode tag characters. What a language really uses is
                 kept: French no-break spaces, Arabic direction marks and
                 joiners, the joiner inside an emoji like 👨‍👩‍👧.
  2. TYPOGRAPHIC em dash -> comma, en dash -> hyphen, curly quotes -> straight,
                 ellipsis -> three dots, bullet -> hyphen. In French the
                 apostrophe ’ and the guillemets « » stay.
  3. LEXICAL     replace the slop lexicon of the text's language
                 (lex/<lang>.json) with plain words, preserving capitalisation
                 and leaving URLs untouched. No lexicon for the language: the
                 pass is skipped and the report says so. The English list is
                 never applied to another language.

Structural tells (rule-of-three, "not just X, it's Y", hashtag walls) are
REPORTED, never auto-rewritten - rewriting a sentence's shape needs judgement,
so that is the model's job, not a regex's.

Usage
  python3 humanize.py draft.txt
  python3 humanize.py draft.txt --lang fr --report
  pbpaste | python3 humanize.py - --report
  python3 humanize.py draft.txt --json
  python3 humanize.py draft.txt -o clean.txt
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

LEX = os.path.join(HERE, "slop.json")
LEX_DIR = os.path.join(HERE, "lex")

# URLs, e-mails, @handles, #hashtags and bare domains: no pass rewrites them.
URL_RE = L.PROTECT_RE
SENT_RE = re.compile(r"[^.!?؟\n]+[.!?؟]*")


def load_lexicon(path=LEX):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_lang_lexicon(lang, lex_dir=LEX_DIR):
    """lex/<lang>.json, or None when nobody wrote one for this language yet."""
    path = os.path.join(lex_dir, f"{lang}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return None


def _cp(spec):
    """'U+200B' -> 0x200b;  'U+E0000-U+E007F' -> (start, end)."""
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a[2:], 16), int(b[2:], 16))
    return int(spec[2:], 16)


def protect_urls(text):
    """Swap URLs for placeholders so no pass rewrites inside a link."""
    found = []

    def stash(m):
        found.append(m.group(0))
        return f"\x00URL{len(found) - 1}\x00"

    return URL_RE.sub(stash, text), found


def restore_urls(text, found):
    for i, url in enumerate(found):
        text = text.replace(f"\x00URL{i}\x00", url)
    return text


def _invisible_table(lex):
    """codepoint -> (label, action), ranges expanded lazily."""
    single, ranges = {}, []
    for entry in lex["invisible"]:
        cp = _cp(entry["cp"])
        label = entry["cp"] + " " + entry["name"]
        if isinstance(cp, tuple):
            ranges.append((cp[0], cp[1], label, entry["action"]))
        else:
            single[cp] = (label, entry["action"])
    return single, ranges


def pass_invisible(text, lex, lang="en"):
    """Delete or space-normalise invisible characters. Returns (text, hits, kept)."""
    single, ranges = _invisible_table(lex)
    counts, kept, out = {}, {}, []
    for i, c in enumerate(text):
        cp = ord(c)
        rule = single.get(cp)
        if rule is None:
            for lo, hi, label, action in ranges:
                if lo <= cp <= hi:
                    rule = (label, action)
                    break
        if rule is None and unicodedata.category(c) == "Cf":
            rule = ("other invisible format chars", "delete")
        if rule is None:
            out.append(c)
            continue
        label, action = rule
        if L.legitimate(text, i, lang):
            kept[label] = kept.get(label, 0) + 1
            out.append(c)
            continue
        counts[(label, action)] = counts.get((label, action), 0) + 1
        out.append("" if action == "delete" else " ")
    hits = [{"name": k[0], "count": n, "action": k[1]} for k, n in counts.items()]
    kept = [{"name": k, "count": n} for k, n in kept.items()]
    return "".join(out), hits, kept


def pass_typographic(text, lex, lang="en"):
    hits = []
    keep = L.keep_chars(lang)
    for entry in lex["typographic"]:
        ch = entry["from"]
        if ch in keep:
            continue
        n = text.count(ch)
        if not n:
            continue
        hits.append({"name": f"{ch} {entry['name']}", "count": n, "to": entry["to"].strip() or "(space)"})
        if ch == "—":
            # A dash opening a line is a dialogue or list mark: drop it, a comma
            # there would be broken text. Elsewhere " word — word " and
            # "word—word" both collapse to a comma + space.
            text = re.sub(r"(?m)^([ \t]*)—[ \t]*", r"\1", text)
            text = re.sub(r"\s*—\s*", ", ", text)
        elif ch == "–":
            text = re.sub(r"\s*–\s*(?=\d)", "-", text)      # 5–10  -> 5-10
            text = re.sub(r"\s+–\s+", ", ", text)            # used as em dash
            text = text.replace("–", "-")
        else:
            text = text.replace(ch, entry["to"])
    # A comma inserted before existing punctuation reads wrong.
    text = re.sub(r",[ \t  ]*([,.;:!?؟])", r"\1", text)
    text = re.sub(r",[ \t]*\n", "\n", text)
    return text, hits


def _match_case(src, repl):
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def _entry_re(find):
    return re.compile(r"(?<!\w)" + re.escape(find).replace(r"\ ", r"\s+") + r"(?!\w)",
                      re.IGNORECASE)


def scan_flagged_words(text, lang_lex):
    """Entries in "mode": "report": stock words a regex cannot replace without
    breaking the sentence (French agreement, elision). Flagged for rewrite."""
    flags = []
    if not lang_lex:
        return flags
    entries = sorted((e for e in lang_lex.get("phrases", []) + lang_lex.get("words", [])
                      if e.get("mode") == "report"), key=lambda e: -len(e["find"]))
    for entry in entries:
        pattern = _entry_re(entry["find"])
        n = len(pattern.findall(text))
        text = pattern.sub(" ", text)     # "de manière optimale" is not also "optimale"
        if n:
            flags.append({"find": entry["find"], "hint": entry.get("hint", ""),
                          "count": n, "family": entry["family"]})
    return flags


def pass_lexical(text, lang_lex, lang="en"):
    """Replace slop words and phrases. Longest first so phrases win."""
    hits = []
    if not lang_lex:
        return text, hits
    entries = sorted((e for e in lang_lex.get("phrases", []) + lang_lex.get("words", [])
                      if e.get("mode", "replace") == "replace"),
                     key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        find = entry["find"]
        pattern = _entry_re(find)
        found = pattern.findall(text)
        if not found:
            continue
        hits.append({"find": find, "replace": entry["replace"] or "(deleted)",
                     "count": len(found), "family": entry["family"]})

        def repl(m, entry=entry):
            # Outside English, a deleted capitalised opener leaves a marker, and
            # only the word right after it gets a capital. Capitalising after
            # every "?" would break French ("Tu viens ? demanda-t-elle").
            if lang != "en" and not entry["replace"] and m.group(0)[:1].isupper():
                return "\x01"
            return _match_case(m.group(0), entry["replace"])
        text = pattern.sub(repl, text)
    if not hits:
        return text, hits
    # Clean up after deletions. Deleting a whole clause leaves orphaned
    # punctuation behind ("system. ." or a line that now opens on a comma),
    # and that reads worse than the slop did.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^[ \t]*(?:[,.;:]+[ \t]*)+", "", text)
    text = re.sub(r"(?m)^[ \t](?=\S)", "", text)       # one space left by a deletion.
                                                      # Deeper indents are deliberate.
    if lang == "fr":
        # French puts a space before ; : ! ? - only commas and full stops hug the word.
        text = re.sub(r"[ \t]+([,.])", r"\1", text)
    else:
        text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r",[ \t  ]*([,.;:!?])", r"\1", text)  # an em dash became a comma,
                                                                   # then the clause after it went
    if lang != "en":
        # A deleted sentence opener ("Fondamentalement, rien...") leaves a marker
        # and a comma: drop both and lift the next word to a capital.
        text = re.sub(r"\x01[\s,;:]*([^\W\d_])", lambda m: m.group(1).upper(), text)
        text = text.replace("\x01", "")
        text = re.sub(r"([.!?…])[ \t  ]*,[ \t]*", r"\1 ", text)
    text = text.replace("...", "\x00ELL\x00")          # protect real ellipses
    text = re.sub(r"\.\s*\.+", ".", text)
    text = re.sub(r"([!?])\s*\.", r"\1", text)
    text = text.replace("\x00ELL\x00", "...")
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if lang == "en":
        # An em dash that became a comma, followed by a sentence connective, leaves
        # a splice ("is important, also, it's proof"). Promote it to a full stop.
        text = re.sub(r",\s*(also|so|still|basically|in the end)\s*,\s*",
                      lambda m: ". " + m.group(1)[0].upper() + m.group(1)[1:] + ", ", text)
    return text, hits


def scan_structures(text, lex, lang_lex=None):
    flags = []
    for s in lex.get("structures", []) + ((lang_lex or {}).get("structures", [])):
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error:
            continue
        found = pattern.findall(text)
        if found:
            flags.append({"name": s["name"], "count": len(found), "fix": s["fix"]})
    # Sentence-length uniformity is structural too, in any language.
    lens = [len(s.split()) for s in SENT_RE.findall(text) if len(s.split()) > 2]
    if len(lens) >= 4:
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        if cv < 0.35:
            flags.append({
                "name": f"Uniform sentence length (variation {cv:.2f})",
                "count": len(lens),
                "fix": "Break one sentence in half. Let another run long. Machines write even.",
            })
    return flags


def restore_capitals(original, text):
    """Deleting an opener leaves the next word lower case.

    Only fix it for writers who capitalise their sentences in the first place:
    a deliberately lower-case voice is a style, not an artefact, and shouting
    over it would be exactly the kind of thing this script exists to stop.
    Scripts without case (Arabic) are left alone by construction.
    """
    starts = re.findall(r"(?:^|[.!?]\s+|\n)\s*([^\W\d_])", original)
    starts = [c for c in starts if c.upper() != c.lower()]
    if not starts or sum(1 for c in starts if c.isupper()) * 2 < len(starts):
        return text
    return re.sub(r"(?:^|(?<=[.!?] )|(?<=[.!?]\n)|(?<=\n))\s*([^\W\d_])",
                  lambda m: m.group(0)[:-1] + m.group(1).upper(), text)


def humanize(text, lex, lang="en", lang_lex=None):
    raw_for_case = text
    text, urls = protect_urls(text)
    text, inv, kept = pass_invisible(text, lex, lang)
    text, typo = pass_typographic(text, lex, lang)
    text, lexi = pass_lexical(text, lang_lex, lang)
    flagged = scan_flagged_words(text, lang_lex)
    if lang == "en":                      # English: calibrated behaviour, always.
        text = restore_capitals(raw_for_case, text)   # Elsewhere pass_lexical does it
                                                      # at the deletion point only.
    text = restore_urls(text, urls)
    return text.strip() + "\n", {
        "lang": lang,
        "lexicon": (f"lex/{lang}.json" if lang_lex else "not available for this language"),
        "invisible": inv,
        "kept": kept,
        "typographic": typo,
        "lexical": lexi,
        "flagged_words": flagged,
        "structures": scan_structures(text, lex, lang_lex),
    }


def render_report(report, out=sys.stderr, source="declared"):
    def head(title):
        print(f"\n{title}\n" + "-" * len(title), file=out)

    total = sum(h["count"] for h in report["invisible"]) \
        + sum(h["count"] for h in report["typographic"]) \
        + sum(h["count"] for h in report["lexical"])

    head("HUMANIZE REPORT")
    print(f"language: {L.LANG_NAMES.get(report['lang'], report['lang'])} ({source}), "
          f"lexicon: {report['lexicon']}", file=out)
    print(f"{total} machine artefacts removed, "
          f"{len(report['structures'])} structural tells flagged for rewrite", file=out)

    if report["invisible"]:
        head("1. INVISIBLE CHARACTERS")
        for h in report["invisible"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['action']}", file=out)
    if report["kept"]:
        head("   KEPT (this language or an emoji uses them)")
        for h in report["kept"]:
            print(f"  {h['count']:>3}x  {h['name']}", file=out)
    if report["typographic"]:
        head("2. TYPOGRAPHY")
        for h in report["typographic"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['to']}", file=out)
    if report["lexical"]:
        head("3. SLOP LEXICON")
        for h in report["lexical"]:
            print(f"  {h['count']:>3}x  {h['find']}  -> {h['replace']}   [{h['family']}]", file=out)
    elif report["lexicon"].startswith("not available"):
        head("3. SLOP LEXICON")
        print("  No word list for this language yet, so no word was changed. "
              "Read the draft for stock phrases yourself.", file=out)
    if report.get("flagged_words"):
        head("3b. STOCK WORDS  (not auto-fixed: the grammar around them needs a person)")
        for h in report["flagged_words"]:
            print(f"  {h['count']:>3}x  {h['find']}  -> {h['hint']}   [{h['family']}]", file=out)
    if report["structures"]:
        head("4. STRUCTURAL TELLS  (not auto-fixed - rewrite these yourself)")
        for h in report["structures"]:
            print(f"  {h['count']:>3}x  {h['name']}\n        {h['fix']}", file=out)
    if not (report["invisible"] or report["typographic"] or report["lexical"]
            or report.get("flagged_words") or report["structures"]):
        head("CLEAN")
        print("  Nothing to strip.", file=out)
    print("", file=out)


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Strip the machine fingerprint out of a draft.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("-o", "--out", help="write cleaned text here instead of stdout")
    ap.add_argument("--report", action="store_true", help="print what changed, to stderr")
    ap.add_argument("--json", action="store_true", help="emit {text, report} as JSON")
    ap.add_argument("--lexicon", default=LEX, help="path to slop.json (shared part)")
    ap.add_argument("--lex-dir", default=LEX_DIR, help="folder holding <lang>.json word lists")
    L.add_lang_arg(ap)
    args = ap.parse_args()

    raw = L.read_input(args.input)
    lang, source = L.resolve(raw, args.lang)
    lex = load_lexicon(args.lexicon)
    lang_lex = load_lang_lexicon(lang, args.lex_dir)
    clean, report = humanize(raw, lex, lang, lang_lex)
    report["lang_source"] = source

    if args.json:
        print(json.dumps({"text": clean, "report": report}, indent=2, ensure_ascii=False))
        return
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(clean)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(clean)
    if args.report:
        render_report(report, source=source)


if __name__ == "__main__":
    main()
