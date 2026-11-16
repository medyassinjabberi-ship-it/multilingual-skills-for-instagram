#!/usr/bin/env python3
"""
audit.py - what actually worked on this account, computed, not eyeballed.

Reads a table of the user's own posts (one row per post, a header row, tab,
comma or semicolon separated) and prints:

  - each post's outlier multiple: its views divided by the median of the
    previous 10 posts OF THE SAME FORMAT (at least 5, or "no baseline"). A
    trailing median, so an account that grew is not flattered by its old posts;
    per format, so a carousel is not judged against reels;
  - shares, saves, follows and comments per 1,000 reached;
  - from 10 comparable posts: top five and bottom five, the hook-or-profile
    diagnosis, and three families of comparisons fixed in advance (format, reel
    length, hook formula), each group needing 5 posts or more, worded by how
    strong the difference is. Day of week and hour only with --when;
  - from 30 posts, a description by thirds of hook length and whether the hook
    has a number;
  - which journal entries (journal.jsonl) match which posts, and which do not.

What it will not do: guess a column it does not have, read a date or a number
it cannot parse (the row is named and left out), compare posts younger than
--min-age days with mature ones, print a p-value, or say "because". With 20 to
60 posts, the honest output is often "nothing you can rely on", and it says so.

Columns are matched by name, in English or French, case and accents ignored:
  date, format, views, reach, likes, comments, saves, shares, follows,
  hold3s, nonfollower, length, permalink, hook, formula
Only `views` (or `reach`) is required. "Impressions" is never read as views.
Fix a header it does not know with --map "views=Plays,reach=Accounts reached".
Dates: 2026-11-16, 2026-11-16 18:30, 16/11/2026, 11/16/2026, 16/11/26 (the
column is read as day-first or month-first as a whole; if it cannot tell, it
asks). Hours are taken as written in the file; a timezone suffix is ignored.

Usage
  python3 audit.py posts.tsv
  python3 audit.py posts.csv --map "views=Plays" --out ~/.claude/instagram/insights.md
  python3 audit.py posts.tsv --when             # also compare day of week and hour
  python3 audit.py posts.tsv --json
"""

import argparse
import csv
import datetime as dt
import io
import json
import math
import os
import random
import re
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402
import journal as J  # noqa: E402

WINDOW = 10          # previous posts of the same format in the baseline
MIN_BASE = 5         # fewer earlier posts than this: no baseline
MIN_GROUP = 5        # a group smaller than this is never compared
MIN_AGE = 7          # days before a post's numbers are treated as settled
TERCILE_N = 30       # posts needed before describing anything by thirds
FEW = 10             # below this many comparable posts, no ranking and no comparison

ALIASES = {
    "date": ["date", "publish time", "published", "posted", "date de publication",
             "heure de publication", "publication date", "publie le"],
    "format": ["format", "post type", "type", "type de publication", "media type", "type de contenu"],
    "views": ["views", "vues", "plays", "lectures", "video views", "vues de la video"],
    "reach": ["reach", "accounts reached", "couverture", "portee", "comptes touches",
              "comptes atteints", "comptes couverts"],
    "likes": ["likes", "j aime", "mentions j aime"],
    "comments": ["comments", "commentaires"],
    "saves": ["saves", "saved", "enregistrements", "sauvegardes"],
    "shares": ["shares", "sends", "partages", "envois"],
    "follows": ["follows", "new follows", "nouveaux abonnes", "abonnements", "abonnes gagnes"],
    "hold3s": ["hold3s", "hold 3s", "hold at 3s", "3s hold", "retention 3s", "retention a 3s",
               "maintien 3s", "hold"],
    "nonfollower": ["nonfollower", "non follower", "non followers", "non follower reach",
                    "reach non followers", "non abonnes", "part non abonnes", "non follower share"],
    "length": ["length", "duration", "duration sec", "duration s", "duree", "duree s",
               "duree sec", "seconds", "secondes"],
    "permalink": ["permalink", "link", "url", "lien", "lien permanent"],
    "hook": ["hook", "caption", "description", "legende", "first line", "accroche"],
    "formula": ["formula", "formule"],
}
NEVER = {"impressions": "views", "affichages": "views", "impressions totales": "views"}
NUMERIC = ("views", "reach", "likes", "comments", "saves", "shares", "follows")
PERCENT = ("hold3s", "nonfollower")
# A format cell is read by what it contains: "Reel IG", "Reels vidéo" -> reel.
FORMAT_WORDS = (("carousel", ("carousel", "carrousel", "album")),
                ("story", ("story", "stories")),
                ("reel", ("reel", "video", "clip")),
                ("photo", ("photo", "image", "picture")),
                ("post", ("publication", "post")))
