import re
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.Qsci import *
from PyQt5.QtGui import *


class FindInputLine(QTextEdit):
    enter_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background-color:#ffffff')

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.enter_pressed.emit()
        else:
            super().keyPressEvent(event)


class FindDlg(QDialog):
    def __init__(self, parent=None, qtabs=None):
        QDialog.__init__(self, parent, Qt.WindowStaysOnTopHint)
        self.parent = parent
        self.initUI()
        self.qtabs = qtabs

    def initUI(self):
        self.re = False
        self.cs = None
        self.wo = None
        self.expr = ''
        self.last_match = None

        findButton = QPushButton("Find",self)
        findButton.clicked.connect(self.find)

        replaceButton = QPushButton("Replace",self)
        replaceButton.clicked.connect(self.replace)


        allButton = QPushButton("Replace all",self)
        allButton.clicked.connect(self.replaceAll)


        self.findField = FindInputLine(self)
        self.findField.setMaximumHeight(40)
        self.findField.setTabChangesFocus(True)

        self.caseSens = QCheckBox("Case sensitive",self)
        if self.caseSens.isChecked():
            self.cs = True
        else:
            self.cs = False


        self.wholeWords = QCheckBox("Whole words",self)
        if self.wholeWords.isChecked():
            self.wo = True
        else:
            self.wo = False


        self.normalRadio = QRadioButton("Normal",self)
        self.normalRadio.toggled.connect(self.normalMode)
        self.normalRadio.setChecked(True)

        # Regular Expression Mode - radio button
        self.regexRadio = QRadioButton("RegEx",self)
        self.regexRadio.toggled.connect(self.regexMode)

        self.replaceField = FindInputLine(self)
        self.replaceField.setMaximumHeight(40)
        self.replaceField.setTabChangesFocus(True)

        optionsLabel = QLabel("Options: ",self)

        layout = QGridLayout()

        layout.addWidget(self.findField,1,0,1,4)
        layout.addWidget(self.normalRadio,2,2)
        layout.addWidget(self.regexRadio,2,3)
        layout.addWidget(findButton,2,0,1,2)
        layout.addWidget(self.replaceField,3,0,1,4)
        layout.addWidget(replaceButton,4,0,1,2)
        layout.addWidget(allButton,4,2,1,2)

        spacer = QWidget(self)
        spacer.setFixedSize(0,10)
        layout.addWidget(spacer,5,0)

        layout.addWidget(optionsLabel,6,0)
        layout.addWidget(self.caseSens,6,1)
        layout.addWidget(self.wholeWords,6,2)

        self.resultLabel = QLabel('', self)
        layout.addWidget(self.resultLabel,6,3)

        self.setGeometry(300,300,360,250)
        self.setWindowTitle("Find / Replace")
        self.setLayout(layout)
        self.findField.setFocus(True)
        # Tab moves from the find field straight to the replace field
        self.findButton, self.replaceButton, self.allButton = findButton, replaceButton, allButton
        for first, second in ((self.findField, self.replaceField), (self.replaceField, findButton),
                              (findButton, replaceButton), (replaceButton, allButton)):
            QWidget.setTabOrder(first, second)

        self.findField.enter_pressed.connect(self.find)
        self.replaceField.enter_pressed.connect(self.replace)

    def getCurrentEditor(self):
        return self.qtabs.currentWidget()

    def regexMode(self):
        # Uncheck and then disable case sensitive/whole words in regex mode
        self.caseSens.setChecked(False)
        self.wholeWords.setChecked(False)

        self.caseSens.setEnabled(False)
        self.wholeWords.setEnabled(False)

        self.re = True

    def normalMode(self):
        # Enable case sensitive/whole words
        self.caseSens.setEnabled(True)
        self.wholeWords.setEnabled(True)

        self.re = False

    def options(self):
        """Read the search options at the time of the search."""
        self.expr = self.findField.toPlainText()
        self.cs = self.caseSens.isChecked()
        self.wo = self.wholeWords.isChecked()
        return self.expr, self.re, self.cs, self.wo

    def find(self):
        """Select the next match after the cursor (wraps around)."""
        editor = self.getCurrentEditor()
        self.last_match = None
        if not editor:
            return False
        expr, regex, cs, wo = self.options()
        if not expr:
            self.show_result('')
            return False
        found = editor.findFirst(expr, regex, cs, wo, True)
        if found:
            self.last_match = (id(editor), expr, editor.getSelection())
            self.show_result('')
        else:
            self.show_result('Not found')
        return found

    def is_on_current_match(self, editor):
        """True if the selection is still the match of the last search."""
        return (self.last_match is not None and editor.hasSelectedText()
                and self.last_match == (id(editor), self.findField.toPlainText(), editor.getSelection()))

    def replace(self):
        """
        Replace the highlighted match, then highlight the next one.
        If nothing is highlighted yet, only highlight the first match.
        """
        editor = self.getCurrentEditor()
        if not editor:
            return
        if self.is_on_current_match(editor):
            editor.replace(self.replaceField.toPlainText())
        self.find()

    def replaceAll(self):
        editor = self.getCurrentEditor()
        if not editor:
            return
        expr, regex, cs, wo = self.options()
        if not expr:
            return
        replace_str = self.replaceField.toPlainText()
        line, index = editor.getCursorPosition()
        count = 0
        editor.beginUndoAction()
        try:
            # one pass from the top, no wrap-around: text that was already
            # replaced is never searched again, so replacing "A" by "A B" ends
            found = editor.findFirst(expr, regex, cs, wo, False, True, 0, 0)
            while found:
                before = editor.getSelection()
                editor.replace(replace_str)
                count += 1
                found = editor.findNext()
                if found and editor.getSelection() == before:
                    break   # no progress (e.g. empty regex match)
        finally:
            editor.endUndoAction()
        self.last_match = None
        editor.setCursorPosition(min(line, editor.lines() - 1), 0)
        self.show_result('%d replaced' % count if count else 'Not found')
        return count

    def show_result(self, msg):
        self.resultLabel.setText(msg)
