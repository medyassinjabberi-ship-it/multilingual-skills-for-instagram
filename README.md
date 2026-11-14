# multilingual-skills-for-instagram

**FR** · [EN below](#english)

13 skills Claude pour gérer un compte Instagram, en **anglais, français et darija** (écriture arabe ou arabizi). Gratuit, MIT, sans inscription, sans clé API.

**Rien n'est publié sans toi.** Les skills écrivent, c'est toi qui postes.

## Installer

Dans **Claude Code** (les plugins ne s'installent pas dans l'app Claude du téléphone) :

```
/plugin marketplace add medyassinjabberi-ship-it/multilingual-skills-for-instagram
/plugin install multilingual-skills-for-instagram@multilingual-skills-for-instagram
```

Ou colle ceci dans Claude :

```
https://github.com/medyassinjabberi-ship-it/multilingual-skills-for-instagram

Installe ce skill, puis vérifie que /ig-reel marche.
```

Il faut **Python 3** pour les 5 outils qui calculent (hooks, timing, caption, humanizer, viral).
- Sous Windows : `winget install Python.Python.3.13`. Si la commande `python3` n'existe pas, les skills utilisent `py -3` ou `python`.
- Sous Mac : Python est souvent déjà là.

Ensuite, copie `templates/voice.md` dans `~/.claude/instagram/voice.md` et remplis-le. Mets surtout la ligne `language:` (`fr`, `en`, `ar` ou `aeb-latn`). Tous les skills la lisent.

## Ce que fait ce pack

- **Le français reste du français.** Les espaces insécables, les `’` et les `« »` sont gardés. La liste anti-ChatGPT française ne remplace que ce qui est sans risque ; le reste est signalé, et c'est Claude qui réécrit la phrase.
- **L'arabe et l'arabizi sont comptés correctement.** Les marques de direction et les emojis ne sont jamais détruits. Plus de plantage sous Windows dès qu'il y a de l'arabe.
- **Pas de fausse note.** Les scores ont été calibrés sur l'anglais : hors anglais, chaque signal s'affiche seul, avec la mention « non calibré », et Claude juge le sens avec une grille.
- **La darija n'est jamais inventée.** Claude donne la structure de chaque ligne (son rôle, ce qu'elle doit contenir, sa durée) et te laisse les mots. Il propose une formulation seulement si tu la demandes, marquée « brouillon à valider ».
- **5 hashtags maximum**, comme la limite d'Instagram depuis décembre 2025.
- **Ramadan :** `/ig-plan` prend les heures de tes Insights et tient compte du Ramadan.

## Les 13 skills

| commande | ce qu'elle fait |
| --- | --- |
| `/ig-reel` | Une idée → un reel : 3 hooks tirés de 26 formules, le script, le texte à l'écran, le timing. |
| `/ig-viral` | Trouve ce qui marche dans ta niche, classé par rapport à la médiane de chaque compte. |
| `/ig-caption` | La caption, vérifiée : ce que le feed montre avant « … plus ». |
| `/ig-carousel` | La cover qui fait swiper, puis le texte de chaque slide. |
| `/ig-story` | Les stories du jour, et quel sticker mettre où. |
| `/ig-profile` | Ton profil noté sur 100 selon 12 critères, puis réécrit. |
| `/ig-plan` | La semaine : quoi poster, quel format, quand, et avec qui interagir. |
| `/ig-human` | Retire les traces de ChatGPT et note le texte. |
| `/ig-comment` | Des commentaires chez les autres qui sonnent humain. |
| `/ig-reply` | Trie les commentaires sous tes posts et écrit les réponses. |
| `/ig-dm` | Les DM : la livraison du mot-clé, le premier message, les relances. |
| `/ig-repurpose` | Une vidéo longue → 4 à 6 posts (anglais ↔ français). |
| `/ig-audit` | Ce qui a vraiment marché dans tes posts, et pourquoi. |

## Tests

```bash
python3 -X utf8 tests/test_pack.py
```

Ces tests vérifient :
- que chaque composant fait ce qu'il doit ;
- que le français, l'arabe et l'arabizi ne sont jamais abîmés ;
- que tout tourne sous Windows, même avec de l'arabe.

---

## English

13 Claude skills to run an Instagram account, in **English, French and Tunisian Darija** (Arabic script or arabizi). Free, MIT, no signup, no API key.

**Nothing gets posted until you say yes.** These skills write. You post.

### Install

```
/plugin marketplace add medyassinjabberi-ship-it/multilingual-skills-for-instagram
/plugin install multilingual-skills-for-instagram@multilingual-skills-for-instagram
```

You need **Claude Code** (plugins do not install in the Claude chat app) and Python 3 for the five tools; on Windows, `py -3` or `python` works if `python3` does not. Then copy `templates/voice.md` to `~/.claude/instagram/voice.md` and set its `language:` line to `en`, `fr`, `ar` or `aeb-latn`.

### What it does

- **Unicode-safe tools:**
  - words are counted correctly in French, Arabic script and arabizi;
  - French typography and Arabic direction marks are kept;
  - emoji and flags are never broken;
  - no crash on a Windows console.
- **Honest scores:** the thresholds were calibrated on English. In any other language each signal is shown on its own, marked "not calibrated", and Claude judges meaning with a grid in the SKILL.md.
- **Darija is never invented:** Claude gives the structure with blanks to fill, and writes a draft only on request.

### License

MIT. See [LICENSE](LICENSE).

*Not affiliated with, endorsed by or sponsored by Instagram or Meta. Instagram is a trademark of Meta Platforms, Inc. · Ce projet n'est ni affilié à Instagram ni à Meta.*
