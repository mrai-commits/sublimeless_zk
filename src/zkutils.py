# stuff that didn't make it anywhere else
import re
import sys
import os
import subprocess


evil_fn_chars_re = re.compile('[\\/:"*?<>|]+')
def sanitize_filename(filename):
    """
    Dis-allow characters not allowed on all platforms
    This is so you can't save '*' which doesn't work on Windows
    which prevents ZK portability.
    """
    return evil_fn_chars_re.sub('-', filename)
    
def split_search_terms(search_string):
    """
    Split a search-spec (for find in files) into tuples:
    (posneg, string)
    posneg: True: must be contained, False must not be contained
    string: what must (not) be contained
    """
    in_quotes = False
    in_neg = False
    pos = 0
    str_len = len(search_string)
    results = []
    current_snippet = ''
    while pos < str_len:
        if search_string[pos:].startswith('""'):
            in_quotes = not in_quotes
            if not in_quotes:
                # finish this snippet
                if current_snippet:
                    results.append((in_neg, current_snippet))
                in_neg = False
                current_snippet = ''
            pos += 2
        elif search_string[pos:].startswith('!!') and not in_quotes and not current_snippet:
            in_neg = True
            pos += 2
        elif search_string[pos] in (' ', '\t') and not in_quotes:
            # push current snippet
            if current_snippet:
                results.append((in_neg, current_snippet))
            in_neg = False
            current_snippet = ''
            pos += 1
        else:
            current_snippet += search_string[pos]
            pos += 1
    if current_snippet:
        results.append((in_neg, current_snippet))
    return [(not in_neg, s) for in_neg, s in results]


def split_on_commas(search_string):
    """Split at commas that are not inside ""quotes""."""
    parts, current, in_quotes, pos = [], '', False, 0
    while pos < len(search_string):
        if search_string.startswith('""', pos):
            in_quotes = not in_quotes
            current += '""'
            pos += 2
        elif search_string[pos] == ',' and not in_quotes:
            parts.append(current)
            current = ''
            pos += 1
        else:
            current += search_string[pos]
            pos += 1
    parts.append(current)
    return [part for part in parts if part.strip()]


def term_matcher(term):
    """
    Function telling whether a (lower-case) text contains the search term.
    * stands for any number of letters or digits, ? for exactly one.
    An = marks where the word must begin or end:
        car     car, cars, scare, carrion      (anywhere in a word)
        =car    car, cars, carrion             (words beginning with car)
        car=    car, scar                      (words ending in car)
        =car=   car                            (the whole word)
    """
    begins = term.startswith('=') and len(term.strip('=')) > 0
    ends = term.endswith('=') and len(term.strip('=')) > 0
    if begins:
        term = term[1:]
    if ends:
        term = term[:-1]
    if '*' not in term and '?' not in term and not begins and not ends:
        return lambda text: term in text
    pattern = re.escape(term).replace(r'\*', r'\w*').replace(r'\?', r'\w')
    if begins:
        pattern = r'(?<!\w)' + pattern
    if ends:
        pattern = pattern + r'(?!\w)'
    regex = re.compile(pattern)
    return lambda text: regex.search(text) is not None


def compile_file_search(search_string, comma_is_and=True):
    """
    Turn a find-in-files search into a function text -> bool.

    comma_is_and (the default since 1.0), like the tag search:
        apple pear, plum      (apple or pear) and plum
        =apple=               the whole word apple, not apples or pineapple
        =apple  apple=        words beginning with / ending in apple
        ""apple pie"", !!plum   the phrase, and not plum
    otherwise (as before 1.0) all terms must match:
        apple pear            apple and pear
    """
    search_string = search_string.lower()
    if comma_is_and:
        groups = [split_search_terms(part) for part in split_on_commas(search_string)]
    else:
        groups = [[term] for term in split_search_terms(search_string)]
    groups = [[(presence, term_matcher(term)) for presence, term in group] for group in groups if group]

    def matches(text):
        text = text.lower()
        return all(any(matcher(text) == presence for presence, matcher in group) for group in groups)
    return matches


def open_hyperlink(hyperlink):
    try:
        if sys.platform == 'darwin':
            subprocess.call(['open', hyperlink])
        elif sys.platform == 'win32':
            os.startfile(hyperlink)
        else:
            # assume linux
            # no shell: the address comes from note text
            env = dict(os.environ)
            env.pop('LD_LIBRARY_PATH', None)
            subprocess.Popen(['xdg-open', hyperlink], env=env)
    except:
        # TODO: better error handling 
        pass

if __name__ == '__main__':
    line = 'hello !!""new world!!!"" this !! is awesome!! is!!n\'t !!it??'
    print(line)
    print('    \n'.join([str(x) for x in split_search_terms(line)]))