# -*- coding: utf-8 -*-

import os
import glob
import re
from subprocess import Popen, PIPE
from collections import defaultdict
import traceback
from bibtexparser.customization import convert_to_unicode


class Autobib:
    """
    Static class to group all auto-bibliography functions.
    """
    citekey_matcher = re.compile(r'^@[^{]*{\s*([^,\s}]*)')
    author_matcher = re.compile(r'^\s*author\s*=\s*(.*)', re.IGNORECASE)
    editor_matcher = re.compile(r'^\s*editor\s*=\s*(.*)', re.IGNORECASE)
    title_matcher = re.compile(r'^\s*title\s*=\s*(.*)', re.IGNORECASE)
    year_matcher = re.compile(r'^\s*year\s*=\s*(.*)', re.IGNORECASE)
    crossref_matcher = re.compile(r'^\s*crossref\s*=\s*(.*)', re.IGNORECASE)

    # what may follow a citekey in a text: a separator, or sentence punctuation
    citekey_stops = r"(?=[@',;\#}{~%\[\]\s)]|[.:!?]+(?:\s|$)|$)"

    @staticmethod
    def look_for_bibfile(project):
        """
        Look for a bib file in the view's folder.
        If no bib file there, then query the setting.
        """
        folder = project.folder
        if folder:
            pattern = os.path.join(folder, '*.bib')
            bibs = glob.glob(pattern)
            if bibs:
                print('Using local', bibs[0])
                return bibs[0]
        # try the setting
        bibfile = project.settings.get('bibfile', None)
        if bibfile:
            if os.path.exists(bibfile):
                print('Using global', bibfile)
                return bibfile
            else:
                print('bibfile not found:', bibfile)
                return None

    @staticmethod
    def extract_all_citekeys(bibfile):
        """
        Parse the bibfile and return all citekeys.
        """
        citekeys = set()
        if not os.path.exists(bibfile):
            print('bibfile not found:', bibfile)
            return []
        with open(bibfile, mode='r', encoding='utf-8') as f:
            for line in f:
                match = Autobib.citekey_matcher.findall(line)
                if not match:
                    continue
                citekeys.add(match[0])
        return citekeys

    @staticmethod
    def extract_all_entries(bibfile, unicode_conversion=False):
        """
        Return dict: {citekey: {title, authors, year}}
        """
        entries = defaultdict(lambda: defaultdict(str))
        if not os.path.exists(bibfile):
            print('bibfile not found:', bibfile)
            return {}
        with open(bibfile, mode='r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.endswith(','):
                    line = line[:-1]
                match = Autobib.citekey_matcher.findall(line)
                if match:
                    current_citekey = match[0]
                    continue
                match = Autobib.author_matcher.findall(line)
                if match:
                    authors = match[0]
                    if unicode_conversion:
                        authors = convert_to_unicode({'author': authors})['author']
                    authors = Autobib.parse_authors(authors)
                    entries[current_citekey]['authors'] = authors
                    continue
                match = Autobib.editor_matcher.findall(line)
                if match:
                    editors = match[0]
                    if unicode_conversion:
                        editors = convert_to_unicode({'editor': editors})['editor']
                    editors = Autobib.parse_authors(editors)
                    entries[current_citekey]['editors'] = editors
                    continue
                match = Autobib.title_matcher.findall(line)
                if match:
                    title = match[0]
                    if unicode_conversion:
                        title = convert_to_unicode({'title': title})['title']
                    title = Autobib.remove_latex_commands(title)
                    entries[current_citekey]['title'] = title
                    continue
                match = Autobib.year_matcher.findall(line)
                if match:
                    year = match[0]
                    year = Autobib.remove_latex_commands(year)
                    entries[current_citekey]['year'] = year
                    continue
                match = Autobib.crossref_matcher.findall(line)
                if match:
                    crossref = Autobib.remove_latex_commands(match[0]).strip().strip('"')
                    entries[current_citekey]['crossref'] = crossref
                    continue
        Autobib.resolve_crossrefs(entries)
        return entries

    @staticmethod
    def resolve_crossrefs(entries):
        """
        BibTeX `crossref`: an entry inherits the fields it lacks from its
        parent entry (e.g. a chapter takes editor and year from the book).
        The title is never inherited: the parent's title is the book title.
        """
        lower_keys = {key.lower(): key for key in entries}
        for citekey in list(entries):
            entry = entries[citekey]
            parent_key = entry.get('crossref')
            if not parent_key:
                continue
            parent_key = lower_keys.get(parent_key.lower())
            if parent_key is None or parent_key == citekey:
                continue
            parent = entries[parent_key]
            for field in ('authors', 'editors', 'year'):
                if not entry.get(field) and parent.get(field):
                    entry[field] = parent[field]

    @staticmethod
    def parse_authors(line):
        line = Autobib.remove_latex_commands(line)
        authors = line.split(' and')
        author_tuples = []
        for author in authors:
            first = ''
            last = author.strip()
            if ',' in author:
                last, first = [x.strip() for x in author.split(',')][:2]
            author_tuples.append((last, first))
        if len(author_tuples) > 2:
            authors = '{} et al.'.format(author_tuples[0][0])  # last et al
        else:
            authors = ' & '.join(x[0] for x in author_tuples)
        return authors

    @staticmethod
    def remove_latex_commands(s):
        """
        Simple function to remove any LaTeX commands or brackets from the string,
        replacing it with its contents.
        """
        chars = []
        FOUND_SLASH = False

        for c in s:
            if c == '{':
                # i.e., we are entering the contents of the command
                if FOUND_SLASH:
                    FOUND_SLASH = False
            elif c == '}':
                pass
            elif c == '\\':
                FOUND_SLASH = True
            elif not FOUND_SLASH:
                chars.append(c)
            elif c.isspace():
                FOUND_SLASH = False

        return ''.join(chars)

    # characters pandoc allows inside a citekey (after the first one)
    citekey_candidate = re.compile(r'@([\w][\w:.#$%&\-+?<>~/]*)')
    mmd_citekey_candidate = re.compile(r'\[#([^\]\s,;]+)')
    _citeproc_args_cache = {}

    @staticmethod
    def find_citations(text, citekeys):
        """
        Find all citekeys of the bib file that are cited in text.
        Returns a set of '@citekey' (pandoc) and '#citekey' (MultiMarkdown).
        Works for [@a; @b], [see @a, p. 3], [-@a], @a. and @a's.
        """
        citekeys = set(citekeys)
        founds = set()
        for match in Autobib.citekey_candidate.finditer(text):
            candidate = match.group(1)
            # a key can contain punctuation but never ends with it:
            # shorten until it is a known key
            while candidate and candidate not in citekeys and not candidate[-1].isalnum():
                candidate = candidate[:-1]
            if candidate in citekeys:
                founds.add('@' + candidate)
        for match in Autobib.mmd_citekey_candidate.finditer(text):
            if match.group(1) in citekeys:
                founds.add('#' + match.group(1))
        return founds

    @staticmethod
    def citeproc_args(pandoc_bin):
        """
        Arguments that switch on citation processing. pandoc 2.11 and later
        have it built in (--citeproc); older versions need the separate
        pandoc-citeproc filter, which no longer exists for current versions.
        """
        if pandoc_bin in Autobib._citeproc_args_cache:
            return Autobib._citeproc_args_cache[pandoc_bin]
        version = (99, 0)
        try:
            out = Popen([pandoc_bin, '--version'], stdout=PIPE, stderr=PIPE).communicate()[0]
            match = re.search(r'pandoc(?:\.exe)?\s+(\d+)\.(\d+)', out.decode('utf-8', errors='ignore'))
            if match:
                version = (int(match.group(1)), int(match.group(2)))
        except Exception:
            pass
        if version >= (2, 11):
            args = ['--citeproc']
        else:
            args = ['--filter', os.path.join(os.path.dirname(pandoc_bin), 'pandoc-citeproc')]
        Autobib._citeproc_args_cache[pandoc_bin] = args
        return args

    @staticmethod
    def create_bibliography(text, bibfile, pandoc='pandoc'):
        """
        Create a bibliography for all citations in text in form of a dictionary
        {'@citekey': 'formatted reference'}. Runs pandoc once for all of them.
        """
        citekeys = Autobib.extract_all_citekeys(bibfile)
        if not citekeys:
            return {}
        cited = Autobib.find_citations(text, citekeys)
        if not cited:
            return {}
        keys = sorted({citekey[1:] for citekey in cited})
        pandoc_input = '---\nnocite: |\n  {}\n---\n'.format(', '.join('@' + key for key in keys))
        args = [pandoc, '-f', 'markdown', '-t', 'html']
        args += Autobib.citeproc_args(pandoc) + ['--bibliography', bibfile]
        html_out = Autobib.run_pandoc(args, pandoc_input)
        key2bib = Autobib.parse_references_html(html_out)
        citekey2bib = {}
        for citekey in cited:
            citekey2bib[citekey] = key2bib.get(citekey[1:], '(no bib generated)')
        return citekey2bib

    @staticmethod
    def parse_references_html(html_out):
        """
        Extract {citekey: reference text} from pandoc's HTML bibliography,
        where every entry is a <div id="ref-CITEKEY" class="csl-entry">.
        Emphasis is kept as Markdown (*title*).
        """
        from html.parser import HTMLParser

        class RefParser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.entries = {}
                self.key = None
                self.depth = 0
                self.parts = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if self.key is None:
                    if tag == 'div' and (attrs.get('id') or '').startswith('ref-') \
                            and 'csl-entry' in (attrs.get('class') or ''):
                        self.key = attrs['id'][4:]
                        self.depth = 1
                        self.parts = []
                    return
                if tag == 'div':
                    self.depth += 1
                    self.parts.append(' ')
                elif tag in ('em', 'i'):
                    self.parts.append('*')

            def handle_endtag(self, tag):
                if self.key is None:
                    return
                if tag in ('em', 'i'):
                    self.parts.append('*')
                elif tag == 'div':
                    self.depth -= 1
                    if self.depth == 0:
                        self.entries[self.key] = ' '.join(''.join(self.parts).split())
                        self.key = None

            def handle_data(self, data):
                if self.key is not None:
                    self.parts.append(data)

        parser = RefParser()
        parser.feed(html_out)
        return parser.entries

    @staticmethod
    def parse_pandoc_out(pandoc_out):
        """
        Splits pandoc output into citation and bib part
        """
        pdsplit = pandoc_out.split('\n\n')
        citation = '(no citation generated)'
        bib =  '(no bib generated)'
        if len(pdsplit) >= 1:
            citation = pdsplit[0]
        if len(pdsplit) >= 2:
            bib = pdsplit[1]
        citation = citation.replace('\n', ' ')
        bib = bib.replace('\n', ' ')
        return citation, bib

    @staticmethod
    def run(pandoc_bin, bibfile, stdin):
        """Plain-text citation and reference for the citations in stdin."""
        args = [pandoc_bin, '-t', 'plain'] + Autobib.citeproc_args(pandoc_bin) + ['--bibliography', bibfile]
        return Autobib.run_pandoc(args, stdin)

    @staticmethod
    def run_pandoc(args, stdin):
        stdout = ''
        stderr = ''
        try:
            # using universal_newlines here gets us into decoding troubles as the
            # encoding then is guessed and can be ascii which can't deal with
            # unicode characters. hence, we handle \r ourselves
            p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate(bytes(stdin, 'utf-8'))
            # make me windows-safe
            stdout = stdout.decode('utf-8', errors='ignore').replace('\r', '')
            stderr = stderr.decode('utf-8', errors='ignore').replace('\r', '')
            if p.returncode != 0:
                Autobib.last_error = stderr.strip()
                Autobib.log_exception(f'{args}\n{stderr}')
            else:
                Autobib.last_error = ''
        except FileNotFoundError:
            Autobib.last_error = f'Pandoc executable ({args[0]}) not found'
            print(Autobib.last_error)
            Autobib.log_exception(args, True)
        except:
            Autobib.last_error = traceback.format_exc()
            Autobib.log_exception(args, True)
        return stdout

    last_error = ''

    @staticmethod
    def log_exception(arg, exception=False):
        import tempfile
        log_filn = os.path.join(tempfile.gettempdir(), 'sublimeless_zk-exception.txt')
        with open(log_filn, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(f'{arg}\n')
            if exception:
                f.write(traceback.format_exc())
            f.flush()
