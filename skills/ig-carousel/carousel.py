#!/usr/bin/env python3
"""
carousel.py - lint a carousel's copy, then render the 1080x1350 slides.

Write the slides in one text file. An optional header of `key: value` lines,
then one block per slide, separated by a line that is exactly `---`. In each
block the line starting with `# ` is the headline, the rest is the body.

    handle: @yourhandle
    accent: #E4572E
    theme: dark            (dark or light)
    lang: fr               (optional; otherwise read from the text)
    ---
    # LA CLAUSE À 18 000 €
    Une ligne que je mets maintenant dans chaque contrat.
    ---
    # Ce qu'elle dit
    Paiement à la livraison, pas à la validation.

The linter checks what the ig-carousel rules say: 5 to 10 slides (20 is the
cap), a cover of 6 words or fewer, 25 words or fewer of body per slide (45 on
the recap, which is the second-to-last slide), a handle for the corner, and
one ask, on the last slide. Asks are found in English and French; in Arabic
script and arabizi the ask check says CHECK and Claude reads it.

The renderer writes one HTML page per slide and has a browser already on the
machine (Chrome, Edge, Chromium, or --browser) screenshot it at exactly
1080x1350. Arabic slides are laid out right to left and shaped by the browser.
Text that does not fit is shrunk on the page, never cut. Without a browser it
still writes carousel.html and says how to print it. It also writes alt.txt,
a first draft of the alt text for each slide, from the slide's own words.

Usage
  python3 carousel.py slides.md                   # lint only
  python3 carousel.py slides.md --render --out ./carousel
  python3 carousel.py slides.md --render --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"
  python3 carousel.py slides.md --json

Exit code: 0 ready, 1 a FAIL in the lint (nothing rendered unless --force), 2 bad input.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402

W, H, MARGIN = 1080, 1350, 120
COVER_WORDS, BODY_WORDS, RECAP_WORDS = 6, 25, 45
ASKS = {
    "en": r"\b(comment|save (this|it)|follow|share (this|it)|send (this|it) to|dm me|tag)\b",
    # imperatives only: "Je partage mon avis" is not an ask, "partage-le" is
    "fr": r"(?<![\w'])(commente[sz]?|enregistre[sz]?(-le|-la|-les)?|sauvegarde[sz]?(-le|-la|-les)?|"
          r"abonne[sz]?-(toi|vous)|partage[sz]?-(le|la|les|lui)|partage[sz]? (ce|cette|ça|ca) |"
          r"envoie[sz]?-(le|la|les|moi)|écri(s|vez)-moi|ecri(s|vez)-moi|tague[sz]?|dm-moi|en dm)(?![\w])",
}
KEYS = {"handle", "accent", "theme", "lang"}
THEMES = {
    "dark": {"bg": "#111111", "fg": "#F5F5F5", "muted": "#A0A0A0"},
    "light": {"bg": "#FAFAF7", "fg": "#141414", "muted": "#6B6B6B"},
}
BROWSERS = {
    "win32": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
               "/Applications/Chromium.app/Contents/MacOS/Chromium"],
}
WHICH = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome")


class CarouselError(Exception):
    pass


def parse(text):
    """-> (settings, slides). A slide is {'headline': str, 'body': [lines]}."""
    blocks = re.split(r"(?m)^---\s*$", text.lstrip("\ufeff"))
    settings = {}
    first = blocks[0].strip()
    if first and all(re.match(r"^([A-Za-z_]+)\s*:", l) and re.match(r"^([A-Za-z_]+)", l).group(1).lower() in KEYS
                     for l in first.splitlines() if l.strip()):
        for l in first.splitlines():
            if l.strip():
                k, v = l.split(":", 1)
                settings[k.strip().lower()] = v.strip()
        blocks = blocks[1:]
    elif not first:
        blocks = blocks[1:]
    slides = []
    for b in blocks:
        lines = [l.rstrip() for l in b.strip().splitlines()]
        if not any(l.strip() for l in lines):
            continue
        heads = [i for i, l in enumerate(lines) if l.startswith("# ")]
        head = lines[heads[0]][2:].strip() if heads else ""
        # a second "# " line is kept as body text, never dropped
        body = [l[2:].strip() if (l.startswith("# ") and i != (heads[0] if heads else -1)) else l
                for i, l in enumerate(lines) if l.strip() and i != (heads[0] if heads else -1)]
        if head or any(b.strip() for b in body):
            slides.append({"headline": head, "body": body})
    if not slides:
        raise CarouselError("no slides with any text. Separate slides with a line that is exactly ---")
    return settings, slides


def slide_lang(s, declared, deck=None):
    text = "\n".join([s["headline"]] + s["body"])
    if L.arabic_ratio(text) > 0.3:          # Arabic letters are Arabic script, whatever was declared
        return "ar"
    if declared:
        return declared
    return L.guess(text) or deck or L.UNKNOWN


def count(text):
    return len(L.words(text))


def lint(settings, slides):
    declared = L.normalise(settings["lang"]) if settings.get("lang") else None
    latin = "\n".join(l for s in slides for l in [s["headline"]] + s["body"] if L.arabic_ratio(l) <= 0.3)
    deck = L.guess(latin) if latin.strip() else None      # short slides borrow the deck's language
    out = []   # (level, slide number or None, message)
    n = len(slides)
    if n > 20:
        out.append(("FAIL", None, f"{n} slides: Instagram takes 20 at most"))
    elif n < 5:
        out.append(("WARN", None, f"{n} slides: under 5 the swipe never starts"))
    elif n > 10:
        out.append(("WARN", None, f"{n} slides: past 10 it is a book nobody finishes"))
    if not settings.get("handle"):
        out.append(("WARN", None, "no handle: screenshots of the recap travel without you"))
    asks_on, unchecked = [], []
    for i, s in enumerate(slides, 1):
        s["lang"] = slide_lang(s, declared, deck)
        hw, bw = count(s["headline"]), count(" ".join(s["body"]))
        s["words"] = {"headline": hw, "body": bw}
        if i == 1:
            if not s["headline"]:
                out.append(("FAIL", 1, "the cover has no headline (a line starting with '# ')"))
            elif hw > COVER_WORDS:
                out.append(("FAIL", 1, f"cover headline is {hw} words: {COVER_WORDS} or fewer, it is read at thumbnail size"))
        elif not s["headline"]:
            out.append(("WARN", i, "no headline (a line starting with '# '): the slide reads as a paragraph"))
        elif not 3 <= hw <= 7 and i < n - 1:
            out.append(("WARN", i, f"headline is {hw} word{'s' if hw != 1 else ''}: 3 to 7 reads in one glance"))
        limit = RECAP_WORDS if (i == n - 1 and n >= 4) else BODY_WORDS
        if bw > limit:
            out.append(("FAIL", i, f"{bw} words of body: {limit} or fewer, or it is two slides"))
        rx = ASKS.get(s["lang"])
        text = " ".join([s["headline"]] + s["body"])
        if re.search(r"_{3,}|\{\{[^{}]*\}\}", text):
            out.append(("FAIL", i, "blanks still to fill (____ or {{...}}): the user writes these words"))
        if rx is None:
            unchecked.append(i)
        else:
            k = len(re.findall(rx, text, re.IGNORECASE))
            if k:
                asks_on.append(i)
            if k > 1:
                out.append(("WARN", i, f"{k} asks on one slide: one ask, said once"))
    if len(asks_on) > 1:
        out.append(("WARN", None, f"an ask on slides {', '.join(map(str, asks_on))}: one ask, on the last slide"))
    elif asks_on and asks_on[0] != n:
        out.append(("WARN", asks_on[0], "the ask is not on the last slide"))
    elif not asks_on and n not in unchecked:
        out.append(("WARN", n, "no ask found on the last slide (save, comment a keyword, or follow)"))
    if unchecked:
        out.append(("CHECK", None, f"slides {', '.join(map(str, unchecked))} are not English or French: "
                                   "count the asks by reading (one, on the last slide)"))
    return out


# ---------------------------------------------------------------- rendering

FIT_JS = """
<script>
(function () {
  var box = document.getElementById('box');
  var els = box.querySelectorAll('h1, p, li');
  var guard = 0;
  function over() { return box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1; }
  els.forEach(function (e) {      // a line too wide: shrink that line only
    var n = 0;
    while (e.scrollWidth > box.clientWidth + 1 && n < 60) {
      var s = parseFloat(getComputedStyle(e).fontSize);
      if (s <= 28) break;
      e.style.fontSize = Math.max(s * 0.93, 28) + 'px';
      n++;
    }
  });
  while (box.scrollHeight > box.clientHeight + 1 && guard < 60) {
    els.forEach(function (e) {
      var s = parseFloat(getComputedStyle(e).fontSize);
      e.style.fontSize = Math.max(s * 0.95, 28) + 'px';
    });
    guard++;
  }
  if (over()) {           // a word too long even at 28px: break it rather than cut it
    els.forEach(function (e) { e.style.overflowWrap = 'anywhere'; });
    document.body.setAttribute('data-broken', '1');
  }
})();
</script>"""


def slide_html(s, i, n, settings):
    theme = THEMES.get(settings.get("theme", "dark").lower(), THEMES["dark"])
    accent = settings.get("accent") or "#E4572E"
    if not re.match(r"^#[0-9A-Fa-f]{3,8}$", accent):
        accent = "#E4572E"
    rtl = s["lang"] == "ar" or L.arabic_ratio(s["headline"] + " ".join(s["body"])) > 0.3
    cover = i == 1
    hw = max(s["words"]["headline"], 1)
    h_size = (132 if hw <= 3 else 112 if hw <= 5 else 96) if cover else (80 if hw <= 4 else 68)
    items = []
    bullets = [b for b in s["body"] if re.match(r"^\s*[-•*]\s+", b)]
    if bullets and len(bullets) == len(s["body"]):
        items.append("<ul>" + "".join(f"<li>{html.escape(re.sub(r'^\s*[-•*]\s+', '', b))}</li>"
                                       for b in s["body"]) + "</ul>")
    else:
        items += [f"<p>{html.escape(b)}</p>" for b in s["body"]]
    handle = html.escape(settings.get("handle", ""))
    return f"""<!doctype html>
