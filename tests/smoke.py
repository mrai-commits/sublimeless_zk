"""
Headless smoke test: start Sublimeless, drive core commands that need no
dialog input, record any exception, save a screenshot, quit.

    xvfb-run -a python3 tests/smoke.py [screenshot.png]
Exit code 0 = no exceptions.
"""
import os, sys, tempfile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
os.environ['HOME'] = tempfile.mkdtemp(prefix='szk-home-')   # fresh settings
os.chdir(SRC)
sys.path.insert(0, SRC)

from PyQt5.QtCore import QTimer
import sublimeless_zk as szk

errors = []
def hook(t, v, tb):
    errors.append(''.join(traceback.format_exception(t, v, tb)))
    traceback.print_exception(t, v, tb)
sys.excepthook = hook

shot = sys.argv[1] if len(sys.argv) > 1 else None
app = szk.Sublimeless_Zk()

def welcome_note():
    folder = app.project.folder
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith('.md')][0]

steps = [
    ('open note',        lambda: app.open_document(welcome_note())),
    ('show all notes',   lambda: app.show_all_notes(check_editor=False)),
    ('show all tags',    lambda: app.show_all_tags(check_editor=False)),
    ('find in files',    lambda: app.find_in_files('Welcome')),
    ('tag search',       lambda: app.advanced_tag_search('#zettelkasten')),
    ('auto toc',         lambda: app.auto_toc()),
    ('number headings',  lambda: app.number_headings()),
    ('denumber headings',lambda: app.denumber_headings()),
    ('auto bib',         lambda: app.auto_bib()),
    ('show images',      lambda: app.show_images()),
    ('hide images',      lambda: app.hide_images()),
    ('cycle tabs',       lambda: app.cycle_tabs_forward()),
    ('toggle sidepanel', lambda: (app.show_hide_sidepanel(), app.show_hide_sidepanel())),
    ('status bar',       lambda: app.update_status_bar()),
    ('save all',         lambda: app.save_all()),
]

def run_steps():
    for name, fn in steps:
        try:
            fn()
            app.app.processEvents()
            print('ok  ', name)
        except Exception:
            errors.append(name + '\n' + traceback.format_exc())
            print('FAIL', name)
            traceback.print_exc()
    if shot:
        app.gui.grab().save(shot)
    QTimer.singleShot(500, finish)

def finish():
    print('ERRORS: %d' % len(errors))
    os._exit(1 if errors else 0)

orig = app.connect_signals
def patched():
    orig()
    QTimer.singleShot(2500, run_steps)
app.connect_signals = patched
app.run()