LENGTH_BUCKETS = ((0, 15, "under 15s"), (15, 30, "15-30s"), (30, 60, "30-60s"), (60, 10 ** 6, "over 60s"))
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
HOURS = ((5, 11, "morning 5-11h"), (11, 15, "midday 11-15h"), (15, 19, "afternoon 15-19h"),
         (19, 23, "evening 19-23h"), (23, 29, "night 23-5h"))


class AuditError(Exception):
    pass


# ---------------------------------------------------------------- reading

def norm(header):
    s = unicodedata.normalize("NFKD", header or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\([^)]*\)", lambda m: " " + m.group(0)[1:-1] + " ", s)
    return re.sub(r"[^a-z0-9%@]+", " ", s).replace("%", "").strip()


def map_columns(headers, overrides=None):
    """canonical name -> header. Raises on two headers claiming one field."""
    overrides = overrides or {}
    lookup = {norm(h): h for h in headers}
    mapping, notes = {}, []
    for field, header in overrides.items():
        if field not in ALIASES:
            raise AuditError(f"--map: unknown field {field!r} (fields: {', '.join(ALIASES)})")
        match = [h for h in headers if h.strip().lower() == header.strip().lower()]
        if not match:
            raise AuditError(f"--map: no column named {header!r}")
        mapping[field] = match[0]
    for field, names in ALIASES.items():
        if field in mapping:
            continue
        hits = [lookup[n] for n in names if n in lookup and lookup[n] not in mapping.values()]
        if len(hits) > 1:
            raise AuditError(f"two columns could be {field}: {hits}. Pick one with --map \"{field}=...\"")
        if hits:
            mapping[field] = hits[0]
    for h in headers:
        if norm(h) in NEVER and h not in mapping.values():
            notes.append(f"'{h}' is not read as views: impressions count repeat showings. "
                         f"Use --map \"views={h}\" only if you are sure.")
    if "views" not in mapping and "reach" not in mapping:
        raise AuditError("no views or reach column. Name one 'views' or pass --map \"views=<header>\". "
                         f"Columns seen: {headers}")
    return mapping, notes


def parse_count(cell):
    """'412000', '412 000', '412,000', '20k', '1.2M', '1,2 M' -> int. Empty or unreadable -> None."""
    if cell is None:
        return None
    s = str(cell).strip().lower().replace(" ", " ").replace(" ", " ")
    if s in ("", "-", "n/a", "na", "--"):
        return None
    s = re.sub(r"\s*(vues|views|plays|lectures|vue|view)$", "", s)     # "1470 vues"
    m = re.match(r"^([\d.,\s]+)\s*([km]?)$", s)
    if not m:
        return None
    num, unit = m.group(1).replace(" ", ""), m.group(2)
    if unit:
        num = num.replace(",", ".")
        try:
            return int(round(float(num) * (1000 if unit == "k" else 1_000_000)))
        except ValueError:
            return None
    if re.match(r"^\d{1,3}([.,]\d{3})+$", num):
        return int(re.sub(r"[.,]", "", num))
    try:
        return float(num.replace(",", ".")) if re.search(r"[.,]", num) else int(num)
    except ValueError:
        return None


def parse_length(cell):
    """'28', '28s', '28,5', '0:28', '1:05' -> seconds."""
    if cell is None or not str(cell).strip():
        return None
    s = str(cell).strip().lower().rstrip("s").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return parse_count(s)


def parse_percents(cells):
    """A whole column at once: if any cell has % or is above 1, every bare number is a
    percent ('1' = 1%); otherwise they are fractions ('0.45' = 45%)."""
    raw = []
    for c in cells:
        s = (c or "").strip().replace(",", ".").replace(" ", "").replace(" ", "")
        try:
            raw.append((float(s.rstrip("%")), s.endswith("%")) if s else None)
        except ValueError:
            raw.append(None)
    as_percent = any(r and (r[1] or r[0] > 1) for r in raw)
    return [None if r is None else (r[0] / 100 if as_percent else r[0]) for r in raw]


