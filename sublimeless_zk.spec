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

a = Analysis(
    ['src/sublimeless_zk.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'numpy', 'scipy', 'matplotlib'],
    noarchive=False,
)
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
