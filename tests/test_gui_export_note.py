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


run_gui_tests([test_pandoc_is_found, test_word, test_pdf, test_pdf_without_pandoc, test_no_note_open])
print(OUT)