def parse_percent(cell):
    return parse_percents([cell])[0]


_DATE_PATTERNS = (
    re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}):(\d{2}))?"),
    re.compile(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4}|\d{2})(?![\d])(?:,?\s+(\d{1,2}):(\d{2}))?"),
)


def parse_dates(cells):
    """Parse a whole column at once, so 03/04 is read the same way in every row.
    An unreadable cell comes back as None; the caller names the row."""
    raw = []
    for c in cells:
        c = (c or "").strip()
        m = _DATE_PATTERNS[0].match(c)
        if m:
            y, mo, d, hh, mm = m.groups()
            raw.append(("iso", int(y), int(mo), int(d), hh, mm))
            continue
        m = _DATE_PATTERNS[1].match(c)
        if m:
            a, b, y, hh, mm = m.groups()
            y = int(y) + (2000 if len(y) == 2 else 0)
            raw.append(("ab", int(a), int(b), y, hh, mm))
        else:
            raw.append(None)
    ab = [r for r in raw if r and r[0] == "ab"]
    dayfirst = None
    if ab:
        if any(r[1] > 12 for r in ab):
            dayfirst = True
        if any(r[2] > 12 for r in ab):
            if dayfirst:
                raise AuditError("the date column mixes day-first and month-first dates")
            dayfirst = False
        if dayfirst is None:
            raise AuditError("cannot tell if dates are day/month or month/day (every day is 12 or less). "
                             "Rewrite them as YYYY-MM-DD.")
    out = []
    for r in raw:
        if r is None:
            out.append(None)
            continue
        if r[0] == "iso":
            _, y, mo, d, hh, mm = r
        else:
            _, a, b, y, hh, mm = r
            d, mo = (a, b) if dayfirst else (b, a)
        try:
            out.append((dt.datetime(y, mo, d, int(hh or 0), int(mm or 0)), hh is not None))
        except ValueError:
            out.append(None)
    return out


def norm_format(cell):
    s = norm(cell or "")
    if not s:
        return None
    for fmt, words in FORMAT_WORDS:
        if any(w in s for w in words):
            return fmt
    return s


def read_table(text, overrides=None):
    text = text.lstrip("﻿").lstrip("\r\n \t")
    first = text.splitlines()[0] if text.strip() else ""
    if not first:
        raise AuditError("empty input")
    delim = "\t" if "\t" in first else (";" if first.count(";") > first.count(",") else ",")
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    headers = [h.strip() for h in rows[0]]
    body = [r for r in rows[1:] if any(c.strip() for c in r)]
    mapping, notes = map_columns(headers, overrides)
    if "date" not in mapping:
        # A column whose cells are dates is the date, whatever its header ("Publication").
        for h in headers:
            if h in mapping.values():
                continue
            col = [r[headers.index(h)] if headers.index(h) < len(r) else "" for r in body]
            try:
                parsed = parse_dates(col)
            except AuditError:
                continue
            if col and sum(1 for d in parsed if d) >= 0.8 * len(col):
                mapping["date"] = h
                notes.append(f"'{h}' read as the date: its cells are dates")
                break
    idx = {f: headers.index(h) for f, h in mapping.items()}

    def cell(r, f):
        i = idx.get(f)
        return r[i].strip() if i is not None and i < len(r) else None

    dates = parse_dates([cell(r, "date") for r in body]) if "date" in idx else [None] * len(body)
    percents = {f: parse_percents([cell(r, f) for r in body]) if f in idx else [None] * len(body)
                for f in PERCENT}
    posts, dropped, odd_formats = [], [], set()
    for n, r in enumerate(body, 1):
        p = {"row": n + 1}                       # the line number in the file (header is line 1)
        for f in NUMERIC:
            p[f] = parse_count(cell(r, f)) if f in idx else None
        p["length"] = parse_length(cell(r, "length")) if "length" in idx else None
        for f in PERCENT:
            p[f] = percents[f][n - 1]
        raw_fmt = cell(r, "format") if "format" in idx else None
        p["format"] = norm_format(raw_fmt) if "format" in idx else "post"
        if raw_fmt and p["format"] not in ("reel", "carousel", "photo", "story"):
            odd_formats.add((raw_fmt, p["format"]))
        d = dates[n - 1]
        p["date"], p["has_time"] = (d if d else (None, False))
        for f in ("permalink", "hook"):
            p[f] = cell(r, f) or None
        p["formula"] = J.norm_formula(cell(r, "formula")) if "formula" in idx else None
        p["formula_source"] = "table" if p["formula"] else None
        metric = "views" if "views" in idx else "reach"
        if "date" in idx and p["date"] is None:
            dropped.append(f"line {p['row']}: date {cell(r, 'date')!r} not read, row left out")
            continue
        if p[metric] is None:
            dropped.append(f"line {p['row']}: {metric} {cell(r, metric)!r} not read, row left out")
            continue
        posts.append(p)
    for raw_fmt, fmt in sorted(odd_formats):
        notes.append(f"format '{raw_fmt}' read as '{fmt}'" + (" (a generic post: could be a photo or a carousel)"
                                                              if fmt == "post" else ""))
    return posts, mapping, notes + dropped


