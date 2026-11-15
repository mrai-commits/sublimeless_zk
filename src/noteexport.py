# -*- coding: utf-8 -*-
"""
Export of a single note to Word (.docx) and PDF, new in Sublimeless 1.0.

Word needs pandoc, which is bundled with the app (see settings.get_pandoc).
PDF is printed by Qt itself, so it needs neither pandoc nor LaTeX; pandoc is
only used, when available, to resolve citations and for nicer HTML.
"""
import os
import re
from subprocess import Popen, PIPE

PDF_CSS = '''
body { font-family: Georgia, "Times New Roman", serif; font-size: 11pt; }
h1 { font-size: 20pt; } h2 { font-size: 15pt; } h3 { font-size: 12.5pt; }
h1, h2, h3, h4 { font-family: Helvetica, Arial, sans-serif; }
code, pre { font-family: Menlo, Consolas, "DejaVu Sans Mono", monospace; font-size: 9.5pt; }
pre { background-color: #f3f3f3; }
blockquote { color: #444444; margin-left: 18px; }
p, ul, ol { margin-top: 6px; margin-bottom: 6px; }
table { border-collapse: collapse; margin-top: 10px; margin-bottom: 10px; }
div.references { margin-top: 18px; }
div.csl-entry { margin-bottom: 6px; } td, th { border: 1px solid #999999; padding: 3px 6px; }
'''

AUTOBIB_COMMENT_RE = re.compile(r'<!-- references \(auto\)(.*?)-->', re.DOTALL)


class ExportError(Exception):
    pass


YAML_HEADER_RE = re.compile(r'\A---[ \t]*\n(.*?)\n(?:---|\.\.\.)[ \t]*(?:\n|\Z)', re.DOTALL)


def yaml_has_csl(text):
    """True if the note's YAML header names a citation style itself."""
    header = YAML_HEADER_RE.match(text)
    return bool(header and re.search(r'^csl:[ \t]*\S', header.group(1), re.MULTILINE))


def find_csl(name, folders):
    """
    Full path of a citation style file. `name` may be a full path, or a file
    name with or without .csl that is looked for in `folders`, in order.
    """
    if not name:
        return None
    name = os.path.expanduser(name)
    names = [name] if name.lower().endswith('.csl') else [name, name + '.csl']
    for candidate in names:
        if os.path.isabs(candidate):
            if os.path.isfile(candidate):
                return candidate
            continue
        for folder in folders:
            path = os.path.join(folder, candidate)
            if os.path.isfile(path):
                return path
    return None


def style_args(text, csl_setting, folders):
    """
    Pandoc arguments for the citation style.
    - `folders` are where style and bib files named without a path are found:
      beside the note, in the notes folder, in the settings folder.
    - A `csl:` line in the note's YAML header wins over the setting.
    - Without either, pandoc uses its default (Chicago author-date).
    """
    folders = [f for f in dict.fromkeys(folders) if f and os.path.isdir(f)]
    args = ['--resource-path', os.pathsep.join(folders)] if folders else []
    if yaml_has_csl(text) or not csl_setting:
        return args
    path = find_csl(csl_setting, folders)
    if not path:
        raise ExportError(f'The citation style "{csl_setting}" (setting "csl") was not found.\n\n'
                          'Looked in:\n' + '\n'.join(folders))
    return args + ['--csl', path]


def prepare_markdown(text, with_citeproc):
    """
    Note text as given to the converters. When pandoc formats the citations
    itself, the automatic bibliography that Sublimeless keeps in a comment at
    the end of the note is left out, so that references do not appear twice.
    """
    if with_citeproc:
        text = AUTOBIB_COMMENT_RE.sub('', text)
    return text


def run_pandoc(pandoc, args, text, cwd=None):
    try:
        p = Popen([pandoc] + args, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=cwd)
        out, err = p.communicate(text.encode('utf-8'))
    except OSError as e:
        raise ExportError(f'Pandoc could not be started ({pandoc}):\n{e}')
    if p.returncode != 0:
        raise ExportError('Pandoc reported a problem:\n\n' + err.decode('utf-8', errors='replace')[:1500])
    return out.decode('utf-8', errors='replace')


def citation_args(pandoc, text, bibfile):
    """Arguments that make pandoc format citations, if the note has any."""
    if not bibfile or not os.path.exists(bibfile) or '@' not in text:
        return []
    from autobib import Autobib
    return Autobib.citeproc_args(pandoc) + ['--bibliography', bibfile]


def export_docx(text, out_path, pandoc, bibfile=None, note_folder=None, style=()):
    """Write the note as a Word document."""
    if not pandoc:
        raise ExportError('Pandoc was not found. It is needed for the export to Word.')
    cite = citation_args(pandoc, text, bibfile)
    args = ['-f', 'markdown', '-t', 'docx', '-o', out_path] + cite + list(style)
    if note_folder and '--resource-path' not in args:
        args += ['--resource-path', note_folder]
    run_pandoc(pandoc, args, prepare_markdown(text, bool(cite)), cwd=note_folder)
    return out_path


def note_to_html(text, pandoc=None, bibfile=None, note_folder=None, style=()):
    """HTML body of the note: by pandoc if available, else by python-markdown."""
    if pandoc:
        cite = citation_args(pandoc, text, bibfile)
        return run_pandoc(pandoc, ['-f', 'markdown', '-t', 'html'] + cite + list(style),
                          prepare_markdown(text, bool(cite)), cwd=note_folder)
    import markdown
    return markdown.markdown(text, extensions=['extra', 'sane_lists'])


def export_pdf(text, out_path, pandoc=None, bibfile=None, note_folder=None, page_size='A4', style=()):
    """
    Write the note as a PDF. Needs a running QApplication.
    page_size: 'A4' or 'Letter'.
    """
    from PyQt5.QtCore import QUrl, QMarginsF
    from PyQt5.QtGui import QTextDocument, QPageLayout, QPageSize
    from PyQt5.QtPrintSupport import QPrinter

    body = note_to_html(text, pandoc, bibfile, note_folder, style)
    html = f'<html><head><meta charset="utf-8"><style>{PDF_CSS}</style></head><body>{body}</body></html>'

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(out_path)
    size = QPageSize(QPageSize.Letter if str(page_size).lower() == 'letter' else QPageSize.A4)
    printer.setPageLayout(QPageLayout(size, QPageLayout.Portrait, QMarginsF(22, 22, 22, 22), QPageLayout.Millimeter))

    doc = QTextDocument()
    if note_folder:
        # relative image paths are looked up beside the note
        doc.setBaseUrl(QUrl.fromLocalFile(os.path.join(note_folder, '')))
    # lay out for the printer's resolution; otherwise point sizes are taken
    # as screen pixels and the text comes out tiny
    doc.documentLayout().setPaintDevice(printer)
    doc.setDefaultStyleSheet(PDF_CSS)
    doc.setHtml(html)
    doc.setPageSize(printer.pageRect(QPrinter.DevicePixel).size())
    doc.print_(printer)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise ExportError('The PDF file could not be written.')
    return out_path
