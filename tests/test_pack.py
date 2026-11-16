#!/usr/bin/env python3
"""
Component tests for the pack. Standard library only.

  python3 -X utf8 tests/test_pack.py          (or: python3 -m unittest discover tests)

What is tested:
  - exact behaviour of each component (counting, characters kept or removed,
    hashtags, asks, verdicts withheld outside English, language guessing);
  - order within a language: hooks ranked by rules broken;
  - the intended English behaviour changes, one by one;
  - real crashes: every script is run on a cp1252 console with Arabic input.

  - the tools that close the loop: journal, audit (baselines, guarded
    comparisons, journal join), swipe formula column, beats cards, voice
    check, carousel lint and render (render skipped without a browser).

Not tested here: whether a score predicts views. That needs the held-out set of
real hooks (tests/heldout/), which is never used to build a word list.
"""

import filecmp
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PACK, "skills")
NO_VOICE = os.path.join(tempfile.gettempdir(), "no-such-voice-file.md")


def load(skill, name, root=SKILLS):
    """Import skills/<skill>/<name>.py under a unique module name."""
    folder = os.path.join(root, skill)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location(f"{os.path.basename(root)}_{skill}_{name}",
                                                  os.path.join(folder, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = load("ig-human", "lang")
L.VOICE_FILE = NO_VOICE          # the tests never read the real voice.md
H = load("ig-human", "humanize")
D = load("ig-human", "detect")
C = load("ig-caption", "caption")
K = load("ig-reel", "hookscore")
B = load("ig-reel", "beats")
SW = load("ig-viral", "swipe")
# The scripts share one imported `lang` module: keep it off the real voice.md too.
sys.modules["lang"].voice_langs = lambda *a, **k: []
SLOP = H.load_lexicon()
LEX ={code: H.load_lang_lexicon(code) for code in L.LANGS}

ZWJ, ZWNJ, RLM, LRM, ZWSP = "‍", "‌", "‏", "‎", "​"
NBSP, NNBSP = " ", " "


def humanize(text, lang):
    return H.humanize(text, SLOP, lang, LEX.get(lang))


def resolve(text, declared=None):
    return L.resolve(text, declared, voice_path=NO_VOICE)


def voice(body):
    path = os.path.join(tempfile.mkdtemp(), "voice.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# voice\n" + body + "\n")
    return path


class SharedSync(unittest.TestCase):
    def test_copies_identical(self):
        spec = importlib.util.spec_from_file_location("sync_lang", os.path.join(PACK, "tools", "sync_lang.py"))
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        self.assertIn("ig-audit", sync.SHARED["lang.py"])
        self.assertEqual(set(sync.SHARED["journal.py"]), {"ig-reel", "ig-carousel", "ig-audit"})
        for src, target in sync.pairs():
            with self.subTest(target=target):
                self.assertTrue(filecmp.cmp(src, target, shallow=False), "run tools/sync_lang.py")

    def test_sync_check_passes(self):
        r = subprocess.run([sys.executable, os.path.join(PACK, "tools", "sync_lang.py"), "--check"],
                           capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout)


class Words(unittest.TestCase):
    def test_numbers_are_one_word(self):
        for s in ("18 000", "18" + NBSP + "000", "18" + NNBSP + "000", "18,000"):
            self.assertEqual(L.words(s), ["18000"], s)
        self.assertEqual(L.words("1 200 000"), ["1200000"])

    def test_what_is_not_one_number(self):
        self.assertEqual(L.words("18.000"), ["18", "000"])          # dinars or thousands: not guessed
        self.assertEqual(L.merge_thousands("1,5"), "1,5")
        self.assertEqual(L.words("2024 300"), ["2024", "300"])
        self.assertEqual(L.words("0612 345 678"), ["0612", "345", "678"])

    def test_french_accents(self):
        self.assertEqual(L.words("créateur réseaux sociaux"), ["créateur", "réseaux", "sociaux"])

    def test_arabic_script(self):
        self.assertEqual(len(L.words("13 مشكلة في Instagram ← 0 في 5 دقايق")), 8)
        self.assertEqual(len(L.words("خسرت 18 ألف دينار بسبب بند واحد في العقد.")), 9)
        self.assertEqual(len(L.words("كَتَبَ الوَلَدُ")), 2)            # harakat stay inside

    def test_arabizi(self):
        self.assertEqual(len(L.words("13 mochkla fel Instagram… tarte7 menhom fi 5 dkayek.")), 9)

    def test_lone_dash_is_not_a_word(self):
        self.assertEqual(L.words("hook - payoff"), ["hook", "payoff"])


class Language(unittest.TestCase):
    def test_clear_cases(self):
        self.assertEqual(resolve("I lost my first client because of this, and here is why")[0], "en")
        self.assertEqual(resolve("J'ai perdu mon premier client à cause de ça")[0], "fr")
        self.assertEqual(resolve("13 مشكلة في Instagram في 5 دقايق")[0], "ar")
        self.assertEqual(resolve("13 mochkla fel Instagram, tarte7 menhom fi 5 dkayek")[0], "aeb-latn")

    def test_a_weak_guess_never_unlocks_an_english_verdict(self):
        for text in ("Chbik ma tekhdemch?", "Chouf chnia sar", "Ma tensech tsajel",
                     "Ich habe 18.000 Euro mit einem Vertrag verloren"):
            with self.subTest(text=text):
                lang, _ = resolve(text)
                self.assertNotEqual(lang, "en")
                self.assertFalse(L.calibrated(lang))

    def test_english_units_are_not_arabizi(self):
        for text in ("My b2b reel got 3x more leads", "Post at 7am, not 9pm",
                     "The 2nd reel always flops", "Stop posting at 5pm"):
            with self.subTest(text=text):
                self.assertNotEqual(resolve(text)[0], "aeb-latn")

    def test_declared_wins_and_unknown_is_an_error(self):
        self.assertEqual(resolve("the and is", "fr"), ("fr", "declared"))
        self.assertEqual(resolve("whatever", "arabizi")[0], "aeb-latn")
        self.assertEqual(resolve("whatever", "fr-FR")[0], "fr")
        with self.assertRaises(SystemExit):
            resolve("Perdí 18.000 dólares", "es")

    def test_voice_md_values(self):
        cases = {
            "- **language:** fr": ["fr"],
            "- **Language:** fr, en": ["fr", "en"],
            "language: fr (français)": ["fr"],
            "language: (fr)": ["fr"],
            "language: fr-FR": ["fr"],
            "language: mostly fr": ["fr"],
            "language: en # main": ["en"],
            "language: Darija (arabizi)": ["aeb-latn"],
            "language: tunisian darija": ["ar"],
            "language: derja": ["ar"],
            "- **language:**\n  (the language of the page: `en`, `fr`)": [],
        }
        for body, expected in cases.items():
            with self.subTest(body=body):
                self.assertEqual(L.voice_langs(voice(body), warn=False), expected)

    def test_darija_in_latin_letters_is_arabizi(self):
        for alias in ("tunisian", "darija", "derja", "tunisien"):
            with self.subTest(alias=alias):
                self.assertEqual(resolve("13 mochkla fel Instagram", alias)[0], "aeb-latn")
                self.assertEqual(resolve("13 مشكلة في Instagram", alias)[0], "ar")
        self.assertEqual(L.resolve("13 mochkla fel Instagram", None, voice("language: darija"))[0],
                         "aeb-latn")

    def test_arabic_script_overrides_a_latin_declaration(self):
        lang, source = L.resolve("13 مشكلة في Instagram في 5 دقايق", None, voice("language: fr"))
        self.assertEqual(lang, "ar")
        self.assertIn("script", source)

    def test_only_english_is_calibrated(self):
        self.assertEqual(L.CALIBRATED, {"en"})


class Humanize(unittest.TestCase):
    def test_french_typography_kept(self):
        src = f"Résultat{NNBSP}? 4{NNBSP}200 vues, « vraiment ». C’est ça."
        out, rep = humanize(src, "fr")
        for piece in (f"Résultat{NNBSP}?", f"4{NNBSP}200", "« vraiment »", "C’est"):
            self.assertIn(piece, out)
        self.assertEqual(rep["invisible"], [])

    def test_french_list_never_breaks_grammar(self):
        """Every sentence the review saw broken now comes out unchanged."""
        sentences = [
            "N'hésitez pas à me contacter en DM.",
            "Je veux que vous soyez prêts pour lundi.",
            "C'est une méthode révolutionnaire.",
            "Elle a une approche holistique.",
            "La synergie entre les deux comptes.",
            "L'écosystème Apple est fermé.",
            "Ma pépite du jour : cookies aux pépites de chocolat.",
            "Le moyen de booster ton compte, c'est de sublimer tes photos.",
            "Il faut déverrouiller ton téléphone.",
            "Une connexion authentique avec ton audience.",
            "Le format que l'algorithme adore.",
            "Un hôtel au cœur de la médina.",
            "On va plonger dans la piscine.",
            "Le secteur est en constante évolution.",
            "Rien de crucial, juste un effet de levier.",
            "On le fait de manière optimale.",
            "Par ailleurs, je poste 3 fois par semaine.",
            "Voici un incontournable de Tunis.",
        ]
        for s in sentences:
            with self.subTest(s=s):
                out, rep = humanize(s, "fr")
                self.assertEqual(out.strip(), s)
                self.assertEqual(rep["lexical"], [])

    def test_french_stock_words_are_flagged_not_replaced(self):
        _, rep = humanize("C'est une méthode révolutionnaire, un atout majeur.", "fr")
        flagged = {h["find"] for h in rep["flagged_words"]}
        self.assertEqual(flagged, {"révolutionnaire", "un atout majeur"})

    def test_french_safe_deletions_still_apply(self):
        out, rep = humanize("Il est important de noter que le hook compte. "
                            "C'est un véritable atout.", "fr")
        self.assertEqual(out.strip(), "Le hook compte. C'est un atout.")
        self.assertTrue(rep["lexical"])

    def test_deleted_sentence_opener_leaves_clean_french(self):
        src = ("C’est vrai. Fondamentalement, rien ne change. Indéniablement, ça marche ! "
               "Résolument, on avance.\n— Tu viens ? demanda-t-elle.")
        out, _ = humanize(src, "fr")
        self.assertEqual(out.strip(), "C’est vrai. Rien ne change. Ça marche ! On avance.\n"
                                      "Tu viens ? demanda-t-elle.")

    def test_english_list_not_applied_to_french(self):
        out, _ = humanize("On va leverage cette idée et la rendre seamless.", "fr")
        self.assertIn("leverage", out)
        self.assertIn("seamless", out)

    def test_handles_hashtags_and_links_untouched(self):
        fr = "Merci @booster et @levier pour le #levier. Va sur booster.fr/levier."
        self.assertEqual(humanize(fr, "fr")[0].strip(), fr)
        en = "Thanks @leverage, see bit.ly/leverage and #leverage."
        self.assertEqual(humanize(en, "en")[0].strip(), en)

    def test_arabic_marks_kept(self):
        src = f"مي{ZWNJ}كروفون {RLM}نص{LRM} test ⁧عربي⁩"
        out, rep = humanize(src, "ar")
        for ch in (ZWNJ, RLM, LRM, "⁧", "⁩"):
            self.assertIn(ch, out)
        self.assertTrue(rep["lexicon"].startswith("not available"))

    def test_arabic_marks_kept_inside_a_french_caption(self):
        src = f"Comme on dit : «برشا{RLM} ناس» ont aimé."
        out, _ = humanize(src, "fr")
        self.assertIn(RLM, out)
        self.assertEqual(D.check_fingerprint(src, "fr")[0], 100.0)

    def test_emoji_joiner_and_flag_kept_in_every_language(self):
        family = f"👨{ZWJ}👩{ZWJ}👧"
        flag = "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"
        for code in L.LANGS:
            with self.subTest(lang=code):
                out, _ = humanize(f"Famille {family} et {flag} ok", code)
                self.assertIn(family, out)
                self.assertIn(flag, out)

    def test_machine_invisibles_removed(self):
        out, rep = humanize(f"zero{ZWSP}width and smuggled a\U000E0041b", "en")
        self.assertNotIn(ZWSP, out)
        self.assertNotIn("\U000E0041", out)
        self.assertEqual(sum(h["count"] for h in rep["invisible"]), 2)

    def test_phone_apostrophe_kept_outside_english(self):
        for code in ("fr", "ar", "aeb-latn", "und"):
            with self.subTest(lang=code):
                self.assertIn("’", humanize("C’est bon, w ma t’khafech", code)[0])

    def test_hashtag_wall_starts_past_the_cap(self):
        names = lambda t: [s["name"] for s in H.scan_structures(t, SLOP)]
        five = "Texte.\n\n#un #deux #trois #quatre #cinq"
        self.assertFalse(any("Hashtag wall" in n for n in names(five)))
        self.assertTrue(any("Hashtag wall" in n for n in names(five + " #six")))
        self.assertTrue(any("Hashtag wall" in n for n in names("Texte.\n#a\n#b\n#c\n#d\n#e\n#f")))

    def test_no_linkedin_leftover(self):
        self.assertNotIn("LinkedIn", json.dumps(SLOP))


class Detect(unittest.TestCase):
    EN = ("I lost $18,000 last March because one clause was missing from a contract. "
          "The client paid late. Then they paid less. I had signed the draft without reading "
          "page four, which was where the payment terms lived, and that was on me. Now every "
          "contract gets read out loud before I sign it, twice, by two people.")
    FR = ("Le hook, c’est 80 % du reel, m’a dit un client la semaine dernière. "
          "Il avait raison : j’ai coupé mes 3 premières secondes, et mes vues ont doublé "
          "en 2 semaines. Résultat ? 4 200 vues au lieu de 2 100. Mon conseil : teste-le "
          "sur ton prochain reel, pas sur dix.")

    def test_no_verdict_outside_english(self):
        for code in ("fr", "ar", "aeb-latn", "und"):
            with self.subTest(lang=code):
                _, overall, verdict = D.run(self.FR, SLOP, code, LEX.get(code))
                self.assertIsNone(overall)
                self.assertEqual(verdict, "NOT CALIBRATED")

    def test_english_has_a_measured_verdict(self):
        results, overall, verdict = D.run(self.EN, SLOP, "en", LEX["en"])
        self.assertTrue(all(r[1] != "too short to judge" for r in results.values()))
        self.assertIsNotNone(overall)
        self.assertIn(verdict, ("PASS", "REVIEW", "FLAGGED"))

    def test_phone_apostrophe_is_not_a_fingerprint(self):
        self.assertEqual(D.check_fingerprint("I don’t think it’s that. We’re fine.", "en")[0], 100.0)

    def test_french_spacing_is_not_a_fingerprint(self):
        self.assertEqual(D.check_fingerprint(self.FR.replace(" :", NNBSP + ":"), "fr")[0], 100.0)

    def test_slop_inside_a_link_is_not_counted(self):
        text = " ".join(["word"] * 30) + " see bit.ly/leverage and @leverage"
        self.assertTrue(D.check_slop(text, LEX["en"], "en")[1].startswith("0 stock terms"))

    def test_slop_na_without_lexicon(self):
        score, detail = D.check_slop("نص عربي", None, "ar")
        self.assertIsNone(score)
        self.assertIn("n/a", detail)


class Caption(unittest.TestCase):
    def test_unicode_hashtags(self):
        a = C.analyse("Une phrase.\n\n#créateur #تونس #claude_code #تُونِس", lang="fr")
        self.assertEqual(a["hashtags"], ["#créateur", "#تونس", "#claude_code", "#تُونِس"])

    def test_cap_is_five(self):
        status = lambda a: next(c["status"] for c in a["checks"] if c["check"] == "HASHTAGS")
        self.assertEqual(status(C.analyse("Phrase.\n\n#a1 #b2 #c3 #d4 #e5", lang="en")), "PASS")
        self.assertEqual(status(C.analyse("Phrase.\n\n#a1 #b2 #c3 #d4 #e5 #f6", lang="en")), "FAIL")

    def test_french_asks(self):
        cases = {
            "Commente GUIDE et je te l'envoie en DM.": ["comment a keyword"],
            "Commente CONTRAT et je t’envoie la clause.": ["comment a keyword"],
            "Comment gagner 1 000 abonnés en 30 jours.": [],
            "Je partage ça avec toi : garde la tête froide.": [],
            "Enregistre pour plus tard.": ["save this"],
            "Sauvegarde ce post pour plus tard.": ["save this"],
            "Envoie ce reel à un ami.": ["share this"],
            "Partage à un pote qui poste trop.": ["share this"],
            "Le lien est en bio.": ["link in bio"],
            "Abonne-toi pour la suite.": ["follow"],
            "Écris-moi en DM si tu veux la liste.": ["DM me"],
            "Écris-moi GUIDE en DM.": ["comment a keyword"],
            "Tape 1 si tu veux la suite.": ["comment a keyword"],
            "Lequel tu préfères ?": ["answer a question"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(C.find_asks(text, "fr"), expected)

    def test_flagship_flow_is_one_ask_in_both_languages(self):
        self.assertEqual(len(C.find_asks("Comment CONTRACT and I'll DM you the clause.", "en")), 1)
        self.assertEqual(len(C.find_asks("Commente CONTRAT et je te l'envoie en DM.", "fr")), 1)

    def test_mixed_darija_caption_finds_the_french_ask(self):
        self.assertEqual(C.find_asks("Commente SKILL w nab3athlek el lien", "aeb-latn"),
                         ["comment a keyword"])

    def test_darija_ask_left_to_claude_and_blocks_ready(self):
        a = C.analyse("13 مشكلة في Instagram في 5 دقايق", lang="ar")
        self.assertEqual(next(c for c in a["checks"] if c["check"] == "ONE ASK")["status"], "CHECK")
        self.assertEqual(a["verdict"], "CHECK")

    def test_number_counted_once(self):
        a = C.analyse("J’ai perdu 18 000 € sur un contrat.", lang="fr")
        detail = next(c for c in a["checks"] if c["check"] == "HOOK IS CONCRETE")["detail"]
        self.assertTrue(detail.startswith("1 number"), detail)


class Hookscore(unittest.TestCase):
    def n_issues(self, hook, lang):
        results, _, _, flags = K.run(hook, lang)
        return len(K.issues(results, flags))

    def test_no_overall_number_outside_english(self):
        for code in ("fr", "ar", "aeb-latn", "und"):
            with self.subTest(lang=code):
                _, overall, verdict, _ = K.run("13 مشكلة في 5 دقايق", code)
                self.assertIsNone(overall)
                self.assertEqual(verdict, "NOT CALIBRATED")

    def test_order_french(self):
        good = "J'ai perdu 18 000 € à cause d'une seule clause."
        for bad in ("Salut tout le monde, aujourd'hui je vais vous parler de stratégie de contenu",
                    "Le contenu est important pour réussir sur les réseaux sociaux aujourd'hui en vrai",
                    "Alors voilà, dans cette vidéo je vais vous expliquer quelque chose"):
            with self.subTest(bad=bad):
                self.assertLess(self.n_issues(good, "fr"), self.n_issues(bad, "fr"))

    def test_order_arabic_script(self):
        good = "13 مشكلة في Instagram ← 0 في 5 دقايق"
        bad = "السلام عليكم يا جماعة اليوم باش نحكيو على الستراتيجية متاع المحتوى"
        self.assertLess(self.n_issues(good, "ar"), self.n_issues(bad, "ar"))

    def test_order_arabizi(self):
        good = "13 mochkla fel Instagram, tarte7 menhom fi 5 dkayek."
        bad = "Aslema ya jme3a lyoum bech nahkiw 3al strategie mte3 el contenu"
        self.assertLess(self.n_issues(good, "aeb-latn"), self.n_issues(bad, "aeb-latn"))

    def test_meaning_checks_left_to_claude(self):
        results, _, _, _ = K.run("J'ai perdu 18 000 € sur un contrat.", "fr")
        self.assertIsNone(results["STAKES"][0])
        self.assertIsNone(results["ADDRESS"][0])

    def test_greetings_are_dealbreakers(self):
        for hook, code in (("Salut à tous, voici mon conseil", "fr"),
                           ("Aslema ya jme3a, hedhi nasi7a", "aeb-latn"),
                           ("السلام عليكم، هذي نصيحة", "ar")):
            with self.subTest(lang=code):
                self.assertTrue(K.run(hook, code)[3])

    def test_no_false_greeting_or_opener(self):
        self.assertFalse(K.run("سلامتك أهم من 1000 متابع", "ar")[3])
        for hook, code in (("Bonus : 3 templates gratuits", "fr"),
                           ("YouTube m'a payé 3 000 €", "fr"),
                           ("Tawassol 13 skills fi 5 dkayek", "aeb-latn")):
            with self.subTest(hook=hook):
                self.assertNotIn("weak opener", K.check_frontload(hook, code)[1])

    def test_english_strong_hook(self):
        self.assertEqual(K.run("I lost $18,000 on one missing contract.", "en")[2], "STRONG")


class IntendedEnglishDifferences(unittest.TestCase):
    """English behaviour changes made on purpose."""

    def test_list(self):
        # 1. ’ is not a fingerprint (phones type it): detect.py FINGERPRINT and VOICE.
        self.assertEqual(D.check_fingerprint("don’t", "en")[0], 100.0)
        # 2. Emoji joiners and flags are kept: humanize.py, detect.py.
        self.assertIn(ZWJ, humanize(f"👨{ZWJ}👩", "en")[0])
        # 3. Hashtag wall from 6, not 5 (Instagram's cap is 5).
        # 4. Handles, hashtags and bare domains are not rewritten.
        self.assertIn("bit.ly/leverage", humanize("bit.ly/leverage", "en")[0])
        # 5. Views like 20k and 1.2M are read (swipe.py).
        self.assertEqual(SW.parse_count("1.2M"), 1200000)
        # 6. Files in UTF-16 or with a BOM are read; output is UTF-8 on any console.
        # 7. A line-opening em dash is dropped, not turned into ", ".
        self.assertEqual(humanize("— Who is it?", "en")[0].strip(), "Who is it?")
        # 8. Without --lang or voice.md, a short English hook with too little
        #    evidence is "unknown" and gets no verdict.
        #    Claude always passes --lang (SKILL.md), so this only hits manual runs.
        self.assertEqual(resolve("Stop posting at 5pm")[0], "und")
        self.assertEqual(resolve("Stop posting at 5pm", "en")[0], "en")


class Beats(unittest.TestCase):
    def test_arabic_script_is_timed(self):
        a = B.analyse("خسرت 18 ألف دينار بسبب بند واحد في العقد.\nهذا هو البند اللي نحطّو توّا.",
                      lang="ar", wpm_given=False)
        self.assertEqual(a["total_words"], 15)
        self.assertGreater(a["total_seconds"], 5)
        self.assertTrue(any("English rate" in n for n in a["notes"]))


class Swipe(unittest.TestCase):
    def test_counts_as_instagram_shows_them(self):
        for cell, n in (("412000", 412000), ("412 000", 412000), ("412,000", 412000),
                        ("20k", 20000), ("1.2M", 1200000), ("1,2 M", 1200000), ("3,4K", 3400)):
            with self.subTest(cell=cell):
                self.assertEqual(SW.parse_count(cell), n)
        self.assertIsNone(SW.parse_count("beaucoup"))

    def test_scores_only_for_english_rows(self):
        rows = [
            {"account": "@a", "followers": 4000, "median": 3000, "views": 400000,
             "hook": "nobody tells you your first 30 reels are supposed to flop"},
            {"account": "@b", "followers": 9000, "median": 5000, "views": 90000,
             "hook": "13 mochkla fel Instagram, tarte7 menhom fi 5 dkayek"},
            {"account": "@c", "followers": 50000, "median": 20000, "views": 60000,
             "hook": "J'ai perdu 18 000 € sur un seul contrat, voici la clause"},
        ]
        a = SW.analyse(rows, SW.load_formulas(SW.HOOKS))
        by = {r["account"]: r for r in a["reels"]}
        self.assertIsNotNone(by["@a"]["hook_score"])
        for acc in ("@b", "@c"):
            self.assertIsNone(by[acc]["hook_score"])
            self.assertEqual(by[acc]["formula"], "to classify by reading")


def run_script(script, args, stdin=None, env_extra=None):
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
    env.update(env_extra or {})
    return subprocess.run([sys.executable, script] + args, input=stdin, capture_output=True, env=env)


class CommandLine(unittest.TestCase):
    """Every script runs on a cp1252 console (Windows) with Arabic in, via stdin."""

    AR = "13 مشكلة في Instagram في 5 دقايق.\nاعمل save للـpost هذا.\n".encode("utf-8")

    def test_every_script_on_cp1252_stdin(self):
        for skill, script, extra in (("ig-human", "humanize.py", ["--report"]),
                                     ("ig-human", "detect.py", []),
                                     ("ig-caption", "caption.py", []),
                                     ("ig-reel", "hookscore.py", []),
                                     ("ig-reel", "beats.py", [])):
            with self.subTest(script=script):
                r = run_script(os.path.join(SKILLS, skill, script), ["-", "--lang", "ar"] + extra,
                               stdin=self.AR)
                self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("utf-8", "replace"))
                self.assertIn(r.returncode, (0, 1))

    def test_utf16_and_bom_files(self):
        folder = tempfile.mkdtemp()
        for name, data in (("u16.txt", "J'ai perdu 18 000 €\n".encode("utf-16")),
                           ("bom.txt", "﻿J'ai perdu 18 000 €\n".encode("utf-8"))):
            path = os.path.join(folder, name)
            open(path, "wb").write(data)
            with self.subTest(name=name):
                self.assertEqual(L.read_input(path), "J'ai perdu 18 000 €\n")

    def test_empty_input(self):
        r = run_script(os.path.join(SKILLS, "ig-human", "detect.py"), ["-", "--lang", "en"], stdin=b"")
        self.assertEqual(r.returncode, 2)

    def test_unknown_lang_is_an_error(self):
        r = run_script(os.path.join(SKILLS, "ig-reel", "hookscore.py"), ["--hook", "hola", "--lang", "es"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(b"not a language", r.stderr)


# ------------------------------------------------------------------ v1.1: tools that close the loop

import datetime as dt  # noqa: E402

JR = load("ig-reel", "journal")
AU = load("ig-audit", "audit")
V = load("ig-human", "voice")
CA = load("ig-carousel", "carousel")


def audit_rows(rows, header="date\tformat\tviews"):
    text = header + "\n" + "\n".join("\t".join(map(str, r)) for r in rows)
    posts, mapping, notes = AU.read_table(text)
    return posts, mapping, notes


def series(n, start=dt.date(2026, 1, 1), fmt="reel", views=1000, step=3):
    return [((start + dt.timedelta(days=step * i)).isoformat(), fmt, views) for i in range(n)]


class Journal(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "journal.jsonl")
        self.today = dt.date(2026, 11, 16)

    def test_add_posted_round_trip(self):
        e = JR.load(self.path)
        a = JR.add(e, "reel", "Proposals took five hours.", self.today, formula="5", lang="en")
        b = JR.add(e, "reel", "Second.", self.today)
        self.assertEqual((a["id"], b["id"]), ("20261116-1", "20261116-2"))
        JR.mark_posted(e, a["id"], dt.date(2026, 11, 18), "https://www.instagram.com/reel/ABC/?igsh=x")
        JR.save(e, self.path)
        back = JR.load(self.path)
        self.assertEqual(back[0]["status"], "posted")
        self.assertEqual(back[0]["posted"], "2026-11-18")
        self.assertEqual(back[1]["status"], "ready")
        self.assertEqual(JR.norm_link(back[0]["permalink"]), "instagram.com/reel/ABC")

    def test_arabic_hook_survives(self):
        e = JR.load(self.path)
        JR.add(e, "reel", "خسرت 18 ألف دينار", self.today)
        JR.save(e, self.path)
        self.assertEqual(JR.load(self.path)[0]["hook"], "خسرت 18 ألف دينار")

    def test_recent_names_repeats_and_unposted(self):
        e = []
        JR.add(e, "reel", "a", dt.date(2026, 11, 1), formula="3", theme="Devis", type="teach")
        JR.add(e, "reel", "b", dt.date(2026, 11, 10), formula="3", theme="devis", type="teach")
        JR.mark_posted(e, e[0]["id"], dt.date(2026, 11, 2))
        JR.mark_posted(e, e[1]["id"], dt.date(2026, 11, 11))
        JR.add(e, "reel", "c", dt.date(2026, 11, 5))
        _, notes = JR.recent(e, self.today, 14)
        text = " ".join(notes)
        self.assertIn("formula '3' used 2 times", text)
        self.assertIn("theme 'devis' used 2 times", text)
        self.assertIn("back to back", text)
        self.assertIn("never marked posted", text)

    def test_bad_values_refused(self):
        with self.assertRaises(ValueError):
            JR.add([], "tiktok", "x", self.today)
        with self.assertRaises(ValueError):
            JR.parse_date("16/11/2026")
        self.assertEqual(JR.main(["--file", self.path, "posted", "nope"]), 2)


class AuditColumns(unittest.TestCase):
    def test_french_headers(self):
        _, m, _ = audit_rows([("2026-01-01", "Reel", "1 200", "900", "4")],
                             "Date de publication\tType\tVues\tCouverture\tPartages")
        self.assertEqual(m, {"date": "Date de publication", "format": "Type", "views": "Vues",
                             "reach": "Couverture", "shares": "Partages"})

    def test_impressions_are_never_views(self):
        with self.assertRaises(AU.AuditError):
            audit_rows([("2026-01-01", "5000")], "date\tImpressions")
        posts, m, notes = audit_rows([("2026-01-01", "5000", "4000")], "date\tImpressions\tReach")
        self.assertNotIn("views", m)
        self.assertTrue(any("Impressions" in n for n in notes))

    def test_two_columns_for_one_field_is_an_error(self):
        with self.assertRaises(AU.AuditError):
            audit_rows([("1", "2")], "Views\tVues")
        posts, m, _ = AU.read_table("Views\tPlays\n1\t2\n", {"views": "Plays"})
        self.assertEqual(posts[0]["views"], 2)

    def test_counts_and_percents(self):
        for cell, n in (("1 200", 1200), ("1,200", 1200), ("12k", 12000), ("1,2 M", 1200000), ("", None)):
            self.assertEqual(AU.parse_count(cell), n)
        for cell, v in (("45%", 0.45), ("45", 0.45), ("0.45", 0.45), ("45,5 %", 0.455)):
            self.assertAlmostEqual(AU.parse_percent(cell), v)

    def test_dates_read_as_a_column(self):
        d = AU.parse_dates(["16/11/2026 18:30", "03/04/2026"])
        self.assertEqual(d[1][0], dt.datetime(2026, 4, 3))
        self.assertTrue(d[0][1])
        d = AU.parse_dates(["11/16/2026", "03/04/2026"])
        self.assertEqual(d[1][0], dt.datetime(2026, 3, 4))
        with self.assertRaises(AU.AuditError):
            AU.parse_dates(["03/04/2026", "05/06/2026"])


class AuditMessyInput(unittest.TestCase):
    TODAY = dt.date(2026, 12, 31)

    def test_one_bad_date_is_named_and_the_rest_keep_their_baseline(self):
        rows = series(20)
        rows[4] = ("16 nov. 2026", "reel", 1000)
        posts, _, notes = audit_rows(rows)
        self.assertEqual(len(posts), 19)
        self.assertTrue(any("line 6" in n and "not read" in n for n in notes))
        a = AU.analyse(posts, today=self.TODAY)
        self.assertTrue(a["dated"])

    def test_two_digit_years(self):
        d = AU.parse_dates(["16/11/26", "03/04/26"])
        self.assertEqual(d[0][0], dt.datetime(2026, 11, 16))

    def test_unreadable_views_have_their_own_reason(self):
        rows = series(12)
        rows[3] = (rows[3][0], "reel", "beaucoup")
        rows[4] = (rows[4][0], "reel", "1470 vues")
        posts, _, notes = audit_rows(rows)
        self.assertTrue(any("views 'beaucoup' not read" in n for n in notes))
        self.assertEqual(len(posts), 11)                 # "1470 vues" is read as 1470
        self.assertIn(1470, [p["views"] for p in posts])

    def test_a_column_of_dates_is_the_date(self):
        posts, m, notes = AU.read_table("Publication\tVues\n" + "\n".join(
            f"0{i}/08/2026 09:05\t{100 + i}" for i in range(1, 10)) + "\n13/08/2026 09:05\t50\n")
        self.assertEqual(m["date"], "Publication")
        self.assertTrue(any("read as the date" in n for n in notes))

    def test_voice_numbered_lists_and_numbers(self):
        path = voice("- **Words I would never say out loud:**\n\n  - game changer\n"
                     "- **Clients, numbers or names I cannot say publicly:**\n  1. Acme\n  2. 18 400\n"
                     "  3. Société Générale (banque)\n")
        lists = V.read_voice(path)
        self.assertEqual(lists, {"never": ["game changer"], "private": ["Acme", "18 400", "Société Générale"]})
        hits = V.check("We made 18,400 with ACME. Also 18400. Société Générale paid.", lists)
        self.assertEqual(len([h for h in hits if h["kind"] == "private"]), 3)

    def test_hookscore_gate_and_pending_numbers(self):
        import io
        rows = [{"hook": h, "score": K.run(h, "en")[1], "verdict": K.run(h, "en")[2], "flags": K.run(h, "en")[3],
                 "issues": [], "weakest": "STAKES", "checks": {"STAKES": {"score": 70}}}
                for h in ("I lost {{your number}} on one clause.", "Hey guys, quick tip")]
        buf = io.StringIO()
        K.render_table(rows, "en", out=buf)
        out = buf.getvalue()
        self.assertNotIn("Shoot the top one", out)
        self.assertIn("pending", out)
        self.assertIn("out ", out)
        self.assertTrue(any("Pending" in n for n in B.analyse("I lost {{your number}} on one clause.")["notes"]))

    def test_carousel_blanks_fail_and_second_headline_is_kept(self):
        settings, slides = CA.parse("# ____ ____\n____\n---\n# Real\n# Second line\nbody\n")
        issues = CA.lint(settings, slides)
        self.assertTrue(any(l == "FAIL" and "blanks" in m for l, _, m in issues))
        self.assertIn("Second line", slides[1]["body"])
        settings, slides = CA.parse("Note: my cover\n---\n# Two\nx\n")
        self.assertEqual(settings, {})
        self.assertEqual(len(slides), 2)

    def test_zero_baseline_reason(self):
        posts, _, _ = audit_rows(series(6, views=0) + [("2026-02-01", "reel", 50)])
        a = AU.analyse(posts, today=self.TODAY)
        self.assertIn("the baseline median is 0", {p["why"] for p in a["no_baseline"]})

    def test_formats_read_by_what_they_contain(self):
        for cell, fmt in (("Reel IG", "reel"), ("Reels vidéo", "reel"), ("Vidéo", "reel"),
                          ("Carrousel", "carousel"), ("IG image", "photo"), ("Publication", "post")):
            self.assertEqual(AU.norm_format(cell), fmt, cell)

    def test_lengths_and_percent_columns(self):
        self.assertEqual(AU.parse_length("0:28"), 28)
        self.assertEqual(AU.parse_length("1:05"), 65)
        self.assertEqual(AU.parse_percents(["1", "45", "60%"]), [0.01, 0.45, 0.6])
        self.assertEqual(AU.parse_percents(["0.4", "0.6"]), [0.4, 0.6])

    def test_leading_blank_line(self):
        posts, _, _ = AU.read_table("\n\ndate\tviews\n2026-01-01\t10\n")
        self.assertEqual(posts[0]["views"], 10)

    def test_formula_ids_normalised(self):
        posts, _, _ = audit_rows([("2026-01-01", "reel", 10, "#05"), ("2026-01-02", "reel", 10, "formule 5")],
                                 "date	format	views	formula")
        self.assertEqual({p["formula"] for p in posts}, {"5"})

    def test_too_few_has_no_diagnosis_and_no_insights(self):
        rows = [r + (100, 2) for r in series(10)] + [("2026-03-01", "reel", 9000, 100, 0)]
        posts, _, _ = audit_rows(rows, "date	format	views	reach	follows")
        a = AU.analyse(posts, today=self.TODAY)
        self.assertTrue(a["too_few"])
        self.assertEqual((a["diagnosis"], a["top"]), ([], []))
        self.assertIn("Too few", AU.to_markdown(a))
        self.assertNotIn("x reel", AU.to_markdown(a))

    def test_day_and_hour_only_on_request(self):
        posts, _, _ = audit_rows(series(40))
        self.assertEqual(AU.analyse(posts, today=self.TODAY)["comparisons"]["when"], [])


class AuditNumbers(unittest.TestCase):
    TODAY = dt.date(2026, 12, 31)

    def test_trailing_median_per_format(self):
        rows = series(6, views=1000) + [("2026-01-19", "carousel", 50)] * 1
        rows += [("2026-01-20", "reel", 4000)]
        posts, _, _ = audit_rows(rows)
        a = AU.analyse(posts, today=self.TODAY)
        last = [p for p in posts if p["views"] == 4000][0]
        self.assertEqual(last["baseline"], 1000)          # the carousel is not in a reel's baseline
        self.assertAlmostEqual(last["multiple"], 4.0)
        car = [p for p in posts if p["format"] == "carousel"][0]
        self.assertIsNone(car["multiple"])                # no 5 earlier carousels: no baseline
        self.assertIn(car, a["no_baseline"])

    def test_window_is_the_previous_ten(self):
        rows = series(10, views=100) + series(10, start=dt.date(2026, 3, 1), views=1000)
        rows += [("2026-06-01", "reel", 2000)]
        posts, _, _ = audit_rows(rows)
        AU.analyse(posts, today=self.TODAY)
        self.assertEqual(posts[-1]["baseline"], 1000)     # growth: old 100-view posts are out

    def test_young_posts_are_left_out(self):
        posts, _, _ = audit_rows(series(12) + [("2026-12-28", "reel", 9000)])
        a = AU.analyse(posts, today=self.TODAY)
        self.assertEqual(len(a["young"]), 1)
        self.assertNotIn(posts[-1], a["pool"])

    def test_too_few_says_so(self):
        posts, _, _ = audit_rows(series(13))
        a = AU.analyse(posts, today=self.TODAY)
        self.assertTrue(a["too_few"])
        self.assertEqual(a["comparisons"], {})
        import io
        buf = io.StringIO()
        AU.render(a, {"views": "views"}, [], out=buf)
        self.assertIn("TOO FEW TO COMPARE", buf.getvalue())

    def test_missing_columns_are_na_not_estimates(self):
        posts, _, _ = audit_rows(series(16))
        a = AU.analyse(posts, today=self.TODAY)
        p = a["pool"][0]
        self.assertIsNone(p["shares_k"])
        self.assertIsNone(p["hold3s"])

    def test_small_groups_are_never_compared(self):
        rows = [(d, f, v) for (d, f, v) in series(30)]
        hdr = "date\tformat\tviews\tformula"
        rows = [r + ("1" if i < 4 else "2",) for i, r in enumerate(rows)]
        posts, _, _ = audit_rows(rows, hdr)
        a = AU.analyse(posts, today=self.TODAY)
        self.assertFalse([c for c in a["comparisons"]["formula"] if c["label"] == "#1"])

    def test_a_strong_real_difference_is_named(self):
        import random
        rng = random.Random(3)
        rows, d = [], dt.date(2026, 1, 1)
        for i in range(40):
            f = "1" if i % 2 else "2"
            rows.append((d.isoformat(), "reel", int(1000 * rng.lognormvariate(0, 0.3) * (4 if f == "1" else 1)), f))
            d += dt.timedelta(days=3)
        posts, _, _ = audit_rows(rows, "date\tformat\tviews\tformula")
        a = AU.analyse(posts, today=self.TODAY)
        tiers = [c["tier"] for c in a["comparisons"]["formula"]]
        self.assertEqual(tiers, ["clear"])               # two formulas: one comparison, not two

    def test_wording_is_deterministic(self):
        posts, _, _ = audit_rows([r + ("1" if i % 3 else "2",) for i, r in enumerate(series(40))],
                                 "date\tformat\tviews\tformula")
        a1 = AU.analyse(posts, today=self.TODAY)
        posts, _, _ = audit_rows([r + ("1" if i % 3 else "2",) for i, r in enumerate(series(40))],
                                 "date\tformat\tviews\tformula")
        a2 = AU.analyse(posts, today=self.TODAY)
        self.assertEqual([c["p"] for v in a1["comparisons"].values() for c in v],
                         [c["p"] for v in a2["comparisons"].values() for c in v])

    def test_profile_problem(self):
        rows = [r + (100, 2) for r in series(20, views=1000)] + [("2026-03-15", "reel", 5000, 100, 0)]
        posts, _, _ = audit_rows(rows, "date\tformat\tviews\treach\tfollows")
        for p in posts:
            p["reach"] = p["views"]
        a = AU.analyse(posts, today=self.TODAY)
        self.assertTrue(any(k == "profile" for k, _, _ in a["diagnosis"]))


class AuditJournal(unittest.TestCase):
    TODAY = dt.date(2026, 12, 31)

    def test_join_by_link_then_by_unique_day(self):
        rows = [r + ("",) for r in series(12)]
        rows[5] = rows[5][:3] + ("https://www.instagram.com/reel/XYZ/",)
        posts, _, _ = audit_rows(rows, "date\tformat\tviews\tpermalink")
        entries = [
            {"id": "a", "status": "posted", "posted": "2026-05-05", "format": "reel", "formula": "3",
             "permalink": "https://instagram.com/reel/XYZ?igsh=1", "hook": "h1"},
            {"id": "b", "status": "posted", "posted": rows[7][0], "format": "reel", "formula": "9", "hook": "h2"},
            {"id": "c", "status": "posted", "posted": "2027-01-01", "format": "reel", "hook": "h3"},
            {"id": "d", "status": "ready", "created": rows[8][0], "format": "reel"},
        ]
        a = AU.analyse(posts, entries, self.TODAY)
        by = {e["id"]: p for e, p in a["matched"]}
        self.assertEqual(by["a"]["formula"], "3")
        self.assertEqual(by["a"]["match"], "link")
        self.assertEqual(by["b"]["match"], "date")
        self.assertEqual([e["id"] for e in a["unmatched"]], ["c"])

    def test_a_link_that_is_not_in_the_table_never_falls_back_to_the_date(self):
        rows = [r + ("",) for r in series(12)]
        rows[5] = rows[5][:3] + ("https://www.instagram.com/reel/AAA4/",)
        posts, _, _ = audit_rows(rows, "date	format	views	permalink")
        entries = [{"id": "z", "status": "posted", "posted": rows[5][0], "format": "reel", "formula": "5",
                    "permalink": "https://www.instagram.com/reel/ZZZ999/"},
                   {"id": "y", "status": "posted", "posted": rows[6][0], "format": "reel",
                    "permalink": "https://www.instagram.com/reel/aaa4/"}]
        a = AU.analyse(posts, entries, self.TODAY)
        self.assertEqual(a["matched"], [])               # shortcodes are case-sensitive too
        self.assertIsNone(posts[5]["formula"])

    def test_a_hand_edited_journal_date_does_not_crash(self):
        posts, _, _ = audit_rows(series(12))
        a = AU.analyse(posts, [{"id": "q", "status": "posted", "posted": "16/11/2026"}], self.TODAY)
        self.assertEqual([e["id"] for e in a["unmatched"]], ["q"])
        self.assertTrue(a["journal_notes"])
        _, notes = JR.recent([{"id": "q", "status": "posted", "created": "2026-11-01", "posted": "16/11/2026"}],
                             dt.date(2026, 11, 16))
        self.assertTrue(any("cannot read" in n for n in notes))

    def test_two_posts_the_same_day_are_not_guessed(self):
        rows = series(12)
        rows.append((rows[-1][0], "reel", 900))
        posts, _, _ = audit_rows(rows)
        entries = [{"id": "x", "status": "posted", "posted": rows[-1][0], "format": "reel", "formula": "1"}]
        a = AU.analyse(posts, entries, self.TODAY)
        self.assertEqual(a["matched"], [])


class SwipeV11(unittest.TestCase):
    def rows(self, n, formula=None, account=lambda i: f"@a{i % 6}"):
        out = []
        for i in range(n):
            r = {"account": account(i), "followers": 9000, "median": 1000, "views": 1000 * (n - i),
                 "hook": "J'ai perdu 18 000 € sur un seul contrat"}
            if formula:
                r["formula"] = formula(i)
            out.append(r)
        return out

    def test_formula_column_wins_and_is_counted_as_read(self):
        f = SW.load_formulas(SW.HOOKS)
        a = SW.analyse(self.rows(18, formula=lambda i: "#1" if i < 6 else "Time Collapse"), f)
        self.assertEqual(a["reels"][0]["formula"], "Cost Confession")
        self.assertEqual(a["read"], 18)
        self.assertEqual(dict(a["top_formulas"])["Cost Confession"], 6)

    def test_no_claim_under_fifteen(self):
        import io
        f = SW.load_formulas(SW.HOOKS)
        buf = io.StringIO()
        SW.render(SW.analyse(self.rows(12, formula=lambda i: "1"), f), out=buf)
        self.assertIn("not said", buf.getvalue())

    def test_one_account_dominating_is_flagged(self):
        f = SW.load_formulas(SW.HOOKS)
        a = SW.analyse(self.rows(18, account=lambda i: "@big" if i < 4 else f"@a{i}"), f)
        self.assertEqual(a["dominant"], "@big")

    def test_without_the_column_nothing_changes(self):
        f = SW.load_formulas(SW.HOOKS)
        a = SW.analyse(self.rows(3), f)
        self.assertEqual(a["reels"][0]["formula"], "to classify by reading")
        self.assertEqual(a["read"], 0)


class BeatsCards(unittest.TestCase):
    SCRIPT = "Proposals used to take me five hours.\nNow it takes twenty minutes.\nComment TEMPLATE."

    def test_unmarked_script_is_unchanged(self):
        a = B.analyse(self.SCRIPT)
        self.assertNotIn("cards", a)
        self.assertEqual(len(a["beats"]), 3)

    def test_cards_are_not_speech(self):
        marked = "[on-screen] 5 HOURS -> 20 MIN\n" + self.SCRIPT.replace(
            "Comment", "[écran] THE TEMPLATE THAT DOES IT ALL FOR YOU\nComment")
        a = B.analyse(marked)
        b = B.analyse(self.SCRIPT)
        self.assertEqual(a["total_words"], b["total_words"])
        self.assertEqual([c["beat"] for c in a["cards"]], [1, 3])
        self.assertEqual(a["cards"][0]["end"], a["beats"][2]["start"])
        self.assertTrue(a["cards"][1]["flags"])

    def test_no_card_at_frame_one(self):
        a = B.analyse("First line here.\n[on-screen] LATE CARD\nSecond line here.")
        self.assertTrue(any("frame 1" in n for n in a["notes"]))


class Voice(unittest.TestCase):
    def setUp(self):
        self.path = voice('- **Words I would never say out loud:** game changer, "incroyable", خويا\n'
                          "  - booster\n- **Do I swear:** no\n"
                          "- **Clients, numbers or names I cannot say publicly:** Acme, 18 400\n"
                          "- **Words I actually use:** (list them)\n")

    def test_reads_both_fields(self):
        lists = V.read_voice(self.path)
        self.assertEqual(lists["never"], ["game changer", "incroyable", "خويا", "booster"])
        self.assertEqual(lists["private"], ["Acme", "18 400"])

    def test_matches_whole_words_any_case_accent_script(self):
        lists = V.read_voice(self.path)
        hits = V.check("Un vrai Game-changer, INCROYABLE.\nIncroyablement simple.\nوخويا قالي\n"
                       "Acme m'a payé 18 400 €.", lists)
        found = {(h["entry"], h["line"]) for h in hits}
        self.assertIn(("game changer", 1), found)
        self.assertIn(("incroyable", 1), found)
        self.assertNotIn(("incroyable", 2), found)
        self.assertIn(("خويا", 3), found)
        self.assertIn(("18 400", 4), found)

    def test_placeholder_is_not_a_word(self):
        lists = V.read_voice(voice("- **Words I would never say out loud:** (fill this in)\n"))
        self.assertEqual(lists["never"], [])


class Carousel(unittest.TestCase):
    DECK = ("handle: @me\n---\n# THE $18,000 CLAUSE\nOne line.\n---\n# What it says now\nPayment on delivery.\n"
            "---\n# Why it works so well\nApproval is a feeling.\n---\n# The second clause here\nOne revision.\n"
            "---\n# Recap\n- one\n- two\n---\n# Want it?\nComment CLAUSE and I will send it.\n")

    def issues(self, text):
        settings, slides = CA.parse(text)
        return CA.lint(settings, slides), slides

    def test_clean_deck(self):
        issues, slides = self.issues(self.DECK)
        self.assertEqual(len(slides), 6)
        self.assertFalse([i for i in issues if i[0] in ("FAIL", "WARN")], issues)

    def test_cover_and_body_limits_fail(self):
        long_cover = self.DECK.replace("THE $18,000 CLAUSE", "THE ONE CLAUSE I PUT IN EVERY CONTRACT NOW")
        issues, _ = self.issues(long_cover)
        self.assertTrue(any(l == "FAIL" and s == 1 for l, s, _ in issues))
        wordy = self.DECK.replace("One revision.", " ".join(["word"] * 30))
        issues, _ = self.issues(wordy)
        self.assertTrue(any(l == "FAIL" and s == 4 for l, s, _ in issues))

    def test_ask_must_be_alone_on_the_last_slide(self):
        issues, _ = self.issues(self.DECK.replace("Approval is a feeling.", "Save this post."))
        self.assertTrue(any("an ask on slides" in m for _, _, m in issues))

    def test_arabic_slide_is_rtl_and_ask_is_checked_by_reading(self):
        deck = self.DECK.replace("# What it says now\nPayment on delivery.", "# البند اللي نحطّو\nالخلاص عند التسليم.")
        issues, slides = self.issues(deck)
        self.assertEqual(slides[1]["lang"], "ar")
        self.assertIn('dir="rtl"', CA.slide_html(slides[1], 2, 6, {}))
        self.assertTrue(any(l == "CHECK" for l, _, _ in issues))

    def test_fail_blocks_rendering(self):
        folder = tempfile.mkdtemp()
        src = os.path.join(folder, "s.md")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self.DECK.replace("THE $18,000 CLAUSE", "ONE TWO THREE FOUR FIVE SIX SEVEN"))
        r = run_script(os.path.join(SKILLS, "ig-carousel", "carousel.py"),
                       [src, "--render", "--out", os.path.join(folder, "out")])
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(folder, "out")))

    @unittest.skipUnless(CA.find_browser(), "no Chrome, Edge or Chromium on this machine")
    def test_renders_png_at_1080x1350(self):
        import struct
        folder = tempfile.mkdtemp()
        settings, slides = CA.parse(self.DECK)
        CA.lint(settings, slides)
        report = CA.render(settings, slides[:1], folder)
        self.assertEqual(len(report["pngs"]), 1)
        with open(report["pngs"][0], "rb") as fh:
            self.assertEqual(struct.unpack(">II", fh.read(24)[16:24]), (1080, 1350))


class NewScriptsOnCp1252(unittest.TestCase):
    def test_new_scripts_survive_a_windows_console(self):
        folder = tempfile.mkdtemp()
        tsv = os.path.join(folder, "p.tsv")
        with open(tsv, "w", encoding="utf-8") as fh:
            fh.write("date\tformat\tvues\thook\n" + "\n".join(
                f"2026-01-{i + 1:02d}\treel\t{1000 + i}\tخسرت {i} دينار" for i in range(14)))
        v = voice("- **Words I would never say out loud:** خويا\n")
        for script, args, stdin in (
                (("ig-audit", "audit.py"), [tsv, "--no-journal", "--lang", "ar"], None),
                (("ig-human", "voice.py"), ["-", "--voice", v], CommandLine.AR),
                (("ig-carousel", "carousel.py"), ["-", "--lang", "ar"], "# عنوان\nنص\n".encode("utf-8")),
                (("ig-reel", "journal.py"), ["--file", os.path.join(folder, "j.jsonl"), "add", "--format",
                                             "reel", "--hook", "خسرت 18 ألف"], None)):
            with self.subTest(script=script[1]):
                r = run_script(os.path.join(SKILLS, *script), args, stdin=stdin)
                self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("utf-8", "replace"))
                self.assertIn(r.returncode, (0, 1))


if __name__ == "__main__":
    unittest.main(verbosity=1)
