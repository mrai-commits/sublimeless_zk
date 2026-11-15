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

def check(name, got, want=True):
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

# --- citations in a text (item 6: keys separated by ";")
import shutil
keys = Autobib.extract_all_citekeys(f.name)
TEXT = ('A [@reason2013a; @editor2019] b [-@own2020, p. 3] c @reason2013. '
        'd [e.g., @editor2019] mail a@b.com and @unknown2000')
cited = Autobib.find_citations(TEXT, keys)
results += [
    check('two keys separated by ; are both found', {'@reason2013a', '@editor2019'} <= cited),
    check('key followed by a period is found', '@reason2013' in cited),
    check('suppressed-author citation is found', '@own2020' in cited),
    check('unknown keys and e-mail addresses are ignored', sorted(cited),
          ['@editor2019', '@own2020', '@reason2013', '@reason2013a']),
]
if shutil.which('pandoc'):
    bib = Autobib.create_bibliography(TEXT, f.name, pandoc=shutil.which('pandoc'))
    results += [
        check('pandoc: no error', Autobib.last_error, ''),
        check('pandoc: one reference per cited key', sorted(bib), sorted(cited)),
        check('pandoc: reference text', bib.get('@editor2019'), 'Editor, Only, ed. 2019. Edited Volume.'),
        check('pandoc: crossref chapter names the book editors', 'Reason' in bib.get('@reason2013a', '')),
    ]
else:
    print('skip pandoc tests: pandoc not installed')
sys.exit(0 if all(results) else 1)
