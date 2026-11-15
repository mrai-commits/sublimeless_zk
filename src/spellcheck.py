# -*- coding: utf-8 -*-
"""
Spell checking, new in Sublimeless 1.0.

Engine: spylls, a pure Python implementation of Hunspell, with the Hunspell
dictionaries in the app's "dictionaries" folder (the ones LibreOffice uses).
Several languages can be active at once: a word is fine if any of them
knows it, which suits notes that mix languages.

Looking a word up takes a fraction of a millisecond, but a long note has
thousands of different words. So results are remembered, and words not yet
seen are checked in small portions while the app is idle, never while typing.
"""
import os
import re
import threading

WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")

# parts of a note that are not prose and must not be checked
SKIP_RE = re.compile(
    r"```.*?(?:```|\Z)"                 # fenced code
    r"|`[^`\n]*`"                       # inline code
    r"|<!--.*?(?:-->|\Z)"               # comments, e.g. the automatic bibliography
    r"|\[\[[^\]\n]*\]\]"                # note links
    r"|\[[^\]\n]*@[^\]\n]*\]"           # citations
    r"|\]\([^)\n]*\)"                   # link targets
    r"|(?:https?|ftp|file)://\S+|www\.\S+"
    r"|\S+@\S+\.\w+"                    # e-mail addresses
    r"|(?<![\w])[@#][\w][\w:.#$%&\-+?<>~/]*"   # tags and citekeys
    r"|<[^>\n]+>"                       # HTML tags
    r"|\$[^$\n]+\$"                     # inline maths
    , re.DOTALL)

ALPHABETS = {
    'en': 'abcdefghijklmnopqrstuvwxyz',
    'es': 'abcdefghijklmnopqrstuvwxyzáéíóúüñ',
    'fr': 'abcdefghijklmnopqrstuvwxyzàâçéèêëîïôùûüœ',
}


def words_to_check(text):
    """Yield (start, end, word) for the prose words of a note."""
    pos = 0
    for skip in SKIP_RE.finditer(text):
        yield from _words(text, pos, skip.start())
        pos = skip.end()
    yield from _words(text, pos, len(text))


def _words(text, start, end):
    for match in WORD_RE.finditer(text, start, end):
        word = match.group()
        if len(word) < 2 or (word.isupper() and len(word) <= 6):
            continue                    # single letters, acronyms
        yield match.start(), match.end(), word


