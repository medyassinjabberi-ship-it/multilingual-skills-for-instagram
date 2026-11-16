---
name: ig-audit
description: >-
  Post-mortem on what the user has already posted - which reels actually
  worked, computed by a script against each format's own trailing median,
  what went with them, and what to stop making. Use when the user pastes their
  Instagram insights or past posts and asks "what's working", "why did this
  flop", "read my analytics", "audit my content", or wants to know what to do
  more of.
---

# ig-audit

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.
> **Windows:** if `python3` is not found, run the same commands with `py -3` (or `python`).

The only honest source of what works for an account is that account. Every
rule in every Instagram guide, including the ones in this pack, is a prior.
The user's own last 30 posts are the evidence.

One tool lives in this folder and it runs. Use it: the arithmetic in an audit
is where mistakes hide, and every number below comes from the script, not from
reading screenshots.

```bash
python3 audit.py posts.tsv                                   # the audit
python3 audit.py posts.tsv --out ~/.claude/instagram/insights.md
python3 audit.py posts.csv --map "views=Plays,reach=Accounts reached"
python3 audit.py posts.tsv --when                            # also day of week and hour
```

## Input

One row per post, a header row, tab, comma or semicolon separated. Start from
`posts-template.tsv` in this folder:

```
date  format  views  reach  shares  saves  follows  comments  hold3s  nonfollower  length  permalink  hook  formula
```

Only `views` (or `reach`) is required; every other column makes the audit
sharper, and a missing one prints `n/a`, never an estimate. Headers are matched
in English or French, case and accents ignored (`Vues`, `Couverture`,
`Partages`, `Enregistrements`, `Durée (s)`...). The script prints which column
it read as what: **check that line with the user.** If a header is not
recognised, pass `--map`. "Impressions" is never read as views.

Ways to fill it, best first:

- An Insights export the user downloads themselves (Meta Business Suite,
  Insights, Content, Export), then `--map` for any header it does not know.
- The user's screenshots of each post's Insights, typed into the template by
  you, one row per post. Read the numbers back to the user before running.
- Just dates, formats and view counts: enough for a first pass.

Never log into the account and never scrape it. The user brings the data.

Run `audit.py` from this folder: it also reads `~/.claude/instagram/journal.jsonl`
(written by `/ig-reel` and `/ig-carousel`) and attaches the hook, the formula
and the hook score to each post it can match by link, or by a unique same-day
match. It lists the journal entries it could not match; never pair them by
guessing.

## What the script computes, and why

| metric | how | what it tells you |
| --- | --- | --- |
| **Outlier multiple** | views / median of the **previous 10 posts of the same format** (5 at least, or no baseline) | a real hit or a normal day. Trailing, so growth does not flatter old posts; per format, so a carousel is not judged against reels |
| **Shares, saves, follows, comments per 1k** | per reach, or per views if there is no reach | sends are the strongest signal you can earn; follows say whether the profile converted |
| **Non-follower share** | as exported | whether it travelled at all |
| **Hold at 3s** | as exported | the hook's grade |

Posts younger than 7 days are left out of every comparison (`--min-age`):
their numbers are still moving.

Then, and only from 10 comparable posts up, **three families of comparisons
fixed in advance**: format, reel length, hook formula. Each group is compared
with the rest and needs 5 posts or more; a typical 40-post table runs about 8
comparisons, and the report prints the count. Day and hour are compared only
with `--when`, run when the user asks for it, after saying it adds up to a
dozen comparisons: they are almost never the cause and they are where people
want it to be. Each comparison is worded at one of three levels, and the bar
for "clear" rises with the number of comparisons run:

- **associated with a clear difference**
- **a difference worth testing on purpose**
- **no difference you can rely on**

Simulated on accounts with no real difference, "clear" came out on 1.5 to 3.5%
of 40 to 60-post tables, and some line said "worth testing" on 1 table in 5
to 1 in 4: that wording is a lead to test, never a finding. On a formula that
really did 2.5x, it was flagged in 61% of 40-post tables and 88% of 60-post
ones. So with 40 posts, a real effect is missed often. Say that.

From 30 posts with hooks, it also describes the posts by thirds of hook length
and by whether the hook has a number, in any language. That is a description,
not a cause.

## What you add by reading

The script does not read meaning. You do, on the top five and bottom five:

- **Theme** and **who looked bad in the story**: the user's own cost, a client,
  nobody.
- **Whether the user replied to comments in the first hour.**
- **Formula**, for posts the journal did not tag: name it from
  `ig-reel/hooks.json` by reading the hook, add a `formula` column, and re-run.

State every finding with its n, and use the script's wording level. Never say
"because"; say "went with". With 30 posts you can see a pattern.

**Under 10 comparable posts the script prints TOO FEW TO COMPARE**: no top and
bottom, no HOOK OR PROFILE, no comparison, and `--out` writes that nothing
should steer the plan. Then your output is the table, that sentence, and what
to collect next (more posts, the reach and follows columns). No STOP, no DO
MORE, no pattern read by hand: with 8 posts there is none to read.

## The distinction that saves people months

**A reel that gets views and no follows is not a failed reel, it is a profile
problem.** A reel that gets no views is a hook problem. The script's HOOK OR
PROFILE block applies this rule from the columns that exist: a post at 2x or
more with less than half the account's usual follows per 1k is PROFILE; a post
under 0.7x with a hold at 3s below the account's median is HOOK (only from 10
comparable posts). If PROFILE shows up, stop rewriting hooks and go to
`/ig-profile`.

## Output

The script's report first, unedited, then your reading of it:

```
AUDIT  ·  31 posts  ·  2026-06-12 to 2026-09-05  ·  median views 4,100
baseline: previous 10 posts of the same format (min 5)  ·  rates per 1k reach

TOP 5 BY OUTLIER MULTIPLE
   18.2x  2026-08-24  reel   74,600  sh 1.7  sv 3.1  fo 2.2  nf 62%  h3 71%  #3  Nobody tells you...
  ...
HOOK OR PROFILE
  PROFILE  2026-08-24  18.2x the usual reach but 0.4 follows per 1k (account median 1.9)
COMPARISONS  (7 run, groups of 5+ only)
  hook formula
    #1   median 2.40x vs 0.90x for the rest (n=6 vs 19, 5/6 above the rest's median): a difference worth testing on purpose

WHAT I READ
1. The posts where you were the one who looked bad: 4 of the top 5. n=5, read
   by hand, not tested.
2. Cost Confession hooks went with 2.4x the rest: worth testing on purpose.
   Next two reels: #1 on purpose, then re-run.
3. Your best reel did not convert. Fix the profile before the next hook.

STOP: listicles (3 of the bottom 5, no sends).
DO MORE: #1, on purpose, and measure it.
```

Write the summary with `--out ~/.claude/instagram/insights.md`. `/ig-plan` and
`/ig-reel` read it, so next week is built on the user's own evidence rather
than on defaults, and `/ig-viral` can filter the swipe file to the formulas
that work for this account.

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
