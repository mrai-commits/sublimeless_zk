"""Tests for the functions added in 1.0 (first batch)."""
import os, time
from harness import run_gui_tests, note, check, szk, ZK
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtGui import QKeySequence
import editfeatures, fuzzypanel

N1 = note('201801010401 Features.md', '# Features\ntags = #alpha #beta\n\nplain line\n')
N2 = note('201801010402 Second.md', '# Second\ntags = #alpha\n\nSee [[201801010401]] and [@smith2020].\n')
N3 = note('201801010403 Third.md', '# Third\ntags = #alpha #gamma\n')


def results(app):
    with open(app.project.get_search_results_filn(), encoding='utf-8') as f:
        return f.read()


def fresh(app, text):
    e = app.open_document(N1)
    e.setText(text)
    e.setFocus()
    app.app.processEvents()
    return e


def test_format_shortcuts(app):                # item 1
    e = fresh(app, 'some words here\n')
    e.setSelection(0, 5, 0, 10)
    app.format_selection('**')
    check('bold wraps the selection', e.text(), 'some **words** here\n')
    app.format_selection('**')
    check('bold again unwraps', e.text(), 'some words here\n')
    e.setSelection(0, 5, 0, 10)
    app.format_selection('*')
    check('italic wraps', e.text(), 'some *words* here\n')
    e.setSelection(0, 6, 0, 11)                 # only the word, markers outside
    app.format_selection('*')
    check('italic unwraps with markers outside the selection', e.text(), 'some words here\n')
    e.setSelection(0, 5, 0, 10); app.format_selection('**')
    e.setSelection(0, 7, 0, 12); app.format_selection('*')
    check('italic inside bold gives bold italic', e.text(), 'some ***words*** here\n')
    e = fresh(app, 'ab\n'); e.setCursorPosition(0, 1)
    app.format_selection('`')
    check('no selection: inserts the pair', e.text(), 'a``b\n')
    check('no selection: cursor between the markers', e.getCursorPosition(), (0, 2))
    check('Bold is on Ctrl+B', app.formatBoldAction.shortcut().toString(), 'Ctrl+B')
    check('Insert Bibliography moved to Ctrl+Alt+B', app.autoBibAction.shortcut().toString(), 'Ctrl+Alt+B')   # item 34


def test_list_toggle(app):
    e = fresh(app, 'one\ntwo\n\nthree\n')
    e.setSelection(0, 0, 3, 5)
    app.format_list(False)
    check('dash list over selected lines', e.text(), '- one\n- two\n\n- three\n')
    e.setSelection(0, 0, 3, 7)
    app.format_list(True)
    check('dash list becomes numbered list', e.text(), '1. one\n2. two\n\n3. three\n')
    e.setSelection(0, 0, 3, 8)
    app.format_list(True)
    check('toggle again removes the numbers', e.text(), 'one\ntwo\n\nthree\n')


def press_enter(app, e):
    QTest.keyClick(e, Qt.Key_Return)
    app.app.processEvents()


def test_list_continuation(app):               # item 13
    e = fresh(app, '- first')
    e.setCursorPosition(0, 7); press_enter(app, e)
    check('Enter continues a dash list', e.text(), '- first\n- ')
    QTest.keyClicks(e, 'second'); press_enter(app, e)
    check('and again', e.text(), '- first\n- second\n- ')
    press_enter(app, e)
    check('Enter on an empty item ends the list', e.text(), '- first\n- second\n')
    e = fresh(app, '    9. nine')
    e.setCursorPosition(0, 11); press_enter(app, e)
    check('numbered list counts on, keeps indentation', e.text(), '    9. nine\n    10. ')
    e = fresh(app, 'plain')
    e.setCursorPosition(0, 5); press_enter(app, e)
    check('plain text is left alone', e.text(), 'plain\n')
    e = fresh(app, '- ab')
    e.setCursorPosition(0, 3); press_enter(app, e)
    check('Enter in the middle of an item splits it', e.text(), '- a\n- b')
    e.continue_lists = False
    e.setText('- x'); e.setCursorPosition(0, 3); press_enter(app, e)
    check('can be switched off', e.text(), '- x\n')
    e.continue_lists = True


def test_selection_word_count(app):            # item 31
    e = fresh(app, 'one two three four five\n')
    app.update_status_bar()
    check('status bar: all words', app.gui.word_count_label.text(), 'Words: 5')
    e.setSelection(0, 4, 0, 13)
    app.update_status_bar()
    check('status bar: words in selection', app.gui.word_count_label.text(), 'Words: 2 of 5')


def test_tag_counts(app):                      # items 11, 30
    fresh(app, '# Features\ntags = #alpha #beta\n\nplain line\n')
    app.save_all()
    app.show_all_tags(check_editor=False)
    lines = results(app).split('\n')
    check('tag list shows counts, sorted by name', lines[2:5], ['* #alpha (3)', '* #beta (1)', '* #gamma (1)'])
    note('201801010404 Fourth.md', '# Fourth\ntags = #gamma\n')
    app.show_all_tags(check_editor=False, sort='count')
    check('sorted by count', results(app).split('\n')[2:5], ['* #alpha (3)', '* #gamma (2)', '* #beta (1)'])
    # a tag in the list is still clickable
    app.clicked_tag('#gamma', False, False, False)
    check('clicking a counted tag lists its notes', results(app).split('\n')[0], '# 2 Notes referencing #gamma')