class SpellChecker:
    """One per app. Thread-safe enough for: load in a thread, use in the GUI thread."""

    def __init__(self, dictionary_folder, languages, personal_file=None):
        self.dictionary_folder = dictionary_folder
        self.languages = [lang for lang in languages
                          if os.path.exists(os.path.join(dictionary_folder, lang + '.aff'))]
        self.personal_file = personal_file
        self.personal = set()
        self.dictionaries = {}          # language -> spylls Dictionary
        self.known = {}                 # word -> True/False
        self.suggestions = {}           # misspelled word -> list of corrections
        self.lookup_cost = {}           # language -> seconds for a few non-words
        self._ahead_queue = []
        self._ahead_thread = None
        self._ahead_lock = threading.Lock()
        self.ready = False
        self.error = None
        self._load_personal()

    # ---- loading

    def load(self):
        """Load the dictionaries (about a second each). Safe to call in a thread."""
        try:
            from spylls.hunspell import Dictionary
            for lang in self.languages:
                self.dictionaries[lang] = Dictionary.from_files(os.path.join(self.dictionary_folder, lang))
            self.measure_lookup_cost()
            self.ready = bool(self.dictionaries)
        except Exception as e:      # never let spell checking break the app
            self.error = repr(e)
            self.ready = False
        return self.ready

    def load_in_background(self, on_ready=None):
        def work():
            if self.load() and on_ready:
                on_ready()
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        return thread

    def _load_personal(self):
        if self.personal_file and os.path.exists(self.personal_file):
            with open(self.personal_file, encoding='utf-8', errors='ignore') as f:
                self.personal = {line.strip() for line in f if line.strip()}

    # ---- checking

    def check(self, word):
        """True if the word is spelled correctly in any active language. Remembers the answer."""
        answer = self.known.get(word)
        if answer is None:
            answer = self._lookup(word)
            self.known[word] = answer
        return answer

    def cached(self, word):
        """True/False if already known, None if the word still has to be looked up."""
        return self.known.get(word)

    def _lookup(self, word):
        if word in self.personal or word.lower() in self.personal:
            return True
        variants = [word]
        if '’' in word:
            variants.append(word.replace('’', "'"))
        for dictionary in self.dictionaries.values():
            for variant in variants:
                try:
                    if dictionary.lookup(variant):
                        return True
                except Exception:
                    return True         # a word the engine chokes on is not marked
        if '-' in word:                  # well-known: each part is a word
            parts = [part for part in word.split('-') if part]
            if len(parts) > 1 and all(len(part) < 2 or self.check(part) for part in parts):
                return True
        return False

    # ---- suggestions

    def suggest(self, word, limit=7, seconds=1.2):
        """
        Correct words one typing slip away from `word`: swapped, missing,
        wrong or extra letter, the likeliest first. Hunspell's own suggestions
        take up to half a minute with the French dictionary, so this does the
        common cases and stops after `seconds`. Answers are remembered.
        """
        cached = self.suggestions.get(word)
        if cached is not None:
            return cached[:limit]
        result = self._suggest(word, limit, seconds)
        self.suggestions[word] = result
        return result

    def _suggest(self, word, limit, seconds):
        import time
        deadline = time.time() + seconds
        capitalized = word[:1].isupper()
        alphabet = ''.join(dict.fromkeys(''.join(ALPHABETS.get(lang[:2], ALPHABETS['en'])
                                                   for lang in self.dictionaries)))
        candidates = list(self._edits(word.lower(), alphabet))
        found = {}                      # position in candidates -> word as shown

        def try_dictionary(dictionary):
            for position, candidate in enumerate(candidates):
                if position in found:
                    continue
                shown = candidate[:1].upper() + candidate[1:] if capitalized else candidate
                try:
                    ok = dictionary.lookup(shown) or (capitalized and dictionary.lookup(candidate))
                except Exception:
                    ok = False
                if ok:
                    found[position] = shown
                if time.time() > deadline:
                    return False
            return True

        # quick dictionaries first: they get through all candidates in a few
        # hundredths of a second; the slow one (French) uses the time left
        for lang in sorted(self.dictionaries, key=lambda l: self.lookup_cost.get(l, 0)):
            if not try_dictionary(self.dictionaries[lang]):
                break
        return [found[position] for position in sorted(found)][:limit]

    def measure_lookup_cost(self):
        """How long each dictionary takes to reject a non-word (decides the order in suggest)."""
        import time
        probes = ['qzxv', 'organisatonn', 'xqzkwq', 'teh', 'maissonn', 'hablamoss', 'wurdd', 'zzyqa']
        for lang, dictionary in self.dictionaries.items():
            start = time.time()
            for probe in probes:
                try:
                    dictionary.lookup(probe)
                except Exception:
                    pass
            self.lookup_cost[lang] = time.time() - start

    def suggest_ahead(self, words):
        """
        Work out suggestions for these words in the background, so that they
        are ready when the user right-clicks one of them.
        """
        todo = [word for word in words if word not in self.suggestions]
        if not todo:
            return
        with self._ahead_lock:
            for word in todo:
                if word not in self._ahead_queue:
                    self._ahead_queue.append(word)
            del self._ahead_queue[:-40]         # the most recent ones matter
            if self._ahead_thread is None or not self._ahead_thread.is_alive():
                self._ahead_thread = threading.Thread(target=self._suggest_ahead_worker, daemon=True)
                self._ahead_thread.start()

    def _suggest_ahead_worker(self):
        import time
        while True:
            with self._ahead_lock:
                if not self._ahead_queue:
                    return
                word = self._ahead_queue.pop()
            if word not in self.suggestions:
                try:
                    self.suggestions[word] = self._suggest(word, 7, 1.5)
                except Exception:
                    self.suggestions[word] = []
            time.sleep(0.02)            # leave room for the user interface

    @staticmethod
    def _edits(word, alphabet):
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        swaps = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
        deletes = [a + b[1:] for a, b in splits if b]
        replaces = [a + c + b[1:] for a, b in splits if b for c in alphabet if c != b[0]]
        inserts = [a + c + b for a, b in splits for c in alphabet]
        seen = {word}
        for candidate in swaps + deletes + replaces + inserts:
            if candidate not in seen:
                seen.add(candidate)
                yield candidate

    # ---- personal dictionary

    def add_word(self, word):
        """Accept a word from now on, and keep it in the personal dictionary file."""
        self.personal.add(word)
        self.known[word] = True
        self.suggestions.pop(word, None)
        for key in [k for k, ok in self.known.items() if not ok and '-' in k]:
            del self.known[key]         # compounds containing the word: look up again
        if self.personal_file:
            try:
                os.makedirs(os.path.dirname(self.personal_file), exist_ok=True)
                with open(self.personal_file, 'a', encoding='utf-8') as f:
                    f.write(word + '\n')
            except OSError as e:
                self.error = repr(e)
