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


class LangSync(unittest.TestCase):
    def test_copies_identical(self):
        src = os.path.join(PACK, "shared", "lang.py")
        for skill in ("ig-human", "ig-caption", "ig-reel", "ig-viral"):
            with self.subTest(skill=skill):
                self.assertTrue(filecmp.cmp(src, os.path.join(SKILLS, skill, "lang.py"),
                                            shallow=False), "run tools/sync_lang.py")

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
