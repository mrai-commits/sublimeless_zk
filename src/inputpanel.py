from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class InputPanel(QDialog):
    def __init__(self, parent, label, defaulttext):
        super(InputPanel, self).__init__(parent=parent)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self._text = ''
        self.setObjectName("self")
        hlay = QHBoxLayout(self)
        hlay.addWidget(QLabel(label))
        self.line_edit = QLineEdit()
        self.line_edit.setText(defaulttext)
        hlay.addWidget(self.line_edit)
        self.setLayout(hlay)
        self.setMinimumWidth(600)
        self.line_edit.returnPressed.connect(self._ok_clicked)
        self.line_edit.setFocus()

        self.setStyleSheet("""
            QLineEdit{ background-color: #ffffff; }
            InputPanel { background: #f0f0f0; }
            QLabel{ background: #d08080; }
            QDialog {
                    background: #d08080;
                    }

        """)

    def _ok_clicked(self):
        self._text = self.line_edit.text()
        self.done(1)

    def text(self):
        return self._text


def show_input_panel(parent, label, defaulttext):
    ip = InputPanel(parent, label, defaulttext)
    if parent:
        ip.move(parent.rect().center() - ip.rect().center())
    ret = ip.exec_()
    if ret:
        return ip.text()
    else:
        return None


class TagSearchPanel(QDialog):
    """
    Input line for a tag search with the list of existing tags below it.
    The list narrows down to the tags matching the word being typed.
    Down/Up choose a tag, Tab or a double-click puts it into the line,
    Enter starts the search.
    """
    def __init__(self, parent, label, tag_counts):
        super().__init__(parent=parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._text = ''
        self.tag_counts = dict(tag_counts)
        self.tags = sorted(self.tag_counts, key=lambda tag: tag.lower())
        vlay = QVBoxLayout(self)
        hlay = QHBoxLayout()
        hlay.addWidget(QLabel(label))
        self.line_edit = QLineEdit()
        hlay.addWidget(self.line_edit)
        vlay.addLayout(hlay)
        self.list_box = QListWidget()
        self.list_box.setFocusPolicy(Qt.NoFocus)
        vlay.addWidget(self.list_box)
        hint = QLabel('Down/Up: choose a tag   Tab: insert it   Enter: search   '
                      'space: or   comma: and   !tag: not   tag*: starts with   (# is optional)')
        vlay.addWidget(hint)
        self.setMinimumWidth(600)
        self.setMinimumHeight(360)
        self.line_edit.textEdited.connect(self.update_list)
        self.line_edit.returnPressed.connect(self._ok_clicked)
        self.list_box.itemDoubleClicked.connect(lambda item: self.insert_current_tag())
        self.line_edit.installEventFilter(self)
        self.line_edit.setFocus()
        self.setStyleSheet("""
            QLineEdit{ background-color: #ffffff; }
            QListWidget:item:selected{ background: lightblue; border: 1px solid #6a6ea9; }
            TagSearchPanel { background: #f0f0f0; }
        """)
        self.update_list()

    def current_word(self):
        """The tag being typed: text after the last space or comma, without !."""
        text = self.line_edit.text()[:self.line_edit.cursorPosition()]
        start = max(text.rfind(' '), text.rfind(','), text.rfind('\t')) + 1
        return start, text[start:]

    def update_list(self, *args):
        _, word = self.current_word()
        needle = word.lstrip('!').rstrip('*').lower()
        self.shown_tags = [tag for tag in self.tags if needle in tag.lower()] if needle.strip('#') else list(self.tags)
        self.list_box.clear()
        self.list_box.addItems([f'{tag} ({self.tag_counts[tag]})' for tag in self.shown_tags])
        self.list_box.setCurrentRow(-1)

    def insert_current_tag(self):
        row = self.list_box.currentRow()
        if row < 0 and len(self.shown_tags) == 1:
            row = 0
        if row < 0:
            return False
        tag = self.shown_tags[row]
        start, word = self.current_word()
        text = self.line_edit.text()
        negation = '!' if word.startswith('!') else ''
        end = self.line_edit.cursorPosition()
        new_text = text[:start] + negation + tag + ' ' + text[end:].lstrip()
        self.line_edit.setText(new_text)
        self.line_edit.setCursorPosition(start + len(negation) + len(tag) + 1)
        self.update_list()
        return True

    def eventFilter(self, watched, event):
        if watched is self.line_edit and event.type() == QEvent.KeyPress:
            key = event.key()
            count = self.list_box.count()
            if key == Qt.Key_Down and count:
                self.list_box.setCurrentRow((self.list_box.currentRow() + 1) % count)
                return True
            if key == Qt.Key_Up and count:
                row = self.list_box.currentRow()
                self.list_box.setCurrentRow(row - 1 if row > 0 else count - 1)
                return True
            if key == Qt.Key_Tab:
                self.insert_current_tag()
                return True
        return super().eventFilter(watched, event)

    def _ok_clicked(self):
        self._text = self.line_edit.text().strip()
        self.done(1)

    def text(self):
        return self._text


def show_tag_search_panel(parent, label, tag_counts):
    panel = TagSearchPanel(parent, label, tag_counts)
    if parent:
        panel.move(parent.rect().center() - panel.rect().center())
    if panel.exec_():
        return panel.text()
    return None


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create('Fusion'))
    gui = QMainWindow()
    gui.setFocus()
    gui.show()
    show_input_panel(gui, 'Label', 'Default')
    sys.exit(app.exec_())