# ---------------------------------------------------------------- computing

def median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def per_k(n, base):
    return None if n is None or not base else 1000.0 * n / base


def baselines(posts, metric):
    dated = bool(posts) and all(p["date"] for p in posts)
    for p in posts:
        p["multiple"] = p["multiple_all"] = p["baseline"] = None
        p["why"] = None
    order = sorted(posts, key=lambda p: p["date"]) if dated else list(posts)
    for i, p in enumerate(order):
        if dated:
            same = [q[metric] for q in order[:i] if q["format"] == p["format"]][-WINDOW:]
            alls = [q[metric] for q in order[:i]][-WINDOW:]
        else:
            same = [q[metric] for q in order if q is not p and q["format"] == p["format"]]
            alls = [q[metric] for q in order if q is not p]
        if len(same) < MIN_BASE:
            p["why"] = f"fewer than {MIN_BASE} earlier posts of this format"
        elif not median(same):
            p["why"] = "the baseline median is 0"
        else:
            p["baseline"] = median(same)
            p["multiple"] = p[metric] / p["baseline"]
        if len(alls) >= MIN_BASE and median(alls):
            p["multiple_all"] = p[metric] / median(alls)
    return dated


def compare(label, group, rest, key="multiple"):
    g = [p[key] for p in group if p[key] is not None]
    r = [p[key] for p in rest if p[key] is not None]
    if len(g) < MIN_GROUP or len(r) < MIN_GROUP:
        return None
    mg, mr = median(g), median(r)
    if not mr:
        return None
    return {"label": label, "n": len(g), "n_rest": len(r), "median": mg, "median_rest": mr,
            "ratio": mg / mr, "above": sum(1 for x in g if x > mr), "p": permutation_p(g, r)}


def permutation_p(g, r, rounds=2000):
    """How often a random split of the same posts gives a gap this big in the mean of
    log multiples (logs, so one 40x post does not decide it). Seeded, so the same
    table always prints the same words. Only used to pick the wording; never printed."""
    rng = random.Random(1729)
    lg, lr = [math.log(max(x, 1e-6)) for x in g], [math.log(max(x, 1e-6)) for x in r]
    observed = abs(statistics.fmean(lg) - statistics.fmean(lr))
    pool, k, hits = lg + lr, len(lg), 0
    for _ in range(rounds):
        rng.shuffle(pool)
        if abs(statistics.fmean(pool[:k]) - statistics.fmean(pool[k:])) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (rounds + 1)


def tier(c, k):
    """Three wordings. The bar for 'clear' rises with the number of comparisons run."""
    big = c["ratio"] >= 1.5 or c["ratio"] <= 2 / 3
    if big and c["p"] < 0.05 / max(k, 1) and min(c["n"], c["n_rest"]) >= 8:
        return "clear"
    if big and c["p"] < min(0.05, 0.25 / max(k, 1)):
        return "worth testing"
    return "no difference you can rely on"


def bucket(value, buckets):
    for lo, hi, name in buckets:
        if value is not None and lo <= value < hi:
            return name
    return None


