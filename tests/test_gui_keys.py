"""Shortcuts typed in the editor reach the new commands."""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import run_gui_tests, note, check
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
N = note('201801010501 Keys.md', 'some words here\n')
def keys(app):
    e = app.open_document(N); app.gui.activateWindow(); e.setFocus(); app.app.processEvents()
    QTest.qWaitForWindowActive(app.gui, 2000)
    e.setSelection(0, 5, 0, 10)
    QTest.keyClick(e, Qt.Key_B, Qt.ControlModifier); app.app.processEvents()
    check('Ctrl+B typed in the editor makes bold', e.text(), 'some **words** here\n')
    e.setSelection(0, 0, 0, 4)
    QTest.keyClick(e, Qt.Key_I, Qt.ControlModifier); app.app.processEvents()
    check('Ctrl+I typed in the editor makes italic', e.text(), '*some* **words** here\n')
    e.setCursorPosition(0, 0)
    QTest.keyClick(e, Qt.Key_L, Qt.ControlModifier); app.app.processEvents()
    check('Ctrl+L typed in the editor makes a dash item', e.text(), '- *some* **words** here\n')
run_gui_tests([keys])
