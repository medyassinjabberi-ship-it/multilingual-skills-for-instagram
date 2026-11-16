---
name: ig-plan
description: >-
  Build the week on Instagram - what to post, which format, when, and who to
  engage with. Use when the user says "plan my week", "what should I post",
  "content calendar", "I have nothing to post about", or wants a posting
  schedule and an engagement list.
---

# ig-plan

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.

The control room. Everything else in this pack executes; this decides what gets
executed. Run it once a week, on the same day.

## Input

If `~/.claude/instagram/voice.md`, `insights.md`, `swipe.md` and `log.md`
exist, read them. `insights.md` is what worked on this account, computed by
`/ig-audit`; it outranks everything. The swipe file is the user's evidence from
`/ig-viral` about which formulas are landing in their niche right now, and it
outranks anything in this file.

Then run the journal, which `/ig-reel` and `/ig-carousel` keep:

```bash
python3 ../ig-reel/journal.py recent --days 14
```

Its REPEATS block names any formula or theme used twice in a fortnight, two
posts of the same type back to back, and scripts approved but never marked
posted. Do not plan a repeat without saying so, and ask about the unposted ones
before planning new work: a backlog of shot-but-not-posted reels is next week.
If `ig-reel` is not installed next to this skill, read
`~/.claude/instagram/journal.jsonl` directly: one JSON object per line, with
`id`, `created`, `status` (ready, posted, dropped), `format`, `hook`, `formula`,
`lang`, `theme`, `type` and `posted`. If the journal is missing, fall back on
`log.md`.

If they do not exist, ask for four things and write them down:

1. What the user sells, and to whom.
2. The three or four themes they want to be known for.
3. What actually happened this week: a client call, a number, a mistake, a
   thing they built, an argument they had. This is where posts come from.
4. Ten accounts worth being visible to.

## What to post

Four to five posts a week, and at least three of them Reels. Reels are the only
format on Instagram that reliably reaches people who do not follow the account.
Carousels go deep with the people who already do. Stories are daily and are
planned separately.

Mix across the week, never two of the same type back to back:

| type | share | job |
| --- | --- | --- |
| **Proof** | 1 per week | something that happened, with a number. Reel. |
| **Teach** | 1 to 2 per week | one thing the viewer can do today. Reel or carousel. |
| **Opinion** | 1 per week | a position that could lose you followers. Reel. |
| **Story** | 1 per fortnight | a scene with a cost. Reel. |
| **Offer** | 1 per fortnight | what you sell, said plainly, no apology. Carousel or stories. |

For each slot give: the theme, the specific angle from what actually happened
this week, the format, the type (proof, teach, opinion, story, offer), and the
hook formula number from `ig-reel/hooks.json`. When `insights.md` names a
formula as "worth testing on purpose", put it in the week on purpose, once, and
say it is the test.
Not a topic, an angle. "AI" is not a plan. "The proposal we lost because the
draft had an em dash in it" is a Reel.

## When to post

Take the hours from the user's own Insights (Professional dashboard, Total
followers, Most active times), not from a rule of thumb. Ask for a screenshot if
you do not have it. Only without Insights, fall back on this: post when the
audience is awake and not at work, which for most consumer audiences is early
evening local time and for a business audience early morning.

**Ramadan and other seasons change the clock.** During Ramadan, for an audience
that fasts, activity moves: low in the afternoon, a peak after iftar and late
at night, another before suhoor. Plan the month separately, keep the themes
respectful of it, and check the dates for that year rather than assuming them.
The same goes for Eid, back-to-school and the summer, when the audience is
somewhere else.

But say this plainly: **the hour matters far less than the first two seconds.**
Instagram will keep showing a Reel for days if it performs, and will bury a
well-timed one that does not. If the user is optimising posting times before
their hooks work, they are polishing the wrong thing, and you should say so.

Anchor times to the audience's timezone, not the user's, if those differ.

## The engagement round, which is not optional

20 minutes a day, before posting, not after. Build a list of 10:

- **5 reach** - accounts with an audience the user wants, where a good comment
  gets seen. Comment early, before the thread is 200 deep.
- **3 peers** - same size, same field. This is the group that reciprocates.
- **2 buyers** - people who could actually buy. Comment for weeks before any
  DM, and never pitch in a comment.

Hand the list to `/ig-comment`.

## Output

```
WEEK OF SEP 15

MON  engage only  (20 min, list below)
TUE  7:30pm  REEL      PROOF    #5  Time Collapse   - 5hr proposal to 20 min
WED  stories only + engage
THU  7:00pm  CAROUSEL  TEACH    Job B caption       - the 4-slide clause breakdown
FRI  7:30pm  REEL      OPINION  #2  Negative Command - stop doing discovery calls
SAT  -
SUN  6:00pm  REEL      STORY    #21 Mid-Sentence    - the refund email

STORIES  every day, 3 to 5 frames, question box on Thursday.

ENGAGE  (5 reach / 3 peers / 2 buyers)
  ...

Say "write Tuesday" and I will draft it.
```

Write the plan to `~/.claude/instagram/plan.md` so the other skills can read
it. Nothing is scheduled or posted anywhere. This is a plan and the user runs
it.

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
