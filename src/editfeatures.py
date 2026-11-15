# -*- coding: utf-8 -*-
"""
Editing helpers added for Sublimeless 1.0: formatting shortcuts, list
toggling and list continuation. They only need a QsciScintilla editor.
"""
import re

LIST_ITEM_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])(\s+)(\S.*)$')
EMPTY_LIST_ITEM_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])\s+$')
LIST_PREFIX_RE = re.compile(r'^(\s*)(?:[-*+]|\d+[.)])\s+')
DASH_PREFIX_RE = re.compile(r'^(\s*)[-*+]\s+')
ORDERED_PREFIX_RE = re.compile(r'^(\s*)\d+[.)]\s+')


def _strip_eol(text):
    return text.rstrip('\r\n')


def toggle_wrap(editor, marker):
    """
    Put `marker` around the selection (**bold**, *italic*, `code`), or remove
    it if it is already there. Without a selection, insert the pair and put
    the cursor in the middle.
    """
    n = len(marker)
    if not editor.hasSelectedText():
        line, index = editor.getCursorPosition()
        editor.insert(marker + marker)
        editor.setCursorPosition(line, index + n)
        return

    line1, index1, line2, index2 = editor.getSelection()
    selected = editor.selectedText()

    def is_wrapped(text):
        if len(text) < 2 * n or not (text.startswith(marker) and text.endswith(marker)):
            return False
        if marker == '*':
            # **bold** is not italic; ***both*** is
            stars = len(text) - len(text.lstrip('*'))
            return stars in (1, 3)
        return True

    def is_surrounded(before, after):
        if not (before.endswith(marker) and after.startswith(marker)):
            return False
        if marker in ('*', '**'):
            stars = len(before) - len(before.rstrip('*'))
            return stars in ((1, 3) if marker == '*' else (2, 3))
        return True

    editor.beginUndoAction()
    try:
        if is_wrapped(selected):
            # markers are part of the selection
            new_text = selected[n:-n]
            editor.replaceSelectedText(new_text)
        else:
            before = _strip_eol(editor.text(line1))[:index1]
            after = _strip_eol(editor.text(line2))[index2:]
            if is_surrounded(before, after):
                # markers are just outside the selection
                editor.setSelection(line1, index1 - n, line2, index2 + n)
                editor.replaceSelectedText(selected)
                index1 -= n
                new_text = selected
            else:
                new_text = marker + selected + marker
                editor.replaceSelectedText(new_text)
        if line1 == line2 and '\n' not in new_text:
            editor.setSelection(line1, index1, line1, index1 + len(new_text))
    finally:
        editor.endUndoAction()


def toggle_list(editor, ordered=False):
    """
    Turn the current line or all selected lines into list items ("- " or
    "1. ", "2. " ...), or back into plain lines if they all are items already.
    """
    if editor.hasSelectedText():
        line1, index1, line2, index2 = editor.getSelection()
        if index2 == 0 and line2 > line1:
            line2 -= 1
    else:
        line1, _ = editor.getCursorPosition()
        line2 = line1
    lines = [_strip_eol(editor.text(l)) for l in range(line1, line2 + 1)]
    content = [l for l in lines if l.strip()]
    # only lines that already are items of the requested kind are turned
    # back into plain lines; a dash list becomes a numbered list and vice versa
    same_kind = ORDERED_PREFIX_RE if ordered else DASH_PREFIX_RE
    all_items = bool(content) and all(same_kind.match(l) for l in content)

    new_lines = []
    number = 0
    for text in lines:
        if not text.strip() and len(lines) > 1:
            new_lines.append(text)
            continue
        indent = text[:len(text) - len(text.lstrip())]
        body = LIST_PREFIX_RE.sub('', text) if LIST_PREFIX_RE.match(text) else text.lstrip()
        if all_items:
            new_lines.append(indent + body)
        else:
            number += 1
            new_lines.append(indent + ('%d. ' % number if ordered else '- ') + body)

    editor.beginUndoAction()
    try:
        editor.setSelection(line1, 0, line2, len(lines[-1]))
        editor.replaceSelectedText('\n'.join(new_lines))
        editor.setCursorPosition(line2, len(new_lines[-1]))
    finally:
        editor.endUndoAction()


def next_marker(marker):
    match = re.match(r'(\d+)([.)])', marker)
    if match:
        return '%d%s' % (int(match.group(1)) + 1, match.group(2))
    return marker


def continue_list(editor):
    """
    Call right after Enter created a new line. If the line above is a list
    item, start the next item ("- " or the next number). If the line above is
    an empty item, end the list instead by removing its marker.
    Returns True if it changed anything.
    """
    line, _ = editor.getCursorPosition()
    if line == 0:
        return False
    previous = _strip_eol(editor.text(line - 1))
    current = _strip_eol(editor.text(line))
    current_indent = len(current) - len(current.lstrip())

    if EMPTY_LIST_ITEM_RE.match(previous):
        # Enter on an empty item: the list is finished
        editor.beginUndoAction()
        try:
            editor.setSelection(line - 1, 0, line, current_indent)
            editor.replaceSelectedText('')
            editor.setCursorPosition(line - 1, 0)
        finally:
            editor.endUndoAction()
        return True

    match = LIST_ITEM_RE.match(previous)
    if not match:
        return False
    indent, marker, space, _ = match.groups()
    prefix = indent + next_marker(marker) + space
    editor.beginUndoAction()
    try:
        editor.setSelection(line, 0, line, current_indent)
        editor.replaceSelectedText(prefix)
        editor.setCursorPosition(line, len(prefix))
    finally:
        editor.endUndoAction()
    return True


def indent_list_item(editor):
    """
    Tab in a list item: indent the whole item one level instead of inserting
    spaces at the cursor. A numbered item starts its new sub-list at 1.
    Returns True if the current line was a list item and has been indented.
    """
    if editor.hasSelectedText():
        return False
    line, index = editor.getCursorPosition()
    text = _strip_eol(editor.text(line))
    match = LIST_PREFIX_RE.match(text)
    if not match:
        return False
    editor.beginUndoAction()
    try:
        before = len(text) - len(text.lstrip())
        editor.indent(line)
        text = _strip_eol(editor.text(line))
        shift = (len(text) - len(text.lstrip())) - before
        numbered = re.match(r'^(\s*)(\d+)([.)])', text)
        if numbered and numbered.group(2) != '1':
            start = len(numbered.group(1))
            editor.setSelection(line, start, line, start + len(numbered.group(2)))
            editor.replaceSelectedText('1')
            shift += 1 - len(numbered.group(2))
        editor.setCursorPosition(line, max(0, index + shift))
    finally:
        editor.endUndoAction()
    return True


def unindent_list_item(editor):
    """Shift+Tab in a list item: move the whole item one level back."""
    if editor.hasSelectedText():
        return False
    line, index = editor.getCursorPosition()
    text = _strip_eol(editor.text(line))
    if not LIST_PREFIX_RE.match(text):
        return False
    before = len(text) - len(text.lstrip())
    if before == 0:
        return True                     # already at the first level: nothing to do
    editor.beginUndoAction()
    try:
        editor.unindent(line)
        text = _strip_eol(editor.text(line))
        shift = (len(text) - len(text.lstrip())) - before
        editor.setCursorPosition(line, max(0, index + shift))
    finally:
        editor.endUndoAction()
    return True


def count_words(text):
    return len(text.split())
