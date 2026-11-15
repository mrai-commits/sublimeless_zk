"""Regression tests: highlighting of lists, citations and links; speed."""
import time
from harness import run_gui_tests, note, check, styles, style_at, clickable

LISTS = note('201801010201 Lists.md', '''# Lists

1. first item here
    1. second level item
    2. another second level
        - third level dash
2. back to first

- dash one
    - dash two
    1. number under dash

plain paragraph after

1. loose item

    2. nested after blank line

Ünïcödé line with a [[201801010201]] link and #tag here
''')
CITES = note('201801010202 Cites.md', '''# Cites

A [@smith2020] ok. B [-@smith2020] noauthor. C [e.g., @smith2020] eg. D [@smith2020; @editor2019, p. 3] two.

Mail [write to a@b.com] and MMD [][#mmdkey] here.

Web [first](http://a.example) and [second](http://b.example) rest of the line.

Long [link](http://example.org/''' + 'a' * 400 + ''') end.
''')
clicked = []


def line_of(editor, start):
    for i in range(editor.lines()):
        if editor.text(i).startswith(start):
            return i
    raise KeyError(start)


def test_ordered_lists(app):                   # items 10, 33
    e = app.open_document(LISTS); app.app.processEvents()
    check('first level: number is symbol, text is list', styles(e, line_of(e, '1. first')),
          [(0, 'list.symbol'), (2, 'list.ordered')])
    check('first level: whole text has the list style', style_at(e, line_of(e, '1. first'), 17), 'list.ordered')
    check('second level numbered', styles(e, line_of(e, '    1. second')), [(0, 'list.symbol'), (6, 'list.ordered')])
    check('third level dash under number', styles(e, line_of(e, '        - third'))[:2],
          [(0, 'list.symbol'), (9, 'list.unordered')])
    check('number nested under dash', styles(e, line_of(e, '    1. number under'))[:2],
          [(0, 'list.symbol'), (6, 'list.ordered')])
    check('paragraph after list is plain', styles(e, line_of(e, 'plain paragraph')), [(0, 'default')])
    check('nested item after blank line is a list item, not code',
          styles(e, line_of(e, '    2. nested'))[:2], [(0, 'list.symbol'), (6, 'list.ordered')])


def test_non_ascii_offsets(app):               # clickable ranges after multi-byte characters
    e = app.open_document(LISTS); app.app.processEvents()
    l = line_of(e, 'Ünïcödé')
    text = e.text(l).rstrip('\n')
    marks = clickable(e, l, e.lexer().indicator_id_noteid)
    start = len(text[:text.index('201801010201')].encode('utf-8'))
    check('note link range is correct after umlauts', marks[start - 1:start + 13], '.' + 'X' * 12 + '.')


def test_citations(app):                       # items 14, 26, 6
    e = app.open_document(CITES); app.app.processEvents()
    lexer = e.lexer()
    l = line_of(e, 'A [@smith')
    text = e.text(l)
    for label, frag in (('plain', '@smith2020] ok'), ('suppressed author', '@smith2020] noauthor'),
                        ('with e.g.', '@smith2020] eg'), ('second key after ;', '@editor2019')):
        col = text.index(frag)
        check('citation highlighted: ' + label, style_at(e, l, col), 'citekey')
    marks = clickable(e, l, lexer.indicator_id_citekey)
    check('four citations, five clickable keys', len([m for m in marks.split('.') if m]), 5)
    check('prefix "e.g., " is not clickable', marks[text.index('e.g.')], '.')
    l = line_of(e, 'Mail')
    text = e.text(l)
    check('e-mail address is not a citation', style_at(e, l, text.index('@b.com')), 'default')
    check('MultiMarkdown citation still highlighted', style_at(e, l, text.index('#mmdkey')), 'citekey')

    # clicking a key reports exactly that key
    lexer.cite_key_clicked.connect(lambda key, *a: clicked.append(key))
    l = line_of(e, 'A [@smith')
    text = e.text(l)
    from PyQt5.QtCore import Qt
    ctrl = int(Qt.ControlModifier)        # citations open on Cmd/Ctrl+click
    lexer.on_click_indicator(l, text.index('@editor2019') + 3, ctrl)
    lexer.on_click_indicator(l, text.index('@smith2020] noauthor') + 3, ctrl)
    check('click reports the key under the pointer', clicked[-2:], ['@editor2019', '@smith2020'])


def test_web_links(app):                       # items 37, 45
    e = app.open_document(CITES); app.app.processEvents()
    lexer = e.lexer()
    l = line_of(e, 'Web [first]')
    text = e.text(l)
    check('first link on line', style_at(e, l, text.index('http://a')), 'link.url')
    check('second link on line', style_at(e, l, text.index('http://b')), 'link.url')
    check('text after links is plain', style_at(e, l, text.index('rest of')), 'default')
    urls = []
    lexer.hyperlink_clicked.connect(urls.append)
    lexer.on_click_indicator(l, text.index('http://b') + 2, 0)
    l = line_of(e, 'Long [link]')
    lexer.on_click_indicator(l, e.text(l).index('http://') + 300, 0)
    check('second link opens its own address', urls[:1], ['http://b.example'])
    check('very long (wrapped) link is clickable', urls[1:], ['http://example.org/' + 'a' * 400])


def test_speed(app):                           # item 27
    para = 'Lorem ipsum [@smith2020] dolor [[201801010101]] sit amet #tag **bold** consectetur *it* adipiscing élit sed do. '
    txt = '# Perf\n\n' + '\n\n'.join(para * 5 for _ in range(125)) + '\n'
    e = app.open_document(note('201801010299 Perf.md', txt)); app.app.processEvents()
    t = time.time()
    for _ in range(5):
        e.lexer().styleText(0, len(txt))
    ms = (time.time() - t) / 5 * 1000
    print('     %d words: %.0f ms per restyle' % (len(txt.split()), ms))
    check('10,000-word note restyles in under 150 ms', ms < 150)


def test_critic_markup(app):                   # item 20
    path = note('201801010203 Critic.md', '# Critic\n\nKeep {++added++} and {--gone--} and {~~old~>new~~}, {==marked==}{>>why<<} end.\n\nNumbered:\n\n1. item [@smith2020]\n')
    e = app.open_document(path); app.app.processEvents()
    l = line_of(e, 'Keep')
    text = e.text(l)
    check('off by default', style_at(e, l, text.index('added')), 'default')
    e.lexer().critic_markup = True
    e.lexer().styleText(0, len(e.text())); app.app.processEvents()
    for word, style in (('added', 'critic.addition'), ('gone', 'critic.deletion'), ('old', 'critic.deletion'),
                        ('new', 'critic.addition'), ('marked', 'critic.highlight'), ('why', 'critic.comment')):
        check('CriticMarkup: ' + word, style_at(e, l, text.index(word)), style)
    check('text around stays plain', style_at(e, l, text.index(' end.') + 1), 'default')
    l2 = line_of(e, '1. item')
    check('other highlighting still works beside it', style_at(e, l2, e.text(l2).index('@smith')), 'citekey')


import zkutils, sublimeless_zk
sublimeless_zk.open_hyperlink = lambda url: None      # never start a browser in tests
run_gui_tests([test_ordered_lists, test_non_ascii_offsets, test_citations, test_web_links, test_speed, test_critic_markup])