def one_vs_rest(labels, pick, pool, key="multiple", name=lambda x: x):
    """Each label against the rest. With exactly two labels, A vs B and B vs A are the
    same comparison: run it once, for the smaller group."""
    labels = sorted(labels, key=lambda x: sum(1 for p in pool if pick(p) == x))
    if len(labels) < 2:
        return []
    out = []
    for lab in (labels[:1] if len(labels) == 2 else labels):
        c = compare(name(lab), [p for p in pool if pick(p) == lab], [p for p in pool if pick(p) != lab], key)
        if c:
            out.append(c)
    return out


def comparisons(pool, when=False):
    out = {"format": [], "length": [], "formula": [], "when": []}
    out["format"] = one_vs_rest({p["format"] for p in pool if p["format"]}, lambda p: p["format"],
                                pool, key="multiple_all")
    timed = [p for p in pool if p["length"] is not None]
    out["length"] = one_vs_rest({bucket(p["length"], LENGTH_BUCKETS) for p in timed},
                                lambda p: bucket(p["length"], LENGTH_BUCKETS), timed)
    tagged = [p for p in pool if p["formula"]]
    out["formula"] = one_vs_rest({p["formula"] for p in tagged}, lambda p: p["formula"], tagged,
                                 name=lambda f: f"#{f}")
    if when:
        dated = [p for p in pool if p["date"]]
        out["when"] = one_vs_rest({p["date"].weekday() for p in dated}, lambda p: p["date"].weekday(),
                                  dated, name=lambda i: DAYS[i])

        def band(p):
            h = p["date"].hour + (24 if p["date"].hour < 5 else 0)
            return next(name for lo, hi, name in HOURS if lo <= h < hi)
        hours = [p for p in dated if p["has_time"]]
        out["when"] += one_vs_rest({band(p) for p in hours}, band, hours)
    k = sum(len(v) for v in out.values())
    for rows in out.values():
        for c in rows:
            c["tier"] = tier(c, k)
    return out


def terciles(pool):
    with_hook = [p for p in pool if p["hook"] and p["multiple"] is not None]
    if len(with_hook) < TERCILE_N:
        return None
    for p in with_hook:
        p["_words"] = len(L.words(p["hook"]))
        p["_number"] = bool(re.search(r"[\d٠-٩]", p["hook"]))
    ranked = sorted(with_hook, key=lambda p: p["_words"])
    k = len(ranked) // 3
    thirds = [ranked[:k], ranked[k:2 * k], ranked[2 * k:]]
    rows = []
    for name, part in zip(("shortest third", "middle third", "longest third"), thirds):
        rows.append({"label": f"{name} ({part[0]['_words']}-{part[-1]['_words']} words)", "n": len(part),
                     "median": median([p["multiple"] for p in part])})
    yes = [p for p in with_hook if p["_number"]]
    no = [p for p in with_hook if not p["_number"]]
    if len(yes) >= MIN_GROUP and len(no) >= MIN_GROUP:
        rows.append({"label": "hook has a number", "n": len(yes), "median": median([p["multiple"] for p in yes])})
        rows.append({"label": "hook has no number", "n": len(no), "median": median([p["multiple"] for p in no])})
    return rows


def join_journal(posts, entries):
    """Attach journal entries to posts. An entry with a link matches by link only.
    An entry without one matches by date, only when it is the one entry posted that
    day and there is exactly one post that day."""
    posted = [e for e in entries if e.get("status") == "posted"]
    by_link = {J.norm_link(p["permalink"]): p for p in posts if p["permalink"]}
    matched, unmatched, notes = [], [], []
    for e in posted:
        p, how = None, None
        day = J.safe_date(e.get("posted"))
        if e.get("posted") and day is None:
            notes.append(f"journal {e['id']}: posted date {e['posted']!r} not read, not matched")
            unmatched.append(e)
            continue
        if e.get("permalink"):
            p, how = by_link.get(J.norm_link(e["permalink"])), "link"
        elif day:
            same = [q for q in posts if q["date"] and q["date"].date() == day
                    and (not e.get("format") or q["format"] in (e.get("format"), "post", None))]
            twins = [x for x in posted if x.get("posted") == e["posted"] and not x.get("permalink")]
            if len(same) == 1 and len(twins) == 1:
                p, how = same[0], "date"
        if p is None or p.get("journal"):
            unmatched.append(e)
            continue
        p["journal"], p["match"] = e["id"], how
        if not p["formula"] and e.get("formula"):
            p["formula"], p["formula_source"] = J.norm_formula(e["formula"]), "journal"
        if not p["hook"] and e.get("hook"):
            p["hook"] = e["hook"]
        p["hookscore"] = e.get("hookscore")
        matched.append((e, p))
    return matched, unmatched, notes


