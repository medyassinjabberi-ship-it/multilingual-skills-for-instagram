<div align="center">

# multilingual-skills-for-instagram

### Someone to run your Instagram. Probably better than you.

**13 Claude skills** that find what works in your niche, write your reels, plan your week and draft your replies.<br>
In **English**, **French** and **Tunisian Darija** (Arabic script or arabizi).

![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-D97757)
![skills](https://img.shields.io/badge/skills-13-111111)
![languages](https://img.shields.io/badge/EN%20%7C%20FR%20%7C%20darija-ok-2ea44f)
![MIT](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## The problem

Every week, same story: a blank page, a weak hook, a post that goes out late.

**This pack does the work. You film and you post.**

## What it changes for you

### 🔍 "I don't know what to post."
`/ig-viral` goes and looks at what is **actually** working in your niche. Not raw views: every reel is compared with its own account's median. A big account doing 400,000 views just had a normal day. A small account doing 10× its average found something, and that is what you can copy. You walk away with a swipe file: every reel that broke out, the hook formula it used, ready to shoot.

### 🎬 "My hook is weak and I can't even tell."
`/ig-reel` gives you 3 hooks drawn from 26 formulas and runs them through a real script **before** you shoot. The script is a gate: it throws out the broken ones (a greeting, a preamble, nothing concrete, too long to say). Between two hooks that pass, the score is not a predictor, and the pack says so: it picks on stakes, on your real proof, and on what has worked on your account. Then it writes the script, the timing, and a cue sheet of the on-screen text for your editor.

```
HOOK GATE
==============================================================================
ok   84.4 STRONG  Stop posting at 9am. Your audience is asleep.
ok   80.8 STRONG  3 hooks I stole from accounts with 1M followers
out  39.2 WEAK    Here's a quick tip about Instagram growth

Hooks marked out are out: under 50 or a dealbreaker. Between the ones marked ok,
the score does not pick the winner (AUC 0.56 within one creator's own hooks): choose
on stakes, the user's real proof and what worked on this account.
```
<sub>Real `hookscore.py` output, shortened. The score out of 100 exists in English only: in other languages each signal is shown on its own and Claude judges the rest with a grid.</sub>

### 📈 "I don't know what actually worked for me."
`/ig-audit` runs a real script on your own numbers. It doesn't eyeball screenshots. Each post is compared with **its own format's** last 10 posts, so growth doesn't flatter old posts and a carousel isn't judged against reels. Posts younger than 7 days are left out. It only compares along three lines fixed in advance (format, length, hook formula), and each group needs 5 posts or more. Every result comes with its sample size and one of three plain wordings, from "clear" down to "no difference you can rely on". With 8 posts it says "too few to compare". It also tells you when a reel travelled but your profile didn't convert, which is a profile problem, not a hook problem.

```
COMPARISONS  (7 run, groups of 5+ only)
  hook formula
    #1   median 2.40x vs 0.90x for the rest (n=6 vs 19, 5/6 above the rest's median): a difference worth testing on purpose
  7 comparisons: with this many, one of them can look strong by chance. Test a finding on the next posts before believing it.
```
<sub>Illustrative output. Tested on simulated accounts. When there is no real difference, "clear" comes out on 1.5 to 3.5% of 40 to 60-post accounts, and "worth testing" on about 1 in 5. When a formula really does 2.5×, it is caught 61% of the time at 40 posts and 88% at 60.</sub>

### 🔁 It learns your account.
Every reel and carousel you approve goes into a journal: the hook, the formula, the score. When you say it is posted, the audit links its results back to that hook. `/ig-plan` reads the journal and won't hand you the same formula or theme twice in two weeks. `/ig-reel` reads what worked on **your** account before it reads anyone else's. The longer you use it, the less it runs on generic advice.

### 📅 "I post whenever I have time."
`/ig-plan` builds your week: what to post, which format, which day, what time (from your Insights), and who to engage with. It is built on what your audit found and checked against what you posted lately.

### 💬 "Comments everywhere, no time to answer."
`/ig-reply` sorts them all: the potential client describing your problem, the real question, the critic, the troll. It drafts the replies worth sending and skips the rest. A question thirty people are asking? It turns it into your next reel.

### 🤖 "It sounds like ChatGPT from a mile away."
Every text goes through `/ig-human`, which hunts down AI tics. Your captions, replies and DMs sound like you, not like an assistant.

### 🌍 Your language, your words.
English, French or Darija (Arabic script or arabizi). For Darija it never invents anything: it gives you the structure of each line and you put in your own words.

### 🫵 Nothing goes out without you.
It never posts, likes or comments. It writes, **you publish**. No API key, no signup. The pack is free (you need Claude Code).

## Your week in 5 commands

```
monthly     /ig-viral      → what actually worked in your niche
monday      /ig-plan       → what to post, which format, which day, what time
tuesday     /ig-reel       → your idea becomes a reel: hooks, script, on-screen text, timing
            /ig-caption    → the caption, checked against what shows before "… more"
every day   /ig-reply      → your comments sorted, replies drafted
```

## The 13 skills

**Find and plan**

| command | what it does |
| --- | --- |
| `/ig-viral` | You give it 6 to 12 accounts in your niche; Claude reads them in your browser (logged in as you) or from what you paste, and ranks each reel against its own account's median. |
| `/ig-audit` | What really worked in your own posts, computed per format against its own trailing median, with honest sample sizes. |
| `/ig-plan` | Your week: what to post, which format, when (from your Insights, Ramadan included), and who to engage with. |

**Write**

| command | what it does |
| --- | --- |
| `/ig-reel` | One idea → one reel: 3 hooks from 26 formulas, the script, the on-screen text, the timing. |
| `/ig-carousel` | The cover that earns the swipe, the copy for each slide, checked by a linter, then **the 1080×1350 PNG files**, rendered by the browser you already have. Arabic slides are laid out right to left. |
| `/ig-caption` | The caption, checked against what the feed shows before "… more". 5 hashtags max, the platform limit since December 2025. |
| `/ig-story` | Today's stories, and which sticker goes where. |
| `/ig-repurpose` | One long video → 4 to 6 posts (English ↔ French). |
| `/ig-human` | Strips the ChatGPT out of any text, then checks it against the words **you** said you never say (any language, Darija included). |

**Reply and grow**

| command | what it does |
| --- | --- |
| `/ig-reply` | Sorts the comments under your posts and drafts the replies. |
| `/ig-comment` | Comments on other people's posts that sound human. |
| `/ig-dm` | DMs: keyword delivery, first message, follow-ups. |
| `/ig-profile` | Your profile scored against 12 criteria, then rewritten. |

## Install

In **Claude Code** (plugins do not install in the Claude mobile or chat app):

```
/plugin marketplace add medyassinjabberi-ship-it/multilingual-skills-for-instagram
/plugin install multilingual-skills-for-instagram@multilingual-skills-for-instagram
```

Or just paste this into Claude Code:

```
https://github.com/medyassinjabberi-ship-it/multilingual-skills-for-instagram

Install this skill, then check that /ig-reel works.
```

**Then one step:** copy `templates/voice.md` to `~/.claude/instagram/voice.md` and fill it in. That is your voice: how you talk, what you never say, who you are talking to. Above all set the `language:` line (`en`, `fr`, `ar` or `aeb-latn`). Every skill reads it.

<details>
<summary><b>Python (for the tools that compute)</b></summary>

The hook, timing, caption, humanizer, voice, viral, audit, journal and carousel tools run on **Python 3**, standard library only. The carousel renderer also uses Chrome, Edge or Chromium if one is installed.
- Windows: `winget install Python.Python.3.13`. If `python3` does not exist, the skills use `py -3` or `python`.
- Mac: Python is often already there.

</details>

<details>
<summary><b>Tests</b></summary>

```bash
python3 -X utf8 tests/test_pack.py   # Windows: py -3 -X utf8 tests/test_pack.py
```

They check that every component does its job, that French, Arabic and arabizi text is never damaged, that the audit's baselines and wordings behave on known data, and that everything runs on Windows, even with Arabic.

</details>

## License

MIT. See [LICENSE](LICENSE).

---

<sub>Not affiliated with, endorsed by or sponsored by Instagram or Meta. Instagram is a trademark of Meta Platforms, Inc.</sub>
