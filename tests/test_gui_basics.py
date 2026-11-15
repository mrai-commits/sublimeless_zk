"""Regression tests: links, renaming, titles, find/replace."""
import os
from harness import run_gui_tests, note, check, messages, szk, ZK
import findandreplace
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

N1 = note('201801010101 First note.md', '# First note\ntags = #a\n\nSee [[201801010102]] and [[209901010101]].\n')
N2 = note('201801010102 Vol. 2 Ch. 5 intro.md', '# Vol. 2 Ch. 5 intro\n\nBody [[201801010101]]\n')
N3 = note('201801010103 To rename.md', '# To rename\n')


def results(app):
    with open(app.project.get_search_results_filn(), encoding='utf-8') as f:
        return f.read()


def test_altclick_missing_note(app):          # item 21
    app.open_document(N1)
    app.clicked_noteid('209901010101', False, True, False)
    check('alt-click on missing link lists referencing notes', '1 Notes referencing' in results(app))
    app.clicked_noteid('209901010101', False, False, False)
    check('click on missing link opens nothing', app.get_active_editor().file_name, N1)


def test_title_with_periods(app):             # item 32
    editor = app.open_document(N2)
    check('origin title keeps periods', app.project.get_note_id_and_title_of(editor), ('201801010102', 'Vol. 2 Ch. 5 intro'))
    app.clicked_noteid('201801010102', False, True, False)
    check('referencing title keeps periods', 'Vol. 2 Ch. 5 intro' in results(app).split('\n')[0])


def test_rename_updates_open_list(app):       # items 5, 12
    app.open_document(N3)
    szk.show_input_panel = lambda *a, **k: 'Renamed. Now'
    app.rename_note()
    app.app.processEvents()
    panel = app.gui.notelist_panel
    names = [panel.item(i).text() for i in range(panel.count())]
    check('old name gone from open notes', '201801010103 To rename.md' in names, False)
    check('new name in open notes', '201801010103 Renamed. Now.md' in names)
    check('file renamed on disk', os.path.exists(os.path.join(ZK, '201801010103 Renamed. Now.md')))
    tabs = [app.gui.qtabs.tabText(i) for i in range(app.gui.qtabs.count())]
    check('old name gone from tabs', any('To rename' in t for t in tabs), False)


def dialog(app, find, replace):
    d = findandreplace.FindDlg(app.gui, app.gui.qtabs)
    d.findField.setPlainText(find)
    d.replaceField.setPlainText(replace)
    return d


def test_replace_changes_highlighted_match(app):   # item 8
    e = app.open_document(N1)
    e.setText('A x A y A z A\n'); e.setCursorPosition(0, 0)
    d = dialog(app, 'A', 'Q')
    d.find()
    check('find highlights first match', e.getSelection(), (0, 0, 0, 1))
    d.replace()
    check('replace changes the highlighted match', e.text(), 'Q x A y A z A\n')
    check('replace then highlights the next match', e.getSelection(), (0, 4, 0, 5))
    e.setText('A x A\n'); e.setCursorPosition(0, 0)
    d = dialog(app, 'A', 'Q')
    d.replace()
    check('replace without prior find only highlights', e.text(), 'A x A\n')


def test_replace_all_terminates(app):          # item 42
    e = app.open_document(N1)
    e.setText('A x A y\nA z A\n'); e.setCursorPosition(0, 0)
    d = dialog(app, 'A', 'A B')
    check('replace all A -> A B count', d.replaceAll(), 4)
    check('replace all A -> A B text', e.text(), 'A B x A B y\nA B z A B\n')
    e.undo()
    check('replace all is one undo step', e.text(), 'A x A y\nA z A\n')
    d = dialog(app, 'a', 'b'); d.caseSens.setChecked(True)
    check('case sensitive option is honoured', d.replaceAll(), 0)
    d = dialog(app, 'zzz', 'b')
    d.replaceAll()
    check('replace all reports no match', d.resultLabel.text(), 'Not found')


def test_tab_moves_to_replace_field(app):      # item 40
    d = dialog(app, 'abc', '')
    d.show(); app.app.processEvents()
    d.activateWindow(); d.findField.setFocus(); app.app.processEvents()
    QTest.keyClick(d.findField, Qt.Key_Tab)
    app.app.processEvents()
    check('tab does not insert a tab', d.findField.toPlainText(), 'abc')
    check('tab moves focus to replace field', d.focusWidget() is d.replaceField)
    d.close()


def test_unexpected_error_does_not_close_the_app(app):
    import sys
    from PyQt5.QtCore import QTimer
    hook = app.on_unexpected_error            # the harness replaced sys.excepthook with its own
    try:
        raise RuntimeError('deliberate test error')
    except RuntimeError:
        hook(*sys.exc_info())
    check('the user is told', 'Something went wrong (RuntimeError)' in app.gui.statusBar().currentMessage())
    check('the app is still usable', app.gui.isVisible())


run_gui_tests([test_altclick_missing_note, test_title_with_periods, test_rename_updates_open_list,
               test_replace_changes_highlighted_match, test_replace_all_terminates,
               test_tab_moves_to_replace_field, test_unexpected_error_does_not_close_the_app])
