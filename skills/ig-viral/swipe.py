#!/usr/bin/env python3
"""
swipe.py - rank reels you collected by how far they beat their own account,
name the hook formula each one used, and write the swipe file.

The point of this script is one correction: raw views are not evidence. A
2,000,000-follower account doing 400,000 views had a quiet day. A 4,000-
follower account doing 400,000 views found something. This ranks on the
multiple over the account's own baseline, which is the only version of
"went viral" that tells you anything you can copy.

Input is a tab-separated file you fill in while you browse, one reel per row,
with a header line naming the columns:

    account   followers   median   views    hook
    @someone  48000       11000    412000   nobody tells you your first 30 flop

`median` is that account's typical recent views and is the better baseline.
If you only have `followers`, leave median out and the script says so.
`hook` is the first line of the reel, spoken or on screen, in their words.
An optional `formula` column (an id from ig-reel/hooks.json, "#3", or a name)
is the formula Claude named by reading the hook. It wins over the English
patterns, which is what makes a French or Darija batch rankable by formula.

Usage
  python3 swipe.py captured.tsv
  python3 swipe.py captured.tsv --out ~/.claude/instagram/swipe.md
  python3 swipe.py captured.tsv --json
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

HOOKS = os.path.join(HERE, "..", "ig-reel", "hooks.json")

try:                                              # optional: score the hooks too
    sys.path.insert(1, os.path.join(HERE, "..", "ig-reel"))
    from hookscore import run as score_hook       # noqa: E402
except Exception:                                 # ig-viral copied on its own
    score_hook = None


def load_formulas(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    by_id = {h["id"]: h for h in d["hooks"]}
    order = d.get("classify_order") or sorted(by_id)
    return [(by_id[i]["id"], by_id[i]["name"],
             re.compile(by_id[i]["match"], re.IGNORECASE)) for i in order if i in by_id]


MIN_CLAIM = 15        # reels needed before saying what over-indexes
DOMINANT = 0.5        # one account holding this share of the top third


_ID = re.compile(r"^(?:#|formula\s*|formule\s*|n°\s*)?0*(\d{1,3})\.?$", re.IGNORECASE)


def named(given, formulas):
    """A formula the user or Claude wrote in the `formula` column -> (id, name).
    '#03', '3.', 'formula 3', 'nobody tells you' all work. Unknown -> None."""
    g = (given or "").strip()
    if not g or not formulas:
        return None
    m = _ID.match(g)
    for fid, name, _ in formulas:
        if (m and m.group(1) == str(fid)) or " ".join(g.lower().split()) == name.lower():
            return fid, name
    return None


def classify(hook, formulas, lang="en"):
    if not formulas:
        return None, "unclassified"
    if lang != "en":
        # The 26 formula patterns are English phrasings. Claude names the
        # formula of a French or Darija hook by reading it (SKILL.md).
        return None, "to classify by reading"
    for fid, name, pattern in formulas:
        if pattern.search(hook):
            return fid, name
    return None, "unclassified"


def parse_count(cell):
    """'412000', '412 000', '412,000', '20k', '1.2M', '1,2 M', '3,4K' -> int. None if unreadable.

    Instagram shows views as 20k and 1.2M, so that is what people paste.
    """
    c = (cell or "").strip().lower().replace(" ", " ").replace(" ", " ")
    if not c:
        return None
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([km]|mn|m\.|k\.)?", c.replace(" ", "")
                     if re.search(r"[km]", c) else c)
    if m and m.group(2):
        num = float(m.group(1).replace(",", "."))
        mult = 1000 if m.group(2).startswith("k") else 1_000_000
        return int(round(num * mult))
    digits = re.sub(r"[ ,.]", "", c)
    return int(digits) if digits.isdigit() else None


def read_rows(path):
    if path == "-":
        sys.stdin.reconfigure(encoding="utf-8")
        raw = sys.stdin.read()
    else:
        raw = open(path, encoding="utf-8").read()
    lines = [l for l in raw.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return []
    head = [c.strip().lower() for c in lines[0].split("\t")]
    if "views" in head and "hook" in head:
        cols, body = head, lines[1:]
    else:
        cols, body = ["account", "followers", "views", "hook"], lines
    rows = []
    for line in body:
        cells = line.split("\t")
        if len(cells) < len(cols):
            cells += [""] * (len(cols) - len(cells))
        r = dict(zip(cols, [c.strip() for c in cells]))
        views = parse_count(r.get("views", ""))
        if views is None:
            print(f"skipped row, unreadable views {r.get('views', '')!r}: {line[:60]}",
                  file=sys.stderr)
            continue
        r["views"] = views
        for k in ("followers", "median"):
            r[k] = parse_count(r.get(k, "") or "")
        if r["views"] and r.get("hook"):
            rows.append(r)
    return rows


def analyse(rows, formulas, declared=None):
    used_median = any(r.get("median") for r in rows)
    # One language for the batch (--lang, voice.md, or a guess on all hooks
    # together), overridden per row only by clear evidence: a `lang` column,
    # Arabic script, or a confident guess on that row.
    batch, _ = L.resolve("\n".join(r["hook"] for r in rows), declared)
    for r in rows:
        if r.get("lang"):
            r["lang"], _ = L.resolve(r["hook"], r["lang"])
        else:
            r["lang"] = L.guess(r["hook"]) or batch
        base = r.get("median") or r.get("followers") or 0
        r["baseline"] = base
        r["outlier"] = round(r["views"] / base, 2) if base else None
        given = named(r.get("formula"), formulas)
        if r.get("formula") and not given:
            print(f"note: formula {r['formula']!r} is not in hooks.json, ignored for "
                  f"{r.get('account', '')} \"{r['hook'][:40]}\"", file=sys.stderr)
        if given:
            (r["formula_id"], r["formula"]), r["formula_source"] = given, "read"
        else:
            r["formula_id"], r["formula"] = classify(r["hook"], formulas, r["lang"])
            r["formula_source"] = "matched" if r["formula_id"] else None
        r["words"] = (len(re.findall(r"[A-Za-z0-9$%'’-]+", r["hook"])) if r["lang"] == "en"
                      else len(L.words(r["hook"])))
        if score_hook and r["lang"] == "en":
            _, overall, verdict, _ = score_hook(r["hook"], r["lang"])
            r["hook_score"], r["hook_verdict"] = round(overall, 1), verdict
        elif score_hook:
            # No calibrated score outside English: n/c, never a number to relay.
            r["hook_score"], r["hook_verdict"] = None, "n/c"
        else:
            r["hook_score"], r["hook_verdict"] = None, None
    ranked = sorted(rows, key=lambda r: -(r["outlier"] or 0))
    third = max(1, len(ranked) // 3)
    top, bottom = ranked[:third], ranked[-third:]

    def med(items, key):
        vals = [i[key] for i in items if i.get(key) is not None]
        return round(statistics.median(vals), 1) if vals else None

    counts, bottom_counts = {}, {}
    for r in top:
        counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    for r in bottom:
        bottom_counts[r["formula"]] = bottom_counts.get(r["formula"], 0) + 1
    by_account = {}
    for r in top:
        by_account[r.get("account", "")] = by_account.get(r.get("account", ""), 0) + 1
    lead = max(by_account.items(), key=lambda kv: kv[1]) if by_account else ("", 0)
    return {
        "baseline": "account median" if used_median else "follower count",
        "n": len(ranked),
        "accounts": len({r.get("account", "") for r in ranked}),
        "reels": ranked,
        "top_formulas": sorted(counts.items(), key=lambda kv: -kv[1]),
        "top_hook_score": med(top, "hook_score"),
        "bottom_hook_score": med(bottom, "hook_score"),
        "top_words": med(top, "words"),
        "bottom_words": med(bottom, "words"),
        "unclassified": sum(1 for r in ranked if r["formula"] == "unclassified"),
        "to_read": sum(1 for r in ranked if r["formula"] == "to classify by reading"),
        "langs": sorted({r["lang"] for r in ranked}),
        "bottom_formulas": bottom_counts,
        "read": sum(1 for r in ranked if r.get("formula_source") == "read"),
        "dominant": (lead[0] if len(top) >= 3 and lead[1] / len(top) >= DOMINANT else None),
        "dominant_share": (lead[1], len(top)),
    }


def render(a, out=sys.stdout):
    head = (f"SWIPE FILE  ·  {a['n']} reels  ·  {a['accounts']} accounts  ·  "
            f"baseline: {a['baseline']}")
    print("\n" + head, file=out)
    print("=" * max(len(head), 78), file=out)
    for r in a["reels"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] else "   ?"
        score = (f"{r['hook_score']:.0f}" if r["hook_score"] is not None
                 else ("n/c" if r.get("hook_verdict") == "n/c" else " -"))
        fid = f"#{r['formula_id']:<2}" if r["formula_id"] else "-  "
        print(f"  {mult:>7}  hook {score:>3}  {fid} {r['formula'][:22]:<22} "
              f"{r.get('account', '')[:16]:<16} {r['views']:>9,}", file=out)
        print(f"           \"{r['hook'][:96]}\"", file=out)
    print("-" * max(len(head), 78), file=out)
    print("WHAT IS WORKING IN THIS BATCH", file=out)
    claims = [(n, c) for n, c in a["top_formulas"]
              if c >= 2 and n not in ("unclassified", "to classify by reading")]
    if a["n"] < MIN_CLAIM:
        print(f"  over-indexing:         not said. {a['n']} reels; below {MIN_CLAIM} a count in the top "
              "third is chance.", file=out)
    elif claims:
        print("  top third by outlier:  "
              + ", ".join(f"{n} x{c} (bottom x{a['bottom_formulas'].get(n, 0)})" for n, c in claims[:4]),
              file=out)
    else:
        print("  top third by outlier:  no formula appears twice. Nothing over-indexes yet.", file=out)
    if a["dominant"]:
        k, t = a["dominant_share"]
        print(f"  one account dominates: {a['dominant']} holds {k} of the top {t}. That may be the "
              "account, not the formula.", file=out)
    if a["read"]:
        print(f"  formulas read:         {a['read']} named by reading (formula column), "
              "not matched by pattern.", file=out)
    if a["top_hook_score"] is not None and a["bottom_hook_score"] is not None:
        print(f"  median hook score:     top {a['top_hook_score']:.0f}  "
              f"vs bottom {a['bottom_hook_score']:.0f}  (English hooks only)", file=out)
    print(f"  median hook length:    top {a['top_words']} words  "
          f"vs bottom {a['bottom_words']} words", file=out)
    if a["unclassified"]:
        print(f"  unclassified:          {a['unclassified']} of {a['n']}. Read those by hand, "
              "they are where a formula you do not have yet is hiding.", file=out)
    if a["to_read"]:
        print(f"  not English:           {a['to_read']} of {a['n']}. The formula patterns are "
              "English: name these by reading them.\n"
              "                         Their hook score is n/c (not calibrated): judge them "
              "with the grid in ig-reel/SKILL.md.", file=out)
    print("\n  A hand-collected batch is evidence, not proof. Twelve reels shows you "
          "nothing;\n  forty across six accounts shows you something. Collect more before "
          "you believe it.\n", file=out)


def to_markdown(a):
    lines = ["# Swipe file", "",
             f"{a['n']} reels across {a['accounts']} accounts. "
             f"Ranked by multiple over {a['baseline']}.", ""]
    for r in a["reels"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] else "?"
        lines += [f"## {mult}  {r['formula']}  ({r.get('account', '')})",
                  f"- views: {r['views']:,}  baseline: {r['baseline']:,}",
                  f"- hook score: {r['hook_score']}  words: {r['words']}",
                  f"- hook: \"{r['hook']}\"", ""]
    return "\n".join(lines) + "\n"


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Rank collected reels by outlier multiple.")
    ap.add_argument("input", nargs="?", default="-", help="TSV file, or - for stdin")
    ap.add_argument("--hooks", default=HOOKS, help="path to ig-reel/hooks.json")
    ap.add_argument("--out", help="also write the swipe file as markdown here")
    ap.add_argument("--json", action="store_true")
    L.add_lang_arg(ap)
    args = ap.parse_args()

    rows = read_rows(args.input)
    if not rows:
        print("no usable rows. Need a tab-separated file with at least views and hook.",
              file=sys.stderr)
        sys.exit(2)
    formulas = load_formulas(args.hooks)
    a = analyse(rows, formulas, args.lang)
    if not formulas:
        print("note: hooks.json not found, formulas not named. Pass --hooks.", file=sys.stderr)
    if score_hook is None:
        print("note: hookscore.py not importable, hook scores skipped.", file=sys.stderr)

    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    if args.out:
        path = os.path.expanduser(args.out)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(to_markdown(a))
        print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
