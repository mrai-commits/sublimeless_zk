# -*- coding: utf-8 -*-
"""
A note in a window of its own, new in Sublimeless 1.0.

The window shows a second view of the note that stays open as a tab in the
main window. Both views share one document: what is typed in one appears in
the other, and saving, closing and reloading remain the business of the tab.
That way a note can never be open twice with different contents.
"""
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow


class NoteWindow(QMainWindow):
    closed = pyqtSignal(object)        # emits itself

    def __init__(self, view, primary, actions=()):
        """
        view:    the editor shown in this window
        primary: the editor in the main window's tab; owner of the document
        actions: the app's commands, so that their shortcuts work here too
        """
        super().__init__(None)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.view = view
        self.primary = primary
        view.primary_editor = primary
        view.note_window = self
        view.setDocument(primary.document())
        self.setCentralWidget(view)
        self.addActions(list(actions))
        self.update_title()
        self.resize(720, 760)

    def update_title(self):
        name = os.path.basename(self.primary.file_name or '')
        self.setWindowTitle(name + ('*' if self.primary.isModified() else ''))

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)
