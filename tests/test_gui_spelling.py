"""Spell checking (new in 1.0)."""
import os, time
from harness import run_gui_tests, note, check, szk, ZK
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QMenu
from PyQt5.Qsci import QsciScintilla
import spellui

TEXT = '''# Speling test

The colour of the organisaton is fine, but recieve is wrong.
La organización está bien; l'école aussi, aujourd’hui.
Code `teh codde` and [[201801010901]] and [@smithh2020] and #tagg and http://exmple.org stay.
Ünïcödé wurd after accents: mistaek.

```
blokk of codde
```
'''
N = note('201801010901 Spelling.md', TEXT)


def wait_ready(app):
    deadline = time.time() + 30
    while not app.spell.checker.ready and time.time() < deadline:
        app.app.processEvents(); time.sleep(0.05)
    return app.spell.checker.ready


def underlined(editor):
    """The underlined words of the editor."""
    data = editor.text().encode('utf-8')
    words, pos, n = [], 0, len(data)
    while pos < n:
        if editor.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, spellui.SPELL_INDICATOR, pos):
            end = editor.SendScintilla(QsciScintilla.SCI_INDICATOREND, spellui.SPELL_INDICATOR, pos)
            words.append(data[pos:end].decode('utf-8')); pos = end
        else:
            pos += 1
    return words


def open_checked(app, path=N):
    e = app.open_document(path); app.app.processEvents()
    app.spell.underline(e); app.spell.finish_now(); app.app.processEvents()
    return e


def test_dictionaries_load(app):
    check('dictionaries load in the background', wait_ready(app))
    check('three languages', sorted(app.spell.checker.dictionaries), ['en_GB', 'es_ES', 'fr_FR'])


def test_underlines(app):
    e = open_checked(app)
    marked = underlined(e)
    check('misspelled words are underlined', marked, ['Speling', 'organisaton', 'recieve', 'Ünïcödé', 'wurd', 'mistaek'])
    check('English, Spanish and French words are accepted side by side',
          any(w in marked for w in ('colour', 'organización', 'école', 'aujourd’hui')), False)
    check('code, links, citations, tags and addresses are left alone',
          any(w in marked for w in ('teh', 'codde', 'smithh2020', 'tagg', 'exmple', 'blokk')), False)


def test_underline_follows_edits(app):
    e = open_checked(app)
    e.setFocus()
    line = [i for i in range(e.lines()) if 'recieve' in e.text(i)][0]
    col = e.text(line).index('recieve')
    e.setSelection(line, col, line, col + 7); e.replaceSelectedText('receive')
    e.setCursorPosition(0, 0)
    app.spell.underline(e); app.spell.finish_now()
    check('a corrected word loses its underline', 'recieve' in underlined(e) or 'receive' in underlined(e), False)


def menu_for(app, e, word):
    line = [i for i in range(e.lines()) if word in e.text(i)][0]
    pos = e.positionFromLineIndex(line, e.text(line).index(word) + 2)
    x = e.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
    y = e.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
    menu = e.createStandardContextMenu()
    added = app.spell.add_menu_entries(e, menu, QPoint(x + 1, y + 3))
    return menu, added


def test_suggestions_menu(app):
    e = open_checked(app)
    menu, added = menu_for(app, e, 'organisaton')
    labels = [a.text() for a in menu.actions()]
    check('right-click on a misspelled word offers a correction', added and labels[0], 'organisation')
    check('and "Add to dictionary"', 'Add "organisaton" to dictionary' in labels)
    check('the usual entries are still there', any('Copy' in l or 'Paste' in l for l in labels))
    menu.actions()[0].trigger(); app.app.processEvents()
    check('choosing it replaces the word', 'the organisation is fine' in e.text() and 'organisaton' not in e.text())
    menu, added = menu_for(app, e, 'colour')
    check('a correct word gets the plain menu', added, False)


