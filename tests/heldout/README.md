# Held-out hooks (empty on purpose)

This folder holds real hooks with their real results, used only to check
whether the scores line up with what actually happened. Nothing in it is ever
used to write a word list, a dealbreaker or a threshold. A hook used to build
a rule cannot also test it.

Format: one TSV per language, `hooks_<lang>.tsv`, with this header:

```
lang	hook	views	account_median	source
```

- Real hooks only: the first line of reels that were really posted, as spoken
  or as written on screen. No hook written for this file.
- `source` says where the hook comes from (your account, a public reel with its
  link).
- Darija and arabizi hooks come from a native speaker, in their own wording.

Until this folder has at least 40 hooks across six accounts in a language, the
scores for that language stay "not calibrated".
