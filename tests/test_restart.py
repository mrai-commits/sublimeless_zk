"""
Quit and start again: window layout, panes and note windows must come back.
Runs the app twice as separate processes with the same home folder, the way
a user does. Run: python3 tests/test_restart.py   (needs a display or xvfb)
"""
import os, sys, json, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')

if len(sys.argv) > 2:                       # child process: one run of the app
    phase, home = sys.argv[1], sys.argv[2]
    os.environ['HOME'] = home
    os.chdir(SRC); sys.path.insert(0, SRC)
    from PyQt5.QtCore import QTimer
    import sublimeless_zk as szk
    app = szk.Sublimeless_Zk()

    def state():
        s = app.gui.layout_state()
        s['note_windows'] = sorted(os.path.basename(w.primary.file_name) for w in app.note_windows)
        s['note_window_sizes'] = [[w.width(), w.height()] for w in app.note_windows]
        return s

    def step():
        if phase == '1':
            app.gui.setGeometry(100, 80, 1250, 760)
            app.toggle_open_files_panel(); app.app.processEvents()
            app.gui.mainsplit.setSizes([200, 800, 250]); app.gui.subsplit.setSizes([500, 200])
            window = app.open_note_window(app.gui.qtabs.widget(0)); window.resize(520, 430)
            app.app.processEvents()
            print('STATE', json.dumps(state())); sys.stdout.flush()
            QTimer.singleShot(300, app.quit_application)
        else:
            print('STATE', json.dumps(state())); sys.stdout.flush()
            os._exit(0)

    original = app.connect_signals
    app.connect_signals = lambda: (original(), QTimer.singleShot(2500, step))
    app.run()
    sys.exit(0)

home = tempfile.mkdtemp(prefix='szk-restart-')
states = []
for phase in ('1', '2'):
    out = subprocess.run([sys.executable, '-W', 'ignore', os.path.abspath(__file__), phase, home],
                         capture_output=True, text=True, timeout=90).stdout
    line = [l for l in out.split('\n') if l.startswith('STATE ')]
    states.append(json.loads(line[0][6:]) if line else None)

before, after = states
failed = 0
def check(name, ok):
    global failed
    print('ok  ' if ok else 'FAIL', name)
    failed += not ok
check('both runs reported', before is not None and after is not None)
if before and after:
    check('window size and position come back', after['geometry'] == before['geometry'])
    check('the open-notes pane stays open', after['open_files_panel'] is True)
    check('pane widths come back', after['mainsplit'] == before['mainsplit'] and after['subsplit'] == before['subsplit'])
    check('the note window comes back', after['note_windows'] == before['note_windows'] and len(after['note_windows']) == 1)
    check('with its size', after['note_window_sizes'] == before['note_window_sizes'])
    if failed:
        print(before); print(after)
print('FAILURES: %d' % failed)
sys.exit(1 if failed else 0)