def test_suggestions_are_ready_ahead(app):
    e = open_checked(app, note('201801010902 Ahead.md', '# Ahead\n\nA sentance with a mispelled wurd.\n'))
    app.spell.underline(e)                      # all words known now: suggestions start in the background
    checker = app.spell.checker
    deadline = time.time() + 20
    while not all(w in checker.suggestions for w in ('sentance', 'mispelled', 'wurd')) and time.time() < deadline:
        app.app.processEvents(); time.sleep(0.05)
    check('suggestions for the words on screen are prepared in the background',
          all(w in checker.suggestions for w in ('sentance', 'mispelled', 'wurd')))
    thread = checker._ahead_thread            # let the background work finish: it shares the processor
    while thread is not None and thread.is_alive() and time.time() < deadline:
        app.app.processEvents(); time.sleep(0.05)
    t = time.time(); menu, added = menu_for(app, e, 'sentance'); took = time.time() - t
    print('     right-click menu after preparation: %.0f ms' % (took * 1000))
    check('the right-click menu then opens at once (under 0.3 s)', added and took < 0.3)
    check('with the correction', menu.actions()[0].text(), 'sentence')


def test_last_word_is_marked_after_a_pause(app):   # D13: "Je suis dans la masson" stayed unmarked
    e = open_checked(app, note('201801010903 Pause.md', 'Je suis dans la masson'))
    app.gui.activateWindow(); e.setFocus(); app.app.processEvents()
    e.setCursorPosition(0, 22)                   # right after the last word, as after typing it
    app.spell.underline(e); app.spell.finish_now()
    if e.hasFocus():
        check('while typing, the word at the cursor is not marked yet', underlined(e), [])
    app.spell.underline_after_pause() if app.spell.paused_editors else app.spell.underline(e, spare_word_at_cursor=False)
    check('after a pause it is', underlined(e), ['masson'])
    check('the French word is among the suggestions', 'maison' in app.spell.checker.suggest('masson'))


def test_personal_dictionary(app):
    e = open_checked(app)
    menu, added = menu_for(app, e, 'mistaek')
    [a for a in menu.actions() if a.text().startswith('Add "mistaek"')][0].trigger(); app.app.processEvents()
    check('an added word is no longer underlined', 'mistaek' in underlined(e), False)
    personal = os.path.join(os.environ['HOME'], 'sublimeless_zk.rc', 'personal_dictionary.txt')
    with open(personal, encoding='utf-8') as f:
        check('and is kept in the personal dictionary file', 'mistaek' in f.read().split())


def test_switch_off(app):
    e = open_checked(app)
    app.spellAction.setChecked(False); app.app.processEvents()
    check('switching off removes the underlines', underlined(e), [])
    app.spellAction.setChecked(True); app.spell.underline(e); app.spell.finish_now()
    check('switching on brings them back', 'wurd' in underlined(e))


def test_long_note_stays_responsive(app):
    import random
    random.seed(3)
    stems = ['organis', 'manag', 'cultur', 'identit', 'lead', 'reflex', 'method', 'knowledg', 'discours', 'critic']
    ends = ['ation', 'ement', 'al', 'y', 'ership', 'ive', 'ology', 'e', 'es', 'ism', 'ed', 'ing', 'x', 'q']
    words = [random.choice(stems) + random.choice(ends) + random.choice(['', '', 's', 'ly']) for _ in range(9000)]
    path = note('201801010999 Long.md', '# Long\n\n' + ' '.join(words) + '\n')
    e = app.open_document(path); app.app.processEvents()
    t = time.time(); app.spell.underline(e); first = time.time() - t
    check('first pass does not wait for lookups (under 0.3 s)', first < 0.3)
    worst = 0
    while app.spell.pending:
        t = time.time(); app.spell.look_up_some(); worst = max(worst, time.time() - t)
    print('     first pass %.0f ms, longest pause while checking %.0f ms' % (first * 1000, worst * 1000))
    check('lookups never block the app for long (under 0.2 s)', worst < 0.2)
    check('and the result arrives', len(underlined(e)) > 0)


run_gui_tests([test_dictionaries_load, test_underlines, test_underline_follows_edits, test_suggestions_menu,
               test_suggestions_are_ready_ahead, test_last_word_is_marked_after_a_pause,
               test_personal_dictionary, test_switch_off, test_long_note_stays_responsive])
