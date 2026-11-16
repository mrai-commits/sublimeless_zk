"""
Shared harness for GUI regression tests: starts Sublimeless headless on a
temporary Zettelkasten with a fresh settings folder, runs test functions
inside the running app, reports, exits non-zero on failure.

    from harness import run_gui_tests, note, check
"""
import os, sys, tempfile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
os.environ['HOME'] = tempfile.mkdtemp(prefix='szk-home-')
os.chdir(SRC)
sys.path.insert(0, SRC)

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.Qsci import QsciScintilla
import sublimeless_zk as szk

ZK = tempfile.mkdtemp(prefix='szk-zk-')
failures = []
messages = []          # texts of message boxes that would have been shown

# message boxes would block a headless run: record them instead
QMessageBox.exec_ = lambda self: messages.append(self.text()) or 0
QMessageBox.warning = staticmethod(lambda parent, title, text, *a, **k: messages.append(text) or 0)
QMessageBox.question = staticmethod(lambda parent, title, text, *a, **k: messages.append(text) or QMessageBox.Yes)


def note(name, text):
    path = os.path.join(ZK, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def check(name, got, want=True):
    ok = got == want
    print('ok  ' if ok else 'FAIL', name, '' if ok else '(got %r, want %r)' % (got, want))
    if not ok:
        failures.append(name)
    return ok


def styles(editor, line):
    """Style names along a line as [(column, style), ...] (byte columns)."""
    start = editor.positionFromLineIndex(line, 0)
    end = editor.positionFromLineIndex(line + 1, 0) if line + 1 < editor.lines() else editor.length()
    lexer, out, prev = editor.lexer(), [], None
    for pos in range(start, end):
        s = lexer.description(editor.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos))
        if s != prev:
            out.append((pos - start, s))
            prev = s
    return out


def style_at(editor, line, column):
    pos = editor.positionFromLineIndex(line, column)
    return editor.lexer().description(editor.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos))


def clickable(editor, line, indicator):
    """String with X for every position of the line carrying the indicator."""
    start = editor.positionFromLineIndex(line, 0)
    end = editor.positionFromLineIndex(line + 1, 0) if line + 1 < editor.lines() else editor.length()
    return ''.join('X' if editor.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, indicator, pos) else '.'
                   for pos in range(start, end))


def run_gui_tests(tests, timeout_s=120):
    app = szk.Sublimeless_Zk()

    def hook(t, v, tb):
        failures.append('uncaught ' + t.__name__)
        traceback.print_exception(t, v, tb)
    sys.excepthook = hook

    # The app installs its own handler for unexpected errors when it starts,
    # which keeps it running. In tests every such error must count as a failure.
    handle = app.on_unexpected_error
    def counting_handler(t, v, tb):
        failures.append('unexpected error ' + t.__name__)
        print('FAIL unexpected error in the app:', t.__name__, v)
        handle(t, v, tb)
    app.on_unexpected_error = counting_handler

    def run():
        app.open_folder(ZK)
        app.app.processEvents()
        for test in tests:
            print('--', test.__name__)
            try:
                test(app)
                app.app.processEvents()
            except Exception:
                failures.append(test.__name__)
                print('FAIL', test.__name__, '(exception)')
                traceback.print_exc()
        print('FAILURES: %d' % len(failures))
        sys.stdout.flush()
        os._exit(1 if failures else 0)

    def watchdog():
        print('FAIL timeout: the app hung')
        sys.stdout.flush()
        os._exit(2)

    orig = app.connect_signals
    def patched():
        orig()
        QTimer.singleShot(1500, run)
    app.connect_signals = patched
    import threading
    t = threading.Timer(timeout_s, watchdog); t.daemon = True; t.start()
    app.run()
