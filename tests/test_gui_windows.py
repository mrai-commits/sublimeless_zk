"""Notes in their own windows (new in 1.0)."""
import os
from harness import run_gui_tests, note, check, szk, ZK
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

A = note('201801010801 Alpha.md', '# Alpha\n\nfirst note with [[201801010802]] link\n')
B = note('201801010802 Beta.md', '# Beta\n\nsecond note\n')
C = note('201801010803 Gamma.md', '# Gamma\n')


def tab_names(app):
    return [app.gui.qtabs.tabText(i) for i in range(app.gui.qtabs.count())]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def focus(app, widget):
    widget.window().activateWindow(); widget.setFocus(); app.app.processEvents()
    QTest.qWaitForWindowActive(widget.window(), 1000)
    app.app.processEvents()


def test_open_window(app):
    primary = app.open_document(A)
    window = app.open_note_window(); app.app.processEvents()
    check('a window opens', window is not None and window.isVisible())
    check('its title is the note name', window.windowTitle(), '201801010801 Alpha.md')
    check('the note stays open as a tab', '201801010801 Alpha.md' in tab_names(app))
    check('the window shows the note text', window.view.text(), primary.text())
    again = app.open_note_window(primary)
    check('a second request reuses the window', again is window and len(app.note_windows) == 1)


def test_text_is_shared(app):
    primary = app.open_document(A)
    window = app.open_note_window(primary); app.app.processEvents()
    focus(app, window.view)
    window.view.setCursorPosition(2, 0)
    QTest.keyClicks(window.view, 'XYZ '); app.app.processEvents()
    check('typing in the window appears in the tab', primary.text().split('\n')[2].startswith('XYZ first note'))
    check('the tab is marked as changed', '201801010801 Alpha.md*' in tab_names(app))
    check('the window title is marked as changed', window.windowTitle().endswith('*'))
    primary.setCursorPosition(0, 7); primary.insert(' TAB')
    check('typing in the tab appears in the window', window.view.text(0).strip(), '# Alpha TAB')
    check('highlighting works in the window',
          window.view.lexer().description(window.view.SendScintilla(window.view.SCI_GETSTYLEAT, 2)), 'h1.text')


def test_save_from_window(app):
    primary = app.open_document(A)
    app.open_document(B)                       # another tab is current in the main window
    window = app.open_note_window(primary); app.app.processEvents()
    focus(app, window.view)
    check('the active editor is the window', app.get_active_editor() is window.view)
    app.save(); app.app.processEvents()
    check('save in the window writes that note', 'XYZ first note' in read(A))
    check('and not the current tab', read(B), '# Beta\n\nsecond note\n')
    check('the changed mark is gone from the tab', '201801010801 Alpha.md' in tab_names(app))
    check('and from the window title', window.windowTitle(), '201801010801 Alpha.md')


def test_commands_apply_to_window(app):
    primary = app.open_document(A)
    window = app.open_note_window(primary); app.app.processEvents()
    focus(app, window.view)
    window.view.setSelection(0, 2, 0, 7)
    QTest.keyClick(window.view, Qt.Key_B, Qt.ControlModifier); app.app.processEvents()
    check('a shortcut typed in the window acts on its note', primary.text(0).strip(), '# **Alpha** TAB')
    app.update_status_bar()
    check('status bar counts the window selection', app.gui.word_count_label.text().startswith('Words: 1 of'))


def test_follow_link_from_window(app):
    primary = app.open_document(A)
    window = app.open_note_window(primary); app.app.processEvents()
    line = [i for i in range(window.view.lines()) if '[[' in window.view.text(i)][0]
    window.view.lexer().on_click_indicator(line, window.view.text(line).index('[[') + 4, 0)
    app.app.processEvents()
    check('a link clicked in the window opens the note in the main window',
          os.path.basename(app.gui.qtabs.currentWidget().file_name), '201801010802 Beta.md')
    check('the window keeps its note', window.view.file_name, A)


