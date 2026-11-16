# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.Qsci import *
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QObject, QEvent

from zkscintilla import ZettelkastenScintilla
from zkmdlexer import ZkMdLexer
from themes import Theme
from settings import base_dir
from opennoteswidget import OpenNotesPanel

class TabSwiper(QObject):
    """
    Move through the tabs with the trackpad or mouse wheel: with the pointer
    on the tab bar, a two-finger swipe to the left or right (or turning the
    wheel) goes to the next or previous tab, as in a web browser.
    """
    STEP = 120          # scroll distance per tab; one notch of a mouse wheel

    def __init__(self, tab_widget):
        super().__init__(tab_widget)
        self.tabs = tab_widget
        self.travelled = 0
        tab_widget.tabBar().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Wheel:
            return False
        delta = event.angleDelta()
        # a sideways swipe counts first; a plain mouse wheel turns vertically
        amount = delta.x() if abs(delta.x()) >= abs(delta.y()) else delta.y()
        if amount == 0:
            return True
        if (amount > 0) != (self.travelled > 0):
            self.travelled = 0          # changed direction
        self.travelled += amount
        steps = int(abs(self.travelled) / self.STEP)
        if steps:
            # swiping left (negative) brings the tabs on the right, like scrolling
            direction = -1 if self.travelled > 0 else 1
            self.travelled -= (self.STEP * steps) * (1 if self.travelled > 0 else -1)
            target = max(0, min(self.tabs.count() - 1, self.tabs.currentIndex() + direction * steps))
            if target != self.tabs.currentIndex():
                self.tabs.setCurrentIndex(target)
        return True


