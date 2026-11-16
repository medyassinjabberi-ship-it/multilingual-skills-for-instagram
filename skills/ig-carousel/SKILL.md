---
name: ig-carousel
description: >-
  Build an Instagram carousel - the cover that earns the swipe, slide-by-slide
  copy, and the 1080x1350 files to upload. Use when the user says "carousel",
  "slides", "swipe post", "turn this into a carousel", or has a list-shaped or
  step-shaped idea that would die as a single image.
---

# ig-carousel

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.
> **Windows:** if `python3` is not found, run the same commands with `py -3` (or `python`).

Carousels are the highest-dwell format on the grid, because a swipe is an
interaction and a scroll is not. They also get a second chance: Instagram can
show a carousel again starting from a later slide to someone who did not engage
the first time, so slide two has to stand on its own as well.

The format rewards one idea broken into steps. It punishes a caption cut into
pieces.

## When to use it instead of a Reel

Use a carousel when the idea has **sequence and needs to be re-read**: steps, a
framework with parts, a before and after, a list worth screenshotting. Use a
Reel when the idea has motion, a face, or a payoff that has to be seen
happening.

If the idea is one claim, it is neither. Hand it to `/ig-reel` and say so.

## Structure

6 to 10 slides. The cap is 20 and 20 is almost always a book nobody finishes.
Under 5 and the swipe never starts.

```
1         COVER     the hook. 6 words or fewer, at a size that is legible in
                    the grid at thumbnail. One line of promise under it.
2         THE STAKE why this matters, in one sentence. This slide is also a
                    second cover, so it cannot be setup.
3 to N    ONE IDEA PER SLIDE. A headline of 3 to 7 words, at most 25 words
                    under it. If a slide needs a paragraph, it is two slides.
N+1       RECAP     the whole thing as a list. This is the screenshot slide.
LAST      CTA       one action. Save, comment a keyword, or follow. One.
```

## Slide copy rules

- **The cover is 80% of the result.** Six words. Big. Nothing on the deck saves
  a cover nobody swipes.
- **Design for the grid crop.** The profile grid crops to a portrait rectangle
  that is taller than it is wide, and the exact ratio has moved more than once.
  Build at 1080x1350 and keep the cover text well inside the middle, clear of
  the outer 120 pixels on every side, and the crop stops mattering.
- **Number the slides** (3/8). Completion goes up when people can see the end.
- **No slide is a paragraph.** If it cannot be said in 25 words, split it.
- **The recap slide is the one people screenshot and send.** Sends are the
  strongest signal you can earn. Make it standalone and readable with no
  context.
- **The handle on every slide**, small, bottom corner. Screenshots travel
  without you.
- **Alt text on the cover at minimum.** It is read by screen readers and by
  Instagram.

## Building the files

Instagram wants 1080x1350 (4:5), JPEG or PNG, up to 20 items. One tool lives in
this folder and it runs: it lints the copy against the rules above, then renders
the PNG files with a browser already on the machine (Chrome, Edge or Chromium).

```bash
python3 carousel.py slides.md                          # lint only
python3 carousel.py slides.md --render --out ./carousel
```

`slides.md` is plain text: an optional header (`handle:`, `accent:`,
`theme: dark|light`, `lang:`), then one block per slide separated by a line
that is exactly `---`, the headline on a line starting with `# `, the body
under it (`- ` lines become a list):

```
handle: @yourhandle
accent: #E4572E
---
# THE $18,000 CLAUSE
One line I now put in every contract.
---
# What it says
Payment on delivery, not on approval.
```

The linter FAILs a cover over 6 words, a body over 25 words (45 on the recap),
and more than 20 slides; it WARNs on under 5 or over 10 slides, a missing
handle, and an ask that is not alone on the last slide. Fix every FAIL before
rendering; it refuses to render otherwise. Arabic-script slides are laid out
right to left and shaped by the browser, numbered and signed on the mirrored
side; text that does not fit is shrunk, never cut, and type never goes under
28px. Without a browser it writes `carousel.html` and says so. It also writes
`alt.txt`, a first draft of the alt text from each slide's own words: edit it
with the user before posting.

The template is deliberately plain: one accent colour, big type, the number
and the handle in the corners. If the user has a brand or a design system, use
its colour with `accent:` and say the template is the pack's, not theirs.

## Output

The slide-by-slide copy first, as a numbered list the user can read in ten
seconds and edit before anything is rendered. Then the **caption**, which for a
carousel is Job B in `/ig-caption`: the caption is doing work here, because the
cover has already used its six words.

Run both through `/ig-human`. Build the files only after the user approves the
copy. When they say yes, log it so `/ig-audit` can find it later:

```bash
python3 journal.py add --format carousel --hook "{cover headline}" --lang {lang} --theme "{theme}" --type teach
```

and run `journal.py posted {id} --date YYYY-MM-DD` when they say it is live.

```
CAROUSEL  ·  8 slides

1  COVER   THE $18,000 CLAUSE
           One line I now put in every contract.
2  STAKE   I approved the work. They asked for the money back nine days later.
3          WHAT IT SAYS
           Payment on delivery, not on approval.
...
7  RECAP   All four lines, in order.
8  CTA     Comment CONTRACT and I will send the full clause.

Caption: Job B, hook in line 1, one ask, 3 tags.
```

**For a Darija page** (Arabic script or arabizi), the list above is the
structure, not the words: for each slide, what it must say, the number or name
it must carry, and its word budget, with `____` where the user's words go. Write
`slides.md` the same way, blanks included: `carousel.py` FAILs on `____` and
`{{...}}`, so nothing renders until the user has written every line. Then lint
and render exactly what they wrote.

Nothing is uploaded. The user posts it.

## Language (applies to every skill in this pack)

Answer in the language of the user's page, not the language of this file.
Read the `language:` line in `~/.claude/instagram/voice.md`. If there is none,
use the language the user writes to you in, and ask once if their page is in
another one.

- **English and French:** write the text in full.
- **Modern Standard Arabic:** write in full if the user asks for MSA.
- **Darija (Arabic script or arabizi) and other dialects:** do not invent it.
  Give the structure: what each line must do, what it must contain (the number,
  the name, the ask), and how long it has. Leave the words as blanks for the
  user. Write a Darija wording only if the user asks for one, and label it
  "draft to check" ("brouillon à valider"). A line that sounds translated is
  worse than a blank. `language: ar` covers both MSA and Darija: when you cannot
  tell which, ask once.
- Technical words (reel, hook, caption, save, DM, the tool names) stay in
  English inside a French or Darija line when that is how the user talks.
- **Always pass `--lang`** to the scripts: `en`, `fr`, `ar` (Arabic script,
  Darija included) or `aeb-latn` (arabizi). You know the language; the scripts
  only guess, and a weak guess returns "unknown" with no verdict. Their
  thresholds were set on English. In any other language, report each signal on
  its own and never a global score or verdict: the scripts print "not
  calibrated" for that reason. Say so to the user.
- Nothing in this pack posts to Instagram. The user publishes.
