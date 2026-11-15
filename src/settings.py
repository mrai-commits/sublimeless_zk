from json import JSONDecodeError
import jstyleson as json
from pathlib import Path
import os
import shutil
import sys

settings_filn = os.path.join(Path.home(), 'sublimeless_zk-settings.json')

def base_dir():
    if getattr(sys, 'frozen', False):
        # frozen: PyInstaller puts the data files into sys._MEIPASS
        # (the _internal folder, or Contents/Resources in a macOS app)
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # unfrozen
        base_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    return base_dir


def load_bundled_fonts():
    """
    Make the fonts in the app's fonts folder (Ubuntu Mono) available to the
    app, so they do not have to be installed on the computer. Needs a
    running QApplication. Returns the font families that were loaded.
    """
    from PyQt5.QtGui import QFontDatabase
    families = set()
    folder = os.path.join(base_dir(), 'fonts')
    if not os.path.isdir(folder):
        return families
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(('.ttf', '.otf')):
            font_id = QFontDatabase.addApplicationFont(os.path.join(folder, name))
            if font_id >= 0:
                families.update(QFontDatabase.applicationFontFamilies(font_id))
    return families


default_settings = json.loads(open(os.path.join(base_dir(), 'sublimeless_zk-settings.json'), mode='r', encoding='utf-8', errors='ignore').read())


def get_settings(raw=False, on_error=None):
    if not os.path.exists(settings_filn):
        # copy template
        src_path = os.path.join(base_dir(), 'sublimeless_zk-settings.json')
        shutil.copy2(src_path, settings_filn)
    with open(settings_filn,
              mode='r', encoding='utf-8', errors='ignore') as f:
        txt = f.read()
        if raw:
            return txt
        else:
            try:
                ret = json.loads(txt)
            except JSONDecodeError as e:
                ret = default_settings
                if on_error:
                    e.lineno = get_real_error_lineno(txt, e.lineno)
                    on_error(editor=None, jsonerror=e)
            return ret


def get_real_error_lineno(txt, lineno):
    logical_line_no = 1
    if lineno == 1:
        return 1
    line_index = 0   # just to be safe against the invariant
    for line_index, line in enumerate(txt.split('\n')):
        if line.strip().startswith('//'):
            continue
        logical_line_no += 1
        if logical_line_no == lineno:
            break
    return line_index + 1


_pandoc_cache = {}


def get_pandoc():
    """
    Path of the pandoc program, or None. Order: the path in the settings,
    the pandoc that is bundled with the app, pandoc on the PATH, and the
    usual installation folders (Homebrew on Apple Silicon and Intel Macs).
    """
    import shutil
    configured = get_settings().get('path_to_pandoc', '') or ''
    if configured in _pandoc_cache:
        return _pandoc_cache[configured]
    candidates = [configured]
    try:
        import pypandoc
        bundled = os.path.join(os.path.dirname(pypandoc.__file__), 'files',
                               'pandoc.exe' if sys.platform == 'win32' else 'pandoc')
        candidates.append(bundled)
    except Exception:
        pass
    candidates.append(shutil.which('pandoc') or '')
    candidates.extend(['/opt/homebrew/bin/pandoc', '/usr/local/bin/pandoc', '/usr/bin/pandoc'])
    found = None
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            found = candidate
            break
    _pandoc_cache[configured] = found
    return found


# todo make QObject that emits settings changed / slot interface for eg Project class