def diagnose(pool, rate_base):
    """Hook problem or profile problem, per post, only from columns that exist."""
    out = []
    med_follow = median([p["follows_k"] for p in pool])
    med_nf = median([p["nonfollower"] for p in pool])
    med_hold = median([p["hold3s"] for p in pool])
    for p in pool:
        f = p["follows_k"]
        travelled = p["multiple"] >= 2 and (med_nf is None or p["nonfollower"] is None or p["nonfollower"] >= med_nf)
        if travelled and f is not None and med_follow and f < 0.5 * med_follow:
            out.append(("profile", p, f"{p['multiple']:.1f}x the usual reach but {f:.1f} follows per 1k {rate_base} "
                                      f"(account median {med_follow:.1f}): the reel travelled, the profile did not convert"))
        if p["multiple"] < 0.7 and p["hold3s"] is not None and med_hold and p["hold3s"] < med_hold:
            out.append(("hook", p, f"{p['multiple']:.1f}x and hold at 3s {p['hold3s']:.0%} "
                                   f"(account median {med_hold:.0%}): lost in the first seconds"))
    return out


def analyse(posts, entries=None, today=None, min_age=MIN_AGE, when=False):
    today = today or dt.date.today()
    metric = "views" if any(p["views"] is not None for p in posts) else "reach"
    posts = [p for p in posts if p[metric] is not None]
    dated = baselines(posts, metric)
    matched, unmatched, jnotes = join_journal(posts, entries or [])
    rate_base = "reach" if any(p["reach"] is not None for p in posts) else metric
    for p in posts:
        base = p[rate_base]                      # one base for every row, as the header says
        for f in ("shares", "saves", "follows", "comments"):
            p[f"{f}_k"] = per_k(p[f], base)
        p["young"] = bool(p["date"] and (today - p["date"].date()).days < min_age)
    pool = [p for p in posts if not p["young"] and p["multiple"] is not None]
    too_few = len(pool) < FEW
    a = {
        "n": len(posts), "metric": metric, "dated": dated, "rate_base": rate_base, "min_age": min_age,
        "range": None, "young": [p for p in posts if p["young"]],
        "no_baseline": [p for p in posts if not p["young"] and p["multiple"] is None],
        "pool": pool, "too_few": too_few,
        "top": [] if too_few else sorted(pool, key=lambda p: -p["multiple"])[:5],
        "bottom": [] if too_few else sorted(pool, key=lambda p: p["multiple"])[:5],
        "matched": matched, "unmatched": unmatched, "journal_notes": jnotes,
        "median_metric": median([p[metric] for p in posts]),
    }
    ds = [p["date"] for p in posts if p["date"]]
    if ds:
        a["range"] = (min(ds).date(), max(ds).date())
    a["diagnosis"] = [] if too_few else diagnose(pool, rate_base)
    a["comparisons"] = {} if too_few else comparisons(pool, when)
    a["n_comparisons"] = sum(len(v) for v in a["comparisons"].values())
    a["terciles"] = None if too_few else terciles(pool)
    return a


# ---------------------------------------------------------------- printing

def fmt_n(x):
    if x is None:
        return "n/a"
    return f"{x:,.0f}" if x >= 100 else f"{x:.1f}" if isinstance(x, float) else str(x)


def fmt_pct(x):
    return "n/a" if x is None else f"{x:.0%}"


def day_of(p):
    return p["date"].date().isoformat() if p["date"] else f"line {p['row']}"


def post_line(p, a):
    hook = (p["hook"] or "").replace("\n", " ")[:42]
    formula = f"#{p['formula']}" if p["formula"] else "  -"
    return (f"  {p['multiple']:5.1f}x  {day_of(p)}  {p['format'] or '-':<8} {fmt_n(p[a['metric']]):>9} "
            f"sh {fmt_n(p['shares_k']):>5}  sv {fmt_n(p['saves_k']):>5}  fo {fmt_n(p['follows_k']):>5}  "
            f"nf {fmt_pct(p['nonfollower']):>4}  h3 {fmt_pct(p['hold3s']):>4}  {formula:<4} {hook}")


