---
name: ig-reel
description: >-
  Write an Instagram Reel from a raw idea - hook options off 26 formulas, the
  spoken script, the on-screen text, and a timed beat sheet - in the user's own
  voice and scored before they shoot it. Use whenever the user wants a Reel, a
  short-form video script, a hook, a voiceover, "make a reel about X", "what
  should I say in this video", or is about to record and does not have the
  first line yet.
---

# ig-reel

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.
> **Windows:** if `python3` is not found, run the same commands with `py -3` (or `python`).

Turns one raw idea into a Reel that somebody finishes.

Three tools live in this folder and they all actually run. Use them. Do not
eyeball the hook and do not guess at the length.

```bash
python3 hookscore.py hooks.txt              # catch broken hooks (a gate, not a ranking)
python3 hookscore.py --hook "one line"      # check a single one
python3 beats.py script.txt --target 30     # timed beat sheet + on-screen cards, before you shoot
python3 hookscore.py hooks.txt --lang fr    # French, Arabic script (ar) or arabizi (aeb-latn)
python3 journal.py add --format reel --hook "..." --formula 5 --lang en   # on "yes"
python3 journal.py recent                   # what was made lately, what repeats
```

## Outside English: what the script measures and what you judge

`hookscore.py` was tested on English hooks. In French, Arabic script and
arabizi it measures the mechanics only (LENGTH, SPECIFICITY as numbers and
names, FRONTLOAD, greetings and preambles). It prints no overall score: it
counts the rules each hook breaks and ranks by that, fewest first. That says
which hooks break a rule, not which one is good. STAKES and ADDRESS print "n/a". Judge them yourself, for each hook, with this
grid, and show your reading next to the script's numbers:

| question | strong | weak |
| --- | --- | --- |
| **Stakes**: what can the viewer lose or miss? | a cost, a mistake, a loss, a "before it is too late" | a topic, a statement, nothing at risk |
| **Address**: who is it aimed at? | "you" / "tu" / "vous" / "enti", or an imperative | nobody: a general truth |
| **Formula**: which of the 26 in `hooks.json`? | one, named, by reading the meaning | none fits: say so |
| **Said aloud**: could the user say it in one breath, in their own words? | yes | it sounds written or translated |

Known limit, kept so English scores stay calibrated: in English, `hookscore.py` matches weak openers by prefix, so a hook starting with "You" is penalised as "yo". Do not relay that penalty as real.

`beats.py` times at 165 words per minute, an English rate. Arabic script packs
prefixes into one word, so the same script has fewer, longer words. Ask the user
to read one script out loud with a timer once, then pass `--wpm` and write the
number in `voice.md` under Pace.

## Before you write

1. Read `~/.claude/instagram/voice.md` if it exists. That is the user's voice
   profile: how they talk on camera, what they never say, who they are talking
   to. If it does not exist, ask for **three of their own reels**, transcribe or
   read them, infer the voice, and write the file. A script in the wrong voice
   is unusable, because they have to say it out loud.
2. Read `hooks.json` in this folder. 26 formulas, each with a template, a filled
   example, the on-screen version, what it is for, and how it gets ruined.
   Four of them are in there because they kept turning up in real hooks, not
   because they completed a pattern.
3. If the idea is thin, do not pad it. Ask one batched question: what happened,
   to whom, and what did it cost or return. A Reel needs one specific true
   thing. Get it before writing.
4. If `~/.claude/instagram/swipe.md` exists, read it. `/ig-viral` writes that
   file, and it is the user's own evidence about which formulas are working in
   their niche right now. It beats the defaults in this file.
5. If `~/.claude/instagram/insights.md` exists, read it. `/ig-audit` writes it
   from the user's own posts, and it outranks the swipe file: it is what worked
   on this account. Run `python3 journal.py recent` too, so the new reel does
   not reuse a formula or a theme from the last two weeks without saying so.

## The shape

A Reel is decided in the first two seconds and kept by the next five.

```
0:00 - 0:02   HOOK        the claim. Spoken line and on-screen line, written
                          separately. Motion in the first frame, not a static face.
0:02 - 0:07   THE STAKE   why this matters to the person watching. One line.
0:07 - ...    THE BODY    one idea per beat, and the frame changes every beat.
LAST 3s       THE PAYOFF  deliver what the hook promised, then the single ask.
LAST LINE     THE LOOP    echo one word from the hook so the replay lands clean.
```

Length: 15 to 45 seconds is the working range. Reels run to 3 minutes and
almost nobody should use it. Under 7 seconds the loop counts inflate and
nothing else does.

## The loop

**1. Pick three hooks, not one.** Run the idea through `hooks.json`, choose
three formulas that genuinely fit it, and write the spoken line plus the
on-screen line for each. Different formulas, not three rewrites of one.

**2. Gate them, then choose.** Put the three spoken lines in a file, one per
line, and run `hookscore.py`. It is a **gate, not a ranking**. It reliably
catches broken hooks: a greeting, a preamble, nothing concrete, too long to say
in three seconds. In English a hook under 50 is out; in other languages, a hook
that breaks a rule is out. Rewrite or replace it.