def test_recent_periods(app):                  # item 9
    now = int(time.time())
    app.app_state.recently_viewed[app.project.folder] = {N1: now - 60, N2: now - 3 * 3600, N3: now - 30 * 3600}
    app.project.settings['recent_notes_hours'] = [1, 6, 24, 168]
    app.show_recent_views()
    text = app.gui.search_results_editor.text()
    heads = [l for l in text.split('\n') if l.startswith('## ')]
    check('period headings come from the setting', heads, ['## Last hour', '## Last 6 hours', '## Last 24 hours', '## Last 7 days'])
    section = text.split('## Last 6 hours')[1].split('##')[0]
    check('a note opened 3 hours ago is under "Last 6 hours"', '201801010402' in section)
    check('and only there', text.count('201801010402'), 1)


def test_palette_wraps_around(app):            # item 16
    panel = fuzzypanel.FuzzySearchPanel(item_dict={c: c for c in 'abcde'})
    panel.text_changed()
    panel.up_pressed()
    check('up from the first entry goes to the last', panel.list_box.currentRow(), 4)
    panel.down_pressed()
    check('down from the last entry goes to the first', panel.list_box.currentRow(), 0)


def test_pane_sizes_remembered(app):           # item 17
    app.gui.resize(1200, 700); app.app.processEvents()
    app.gui.mainsplit.setSizes([0, 800, 400]); app.gui.subsplit.setSizes([500, 150])
    app.app.processEvents()
    wanted = (app.gui.mainsplit.sizes(), app.gui.subsplit.sizes())
    app.save_appstate()
    import appstate
    saved = appstate.AppState().window
    check('pane sizes are written to the state file', (saved.get('mainsplit'), saved.get('subsplit')), wanted)
    app.gui.mainsplit.setSizes([0, 600, 600]); app.gui.subsplit.setSizes([300, 300])
    app.gui.restore_layout(saved); app.app.processEvents()
    check('pane sizes are restored', (app.gui.mainsplit.sizes(), app.gui.subsplit.sizes()), wanted)


def test_new_note_keep_text(app):              # items 15, 19
    e = fresh(app, 'An idea worth its own note. More.\n')
    e.setSelection(0, 3, 0, 7)
    szk.show_input_panel = lambda *a, **k: 'Idea?'
    app.zk_new_zettel(keep_text=True)
    text = e.text()
    check('selected text stays', text.startswith('An idea [['), True)
    check('link follows the text', text[8:10] == '[[' and text.rstrip().endswith('worth its own note. More.'))
    new = [f for f in os.listdir(ZK) if f.endswith('Idea-.md')]
    check('? is replaced in the file name', len(new), 1)
    check('and the user is told', 'not allowed in file names' in app.gui.statusBar().currentMessage())
    with open(os.path.join(ZK, new[0]), encoding='utf-8') as f:
        check('the title in the note keeps the ?', 'Idea?' in f.read())


def test_insert_link_other_way(app):           # item 23
    e = fresh(app, '\n')
    szk.show_fuzzy_panel = lambda *a, **k: ('201801010402 Second', '201801010402 Second')
    app.project.settings['insert_links_with_titles'] = False
    e.setCursorPosition(0, 0); app.insert_link()
    check('default: link without title', e.text(), '[[201801010402]]\n')
    e.setText('\n'); e.setCursorPosition(0, 0); app.insert_link(toggle_title=True)
    check('other way round: link with title', e.text(), '[[201801010402]] Second\n')


def test_follow_link_close_parent(app):        # item 25
    app.save_all()
    e = app.open_document(N2)
    e.setCursorPosition(3, 10)                  # inside [[201801010401]]
    app.follow_link_close_parent()
    app.app.processEvents()
    names = [app.gui.qtabs.tabText(i) for i in range(app.gui.qtabs.count())]
    check('target note is active', os.path.basename(app.get_active_editor().file_name), '201801010401 Features.md')
    check('parent note is closed', any('Second' in n for n in names), False)


def test_click_link_close_parent(app):         # item 25, with the mouse
    app.save_all()
    e = app.open_document(N2); app.app.processEvents()
    both = int(Qt.ControlModifier | Qt.ShiftModifier)
    e.lexer().on_click_indicator(3, 10, both)   # Cmd/Ctrl+Shift+click on [[201801010401]]
    app.app.processEvents()
    names = [app.gui.qtabs.tabText(i) for i in range(app.gui.qtabs.count())]
    check('Cmd+Shift+click opens the target', os.path.basename(app.get_active_editor().file_name), '201801010401 Features.md')
    check('and closes the parent note', any('Second' in n for n in names), False)
    e = app.open_document(N2); app.app.processEvents()
    e.lexer().on_click_indicator(3, 10, 0)
    app.app.processEvents()
    names = [app.gui.qtabs.tabText(i) for i in range(app.gui.qtabs.count())]
    check('a plain click keeps the parent open', any('Second' in n for n in names), True)


def test_citation_needs_modifier(app):         # item 41
    e = app.open_document(N2); app.app.processEvents()
    clicked = []
    e.lexer().cite_key_clicked.connect(lambda key, *a: clicked.append(key))
    col = e.text(3).index('@smith') + 2
    e.lexer().on_click_indicator(3, col, 0)
    check('plain click on a citation does nothing', clicked, [])
    e.lexer().on_click_indicator(3, col, int(Qt.ControlModifier))
    check('Cmd/Ctrl+click opens it', clicked, ['@smith2020'])
    e.setCursorPosition(3, col); app.zk_follow_link()
    check('follow-link key opens it', clicked, ['@smith2020', '@smith2020'])


run_gui_tests([test_format_shortcuts, test_list_toggle, test_list_continuation, test_selection_word_count,
               test_tag_counts, test_recent_periods, test_palette_wraps_around, test_pane_sizes_remembered,
               test_new_note_keep_text, test_insert_link_other_way, test_follow_link_close_parent,
               test_click_link_close_parent, test_citation_needs_modifier])
