# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for macOS, Windows and Linux:
#     pyinstaller --noconfirm sublimeless_zk.spec
# Result: dist/Sublimeless_ZK.app (macOS) or dist/sublimeless_zk/ (Windows, Linux)
import os
import sys
import glob
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

sys.path.insert(0, os.path.join(SPECPATH, 'src'))
from version import version

datas = [
    ('sublimeless_zk-settings.json', '.'),
    ('saved_searches_default.md', '.'),
    ('search_results_default.md', '.'),
    ('build_commands.json', '.'),
    ('app_logo_64.png', '.'),
    ('app_picture.png', '.'),
    ('sublimeless_zk.ico', '.'),
    ('data/setevi-template.html', 'data'),
]
datas += [(f, 'themes') for f in glob.glob('themes/*.json')]
datas += [(f, 'zettelkasten') for f in glob.glob('zettelkasten/*')]
datas += [(f, 'fonts') for f in glob.glob('fonts/*')]
datas += [(f, 'dictionaries') for f in glob.glob('dictionaries/*')]

binaries = []
# pandoc, bundled by the pypandoc_binary package: keep it beside the package
import pypandoc
pandoc_dir = os.path.join(os.path.dirname(pypandoc.__file__), 'files')
for f in glob.glob(os.path.join(pandoc_dir, 'pandoc*')):
    binaries.append((f, 'pypandoc/files'))

# MultiMarkdown is optional: the app falls back to its basic parser without it
try:
    import pymmd
    for f in glob.glob(os.path.join(os.path.dirname(pymmd.__file__), 'files', '*')):
        binaries.append((f, 'pymmd/files'))
except Exception:
    pass

hiddenimports = (collect_submodules('pygments') + collect_submodules('markdown') + collect_submodules('spylls')
                 + ['PyQt5.QtPrintSupport'])

# The app uses QtCore, QtGui, QtWidgets, QtPrintSupport and QScintilla only.
# Everything else of Qt is left out; the web engine alone is about 250 MB.
UNUSED_QT = ['PyQt5.' + name for name in (
    'Qt', 'QtWebEngine', 'QtWebEngineCore', 'QtWebEngineWidgets', 'QtWebChannel', 'QtWebSockets',
    'QtQml', 'QtQuick', 'QtQuick3D', 'QtQuickWidgets', 'QtMultimedia', 'QtMultimediaWidgets',
    'QtBluetooth', 'QtNfc', 'QtSensors', 'QtSerialPort', 'QtSql', 'QtTest', 'QtLocation',
    'QtPositioning', 'QtDesigner', 'QtHelp', 'QtOpenGL', 'QtRemoteObjects', 'QtTextToSpeech',
    'QtXmlPatterns', 'QtNetworkAuth', 'QtDBus', 'QtSvg', 'QtXml', 'QtNetwork', 'QAxContainer')]

a = Analysis(
    ['src/sublimeless_zk.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'numpy', 'scipy', 'matplotlib'] + UNUSED_QT,
    noarchive=False,
)

def unused(entry):
    """Qt files that only the left-out modules need: QML, the web engine's
    resources and helper program, and the translations of Qt's own dialogs."""
    dest = entry[0].replace('\\', '/')
    return any(part in dest for part in (
        '/Qt5/qml/', '/Qt5/resources/', '/Qt5/libexec/', '/Qt5/translations/',
        '/Qt/qml/', '/Qt/resources/', '/Qt/libexec/', '/Qt/translations/',
        'QtWebEngine', 'Qt5WebEngine', 'Qt5Quick', 'Qt5Qml', 'Qt5Multimedia', 'Qt5Designer',
        'Qt53D', 'Qt5Location', 'Qt5Positioning', 'Qt5Sensors', 'Qt5Bluetooth', 'Qt5Nfc', 'Qt5Sql', 'Qt5Test',
        'Qt5Help', 'Qt5RemoteObjects', 'Qt5TextToSpeech', 'Qt5XmlPatterns', 'Qt5SerialPort', 'Qt5WebChannel',
        'Qt5WebSockets', 'Qt5WebView'))


a.binaries = [entry for entry in a.binaries if not unused(entry)]
a.datas = [entry for entry in a.datas if not unused(entry)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='sublimeless_zk',
    console=False,
    icon='sublimeless_zk.ico' if sys.platform == 'win32' else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name='sublimeless_zk')

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Sublimeless_ZK.app',
        icon='if_Note_Book_Alt_86976.icns',
        bundle_identifier='io.github.sublimeless-zk',
        version=version,
        info_plist={
            'CFBundleDisplayName': 'Sublimeless ZK',
            'CFBundleShortVersionString': version,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        },
    )