Among the hooks that pass, the score does not tell you which one will travel:
tested on real hooks, it separated a creator's own hits from their misses at
AUC 0.56, barely better than a coin (see the top of `hookscore.py`). So do not
pick the highest number. Choose with the grid above (stakes, address, formula,
said aloud), with the user's own evidence (`insights.md`, then `swipe.md`), and
with which hook carries the user's real proof. Say why you chose it in one line.

**3. Write the script** on the winning hook. Plain spoken language, the way the
user actually talks. Contractions. Short lines. No sentence they would have to
rehearse.

**4. Time it.** Write the on-screen text into the same file, each card on its
own line starting with `[on-screen]`, just above the spoken line it goes up
with. Run `beats.py script.txt --target {length}`. Fix every flag: a hook past
3 seconds, any beat over 4 seconds, a run of beats with nothing concrete in
them, no loop, no card at frame 1, a card over six words. Re-run until it is
clean. The ON-SCREEN CARDS block is the editor's cue sheet: hand it over as is,
and say the timecodes are estimates to retime after recording.

**5. Humanize it.** Run the script through `/ig-human` before showing it,
including its `voice.py` check against the words the user never says. A
written-sounding line is obvious the moment someone says it out loud.

**6. Print the block.** Not while anything is still a placeholder: if the
script or a card still has a `{{...}}` (`hookscore.py` and `beats.py` print
"pending"), ask the user for the real value and stop there. A reel with a
placeholder is not READY and is not logged. Otherwise: the script in a fenced
block, the on-screen text as a separate list with timings, and then:

```
REEL READY
hook:       #1 Cost Confession, scored 54.8 OK
length:     28.4s across 9 beats at 165 wpm
on-screen:  6 cards
humanizer:  4 artefacts stripped, human score 81 PASS
voice:      clean (0 words the user never says)
caption:    run /ig-caption next

Reply "yes" to log it, or tell me what to change.
```

**7. Never publish.** This skill produces a script. The user shoots it and
posts it. On "yes", log it:

```bash
python3 journal.py add --format reel --hook "{first spoken line}" --formula {id}         --lang {lang} --theme "{theme}" --type {proof|teach|opinion|story|offer}         --hookscore {English overall, or leave out} --length {seconds}
```

Tell the user the id it prints, and that when the reel is live they can say
"posted" (with the link if they have it). Then:

- If more than one entry is `ready` (`python3 journal.py list --status ready`),
  ask which one went out. Never pick one by guessing.
- Ask the date if they did not say it ("today?"), and the link: the link is
  what lets the audit match the post for sure.
- Run `python3 journal.py posted {id} --date YYYY-MM-DD --permalink {link}`.

Never mark a post as posted on a guess. This is what lets `/ig-audit` trace a result
back to the hook and the formula that produced it. An older
`~/.claude/instagram/log.md` is still read by the other skills; new entries go
to the journal.

## On-screen text is a separate script

Write it separately, every time. It is read before it is heard.

- **Six words or fewer per card.** It is being read at arm's length by someone
  who is not listening yet.
- **The hook card is up at frame 1**, not after a beat of silence.
- **Keep it inside the safe zone.** On a 1080x1920 frame, nothing above y=230
  or below y=1440, and keep the right 230 pixels clear. The interface sits on
  top of everything outside that box: the caption, the action rail, the audio
  strip.
- **Never put the hook where the caption sits.** That is the bottom of the
  frame and it is covered.
- **Burn in captions for the body.** Most people watch muted first.

## Rules that make the difference

- **One idea per Reel.** If the script has two, you have two Reels. Say so.
- **Numbers over adjectives.** "$4,200" beats "a lot". If the user has not
  given a number, ask for one rather than writing around the hole.
- **Cut the intro.** No greeting, no "in this video", no name, no logo sting.
  The video starts at the sentence you would normally reach at second six.
- **Change the frame every beat.** A static shot for 8 seconds is where people
  leave, and `beats.py` will flag it.
- **One ask at the end.** Comment a keyword, save it, or follow. One.
- **Never fabricate.** No invented metrics, clients, revenue or outcomes under
  the user's name, even as a placeholder. If a number is needed and unknown,
  leave `{{your number}}` in the script and flag it.
- **Do not write a script around a trending audio the user cannot use.** If the
  idea needs the user's own voice, say so.

## Example

```
/ig-reel we cut proposal time from 5 hours to 20 minutes with one template
```

```
HOOK GATE
  ok   77.8  #1  Cost Confession "I was losing {{hours per week}} hours a week to proposals."
                                 on screen: {{N}} HOURS A WEEK, GONE
                                 pending: the user has not said how many hours
  ok   51.2  #5  Time Collapse   "Proposals used to take me five hours. Twenty minutes now."
                                 on screen: 5 HOURS -> 20 MIN
  out  36.6  #9  The Steal       "Steal the proposal template that did it."
                                 on screen: STEAL THIS

#9 is out. #1 and #5 pass the gate. #1 scores higher only because the
placeholder counts as a number: the score does not choose between them. #5 uses
nothing but what the user said and reads in one glance on screen, so it is the
one to shoot today. #1 is better on stakes, and it becomes the pick the moment
the user answers: "How many hours a week did proposals cost you before?"
Never fill that number in yourself.
```

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
