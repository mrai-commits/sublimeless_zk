from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


def fold(text):
    """Lower case without accents, so that "gumusay" finds "Gümüsay"."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def find_items(search_string, items, max_items, folded=None, loose=True):
    """
    Entries matching what the user typed, best first:
    1. entries that contain every typed word (in any order, ignoring case
       and accents), e.g. "weick 1995 sense" for one paper among many of the
       same author;
    2. only if there is no such entry: loose "fuzzy" matches, as before.

    folded: the entries already passed through fold(), in the same order.
    Passing it makes a search over thousands of entries take a few
    milliseconds, which matters because this runs on every keystroke.
    """
    if not isinstance(items, list):
        items = list(items)
    words = fold(search_string).split()
    if not words:
        return items[:max_items]
    if folded is None:
        folded = [fold(item) for item in items]
    first = words[0]
    rest = words[1:]
    exact = []
    for index, text in enumerate(folded):
        if first in text and all(word in text for word in rest):
            exact.append(items[index])
            if len(exact) >= max_items:
                break
    if exact or not loose:
        return exact
    # loose match: the typed letters in this order, with anything in between.
    # The tightest matches come first.
    letters = ''.join(words)
    loose = []
    for index, text in enumerate(folded):
        start = pos = text.find(letters[0])
        if pos < 0:
            continue
        for letter in letters[1:]:
            pos = text.find(letter, pos + 1)
            if pos < 0:
                break
        else:
            loose.append((pos - start, start, index))
    loose.sort()
    return [items[index] for _, _, index in loose[:max_items]]


NEW_ENTRY = '\x00new'      # value returned for a typed entry that is not in the list


class PanelInputLine(QLineEdit):
    down_pressed = pyqtSignal()
    up_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background-color:#ffffff')

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key_Down:
            self.down_pressed.emit()
        elif key == Qt.Key_Up:
            self.up_pressed.emit()


class FuzzySearchPanel(QWidget):
    item_selected = pyqtSignal(str, str)    # key, value
    close_requested = pyqtSignal()

    def __init__(self, parent=None, item_dict=None, max_items=20):
        super().__init__(parent)
        self.max_items = max_items
        self.setObjectName("FuzzySearchPanel")
        self.item_dict = item_dict    #    { show_as: associated_value }
        if self.item_dict is None:
            self.item_dict = {}

        # prepared once, so that each keystroke only does a plain text search
        self.allow_new = False     # Enter with no match returns what was typed
        self.all_items = list(self.item_dict.keys())
        self.folded_items = [fold(item) for item in self.all_items]
        self.fuzzy_items = self.all_items[:max_items]
        self.initUI()

    def initUI(self):
        vlay = QVBoxLayout()
        self.input_line = PanelInputLine()
        self.list_box = QListWidget()
        for i in range(self.max_items):
            self.list_box.insertItem(i, '')
        vlay.addWidget(self.input_line)
        vlay.addWidget(self.list_box)
        self.update_listbox()
        self.setLayout(vlay)
        self.setMinimumWidth(600)
        self.list_box.setAlternatingRowColors(True)

        # style
        self.setStyleSheet(""" QListWidget:item:selected{
                                    background: lightblue;
                                    border: 1px solid #6a6ea9;
                                }
                                QListWidget{
                                    background: #f0f0f0;
                                    show-decoration-selected: 1;                                
                                }
                                QListWidget::item:alternate {
                                    background: #E0E0E0;
                                }    
                                QLineEdit {
                                background-color: #ffffff;
                                }             
                                """
                           )

        # connections
        self.input_line.textChanged.connect(self.text_changed)
        self.input_line.returnPressed.connect(self.return_pressed)
        self.input_line.down_pressed.connect(self.down_pressed)
        self.input_line.up_pressed.connect(self.up_pressed)
        self.list_box.itemDoubleClicked.connect(self.item_doubleclicked)
        self.list_box.installEventFilter(self)
        self.input_line.setFocus()

    def update_listbox(self):
        # one repaint for the whole list instead of one per row
        self.list_box.setUpdatesEnabled(False)
        try:
            for i in range(self.max_items):
                item = self.list_box.item(i)
                if i < len(self.fuzzy_items):
                    if item.text() != self.fuzzy_items[i]:
                        item.setText(self.fuzzy_items[i])
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            self.list_box.setCurrentRow(0)
        finally:
            self.list_box.setUpdatesEnabled(True)

    def text_changed(self):
        search_string = self.input_line.text()
        if search_string:
            self.fuzzy_items = find_items(search_string, self.all_items, self.max_items, self.folded_items,
                                          loose=not self.allow_new)
        else:
            self.fuzzy_items = list(self.item_dict.keys())[:self.max_items]
        self.update_listbox()

    def up_pressed(self):
        count = min(len(self.fuzzy_items), self.max_items)
        if not count:
            return
        row = self.list_box.currentRow()
        # going up from the first entry continues at the last one
        self.list_box.setCurrentRow(row - 1 if row > 0 else count - 1)

    def down_pressed(self):
        count = min(len(self.fuzzy_items), self.max_items)
        if not count:
            return
        row = self.list_box.currentRow()
        # going down from the last entry continues at the first one
        self.list_box.setCurrentRow(row + 1 if row < count - 1 else 0)

    def return_pressed(self):
        if len(self.fuzzy_items) > 0:
            row = self.list_box.currentRow()
            key = self.fuzzy_items[row]
            value = self.item_dict[key]
            self.item_selected.emit(key, value)
        elif self.allow_new and self.input_line.text().strip():
            # nothing matches: hand back what was typed, as a new entry
            self.item_selected.emit(self.input_line.text().strip(), NEW_ENTRY)


    def item_doubleclicked(self):
        row = self.list_box.currentRow()
        key = self.fuzzy_items[row]
        value = self.item_dict[key]
        self.item_selected.emit(key, value)
    
    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.InsertParagraphSeparator):
            self.return_pressed()
            return True
        else:
            return QWidget.eventFilter(self, watched, event)


class FuzzySearchDialog(QDialog):
    def __init__(self, parent, title, item_dict, max_items=20):
        super(FuzzySearchDialog, self).__init__(parent=parent)
        self.setObjectName("self")
        self.setWindowTitle(title)
        hlay = QHBoxLayout()
        self.panel = FuzzySearchPanel(item_dict=item_dict, max_items=max_items)
        hlay.addWidget(self.panel)
        self.setLayout(hlay)

        self.panel.close_requested.connect(self.cancel)
        self.panel.item_selected.connect(self.item_selected)
        self.value = None
        self.panel.input_line.setFocus()
        # style
        self.setStyleSheet(""" QDialog {
                                    background: #ffffff;
                                }
                                """
                           )

    def item_selected(self, key, value):
        self.value = (key, value)
        self.done(1)

    def cancel(self):
        self.done(0)


def show_fuzzy_panel(parent, title, item_dict, max_items=50, longlines=False, manylines=False, allow_new=False):
    """
    item_dict: show: return
    """
    dlg = FuzzySearchDialog(parent, title, item_dict, max_items)
    dlg.panel.allow_new = allow_new
    if parent:
        pass
        #dlg.move(parent.rect().center() - dlg.rect().center())
    if longlines:
        dlg.setMinimumWidth(1024)
    if manylines:
        dlg.setMinimumHeight(400)
    ret = dlg.exec_()
    if ret:
        return dlg.value
    else:
        return None, None
