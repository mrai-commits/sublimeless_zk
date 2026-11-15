"""HTML export (Zk2Setevi) with each Markdown parser. Run: python3 tests/test_export.py"""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SRC = os.path.join(ROOT, 'src')
os.environ['HOME'] = tempfile.mkdtemp(prefix='szk-home-')
os.chdir(SRC); sys.path.insert(0, SRC)

from project import Project
from libzk2setevi.convert import Zk2Setevi, HAVE_MMD

failed = 0
print('MultiMarkdown available:', HAVE_MMD)
for parser in ('basic', 'mmd', 'pandoc'):
    out = tempfile.mkdtemp(prefix='szk-out-')
    try:
        Zk2Setevi(home=ROOT, project=Project(os.path.join(ROOT, 'zettelkasten')), out_folder=out,
                  bibfile=None, extension='.md', linkstyle='double', parser=parser,
                  white_tags='', black_tags='',
                  timestamp_from='190001010000', timestamp_until='210001010000',
                  progress_callback=lambda *a: None, finish_callback=lambda: None).create_html()
        size = os.path.getsize(os.path.join(out, 'index.html'))
        assert size > 1000
        print('ok  ', parser, size, 'bytes')
    except Exception as e:
        import traceback; traceback.print_exc()
        print('FAIL', parser, e); failed += 1
sys.exit(1 if failed else 0)