<html lang="{'ar' if rtl else 'und'}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; }}
  body {{ width: {W}px; height: {H}px; overflow: hidden; background: {theme['bg']}; color: {theme['fg']};
         font-family: "Segoe UI", "Helvetica Neue", Arial, "Noto Sans Arabic", "Noto Sans", Tahoma, sans-serif; }}
  .slide {{ position: relative; width: {W}px; height: {H}px; box-sizing: border-box; padding: {MARGIN}px; }}
  #box {{ position: absolute; inset: {MARGIN + 60}px {MARGIN}px {MARGIN + 60}px {MARGIN}px; overflow: hidden;
          display: flex; flex-direction: column; justify-content: {'center' if cover else 'flex-start'}; }}
  h1 {{ font-size: {h_size}px; line-height: 1.08; margin: 0 0 40px; font-weight: 800; letter-spacing: -0.01em; }}
  h1::after {{ content: ""; display: block; width: 140px; height: 12px; background: {accent}; margin-top: 36px; }}
  p, li {{ font-size: {56 if cover else 46}px; line-height: 1.32; margin: 0 0 24px; color: {theme['fg']}; }}
  ul {{ margin: 0; padding: 0; list-style: none; }}
  li {{ position: relative; padding-inline-start: 1.2em; }}
  li::before {{ content: ""; position: absolute; inset-inline-start: 0; top: 0.5em; width: 0.42em; height: 0.42em;
               background: {accent}; }}
  .num {{ position: absolute; top: 64px; {'left' if rtl else 'right'}: {MARGIN}px; font-size: 34px;
          color: {accent}; font-weight: 700; }}
  .handle {{ position: absolute; bottom: 64px; {'right' if rtl else 'left'}: {MARGIN}px; font-size: 32px;
             color: {theme['muted']}; direction: ltr; }}
