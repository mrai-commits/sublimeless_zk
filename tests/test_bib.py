"""Bibliography parsing. Run: python3 tests/test_bib.py"""
import os, sys, tempfile
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, SRC)
from autobib import Autobib

BIB = r'''
@incollection{reason2013a,
	abstract = {{Action research is a family of practices. It starts from an orientation of change with others.}},
	crossref = {reason2013},
	date-added = {2021-12-28 17:49:54 +0100},
	pages = {1--10},
	title = {Introduction}}

@book{reason2013,
	editor = {Reason, Peter and Bradbury, Hilary},
	title = {The SAGE Handbook of Action Research},
	year = {2013}}

@book{editor2019,
  editor = {Editor, Only},
  title = {Edited Volume},
  year = {2019}
}
@incollection{own2020,
  author = {Own, Author},
  crossref = {editor2019},
  title = {Chapter},
  year = {2020}
}
@misc{dangling, crossref = {missing},
  title = {No parent}
}
'''

def check(name, got, want):
    ok = got == want
    print('ok  ' if ok else 'FAIL', name, '' if ok else '(got %r, want %r)' % (got, want))
    return ok

f = tempfile.NamedTemporaryFile('w', suffix='.bib', delete=False, encoding='utf-8'); f.write(BIB); f.close()
e = Autobib.extract_all_entries(f.name)
results = [
    check('crossref: chapter inherits editors', e['reason2013a']['editors'], 'Reason & Bradbury'),
    check('crossref: chapter inherits year', e['reason2013a']['year'], '2013'),
    check('crossref: chapter keeps own title', e['reason2013a']['title'], 'Introduction'),
    check('crossref: own author is kept', e['own2020']['authors'], 'Own'),
    check('crossref: own year is kept', e['own2020']['year'], '2020'),
    check('crossref: missing parent is harmless', e['dangling']['title'], 'No parent'),
    check('editor-only entry', e['editor2019']['editors'], 'Editor'),
]
sys.exit(0 if all(results) else 1)
