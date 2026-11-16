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
`/ig-reel` gives you 3 hooks drawn from 26 formulas and has a real script score them **before** you shoot. Then it writes the script, the on-screen text and the timing.

```
HOOK RANKING
==============================================================================
->  84.4 STRONG  Stop posting at 9am. Your audience is asleep.
    80.8 STRONG  3 hooks I stole from accounts with 1M followers
    39.2 WEAK    Here's a quick tip about Instagram growth

Shoot the top one. If the top one is under 50, none of these are the hook.
```
<sub>Real `hookscore.py` output, shortened. The score out of 100 exists in English only: in other languages each signal is shown on its own and Claude judges the rest with a grid.</sub>

### 📅 "I post whenever I have time."
`/ig-plan` builds your week: what to post, which format, which day, what time (from your Insights), and who to engage with. `/ig-audit` reads your past posts and tells you what really worked, why, and what to **stop** doing.

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
| `/ig-audit` | What really worked in your own posts, and why. |
| `/ig-plan` | Your week: what to post, which format, when (from your Insights, Ramadan included), and who to engage with. |

**Write**

| command | what it does |
| --- | --- |
| `/ig-reel` | One idea → one reel: 3 hooks from 26 formulas, the script, the on-screen text, the timing. |
| `/ig-carousel` | The cover that earns the swipe, then the copy for each slide. |
| `/ig-caption` | The caption, checked against what the feed shows before "… more". 5 hashtags max, the platform limit since December 2025. |
| `/ig-story` | Today's stories, and which sticker goes where. |
| `/ig-repurpose` | One long video → 4 to 6 posts (English ↔ French). |
| `/ig-human` | Strips the ChatGPT out of any text. |

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
<summary><b>Python (for the 5 tools that compute)</b></summary>

The hook, timing, caption, humanizer and viral tools run on **Python 3**.
- Windows: `winget install Python.Python.3.13`. If `python3` does not exist, the skills use `py -3` or `python`.
- Mac: Python is often already there.

</details>

<details>
<summary><b>Tests</b></summary>

```bash
python3 -X utf8 tests/test_pack.py   # Windows: py -3 -X utf8 tests/test_pack.py
```

They check that every component does its job, that French, Arabic and arabizi text is never damaged, and that everything runs on Windows, even with Arabic.

</details>

## License

MIT. See [LICENSE](LICENSE).

---

<sub>Not affiliated with, endorsed by or sponsored by Instagram or Meta. Instagram is a trademark of Meta Platforms, Inc.</sub>
