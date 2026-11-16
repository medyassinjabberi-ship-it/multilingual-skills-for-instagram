---
name: ig-human
description: >-
  Strip the machine fingerprint out of any draft - em dashes, AI slop words,
  invisible watermark characters - and score it against a five-check detection
  panel before it goes out. Use whenever text needs to sound human, when the
  user says humanize, "does this sound like AI", "remove the em dashes",
  "de-slop this", "this sounds like ChatGPT", or before any caption, script,
  comment, reply or DM is shown to the user.
---

# ig-human

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.
> **Windows:** if `python3` is not found, run the same commands with `py -3` (or `python`).

Two tools live in this folder and they both actually run. Use them. Do not
eyeball this.

```bash
python3 humanize.py draft.txt --report        # clean it, show what changed
python3 detect.py draft.txt                    # score it, five checks
python3 detect.py before.txt after.txt         # prove the delta
python3 humanize.py draft.txt --lang fr --report   # say the language when you know it
python3 voice.py draft.txt                     # the user's own "never say" words, any language
```

`voice.py` reads two fields the user filled in `~/.claude/instagram/voice.md`:
**Words I would never say out loud** and **Clients, numbers or names I cannot
say publicly**. It finds them in the draft as whole words or phrases, case and
accents ignored, Arabic diacritics ignored and attached prefixes (و ف ب ل ك ال)
allowed. Because the words come from the user, it works in Darija and arabizi
too. A CANNOT SAY hit comes out before anything is shown as ready; a NEVER SAYS
hit gets rewritten in the user's own words.

`slop.json` holds what does not depend on a language: 18 invisible character
classes, 11 typographic substitutions and 4 structural tells (emoji, hashtag
wall, emoji bullets, caps). The words live in one file per language:

- `lex/en.json`: 154 English stock words and phrases with plain replacements,
  and 12 English structural tells. The last block of each list is
  Instagram-specific.
- `lex/fr.json`: the French list. French agrees in gender and number and
  elides (`l'`, `d'`), which a find-and-replace cannot do. So only safe
  deletions are applied (empty adverbs, whole essay formulas such as "il est
  important de noter que"). Every other entry is `"mode": "report"`: the report
  lists it under **STOCK WORDS** with a hint, and you rewrite the whole sentence
  yourself.
- No file for a language (Arabic script, arabizi for now): no word is changed,
  SLOP DENSITY says "n/a", and you read the draft for stock phrases yourself.

The English list is never applied to French or Arabic text: it would rewrite
"crucial" in a French sentence into the English "important" grammar. Every list
is meant to be edited. If the user has a word
they always use that the lexicon strips, take it out of the file.

## Why this matters more on Instagram than it looks

Captions are short and scripts get said out loud. A written-sounding line in a
600-character caption is a larger share of the text than the same line in an
essay, and a voiceover that nobody could say naturally is obvious in the first
take. The tell here is not a detector flagging the post. The tell is a person
scrolling past something that reads like a brand, or a creator stumbling over
their own script.

## What gets fixed automatically

**1. Invisible characters.** Zero-width spaces and joiners, word joiners, soft
hyphens, byte-order marks, Unicode tag characters, invisible separators,
non-breaking and narrow spaces. A keyboard does not produce these. They survive
copy-paste, they are invisible in every editor, and they are the most
mechanical thing in generated text. `humanize.py` deletes every one, including
any remaining Unicode format character it does not have a name for, **except
what a language or an emoji really uses**: French no-break and narrow spaces
(before `: ; ! ?`, inside `« »`, in `18 000`), Arabic direction marks and
joiners (RLM, LRM, ALM, ZWNJ, ZWJ), the joiner inside a family or job emoji,
and the tag characters inside a regional flag. The report lists them under KEPT.

**2. Typography.** Em dash to comma, en dash to hyphen, curly quotes to
straight, ellipsis to three dots, bullet character to hyphen. In French the
apostrophe `’` and the guillemets `« »` stay: they are correct French. The em dash pass
is the one that matters: it collapses the dash to a comma and then cleans up
the double punctuation and orphaned periods that leaves behind.

**3. The slop lexicon.** delve, leverage, robust, seamless, crucial, testament
to, "in today's fast-paced world", plus the Instagram block: "stop scrolling",
"in today's video", "follow for more", "tag someone who needs this", "the
algorithm loves", "run don't walk". Each swapped for a plain word or deleted,
with capitalisation preserved and URLs, @handles, #hashtags and domains left
untouched.

## What does NOT get fixed automatically

Structural tells get **flagged, not rewritten**, because changing the shape of
a sentence needs judgement:

- "It's not just X, it's Y" and "not only X but also Y"
- Rule-of-three triads
- Rhetorical one-word question lines: "The result?"
- The video preamble: "in this video I'm going to show you"
- Emoji bullet lists
- Three or more shouted words in a row
- Hashtag walls
- Reflex bait: "follow for more", "tag someone who", "double tap if"

That list is your job. Rewrite each flagged line by hand, keeping the meaning,
then re-run `detect.py`. This is the part that moves the score from REVIEW to
PASS, and it is the part a script cannot do.

## The five checks

`detect.py` scores five signals 0-100, higher is more human:

| check | what it measures | machine looks like |
| --- | --- | --- |
| BURSTINESS | sentence-length variation | every sentence the same length |
| SPECIFICITY | numbers, names, concrete markers per 100 words | abstract nouns, no figures |
| SLOP DENSITY | lexicon hits per 100 words | stock vocabulary |
| FINGERPRINT | invisible chars, em dashes, curly quotes per 1k chars (`’` is not counted; `“ ”` and `…` still are, as English was calibrated with them, although iPhones type those too: read that signal with care) | typographically perfect |
| VOICE | contractions, person, structural tells | no contractions, staged reveals |

The verdict weights the mean at 60% and the **weakest single check** at 40%,
because one signal is enough. PASS needs an overall of 70+ with no check
below 55.

**Outside English there is no verdict.** The thresholds were set on English
text. In French, Arabic script and arabizi the panel prints each signal marked
"not calibrated" and names the weakest one. FINGERPRINT counts only true
invisibles and em dashes; French VOICE drops the contractions sub-signal
(elision is grammar, not voice); Arabic-script VOICE does not count pronouns,
which are suffixes. Report the signals and what to fix, never "PASS" or a
percentage of "human".

## Say this honestly

These are five local heuristics modelled on the signals public detectors key
on. They run entirely on the user's machine and nothing is uploaded. They are
**not** GPTZero, Originality, Copyleaks, Winston or Turnitin, they do not call
those APIs, and they cannot promise those verdicts. Fixing what they measure
does tend to move those numbers, because they are measuring the same underlying
things. That is the claim. Do not make a bigger one on the user's behalf, and
do not tell a user their text is undetectable.

## Order of operations

1. `humanize.py draft.txt -o clean.txt --report`
2. Read the structural flags. Rewrite those lines yourself.
3. `detect.py draft.txt clean.txt` to show the before and after.
4. If the verdict is not PASS (or, outside English, a signal is low), fix the
   weakest check named in the output and go again. Two rounds is normal. Five means the draft was written by formula,
   and the fix is a different draft, not more passes.
5. Run `voice.py` on the final text. Fix every hit.
6. Show the user the cleaned text and the score. Never the score alone.

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
