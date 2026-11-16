

class TagSearch:
    """
    Advanced tag search.

    Grammar:
    ```
        search-spec: search-term [, search-term]*
        search-term: tag-spec [ tag-spec]*
        tag-spec: [!]#tag-name[*]
        tag-name: {any valid tag string}
    ```
    """

    @staticmethod
    def normalize(search_spec):
        """
        Make what the user typed into a valid search-spec: the # may be left
        out (index, quality  ->  #index, #quality), and stray commas or
        spaces do no harm. ! and a trailing * keep their meaning.
        """
        terms = []
        for term in search_spec.split(','):
            specs = []
            for tspec in term.split():
                negated = tspec.startswith('!')
                name = tspec.lstrip('!').strip()
                if not name.strip('#*'):
                    continue
                if not name.startswith('#'):
                    name = '#' + name
                specs.append(('!' if negated else '') + name)
            if specs:
                terms.append(' '.join(specs))
        return ', '.join(terms)

    @staticmethod
    def advanced_tag_search(search_spec, project):
        """
        Return ids of all notes matching the search_spec.
        """
        note_tag_map, tags2ids = project.find_all_notes_all_tags()
        #print('Note Tag Map for ', project.folder)
        #for k, v in note_tag_map.items():
        #    print('{} : {}'.format(k, v))
        for sterm in [s.strip() for s in search_spec.split(',')]:
            # iterate through all notes and apply the search-term
            sterm_results = {}
            for note_id, tags in note_tag_map.items():
                if not note_id:
                    continue
                # apply each tag-spec match to all tags
                for tspec in sterm.split():
                    if tspec[0] == '!':
                        if tspec[-1] == '*':
                            match = TagSearch.match_not_startswith(tspec, tags)
                        else:
                            match = TagSearch.match_not(tspec, tags)
                    else:
                        if tspec[-1] == '*':
                            match = TagSearch.match_startswith(tspec, tags)
                        else:
                            match = TagSearch.match_tag(tspec, tags)
                    if match:
                        sterm_results[note_id] = tags   # remember this note
            # use the results for the next search-term
            note_tag_map = sterm_results
        result = list(sterm_results.keys())
        result.sort()
        return result

    @staticmethod
    def match_not(tspec, tags):
        return tspec[1:] not in tags

    @staticmethod
    def match_tag(tspec, tags):
        return tspec in tags

    @staticmethod
    def match_not_startswith(tspec, tags):
        tspec = tspec[1:-1]
        return len([t for t in tags if t.startswith(tspec)]) == 0

    @staticmethod
    def match_startswith(tspec, tags):
        tspec = tspec[:-1]
        return [t for t in tags if t.startswith(tspec)]
