"""
iPad OS Style Virtual Keyboard Widget

A custom on-screen keyboard that mimics the iPad OS keyboard design.
Includes multiple layouts (letters, numbers, symbols) with smooth transitions.
"""

import logging
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QGridLayout, QSpacerItem, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

logger = logging.getLogger(__name__)


class IpadKeyboard(QWidget):
    """iPad OS style virtual keyboard widget."""

    # Signals
    key_pressed = pyqtSignal(str)  # Emitted when a key is pressed
    backspace_pressed = pyqtSignal()  # Emitted when backspace is pressed
    enter_pressed = pyqtSignal()  # Emitted when enter is pressed
    dismiss_pressed = pyqtSignal()  # Emitted when dismiss button is pressed

    def __init__(self, parent=None):
        logger.info("IpadKeyboard.__init__ called with parent: %s", parent)
        try:
            super().__init__(parent)
            logger.debug("QWidget.__init__ completed")
            self.current_layout = "letters"  # letters, numbers, symbols
            self.shift_pressed = False
            self.caps_lock = False

            logger.debug("About to call _setup_ui()")
            self._setup_ui()
            logger.debug("_setup_ui() completed")

            logger.debug("About to call _setup_connections()")
            self._setup_connections()
            logger.debug("_setup_connections() completed")

            logger.info("IpadKeyboard initialization completed successfully")
        except Exception as e:
            logger.error("IpadKeyboard initialization failed: %s", e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    def _setup_ui(self):
        """Setup the keyboard UI."""
        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Main container with rounded corners and shadow effect
        main_frame = QFrame(self)
        main_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(242, 242, 247, 0.95);
                border: 1px solid rgba(142, 142, 147, 0.3);
                border-radius: 10px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
            }
        """)

        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Keyboard rows
        self.rows_container = QWidget()
        rows_layout = QVBoxLayout(self.rows_container)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(6)

        # Create all keyboard layouts
        self._create_letters_layout()
        self._create_numbers_layout()
        self._create_symbols_layout()

        # Show letters layout by default
        self._show_layout("letters")

        main_layout.addWidget(self.rows_container)

        # Bottom row with space and enter
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)

        # Space bar - make it wider proportionally
        space_width = int(self.width() * 0.5)  # 50% of keyboard width
        space_btn = self._create_key_button("space", "space", width=space_width)
        space_btn.setText("space")
        bottom_layout.addWidget(space_btn)

        # Enter key
        enter_width = int(self.width() * 0.15)  # 15% of keyboard width
        enter_btn = self._create_key_button("↵", "return", width=enter_width)
        enter_btn.setStyleSheet(enter_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(0, 122, 255, 0.1);
                border: 1px solid rgba(0, 122, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        bottom_layout.addWidget(enter_btn)

        rows_layout.addLayout(bottom_layout)

        # Set main frame as central widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_frame)

        # Size the keyboard - make it responsive to screen size
        screen = QApplication.primaryScreen()
        if screen:
            screen_size = screen.availableGeometry()
            # Scale keyboard to fit screen (max 90% width, fixed height)
            keyboard_width = min(800, int(screen_size.width() * 0.9))
            self.setFixedSize(keyboard_width, 260)
        else:
            self.setFixedSize(800, 260)

    def _create_key_button(self, text: str, key_code: str = "", width: int = 50, height: int = 45) -> QPushButton:
        """Create a keyboard key button with iPad styling."""
        btn = QPushButton(text)
        btn.setFixedSize(width, height)

        # Store key code for processing
        btn.setProperty("key_code", key_code or text.lower())

        btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid rgba(142, 142, 147, 0.3);
                border-radius: 5px;
                color: #1c1c1e;
                font-size: 16px;
                font-weight: 400;
            }
            QPushButton:pressed {
                background-color: #e5e5ea;
                border-color: rgba(0, 122, 255, 0.5);
            }
            QPushButton:hover {
                background-color: #f2f2f7;
            }
        """)

        btn.clicked.connect(lambda: self._on_key_pressed(btn))
        return btn

    def _create_letters_layout(self):
        """Create the letters keyboard layout."""
        self.letters_widget = QWidget()
        layout = QVBoxLayout(self.letters_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Row 1: q w e r t y u i o p
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        keys = ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]
        for key in keys:
            row1.addWidget(self._create_key_button(key.upper(), key))
        layout.addLayout(row1)

        # Row 2: a s d f g h j k l
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        keys = ["a", "s", "d", "f", "g", "h", "j", "k", "l"]
        for key in keys:
            row2.addWidget(self._create_key_button(key.upper(), key))
        row2.addItem(QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(row2)

        # Row 3: shift z x c v b n m backspace
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        shift_btn = self._create_key_button("⇧", "shift", width=70)
        row3.addWidget(shift_btn)

        keys = ["z", "x", "c", "v", "b", "n", "m"]
        for key in keys:
            row3.addWidget(self._create_key_button(key.upper(), key))

        backspace_btn = self._create_key_button("⌫", "backspace", width=70)
        backspace_btn.setStyleSheet(backspace_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(142, 142, 147, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(142, 142, 147, 0.2);
            }
        """)
        row3.addWidget(backspace_btn)
        layout.addLayout(row3)

        # Row 4: 123 dismiss space return
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        numbers_btn = self._create_key_button("123", "numbers", width=60)
        row4.addWidget(numbers_btn)

        dismiss_btn = self._create_key_button("⌨", "dismiss", width=50)
        dismiss_btn.setStyleSheet(dismiss_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(255, 59, 48, 0.1);
                border-color: rgba(255, 59, 48, 0.3);
                color: #ff3b30;
            }
            QPushButton:pressed {
                background-color: rgba(255, 59, 48, 0.2);
            }
        """)
        row4.addWidget(dismiss_btn)
        layout.addLayout(row4)

    def _create_numbers_layout(self):
        """Create the numbers/symbols keyboard layout."""
        self.numbers_widget = QWidget()
        layout = QVBoxLayout(self.numbers_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Row 1: 1 2 3 4 5 6 7 8 9 0
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        for key in keys:
            row1.addWidget(self._create_key_button(key, key))
        layout.addLayout(row1)

        # Row 2: - / : ; ( ) $ & @ "
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        keys = ["-", "/", ":", ";", "(", ")", "$", "&", "@", "\""]
        for key in keys:
            row2.addWidget(self._create_key_button(key, key))
        layout.addLayout(row2)

        # Row 3: symbols . , ? ! ' backspace
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        symbols_btn = self._create_key_button("#+=", "symbols", width=60)
        row3.addWidget(symbols_btn)

        keys = [".", ",", "?", "!", "'"]
        for key in keys:
            row3.addWidget(self._create_key_button(key, key))

        backspace_btn = self._create_key_button("⌫", "backspace", width=60)
        backspace_btn.setStyleSheet(backspace_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(142, 142, 147, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(142, 142, 147, 0.2);
            }
        """)
        row3.addWidget(backspace_btn)
        layout.addLayout(row3)

        # Row 4: ABC dismiss space return
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        letters_btn = self._create_key_button("ABC", "letters", width=60)
        row4.addWidget(letters_btn)

        dismiss_btn = self._create_key_button("⌨", "dismiss", width=50)
        dismiss_btn.setStyleSheet(dismiss_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(255, 59, 48, 0.1);
                border-color: rgba(255, 59, 48, 0.3);
                color: #ff3b30;
            }
            QPushButton:pressed {
                background-color: rgba(255, 59, 48, 0.2);
            }
        """)
        row4.addWidget(dismiss_btn)
        layout.addLayout(row4)

    def _create_symbols_layout(self):
        """Create the symbols keyboard layout."""
        self.symbols_widget = QWidget()
        layout = QVBoxLayout(self.symbols_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Row 1: [ ] { } # % ^ * + =
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        keys = ["[", "]", "{", "}", "#", "%", "^", "*", "+", "="]
        for key in keys:
            row1.addWidget(self._create_key_button(key, key))
        layout.addLayout(row1)

        # Row 2: _ \ | ~ < > € £ ¥ •
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        keys = ["_", "\\", "|", "~", "<", ">", "€", "£", "¥", "•"]
        for key in keys:
            row2.addWidget(self._create_key_button(key, key))
        layout.addLayout(row2)

        # Row 3: 123 . , ? ! ' backspace
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        numbers_btn = self._create_key_button("123", "numbers", width=60)
        row3.addWidget(numbers_btn)

        keys = [".", ",", "?", "!", "'"]
        for key in keys:
            row3.addWidget(self._create_key_button(key, key))

        backspace_btn = self._create_key_button("⌫", "backspace", width=70)
        backspace_btn.setStyleSheet(backspace_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(142, 142, 147, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(142, 142, 147, 0.2);
            }
        """)
        row3.addWidget(backspace_btn)
        layout.addLayout(row3)

        # Row 4: ABC dismiss space return
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        letters_btn = self._create_key_button("ABC", "letters", width=60)
        row4.addWidget(letters_btn)

        dismiss_btn = self._create_key_button("⌨", "dismiss", width=50)
        dismiss_btn.setStyleSheet(dismiss_btn.styleSheet() + """
            QPushButton {
                background-color: rgba(255, 59, 48, 0.1);
                border-color: rgba(255, 59, 48, 0.3);
                color: #ff3b30;
            }
            QPushButton:pressed {
                background-color: rgba(255, 59, 48, 0.2);
            }
        """)
        row4.addWidget(dismiss_btn)
        layout.addLayout(row4)

    def _show_layout(self, layout_name: str):
        """Show the specified keyboard layout."""
        # Hide all layouts
        if hasattr(self, 'letters_widget'):
            self.letters_widget.hide()
        if hasattr(self, 'numbers_widget'):
            self.numbers_widget.hide()
        if hasattr(self, 'symbols_widget'):
            self.symbols_widget.hide()

        # Show the requested layout
        if layout_name == "letters":
            self.letters_widget.show()
        elif layout_name == "numbers":
            self.numbers_widget.show()
        elif layout_name == "symbols":
            self.symbols_widget.show()

        self.current_layout = layout_name

    def _setup_connections(self):
        """Setup signal connections."""
        # Connections are handled in _create_*_layout methods
        pass

    def _on_key_pressed(self, button: QPushButton):
        """Handle key press events."""
        key_code = button.property("key_code")
        button_text = button.text()

        logger.info("Keyboard button pressed: text='%s', key_code='%s'", button_text, key_code)

        if key_code == "shift":
            self._toggle_shift()
            logger.debug("Shift toggled")
        elif key_code == "letters":
            self._show_layout("letters")
            logger.debug("Switched to letters layout")
        elif key_code == "numbers":
            self._show_layout("numbers")
            logger.debug("Switched to numbers layout")
        elif key_code == "symbols":
            self._show_layout("symbols")
            logger.debug("Switched to symbols layout")
        elif key_code == "backspace":
            logger.debug("Emitting backspace signal")
            self.backspace_pressed.emit()
        elif key_code == "return":
            logger.debug("Emitting enter signal")
            self.enter_pressed.emit()
        elif key_code == "dismiss":
            logger.debug("Emitting dismiss signal")
            self.dismiss_pressed.emit()
        elif key_code == "space":
            logger.debug("Emitting space character")
            self.key_pressed.emit(" ")
        else:
            # Regular character key
            char = key_code
            if self.shift_pressed and not self.caps_lock:
                char = char.upper()
            elif self.caps_lock:
                char = char.upper()
            else:
                char = char.lower()

            logger.debug("Emitting character: '%s' (original: '%s')", char, key_code)
            self.key_pressed.emit(char)

            # Auto-unshift after typing a letter (iOS behavior)
            if self.shift_pressed and key_code.isalpha() and not self.caps_lock:
                self._toggle_shift()
                logger.debug("Auto-unshifted after letter")

    def _toggle_shift(self):
        """Toggle shift state."""
        self.shift_pressed = not self.shift_pressed
        # Update UI to show shift state
        # In a real implementation, you'd update the shift button appearance
        logger.debug("Shift toggled: %s", self.shift_pressed)

    def show_at_position(self, x: int, y: int):
        """Show the keyboard at a specific position."""
        logger.info("Showing keyboard at position (%d, %d)", x, y)
        logger.debug("Keyboard widget: %s", self)
        logger.debug("Keyboard size: %s", self.size())
        logger.debug("Keyboard isVisible before: %s", self.isVisible())

        self.move(x, y)
        logger.debug("Moved to (%d, %d)", x, y)

        self.show()
        logger.debug("show() called")

        self.raise_()
        logger.debug("raise_() called")

        logger.info("Keyboard show() called, widget visible: %s", self.isVisible())

        # Force repaint
        self.update()
        QApplication.processEvents()

    def hide_keyboard(self):
        """Hide the keyboard."""
        self.hide()