WORDING = {
    "clear": "associated with a clear difference",
    "worth testing": "a difference worth testing on purpose",
    "no difference you can rely on": "no difference you can rely on",
}
LEGEND = "(sh/sv/fo = shares/saves/follows per 1k {base}, nf = non-follower, h3 = hold at 3s)"


def render(a, mapping, notes, out=sys.stdout):
    w = lambda s="": print(s, file=out)  # noqa: E731
    rng = f"{a['range'][0]} to {a['range'][1]}" if a["range"] else "no dates"
    w(f"AUDIT  ·  {a['n']} posts  ·  {rng}  ·  median {a['metric']} {fmt_n(a['median_metric'])}")
    base = ("previous 10 posts of the same format (min 5)" if a["dated"]
            else "all other posts of the same format (no dates: growth is not corrected)")
    w(f"baseline: {base}  ·  rates per 1k {a['rate_base']}")
    w()
    w("COLUMNS  " + ", ".join(f"{f}={h!r}" for f, h in mapping.items()))
    missing = [f for f in ("reach", "shares", "saves", "follows", "hold3s", "nonfollower", "length", "formula")
               if f not in mapping]
    if missing:
        w("missing  " + ", ".join(missing) + "  (shown as n/a, never estimated)")
    for n in notes + a["journal_notes"]:
        w("note     " + n)
    if a["young"]:
        w(f"left out {len(a['young'])} post(s) younger than {a['min_age']} days: their numbers are still moving")
    reasons = {}
    for p in a["no_baseline"]:
        reasons.setdefault(p["why"], []).append(p)
    for why, ps in reasons.items():
        w(f"left out {len(ps)} post(s): {why}")
    w()
    if not a["pool"]:
        w("Nothing to rank: no post has a baseline yet.")
        return
    if a["too_few"]:
        w(f"ALL COMPARABLE POSTS  {LEGEND.format(base=a['rate_base'])}")
        for p in sorted(a["pool"], key=lambda p: -p["multiple"]):
            w(post_line(p, a))
        w()
        w(f"TOO FEW TO COMPARE  {len(a['pool'])} comparable posts. Below {FEW}, any pattern is noise:")
        w("no top and bottom, no hook-or-profile call, no comparison. Keep posting, run this again with more.")
        return
    w(f"TOP 5 BY OUTLIER MULTIPLE   {LEGEND.format(base=a['rate_base'])}")
    for p in a["top"]:
        w(post_line(p, a))
    w("BOTTOM 5")
    for p in a["bottom"]:
        w(post_line(p, a))
    w()
    if a["diagnosis"]:
        w("HOOK OR PROFILE")
        for kind, p, text in a["diagnosis"]:
            w(f"  {kind.upper():<8} {day_of(p)}  {text}")
        if any(k == "profile" for k, _, _ in a["diagnosis"]):
            w("  -> reels that travel without converting: fix the profile (/ig-profile) before the hooks.")
        w()
    w(f"COMPARISONS  ({a['n_comparisons']} run, groups of {MIN_GROUP}+ only)")
    titles = {"format": "format (vs the account's usual reach, any format)", "length": "reel length",
              "formula": "hook formula", "when": "day and hour (--when)"}
    for k in ("format", "length", "formula", "when"):
        rows = a["comparisons"].get(k) or []
        if not rows:
            continue
        w(f"  {titles[k]}")
        for c in rows:
            w(f"    {c['label']:<18} median {c['median']:.2f}x vs {c['median_rest']:.2f}x for the rest "
              f"(n={c['n']} vs {c['n_rest']}, {c['above']}/{c['n']} above the rest's median): {WORDING[c['tier']]}")
    if not a["n_comparisons"]:
        w("  no group reached 5 posts: nothing to compare yet.")
    else:
        w(f"  {a['n_comparisons']} comparisons. On accounts with no real difference, about 1 table in 4 still")
        w("  shows a 'worth testing' line by chance. Test a finding on the next posts before believing it.")
    w()
    if a["terciles"]:
        w("BY THIRDS  (a description of these posts, not a cause)")
        for r in a["terciles"]:
            w(f"  {r['label']:<32} n={r['n']:<3} median {r['median']:.2f}x")
        w()
    if a["matched"] or a["unmatched"]:
        w(f"JOURNAL  {len(a['matched'])} matched ({sum(1 for _, p in a['matched'] if p['match'] == 'link')} by link)"
          f", {len(a['unmatched'])} not found in this table")
        for e in a["unmatched"][:8]:
            w(f"  not found: {e['id']} posted {e.get('posted')}  {(e.get('hook') or '')[:50]}")
        w()
    w("This says what went with what on this account. It does not say why: the face, the edit,")
    w("the audio and who Instagram showed it to are not in this table.")