</style></head>
<body><div class="slide">
  <div class="num">{i}/{n}</div>
  <div id="box">{f"<h1>{html.escape(s['headline'])}</h1>" if s['headline'] else ''}{''.join(items)}</div>
  {f'<div class="handle">{handle}</div>' if handle else ''}
</div>{FIT_JS}</body></html>"""


def find_browser(given=None):
    for cand in [given, os.environ.get("IG_BROWSER")]:
        if cand:
            if os.path.exists(cand) or shutil.which(cand):
                return shutil.which(cand) or cand
            raise CarouselError(f"browser not found: {cand}")
    for p in BROWSERS.get(sys.platform, []):
        if os.path.exists(p):
            return p
    for name in WHICH:
        found = shutil.which(name)
        if found:
            return found
    return None


def screenshot(browser, page, png):
    profile = tempfile.mkdtemp(prefix="igcarousel-")
    try:
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--disable-extensions", f"--user-data-dir={profile}", "--force-device-scale-factor=1",
               f"--window-size={W},{H}", f"--screenshot={os.path.abspath(png)}", Path(page).resolve().as_uri()]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0 and os.path.exists(png) and os.path.getsize(png) > 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def render(settings, slides, out_dir, browser_arg=None):
    os.makedirs(out_dir, exist_ok=True)
    n = len(slides)
    pages, report = [], {"pngs": [], "html": None, "browser": None, "failed": []}
    for i, s in enumerate(slides, 1):
        page = os.path.join(out_dir, f"slide-{i:02d}.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(slide_html(s, i, n, settings))
        pages.append(page)
    preview = os.path.join(out_dir, "carousel.html")
    with open(preview, "w", encoding="utf-8") as fh:
        fh.write("<!doctype html><meta charset='utf-8'><title>carousel</title><body style='background:#ccc'>"
                 + "".join(f"<iframe src='{os.path.basename(p)}' width='{W}' height='{H}' "
                           f"style='border:0;display:block;margin:20px auto;transform-origin:top'></iframe>"
                           for p in pages) + "</body>")
    report["html"] = preview
    with open(os.path.join(out_dir, "alt.txt"), "w", encoding="utf-8") as fh:
        for i, s in enumerate(slides, 1):
            text = " ".join([s["headline"].rstrip(".") + "."] + [re.sub(r"^\s*[-•*]\s+", "", b) for b in s["body"]])
            fh.write(f"slide {i}/{n}: {text.strip()}\n")
    browser = find_browser(browser_arg)
    report["browser"] = browser
    if not browser:
        return report
    for i, page in enumerate(pages, 1):
        png = os.path.join(out_dir, f"slide-{i:02d}.png")
        if screenshot(browser, page, png):
            report["pngs"].append(png)
        else:
            report["failed"].append(i)
    return report


def main():
    L.setup_stdout()
    ap = argparse.ArgumentParser(description="Lint and render an Instagram carousel.")
    ap.add_argument("input", nargs="?", default="-", help="slides file, or - for stdin")
    ap.add_argument("--render", action="store_true", help="write the slides as 1080x1350 PNG")
    ap.add_argument("--out", default="carousel", help="folder for the files (default ./carousel)")
    ap.add_argument("--browser", help="path to Chrome, Edge or Chromium")
    ap.add_argument("--force", action="store_true", help="render even with a FAIL")
    ap.add_argument("--json", action="store_true")
    L.add_lang_arg(ap)
    args = ap.parse_args()
    try:
        settings, slides = parse(L.read_input(args.input))
        if args.lang:
            settings["lang"] = args.lang
        if settings.get("lang") and not L.normalise(settings["lang"]):
            raise CarouselError(f"lang: {settings['lang']!r} is not a language this pack reads (en, fr, ar, aeb-latn)")
        issues = lint(settings, slides)
    except CarouselError as exc:
        print(f"carousel: {exc}", file=sys.stderr)
        return 2
    fails = [x for x in issues if x[0] == "FAIL"]
    report = None
    if args.render and (not fails or args.force):
        report = render(settings, slides, args.out, args.browser)
    if args.json:
        print(json.dumps({"settings": settings, "slides": slides,
                          "issues": [{"level": a, "slide": b, "message": c} for a, b, c in issues],
                          "render": report}, ensure_ascii=False, indent=2))
        return 1 if fails else 0
    n = len(slides)
    print(f"CAROUSEL  ·  {n} slides  ·  {'READY' if not fails else 'FIX FIRST'}")
    for i, s in enumerate(slides, 1):
        tag = "COVER" if i == 1 else "CTA" if i == n else "RECAP?" if i == n - 1 and n >= 4 else ""
        print(f"  {i:>2}  {tag:<6} {s['headline'][:60]}  ({s['words']['headline']} + {s['words']['body']} words, {s['lang']})")
    if issues:
        print()
        for level, slide, msg in issues:
            where = f"slide {slide}" if slide else "deck"
            print(f"  {level:<5} {where:<8} {msg}")
    if args.render and fails and not args.force:
        print("\nNot rendered: fix the FAIL lines first (or --force).")
    elif report:
        print(f"\nfiles in {os.path.abspath(args.out)}")
        if report["pngs"]:
            print(f"  {len(report['pngs'])} PNG at {W}x{H}, rendered with {os.path.basename(report['browser'])}")
        if report["failed"]:
            print(f"  slides {report['failed']} did not render: open {report['html']} and check them")
        if not report["browser"]:
            print("  no Chrome, Edge or Chromium found: open carousel.html and screenshot each slide, "
                  "or pass --browser")
        print("  alt.txt has a first draft of the alt text for each slide: edit it before posting.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
