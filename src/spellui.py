# -*- coding: utf-8 -*-
"""
Spell checking in the editors: red wavy underlines and the right-click menu
with suggestions. The checking itself is in spellcheck.py.
"""
import time
import bisect
import weakref
from PyQt5.QtCore import QObject, QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from PyQt5 import sip
from PyQt5.Qsci import QsciScintilla
import spellcheck

SPELL_INDICATOR = 9


class SpellUnderliner(QObject):
    """One per app: underlines misspelled words in all editors it is given."""

    def __init__(self, checker, parent=None):
        super().__init__(parent)
        self.checker = checker
        self.enabled = True
        self.suggest_ahead = True       # prepare suggestions in the background
        self.editors = weakref.WeakSet()
        self.waiting = weakref.WeakSet()    # editors to underline again soon
        self.pending = {}                   # words still to look up
        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.setInterval(250)
        self.typing_timer.timeout.connect(self.underline_waiting)
        # after a longer pause the word at the cursor is checked too, so the
        # last word of a sentence does not stay unmarked
        self.pause_timer = QTimer(self)
        self.pause_timer.setSingleShot(True)
        self.pause_timer.setInterval(1500)
        self.pause_timer.timeout.connect(self.underline_after_pause)
        self.paused_editors = weakref.WeakSet()
        self.lookup_timer = QTimer(self)
        self.lookup_timer.setInterval(0)
        self.lookup_timer.timeout.connect(self.look_up_some)

    # ---- which editors

    def attach(self, editor):
        editor.spell_underliner = self
        editor.indicatorDefine(QsciScintilla.SquiggleIndicator, SPELL_INDICATOR)
        editor.setIndicatorForegroundColor(QColor('#e5484d'), SPELL_INDICATOR)
        editor.setIndicatorDrawUnder(True, SPELL_INDICATOR)
        self.editors.add(editor)
        self.request(editor)

    def set_enabled(self, enabled):
        self.enabled = enabled
        for editor in list(self.editors):
            if enabled:
                self.request(editor)
            else:
                self.clear(editor)

    def refresh_all(self):
        """E.g. when the dictionaries have finished loading or a word was added."""
        for editor in list(self.editors):
            self.request(editor)

    # ---- underlining

    def request(self, editor):
        """Underline soon. Called on every change; the work is done once typing pauses."""
        if self.enabled and self.checker.ready and not sip.isdeleted(editor):
            self.waiting.add(editor)
            self.typing_timer.start()
            self.paused_editors.add(editor)
            self.pause_timer.start()

    def underline_after_pause(self):
        for editor in list(self.paused_editors):
            self.underline(editor, spare_word_at_cursor=False)
        self.paused_editors.clear()

    def underline_waiting(self):
        for editor in list(self.waiting):
            self.underline(editor)
        self.waiting.clear()

    @staticmethod
    def clear(editor):
        if sip.isdeleted(editor):
            return
        editor.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, SPELL_INDICATOR)
        editor.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, editor.length())

    def underline(self, editor, spare_word_at_cursor=True):
        """Mark the misspelled words of the editor's text; queue the words not seen before."""
        if not (self.enabled and self.checker.ready):
            return
        if sip.isdeleted(editor):
            # the view of a note window that was closed
            self.editors.discard(editor)
            return
        text = editor.text()
        # Scintilla counts in UTF-8 bytes
        wide_positions, wide_extra, extra = [], [0], 0
        for match in _NON_ASCII.finditer(text):
            extra += len(match.group().encode('utf-8')) - 1
            wide_positions.append(match.start())
            wide_extra.append(extra)

        def bytepos(charpos):
            return charpos + wide_extra[bisect.bisect_left(wide_positions, charpos)]

        # the word being typed is not marked until the cursor leaves it
        cursor = None
        if spare_word_at_cursor and editor.hasFocus() and not editor.hasSelectedText():
            line, index = editor.getCursorPosition()
            line_start = sum(len(l) for l in text.split('\n')[:line]) + line if line else 0
            cursor = line_start + index

        # suggestions for the misspelled words on screen are prepared ahead
        first_line = editor.firstVisibleLine()
        lines_on_screen = editor.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)
        screen_start = editor.positionFromLineIndex(first_line, 0)
        last_line = min(editor.lines() - 1, first_line + lines_on_screen)
        screen_end = editor.positionFromLineIndex(last_line, 0) + len(editor.text(last_line).encode('utf-8'))
        on_screen = []

        self.clear(editor)
        unknown = False
        for start, end, word in spellcheck.words_to_check(text):
            ok = self.checker.cached(word)
            if ok is None:
                self.pending[word] = True
                unknown = True
            elif not ok and not (cursor is not None and start <= cursor <= end):
                b_start = bytepos(start)
                editor.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, b_start, bytepos(end) - b_start)
                if screen_start <= b_start <= screen_end:
                    on_screen.append(word)
        if unknown:
            self.waiting_for_lookup(editor)
        elif on_screen and self.suggest_ahead:
            self.checker.suggest_ahead(on_screen)

    def waiting_for_lookup(self, editor):
        self._after_lookup = getattr(self, '_after_lookup', weakref.WeakSet())
        self._after_lookup.add(editor)
        if not self.lookup_timer.isActive():
            self.lookup_timer.start()

    def look_up_some(self):
        """Look up queued words for a few milliseconds, then let the app breathe."""
        deadline = time.time() + 0.012
        while self.pending and time.time() < deadline:
            word, _ = self.pending.popitem()
            self.checker.check(word)
        if not self.pending:
            self.lookup_timer.stop()
            for editor in list(getattr(self, '_after_lookup', [])):
                self.underline(editor)
            self._after_lookup = weakref.WeakSet()

    def finish_now(self):
        """Look up everything that is queued (used by tests and the self-test)."""
        while self.pending:
            word, _ = self.pending.popitem()
            self.checker.check(word)
        self.lookup_timer.stop()
        for editor in list(self.editors):
            self.underline(editor)

    # ---- right-click menu

    def misspelled_word_at(self, editor, point):
        """(byte start, byte end, word) of the underlined word at a widget position, or None."""
        pos = editor.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINTCLOSE, point.x(), point.y())
        if pos < 0 or not editor.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, SPELL_INDICATOR, pos):
            return None
        start = editor.SendScintilla(QsciScintilla.SCI_INDICATORSTART, SPELL_INDICATOR, pos)
        end = editor.SendScintilla(QsciScintilla.SCI_INDICATOREND, SPELL_INDICATOR, pos)
        word = editor.text().encode('utf-8')[start:end].decode('utf-8', errors='ignore')
        return start, end, word

    def add_menu_entries(self, editor, menu, point):
        """Put suggestions and "Add to dictionary" at the top of a context menu."""
        if not (self.enabled and self.checker.ready):
            return False
        found = self.misspelled_word_at(editor, point)
        if not found:
            return False
        start, end, word = found
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            suggestions = self.checker.suggest(word)
        finally:
            QApplication.restoreOverrideCursor()
        first = menu.actions()[0] if menu.actions() else None
        entries = []
        for suggestion in suggestions:
            action = menu.addAction(suggestion) if first is None else None
            if action is None:
                from PyQt5.QtWidgets import QAction
                action = QAction(suggestion, menu)
                menu.insertAction(first, action)
            font = action.font(); font.setBold(True); action.setFont(font)
            action.triggered.connect(lambda checked=False, s=suggestion: self.replace(editor, start, end, s))
            entries.append(action)
        from PyQt5.QtWidgets import QAction
        if not suggestions:
            none = QAction('(no suggestions)', menu); none.setEnabled(False)
            menu.insertAction(first, none)
        add = QAction(f'Add "{word}" to dictionary', menu)
        add.triggered.connect(lambda checked=False: self.add_word(word))
        menu.insertAction(first, add)
        if first is not None:
            menu.insertSeparator(first)
        return True

    def replace(self, editor, start, end, new_word):
        editor.SendScintilla(QsciScintilla.SCI_SETTARGETRANGE, start, end)
        data = new_word.encode('utf-8')
        editor.SendScintilla(QsciScintilla.SCI_REPLACETARGET, len(data), data)
        self.request(editor)

    def add_word(self, word):
        self.checker.add_word(word)
        for editor in list(self.editors):
            self.underline(editor)


import re
_NON_ASCII = re.compile(r'[^\x00-\x7f]')