def to_markdown(a):
    lines = [f"# Insights ({dt.date.today().isoformat()})", "",
             f"{a['n']} posts, baseline = same-format trailing median, metric {a['metric']}.", ""]
    if a["too_few"]:
        lines.append(f"Too few comparable posts ({len(a['pool'])}) to conclude anything. "
                     "Nothing here should steer the plan: use the defaults and the swipe file.")
        return "\n".join(lines) + "\n"
    lines.append("## Top 5")
    lines += [f"- {p['multiple']:.1f}x {p['format']} #{p['formula'] or '-'} {(p['hook'] or '')[:60]}" for p in a["top"]]
    lines.append("## Bottom 5")
    lines += [f"- {p['multiple']:.1f}x {p['format']} #{p['formula'] or '-'} {(p['hook'] or '')[:60]}" for p in a["bottom"]]
    lines += ["", f"## Comparisons ({a['n_comparisons']} run; about 1 table in 4 shows a 'worth testing' by chance)"]
    for rows in a["comparisons"].values():
        lines += [f"- {c['label']}: {c['ratio']:.2f}x the rest, n={c['n']}, {WORDING[c['tier']]}" for c in rows]
    for kind, p, text in a["diagnosis"]:
        lines.append(f"- {kind}: {text}")
    return "\n".join(lines) + "\n"


def jsonable(a):
    def post(p):
        q = {k: v for k, v in p.items() if not k.startswith("_")}
        q["date"] = p["date"].isoformat() if p["date"] else None
        return q
    out = dict(a)
    for k in ("young", "no_baseline", "pool", "top", "bottom"):
        out[k] = [post(p) for p in a[k]]
    out["matched"] = [{"journal": e["id"], "line": p["row"], "by": p["match"]} for e, p in a["matched"]]
    out["unmatched"] = [e["id"] for e in a["unmatched"]]
    out["diagnosis"] = [{"kind": k, "line": p["row"], "text": t} for k, p, t in a["diagnosis"]]
    out["range"] = [d.isoformat() for d in a["range"]] if a["range"] else None
    return out


def parse_map(s):
    out = {}
    for part in (s or "").split(","):
        if part.strip():
            if "=" not in part:
                raise AuditError(f"--map wants field=Header, got {part!r}")
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Audit the user's own posts.")
    ap.add_argument("input", nargs="?", default="-", help="TSV/CSV file, or - for stdin")
    ap.add_argument("--map", help='fix headers: "views=Plays,reach=Accounts reached"')
    ap.add_argument("--journal", help="journal.jsonl (default ~/.claude/instagram/journal.jsonl)")
    ap.add_argument("--no-journal", action="store_true")
    ap.add_argument("--min-age", type=int, default=MIN_AGE, help="days before a post counts (default 7)")
    ap.add_argument("--when", action="store_true", help="also compare day of week and hour")
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    ap.add_argument("--out", help="also write a short markdown summary here (insights.md)")
    ap.add_argument("--json", action="store_true")
    L.add_lang_arg(ap)          # accepted for symmetry with the other tools; numbers have no language
    args = ap.parse_args()
    try:
        text = L.read_input(args.input)
        posts, mapping, notes = read_table(text, parse_map(args.map))
        entries = [] if args.no_journal else J.load(args.journal)
        today = J.parse_date(args.today) if args.today else None
        a = analyse(posts, entries, today, args.min_age, args.when)
    except (AuditError, ValueError) as exc:
        print(f"audit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(jsonable(a) | {"columns": mapping, "notes": notes}, ensure_ascii=False, indent=2, default=str))
    else:
        render(a, mapping, notes)
    if args.out:
        path = os.path.expanduser(args.out)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
