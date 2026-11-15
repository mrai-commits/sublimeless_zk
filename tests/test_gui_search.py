"""Tests for search and citation functions added in 1.0."""
import os
from harness import run_gui_tests, note, check, szk, ZK
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import zkutils, fuzzypanel, inputpanel

note('refs.bib', '''@book{weick1995, author={Weick, Karl E.}, title={Sensemaking in Organizations}, year={1995}, publisher={Sage}}
@article{weick1993, author={Weick, Karl E.}, title={The Collapse of Sensemaking}, journal={ASQ}, year={1993}}
@book{gumusay2020, author={Gümüsay, Ali}, title={Unlocking Hybridity}, year={2020}, publisher={Pub}}
''')
A = note('201801010701 Apple.md', '# Apple\ntags = #fruit #red\n\napple pie and organisation\n')
B = note('201801010702 Pear.md', '# Pear\ntags = #fruit #green\n\npear tart and organization\n')
C = note('201801010703 Plum.md', '# Plum\ntags = #fruit\n\nplum, apple and pear together\n')
D = note('201801010704 Zebra.md', '# Zebra\ntags = #animal\n\nnothing here\n')


def found(app, spec):
    return sorted(os.path.basename(f).split(' ')[0][-2:] for f in app.find_in_files(spec))


def test_file_search_syntax(app):              # item 39
    check('space means or', found(app, 'pie tart'), ['01', '02'])
    check('comma means and', found(app, 'apple, pear'), ['03'])
    check('or and and combined', found(app, 'pie tart, organi'), ['01', '02'])
    check('!! means not', found(app, 'apple, !!plum'), ['01'])
    check('phrase in double double-quotes', found(app, '""apple and pear""'), ['03'])
    check('a comma inside a phrase is text', found(app, '""plum, apple""'), ['03'])
    app.project.settings['search_comma_is_and'] = False
    check('old rule can be switched back on', found(app, 'apple pear'), ['03'])
    app.project.settings['search_comma_is_and'] = True


def test_wildcards(app):                       # item 46
    check('? stands for one letter', found(app, 'organi?ation'), ['01', '02'])
    check('* stands for any letters', found(app, 'org*tion'), ['01', '02'])
    check('* does not run over words', found(app, 'apple*pear'), [])


def test_tag_search_panel(app):                # item 38
    panel = inputpanel.TagSearchPanel(None, 'tags', {'#fruit': 3, '#red': 1, '#green': 1, '#animal': 1})
    check('all tags are listed with counts', [panel.list_box.item(i).text() for i in range(panel.list_box.count())],
          ['#animal (1)', '#fruit (3)', '#green (1)', '#red (1)'])
    panel.show(); app.app.processEvents()
    QTest.keyClicks(panel.line_edit, '#fr')
    check('typing narrows the list', panel.shown_tags, ['#fruit'])
    QTest.keyClick(panel.line_edit, Qt.Key_Tab)
    check('Tab inserts the tag', panel.line_edit.text(), '#fruit ')
    QTest.keyClicks(panel.line_edit, ', !#g')
    QTest.keyClick(panel.line_edit, Qt.Key_Down)
    QTest.keyClick(panel.line_edit, Qt.Key_Tab)
    check('a negated tag is completed too', panel.line_edit.text(), '#fruit , !#green ')
    panel._ok_clicked()
    app.advanced_tag_search(panel.text())
    with open(app.project.get_search_results_filn(), encoding='utf-8') as f:
        head = f.read().split('\n')[0]
    check('the search runs with the composed line', head.startswith('# 2 Notes matching search'))
    panel.close()


def test_sort_setting(app):                    # item 36: existing setting, verified
    note('201801010700 Zzz first id.md', '# Zzz\ntags = #fruit\n')
    def order():
        app.advanced_tag_search('#fruit')
        with open(app.project.get_search_results_filn(), encoding='utf-8') as f:
            return [l for l in f.read().split('\n') if '[[' in l][0]
    app.project.settings['sort_notelists_by'] = 'id'
    check('tag search sorted by id', '201801010700' in order())
    app.project.settings['sort_notelists_by'] = 'title'
    check('tag search sorted by title', '201801010701' in order())
    app.project.settings['sort_notelists_by'] = 'id'


def test_selector_finds_by_words(app):         # item 35
    items = ['Weick 1995 - Sensemaking in Organizations (weick1995)',
             'Weick 1993 - The Collapse of Sensemaking (weick1993)',
             'Gümüsay 2020 - Unlocking Hybridity (gumusay2020)',
             'Wernick 1990 - Something else (wernick1990)']
    check('author and year pick one paper', fuzzypanel.find_items('weick 1993', items, 50)[0], items[1])
    check('words in any order', fuzzypanel.find_items('collapse weick', items, 50)[0], items[1])
    check('accents are ignored', fuzzypanel.find_items('gumusay', items, 50)[0], items[2])
    check('exact matches come before loose ones', fuzzypanel.find_items('weick', items, 50)[:2], items[:2])
    check('loose typing still works when nothing matches exactly', fuzzypanel.find_items('wck93', items, 50)[0], items[1])
    check('nothing found gives an empty list', fuzzypanel.find_items('qqqq', items, 50), [])
    # speed with a library of 4,000 entries: every keystroke runs a search
    import time, random
    random.seed(1)
    names = ['Alvesson', 'Alvarez', 'Aldrich', 'Smith', 'Müller', 'Weick', 'Allen', 'Albert']
    big = {f'{random.choice(names)} & {random.choice(names)} {1980 + i % 45} - A reasonably long title about organisational identity and culture, number {i} (key{i})': i
           for i in range(4000)}
    panel = fuzzypanel.FuzzySearchPanel(item_dict=big, max_items=50)
    worst = 0
    for typed in ('a', 'al', 'alv', 'alve', 'alvesson 1999', 'alvsn', 'zzqx'):
        panel.input_line.setText(typed)
        t = time.time(); panel.text_changed(); worst = max(worst, time.time() - t)
    print('     slowest keystroke with 4,000 entries: %.0f ms' % (worst * 1000))
    check('no keystroke takes longer than 50 ms with 4,000 entries', worst < 0.05)


def test_insert_full_reference(app):           # item 7
    e = app.open_document(D)
    e.setText('See: \n'); e.setCursorPosition(0, 5)
    szk.show_fuzzy_panel = lambda parent, title, choices, **k: ('x', 'weick1995')
    app.bib_entries = None
    app.insert_full_reference()
    check('full reference is inserted', e.text(), 'See: Weick, Karl E. 1995. Sensemaking in Organizations. Sage.\n')


def test_delete_note_updates_open_list(app):
    victim = note('201801010799 Delete me.md', '# Delete me\n')
    app.open_document(victim); app.app.processEvents()
    app.delete_note(); app.app.processEvents()
    panel = app.gui.notelist_panel
    check('deleted note leaves the open-notes panel',
          any('Delete me' in panel.item(i).text() for i in range(panel.count())), False)
    check('and is gone from disk', os.path.exists(victim), False)


run_gui_tests([test_file_search_syntax, test_wildcards, test_tag_search_panel, test_sort_setting,
               test_selector_finds_by_words, test_insert_full_reference, test_delete_note_updates_open_list])
