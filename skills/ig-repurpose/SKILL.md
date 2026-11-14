---
name: ig-repurpose
description: >-
  Turn one long asset - a YouTube video, podcast, livestream, newsletter, blog
  post or client call - into a week of reels and carousels. Use when the user
  says "repurpose this", "turn this into reels", "I have a video/podcast/
  transcript", "cut this up", or pastes something long and wants it on
  Instagram.
---

# ig-repurpose

> **Language:** answer in the page's language, pass `--lang` to every script, and never invent Darija: see the Language section at the end of this file.

One good long asset contains four to six posts. Most people extract one and
throw the rest away.

## Input

A transcript, an article, a newsletter, a script, a call summary, a livestream.
If the user gives a URL and this session has a transcript tool, use it;
otherwise ask them to paste. Read the whole thing before extracting anything.

If the source is a video the user owns, ask for the file too. A Reel built on
their own footage beats one built on their own words read again.

**Languages.** You can repurpose between English and French, both ways. You do
not translate into Darija: from an English or French source, give a Darija page
the structure (the claim, the number, the story beat, the ask, the time each
line has) and leave the words to the user. A Darija source can be cut into
posts in Darija, keeping the user's own sentences.

## Extract, do not summarise

A summary of a video is not a Reel. Nobody wants the summary. Go through the
asset and pull out the things that stand alone:

| pull | what it is |
| --- | --- |
| **Claims** | every sentence that would start an argument |
| **Numbers** | every figure, cost, duration, percentage |
| **Stories** | every moment with a person, a scene and a cost |
| **Mechanisms** | every "the way this actually works is..." |
| **Mistakes** | every admission of something that went wrong |
| **Lines** | every sentence already quotable as-is |

List what you found, with counts, before writing anything. If the asset yields
fewer than four items, it is thin, and four posts squeezed out of it will be
thin too. Say that.

## Then pick the format per extract

Not everything is a Reel.

- **Claim, mistake, story** to a Reel. They need a voice and a face.
- **Mechanism, numbered list** to a carousel. They need to be re-read.
- **A quotable line** to a story frame, not a post.

## Then build the week

Each extract becomes one post and each post stands completely on its own. The
viewer has not seen the source and never will. Never write "as I said in my
latest video". The post is the thing.

Assign a hook formula from `ig-reel/hooks.json` to each and vary them. Five
posts from one source with the same hook shape reads as a content mill, because
it is one.

If the source is the user's own video, **use the actual footage**. The clip
where they said the thing, with the real reaction in it, beats a re-record
every time. Cut on the sentence, not on the breath.

Order across the week so the strongest claim goes first, the story lands
midweek, and the mechanism goes last, when the people who liked the earlier
ones are watching for it.

## Output

```
SOURCE: "Why we killed discovery calls" (42 min podcast, 8,900 words)

FOUND  5 claims, 9 numbers, 3 stories, 4 mechanisms, 2 mistakes, 7 quotable lines

WEEK
TUE  REEL      #2  Negative Command  Stop running discovery calls
                                     use the 14:20 clip, he laughs at the end
WED  CAROUSEL  Job B caption         The 4-question form that replaced the call
FRI  REEL      #21 Mid-Sentence      "...and he asked for a refund nine days later"
SUN  REEL      #5  Time Collapse     Six hours a week back, one deleted link

Say "write Tuesday" and I will draft it.
```

Then draft on request, one at a time, each through `/ig-reel` and `/ig-human`.
Do not dump four finished scripts at once. They will all sound the same and the
user will shoot none of them.

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