class MainWindow(QMainWindow):    
    def __init__(self, theme, close_handler):
        super(MainWindow, self).__init__()

        # load theme
        self.theme = theme
        self.close_handler = close_handler
        
        self.setGeometry(300, 200, 900, 600)
        self.setWindowTitle("Sublimeless Zettelkasten")
        #self.setStyleSheet("QTabBar{font: 8px;}")

        self._frm = QFrame(self)
        self._frm.setStyleSheet("QWidget { background-color: #ffeaeaea }")
        self._lyt = QVBoxLayout()
        self._frm.setLayout(self._lyt)
        self.setCentralWidget(self._frm)
        self._myFont = QFont()
        self._myFont.setPointSize(14)

        self.qtabs = QTabWidget()
        # start with a 50:50 split
        self.qtabs.setGeometry(0,0,450,600)

        mainsplit = QSplitter()
        mainsplit.setOrientation(Qt.Horizontal)
        subsplit = QSplitter()
        self.notelist_panel = OpenNotesPanel()
        self.notelist_panel.setVisible(False)
        self.search_results_editor = self.make_search_results_editor()
        self.saved_searches_editor = self.make_saved_searches_editor()
        subsplit.addWidget(self.search_results_editor)
        subsplit.addWidget(self.saved_searches_editor)
        subsplit.setOrientation(Qt.Vertical)
        mainsplit.addWidget(self.notelist_panel)
        mainsplit.addWidget(self.qtabs)
        mainsplit.addWidget(subsplit)
        mainsplit.setCollapsible(0, False)
        mainsplit.setCollapsible(1, False)
        mainsplit.setCollapsible(2, False)

        self.qtabs.setMovable(True)
        self.qtabs.setDocumentMode(True)
        self._lyt.addWidget(mainsplit)
        self.mainsplit = mainsplit
        self.subsplit = subsplit
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.qtabs.setTabsClosable(True)
        self.tab_swiper = TabSwiper(self.qtabs)
        if sys.platform == 'win32':
            self.setWindowIcon(QIcon(f"{os.path.join(base_dir(), 'sublimeless_zk.ico')}"))
            
        self.tab_spaces_label = QLabel('')
        self.tab_spaces_label.setStyleSheet('QLabel{ color: #606060; }')
        self.line_count_label = QLabel('')
        self.line_count_label.setStyleSheet('QLabel{ color: #303030; }')
        self.word_count_label = QLabel('')
        self.word_count_label.setStyleSheet('QLabel{ color: #303030; }')
        self.statusBar().addPermanentWidget(self.tab_spaces_label)
        spc = QWidget()
        spc.setMinimumWidth(20)

        self.statusBar().addPermanentWidget(spc)
        self.statusBar().addPermanentWidget(self.line_count_label)
        self.statusBar().addPermanentWidget(self.word_count_label)
        self.statusBar().showMessage('Welcome to Sublimeless_ZK', 3000)
        self.show()

    def layout_state(self):
        """Pane sizes and window geometry, to be restored at the next start."""
        g = self.geometry()
        return {
            'mainsplit': self.mainsplit.sizes(),
            'subsplit': self.subsplit.sizes(),
            'geometry': [g.x(), g.y(), g.width(), g.height()],
            'maximized': self.isMaximized(),
            'side_panel': self.saved_searches_editor.isVisible(),
            'open_files_panel': self.notelist_panel.isVisible(),
        }

    def restore_layout(self, state):
        if not isinstance(state, dict) or not state:
            return
        try:
            geometry = state.get('geometry')
            if geometry and len(geometry) == 4 and geometry[2] > 200 and geometry[3] > 150:
                # only if that place still is on a connected screen
                rect = QRect(*[int(v) for v in geometry])
                if any(screen.availableGeometry().intersects(rect) for screen in QApplication.screens()):
                    self.setGeometry(rect)
            if state.get('maximized'):
                self.showMaximized()
            if state.get('open_files_panel') is True:
                self.notelist_panel.setVisible(True)
            if state.get('side_panel') is False:
                self.saved_searches_editor.setVisible(False)
                self.search_results_editor.setVisible(False)
            for name in ('mainsplit', 'subsplit'):
                sizes = state.get(name)
                splitter = getattr(self, name)
                if sizes and len(sizes) == splitter.count() and sum(sizes) > 0:
                    splitter.setSizes([int(v) for v in sizes])
        except Exception as e:
            print('could not restore the window layout:', e)

    def apply_font_settings(self, settings):
        # apply font settings
        if 'ui.tabs.font.face' in settings and 'ui.tabs.font.size' in settings:
            try:
                self.qtabs.setFont(QFont(settings['ui.tabs.font.face'], settings['ui.tabs.font.size']))
            except:
                pass
        else:
            self.qtabs.setFont(QFont(self.qtabs.font().family(), 8))
        if 'ui.statusbar.font.face' in settings and 'ui.statusbar.font.size' in settings:
            try:
                self.statusBar().setFont(QFont(settings['ui.statusbar.font.face'], settings['ui.statusbar.font.size']))
            except:
                pass
        if 'ui.editorinfo.font.face' in settings and 'ui.editorinfo.font.size' in settings:
            try:
                font = QFont(settings['ui.editorinfo.font.face'], settings['ui.editorinfo.font.size'])
                self.line_count_label.setFont(font)
                self.word_count_label.setFont(font)
                self.tab_spaces_label.setFont(font)
            except:
                pass
        else:
            font = QFont(self.line_count_label.font().family(), 9)
            self.line_count_label.setFont(font)
            self.word_count_label.setFont(font)
            self.tab_spaces_label.setFont(font)
        if 'ui.notepanel.font.face' in settings and 'ui.notepanel.font.size' in settings:
            try:
                self.notelist_panel.setFont(QFont(settings['ui.notepanel.font.face'], settings['ui.notepanel.font.size']))
            except:
                pass
        else:
            self.notelist_panel.setFont(QFont(self.notelist_panel.font().family(), 10))
        
    def new_zk_editor(self, filn=None, settings=None):
        editor = ZettelkastenScintilla(document_filn=filn)
        editor.continue_lists = bool((settings or {}).get('continue_lists', True))
        editor.setUtf8(True)             # Set encoding to UTF-8
        if filn:
            with open(filn,
                      mode='r', encoding='utf-8', errors='ignore') as f:
                txt = f.read()
            editor.setText(txt)
        editor.setLexer(None)            # We install lexer later

        if settings is None:
            settings = {}
        
        wrapmode = QsciScintilla.WrapWord
        wrapvisual = QsciScintilla.WrapFlagByText
        wrapindentmode = QsciScintilla.WrapIndentIndented
        autoindent = True
        indentationguides = True
        usetabs = False

        if settings.get('wrap_lines', True) == False:
            wrapmode = QsciScintilla.WrapNone
        if settings.get('show_wrap_markers', True) == False:
            wrapvisual = QsciScintilla.WrapFlagNone
        if settings.get('indent_wrapped_lines', True) == False:
            wrapindentmode = QsciScintilla.WrapIndentSame
        if settings.get('auto_indent', True) == False:
            autoindent = False
        if settings.get('show_indentation_guides', True) == False:
            indentationguides = False
        if settings.get('use_tabs', False) == True:
            usetabs = True

        editor.setWrapMode(wrapmode)
        editor.setWrapVisualFlags(wrapvisual)
        editor.visual_flags = wrapvisual
        editor.setWrapIndentMode(wrapindentmode)

        editor.setEolMode(QsciScintilla.EolUnix)
        editor.setEolVisibility(False)

        editor.setIndentationsUseTabs(usetabs)
        editor.setTabWidth(4)
        editor.setIndentationGuides(indentationguides)
        editor.setTabIndents(True)
        editor.setAutoIndent(autoindent)
        editor.setScrollWidthTracking(True)
        editor.setMarginType(0, QsciScintilla.SymbolMargin)
        editor.setMarginWidth(0, "0")        # todo: do we want margins?
        editor.setMarginWidth(1, "")
        editor.setMarginsForegroundColor(QColor("#ff888888"))

        show_block_quotes = True
        lexer = ZkMdLexer(editor, self.theme, highlight_saved_searches=False, show_block_quotes=show_block_quotes)
        editor.setLexer(lexer)
        editor.setCaretLineVisible(True)
        editor.setCaretWidth(8)
        #editor.setMarginsBackgroundColor(QColor("#ff404040"))

        # give it a good size
        editor.setMinimumWidth(QFontMetrics(editor.lexer().default_font).width('M' * 20))
        self.apply_theme(editor)
        return editor

    def apply_theme(self, editors=None, new_theme=None):
        if new_theme is not None:
            self.theme = new_theme
        if editors is not None:
            # got passed in a single editor
            if not isinstance(editors, list):
                editors = [editors]
        else:
            editors = [self.qtabs.widget(i) for i in range(self.qtabs.count())]

        for editor in editors:
            lexer = editor.lexer()
            lexer.apply_theme(self.theme)
            editor.setMarginsBackgroundColor(QColor(self.theme.style_infos['default']['background']))
            editor.set_calculation_font(lexer.default_font)
            editor.setCaretForegroundColor(QColor(lexer.theme.caret))
            editor.setCaretLineBackgroundColor(QColor(lexer.theme.highlight))
            editor.setFont(lexer.default_font)
            editor.setExtraAscent(self.theme.line_pad_top)
            editor.setExtraDescent(self.theme.line_pad_bottom)


    def format_editor_info(self, editor):
        if editor.indentationsUseTabs():
            usetabs = 'TAB'
        else:
            usetabs = 'SPC'
        
        if editor.wrapMode() == QsciScintilla.WrapWord:
            wrapmode = 'Wrap:Y'
        else:
            wrapmode = 'Wrap:N'
        
        if editor.visual_flags == QsciScintilla.WrapFlagByText:
            wrapmode += '+show'
        
        if editor.wrapIndentMode() == QsciScintilla.WrapIndentIndented:
            wrapmode += '+indent'
        
        if editor.autoIndent() == True:
            autoindent = 'Indent:auto'
        else:
            autoindent = 'Indent:no'
        
        if editor.indentationGuides() == True:
            guides = 'Guides:yes'
        else:
            guides = 'Guides:no'
        
        self.tab_spaces_label.setText(f'{usetabs:20} {wrapmode:20} {autoindent:20} {guides:20}')
        return

    def make_search_results_editor(self):
        editor = ZettelkastenScintilla(editor_type='searchresults')
        editor.setUtf8(True)             # Set encoding to UTF-8

        editor.setLexer(None)
        editor.setWrapMode(QsciScintilla.WrapWord)
        editor.setWrapVisualFlags(QsciScintilla.WrapFlagNone)
        editor.setWrapIndentMode(QsciScintilla.WrapIndentIndented)

        editor.setEolMode(QsciScintilla.EolUnix)
        editor.setEolVisibility(False)

        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)
        editor.setIndentationGuides(False)
        editor.setTabIndents(True)
        editor.setAutoIndent(True)

        editor.setMarginType(0, QsciScintilla.SymbolMargin)
        editor.setMarginWidth(0, 10)
        editor.setMarginWidth(1, 10)
        editor.setMarginsForegroundColor(QColor("#ff888888"))

        theme = Theme(f'{base_dir()}/themes/search_results.json')

        lexer = ZkMdLexer(editor, theme, highlight_saved_searches=False, show_block_quotes=False)
        editor.setLexer(lexer)
        editor.set_calculation_font(lexer.default_font)

        editor.setCaretForegroundColor(QColor(lexer.theme.caret))
        editor.setCaretLineVisible(True)
        editor.setCaretLineBackgroundColor(QColor(lexer.theme.highlight))
        editor.setCaretWidth(2)
        editor.setMarginsBackgroundColor(QColor(theme.background))
        editor.setFont(lexer.default_font)
        editor.setExtraAscent(theme.line_pad_top)
        editor.setExtraDescent(theme.line_pad_bottom)

        # no minimum width
        return editor

    def make_saved_searches_editor(self):
        editor = ZettelkastenScintilla(editor_type='savedsearches')
        editor.setUtf8(True)             # Set encoding to UTF-8

        editor.setLexer(None)            # We install lexer later
        editor.setWrapMode(QsciScintilla.WrapWord)
        editor.setWrapVisualFlags(QsciScintilla.WrapFlagNone)
        editor.setWrapIndentMode(QsciScintilla.WrapIndentIndented)

        editor.setEolMode(QsciScintilla.EolUnix)
        editor.setEolVisibility(False)

        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)
        editor.setIndentationGuides(False)
        editor.setTabIndents(True)
        editor.setAutoIndent(True)

        editor.setMarginType(0, QsciScintilla.SymbolMargin)
        editor.setMarginWidth(0, 10)
        editor.setMarginWidth(1, 10)
        editor.setMarginsForegroundColor(QColor("#ff888888"))

        theme = Theme(f'{base_dir()}/themes/saved_searches.json')

        lexer = ZkMdLexer(editor, theme, highlight_saved_searches=True, show_block_quotes=False)
        editor.setLexer(lexer)
        editor.set_calculation_font(lexer.default_font)

        editor.setCaretForegroundColor(QColor(lexer.theme.caret))
        editor.setCaretLineVisible(True)
        editor.setCaretLineBackgroundColor(QColor(lexer.theme.highlight))
        editor.setCaretWidth(2)
        editor.setMarginsBackgroundColor(QColor(theme.background))
        editor.setFont(lexer.default_font)
        editor.setExtraAscent(theme.line_pad_top)
        editor.setExtraDescent(theme.line_pad_bottom)

        # no minimum width
        return editor
        

    def closeEvent(self, event):
        if self.close_handler() == False:
            event.ignore()