def test_close_window_keeps_tab(app):
    primary = app.open_document(A)
    window = app.open_note_window(primary); app.app.processEvents()
    focus(app, window.view)
    app.close_current_tab(); app.app.processEvents()
    check('Close in the window closes the window', len(app.note_windows), 0)
    check('the tab stays', '201801010801 Alpha.md*' in tab_names(app) or '201801010801 Alpha.md' in tab_names(app))
    check('the text is intact', 'XYZ first note' in primary.text())


def test_close_tab_closes_window(app):
    app.save_all()
    primary = app.open_document(C)
    app.open_note_window(primary); app.app.processEvents()
    app.tab_close_requested(app.gui.qtabs.indexOf(primary)); app.app.processEvents()
    check('closing the tab closes its window', len(app.note_windows), 0)
    check('the tab is gone', any('Gamma' in n for n in tab_names(app)), False)


def test_rename_from_window(app):
    primary = app.open_document(C)
    window = app.open_note_window(primary); app.app.processEvents()
    app.open_document(B)
    focus(app, window.view)
    szk.show_input_panel = lambda *a, **k: 'Gamma renamed'
    app.rename_note(); app.app.processEvents()
    check('rename from a window renames that note', os.path.exists(os.path.join(ZK, '201801010803 Gamma renamed.md')))
    check('the other note is untouched', os.path.exists(B))
    check('the window of the old name is closed', len(app.note_windows), 0)
    check('tabs show the new name only', [n for n in tab_names(app) if 'Gamma' in n], ['201801010803 Gamma renamed.md'])


def test_double_click_and_quit(app):
    primary = app.open_document(B)
    app.open_note_window_for_tab(app.gui.qtabs.indexOf(primary)); app.app.processEvents()
    check('double-click on a tab opens its window', len(app.note_windows), 1)
    app.save_all()
    check('quitting is allowed', app.mainwindow_close_handler(), True)
    app.app.processEvents()
    check('and closes the note windows', len(app.note_windows), 0)


def test_windows_come_back(app):
    import appstate
    for path in (A, B):
        app.open_document(path)
    wa = app.open_note_window(app.open_document(A)); wb = app.open_note_window(app.open_document(B))
    wa.setGeometry(120, 90, 500, 400); wb.setGeometry(700, 150, 450, 380); app.app.processEvents()
    app.save_all()
    check('quitting is allowed', app.mainwindow_close_handler(), True)
    app.app.processEvents()
    app.save_appstate()                         # as happens again while shutting down
    saved = appstate.AppState().window.get('note_windows', {}).get(app.project.folder, [])
    check('the open windows are remembered', sorted(os.path.basename(e['file']) for e in saved),
          ['201801010801 Alpha.md', '201801010802 Beta.md'])
    # next start: the state is read again and the folder is opened
    app.app_state = appstate.AppState()
    app.reopen_notes(); app.app.processEvents()
    titles = sorted(w.windowTitle() for w in app.note_windows)
    check('they are reopened at the next start', titles, ['201801010801 Alpha.md', '201801010802 Beta.md'])
    alpha = [w for w in app.note_windows if 'Alpha' in w.windowTitle()][0]
    check('with their size', (alpha.geometry().width(), alpha.geometry().height()), (500, 400))
    app.close_note_windows(app.open_document(B)); app.app.processEvents()
    app.save_appstate()
    saved = appstate.AppState().window.get('note_windows', {}).get(app.project.folder, [])
    check('a window closed by the user is not reopened', [os.path.basename(e['file']) for e in saved], ['201801010801 Alpha.md'])
    app.close_note_windows()


run_gui_tests([test_open_window, test_text_is_shared, test_save_from_window, test_commands_apply_to_window,
               test_follow_link_from_window, test_close_window_keeps_tab, test_close_tab_closes_window,
               test_rename_from_window, test_double_click_and_quit, test_windows_come_back])
