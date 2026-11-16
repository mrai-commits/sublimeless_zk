# -*- coding: utf-8 -*-
"""
Keyboard shortcut cheatsheet, new in Sublimeless 1.0.

The list is read from the menus of the running app, so it is always in line
with the real shortcuts. Only what is typed or clicked rather than chosen
from a menu is written down here by hand.
"""
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QFont
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QShortcut, QLabel)

IS_MAC = sys.platform == 'darwin'
CMD = '⌘' if IS_MAC else 'Ctrl+'
ALT = '⌥' if IS_MAC else 'Alt+'
SHIFT = '⇧' if IS_MAC else 'Shift+'
FOLLOW = ('⌃' if IS_MAC else 'Ctrl+') + ('↩' if IS_MAC else 'Enter')

TYPING_AND_MOUSE = [
    ('Insert a link to a note', 'type [['),
    ('Insert a citation', 'type [@  (or [# for MultiMarkdown)'),
    ('Insert a tag from the list of tags', 'type #?'),
    ('Show all tags with their number of notes', 'type #!'),
    ('Show all notes', 'type [!'),
    ('Follow the link, tag or citation under the cursor', FOLLOW),
    ('Open a note link, tag or web link', 'click'),
    ('Show the notes that link to a note', ALT + 'click on its link'),
    ('Open a note and close the one you came from', CMD + SHIFT + 'click on the link'),
    ('Show the notes citing a source', CMD + 'click on the @citekey'),
    ('Continue a list', 'Enter in a list item (Enter on an empty item ends the list)'),
    ('Zoom the text', CMD + 'mouse wheel'),
]


TAG_SEARCH_SYNTAX = [
    ('Notes with either tag', 'index quality'),
    ('Notes with both tags', 'index, quality'),
    ('Notes without a tag', '!draft'),
    ('Tags starting with ...', 'qual*'),
    ('Combined: (index or quality) and not draft', 'index quality, !draft'),
    ('The # is optional in the tag search window', '#index, quality'),
    ('Choose a tag from the list below the input', 'Down / Up, then Tab'),
]

FILE_SEARCH_SYNTAX = [
    ('Notes with either word', 'apple pear'),
    ('Notes with both words', 'apple, pear'),
    ('Notes without a word', '!!plum'),
    ('An exact phrase', '""apple pie""'),
    ('The whole word only (not apples, pineapple)', '=apple'),
    ('Any letters / exactly one letter', 'sense*   organi?ation'),
    ('Combined', 'apple pear, !!plum, =pie'),
]


def shortcut_text(action):
    """The shortcuts of a menu command as shown to the user ('' if none)."""
    keys = [k.toString(QKeySequence.NativeText) for k in action.shortcuts() if not k.isEmpty()]
    return '  or  '.join(dict.fromkeys(keys))


def collect_menu_shortcuts(menubar):
    """[(menu title, [(command, shortcut), ...]), ...] for all commands that have a shortcut."""
    groups = []

    def walk(menu, entries, prefix=''):
        for action in menu.actions():
            if action.isSeparator():
                continue
            if action.menu() is not None:
                walk(action.menu(), entries, prefix + action.text().replace('&', '') + ': ')
            else:
                keys = shortcut_text(action)
                if keys:
                    entries.append((prefix + action.text().replace('&', ''), keys))

    for top in menubar.actions():
        if top.menu() is None:
            continue
        entries = []
        walk(top.menu(), entries)
        if entries:
            groups.append((top.text().replace('&', ''), entries))
    return groups


class ShortcutsDialog(QDialog):
    def __init__(self, parent, groups, toggle_keys=()):
        super().__init__(parent)
        self.setWindowTitle('Keyboard Shortcuts')
        self.resize(760, 640)
        layout = QVBoxLayout(self)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText('Type to filter, e.g. "tag" or "link"')
        self.filter_edit.setClearButtonEnabled(True)
        layout.addWidget(self.filter_edit)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Command', 'Shortcut'])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QTreeWidget.NoSelection)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.tree)
        layout.addWidget(QLabel('Esc closes this window. All commands are also in the command palette.'))

        bold = QFont(self.font())
        bold.setBold(True)
        for title, entries in groups:
            group_item = QTreeWidgetItem([title, ''])
            group_item.setFont(0, bold)
            self.tree.addTopLevelItem(group_item)
            for command, keys in entries:
                group_item.addChild(QTreeWidgetItem([command, keys]))
        self.tree.expandAll()

        self.filter_edit.textChanged.connect(self.apply_filter)
        for keys in toggle_keys:           # the key that opened the window also closes it
            QShortcut(QKeySequence(keys), self).activated.connect(self.accept)
        self.filter_edit.setFocus()

    def apply_filter(self, text):
        words = text.lower().split()
        for g in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(g)
            visible = 0
            for c in range(group_item.childCount()):
                child = group_item.child(c)
                haystack = (child.text(0) + ' ' + child.text(1) + ' ' + group_item.text(0)).lower()
                hidden = not all(word in haystack for word in words)
                child.setHidden(hidden)
                visible += not hidden
            group_item.setHidden(visible == 0)

    def visible_commands(self):
        out = []
        for g in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(g)
            if group_item.isHidden():
                continue
            out += [group_item.child(c).text(0) for c in range(group_item.childCount())
                    if not group_item.child(c).isHidden()]
        return out
