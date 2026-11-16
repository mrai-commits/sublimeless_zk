"""Export of a note to Word and PDF (new in 1.0)."""
import os, zipfile, tempfile
from harness import run_gui_tests, note, check, ZK
import noteexport, settings

note('refs.bib', '@book{smith2020, author={Smith, John}, title={A Book}, year={2020}, publisher={Pub}}\n')
N = note('201801010601 Export me.md', '''# Export me

Some *text* with a citation [@smith2020] and a list:

1. one
2. two

| a | b |
|---|---|
| 1 | 2 |

<!-- references (auto)

[@smith2020]: Smith, John. 2020. A Book. Pub.

-->
''')
OUT = tempfile.mkdtemp(prefix='szk-export-')


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        return z.read('word/document.xml').decode('utf-8')


def test_pandoc_is_found(app):
    check('pandoc is found without configuration', bool(settings.get_pandoc()))


def test_word(app):
    app.open_document(N)
    out = app.export_note('docx', os.path.join(OUT, 'note.docx'), open_result=False)
    check('Word file is written', bool(out) and os.path.getsize(out) > 2000)
    xml = docx_text(out)
    check('Word: heading and text', 'Export me' in xml and 'citation' in xml)
    check('Word: citation is formatted', '(Smith 2020)' in xml)
    check('Word: reference appears once', xml.count('A Book') , 1)


def test_pdf(app):
    app.open_document(N)
    out = app.export_note('pdf', os.path.join(OUT, 'note.pdf'), open_result=False)
    check('PDF file is written', bool(out) and os.path.getsize(out) > 2000)
    with open(out, 'rb') as f:
        check('PDF has a PDF header', f.read(5), b'%PDF-')


def test_pdf_without_pandoc(app):
    out = noteexport.export_pdf('# Title\n\nPlain *note* without pandoc.\n', os.path.join(OUT, 'plain.pdf'), pandoc=None)
    check('PDF works without pandoc', os.path.getsize(out) > 1000)


def test_no_note_open(app):
    app.gui.qtabs.clear()
    check('nothing to export gives no file', app.export_note('pdf', os.path.join(OUT, 'none.pdf'), open_result=False), None)


CSL = """<?xml version="1.0" encoding="utf-8"?>
<style xmlns="http://purl.org/net/xbiblio/csl" class="in-text" version="1.0">
  <info><title>%s</title><id>%s</id><updated>2020-01-01T00:00:00+00:00</updated></info>
  <citation><layout prefix="{" suffix="}"><text variable="title"/></layout></citation>
  <bibliography><layout><text variable="title" prefix="%s: "/></layout></bibliography>
</style>
"""


def test_citation_style_setting(app):
    note('mystyle.csl', CSL % ('My', 'my', 'MYSTYLE'))
    app.open_document(N)
    app.project.settings['csl'] = 'mystyle.csl'
    out = app.export_note('docx', os.path.join(OUT, 'styled.docx'), open_result=False)
    xml = docx_text(out)
    check('the style from the setting is used in Word', '{a book}' in xml.lower() and 'mystyle: a book' in xml.lower())
    app.project.settings['csl'] = 'mystyle'
    check('the name works without .csl', bool(app.export_note('pdf', os.path.join(OUT, 'styled.pdf'), open_result=False)))
    # the same style for a full reference and the automatic bibliography
    import sublimeless_zk as szk
    e = app.get_active_editor()
    szk.show_fuzzy_panel = lambda *a, **k: ('x', 'smith2020')
    app.bib_entries = None
    e.setCursorPosition(e.lines() - 1, 0)
    app.insert_full_reference()
    check('full reference uses the style', 'mystyle: a book' in e.text().lower())
    e.undo()


def test_yaml_style_wins(app):
    note('other.csl', CSL % ('Other', 'other', 'OTHER'))
    path = note('201801010602 Yaml.md', '---\ntitle: With header\ncsl: other.csl\n---\n\nText [@smith2020].\n')
    app.open_document(path)
    app.project.settings['csl'] = 'mystyle.csl'
    out = app.export_note('docx', os.path.join(OUT, 'yaml.docx'), open_result=False)
    check('a csl line in the note header wins over the setting', 'other: a book' in docx_text(out).lower())


def test_style_in_a_subfolder(app):
    os.makedirs(os.path.join(ZK, 'resources', 'styles'), exist_ok=True)
    with open(os.path.join(ZK, 'resources', 'styles', 'deep.csl'), 'w', encoding='utf-8') as f:
        f.write(CSL % ('Deep', 'deep', 'DEEP'))
    app.open_document(N)
    app.project.settings['csl'] = 'deep.csl'
    out = app.export_note('docx', os.path.join(OUT, 'deep.docx'), open_result=False)
    check('a style in a subfolder of the notes folder is found', bool(out) and 'deep: a book' in docx_text(out).lower())
    path = note('201801010603 Yaml deep.md', '---\ncsl: deep.csl\n---\n\nText [@smith2020].\n')
    app.open_document(path)
    app.project.settings['csl'] = ''
    out = app.export_note('docx', os.path.join(OUT, 'deep2.docx'), open_result=False)
    check('also when the note header names it', bool(out) and 'deep: a book' in docx_text(out).lower())


def test_missing_style_is_explained(app):
    from harness import messages
    app.open_document(N)
    app.project.settings['csl'] = 'nowhere.csl'
    del messages[:]
    out = app.export_note('docx', os.path.join(OUT, 'missing.docx'), open_result=False)
    check('a missing style gives no file', out, None)
    check('and a message naming it and the folders searched', any('nowhere.csl' in m and 'Looked in' in m for m in messages))
    app.project.settings['csl'] = ''


run_gui_tests([test_pandoc_is_found, test_word, test_pdf, test_pdf_without_pandoc, test_citation_style_setting,
               test_yaml_style_wins, test_style_in_a_subfolder, test_missing_style_is_explained, test_no_note_open])
print(OUT)
