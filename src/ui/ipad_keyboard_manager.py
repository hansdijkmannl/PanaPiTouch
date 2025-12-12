"""
iPad Keyboard Manager

Manages the iPad-style virtual keyboard integration with PyQt6 widgets.
Handles showing/hiding the keyboard and connecting it to text input widgets.
"""

import logging
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QApplication
)
from PyQt6.QtCore import QObject, QEvent, QTimer
from PyQt6.QtGui import QTextCursor

from .ipad_keyboard import IpadKeyboard

logger = logging.getLogger(__name__)


class KeyboardEventFilter(QObject):
    """Event filter to detect focus changes on text widgets."""

    def __init__(self, keyboard_manager, parent=None):
        super().__init__(parent)
        self.keyboard_manager = keyboard_manager

    def eventFilter(self, obj, event):
        try:
            logger.debug("Event filter: %s on %s", event.type(), type(obj).__name__)
            if event.type() == QEvent.Type.FocusIn:
                logger.info("FocusIn event detected on %s", type(obj).__name__)
                # Show keyboard when widget gets focus
                self.keyboard_manager.show_keyboard_for_widget(obj)
            elif event.type() == QEvent.Type.FocusOut:
                logger.debug("FocusOut event detected on %s", type(obj).__name__)
                # Hide keyboard after a delay when widget loses focus
                # This allows clicking keyboard buttons without hiding immediately
                QTimer.singleShot(200, lambda: self.keyboard_manager.check_focus_and_hide())
        except Exception as e:
            logger.warning("Error in keyboard event filter: %s", e)
        return super().eventFilter(obj, event)


class IpadKeyboardManager(QObject):
    """Manager for iPad-style virtual keyboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keyboard = None
        self.current_widget = None
        self.event_filter = KeyboardEventFilter(self, self)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_keyboard)

    def _ensure_keyboard_created(self):
        """Create the keyboard widget if it doesn't exist yet."""
        if self.keyboard is None:
            logger.info("Creating iPad keyboard widget...")
            try:
                self.keyboard = IpadKeyboard(None)  # No parent to ensure it's a top-level window
                self._connect_keyboard_signals()
                logger.info("✓ Created iPad keyboard widget successfully")
            except Exception as e:
                logger.error("✗ Failed to create iPad keyboard: %s", e)
                import traceback
                logger.error("Traceback: %s", traceback.format_exc())
                self.keyboard = None
                return False
        return True

    def _connect_keyboard_signals(self):
        """Connect keyboard signals to handlers."""
        if self.keyboard:
            self.keyboard.key_pressed.connect(self._on_key_pressed)
            self.keyboard.backspace_pressed.connect(self._on_backspace_pressed)
            self.keyboard.enter_pressed.connect(self._on_enter_pressed)
            self.keyboard.dismiss_pressed.connect(self._on_dismiss_pressed)

    def _setup_global_filter(self):
        """Setup is handled in setup_widget method for individual widgets."""
        pass  # Individual widgets are handled in setup_widget method

    def show_keyboard_for_widget(self, widget):
        """Show keyboard for a specific text input widget."""
        logger.info("show_keyboard_for_widget called with %s", type(widget).__name__)
        if not isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
            logger.info("Widget type %s not supported", type(widget).__name__)
            return

        # Avoid showing keyboard for the same widget repeatedly
        if self.current_widget == widget:
            logger.info("Keyboard already shown for this widget")
            return

        logger.info("Setting current widget to %s", type(widget).__name__)
        self.current_widget = widget

        logger.info("Calling _ensure_keyboard_created()...")
        if not self._ensure_keyboard_created():
            logger.error("Failed to ensure keyboard is created!")
            return

        logger.info("Keyboard ensured, now positioning...")

        # Cancel any pending hide
        self.hide_timer.stop()

        # Make sure keyboard is created before accessing its properties
        if not self._ensure_keyboard_created():
            logger.error("Failed to create keyboard, cannot show it")
            return

        if self.keyboard is None:
            logger.error("Keyboard is None after _ensure_keyboard_created!")
            return

        try:
            logger.debug("Keyboard object: %s", self.keyboard)
            logger.debug("Keyboard size: %s", self.keyboard.size())

            # Position keyboard below the widget
            widget_rect = widget.rect()
            widget_global_pos = widget.mapToGlobal(widget_rect.bottomLeft())

            logger.debug("Widget rect: %s, global pos: %s", widget_rect, widget_global_pos)

            # Position keyboard centered horizontally below the widget
            keyboard_width = self.keyboard.width()
            keyboard_height = self.keyboard.height()
            logger.debug("Keyboard dimensions: %dx%d", keyboard_width, keyboard_height)

            keyboard_x = widget_global_pos.x() + (widget_rect.width() - keyboard_width) // 2
            keyboard_y = widget_global_pos.y() + 10  # Small gap below widget

            logger.debug("Calculated position: (%d, %d)", keyboard_x, keyboard_y)

            # Ensure keyboard stays on screen
            screen = QApplication.primaryScreen()
            logger.debug("Primary screen: %s", screen)
            if screen:
                screen_geom = screen.availableGeometry()
                logger.debug("Screen geometry: %s", screen_geom)
                keyboard_x = max(0, min(keyboard_x, screen_geom.width() - keyboard_width))
                keyboard_y = max(0, min(keyboard_y, screen_geom.height() - keyboard_height))
            else:
                logger.warning("No primary screen found, using default positioning")
                # Fallback positioning without screen bounds checking
                keyboard_x = max(0, keyboard_x)
                keyboard_y = max(0, keyboard_y)

            logger.info("Final position: (%d, %d)", keyboard_x, keyboard_y)
            self.keyboard.show_at_position(keyboard_x, keyboard_y)

            # Force the keyboard to be visible and on top
            QTimer.singleShot(100, lambda: self._ensure_keyboard_visible())
        except Exception as e:
            logger.error("Failed to position keyboard: %s", e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())
        except Exception as e:
            logger.warning("Failed to position keyboard: %s", e)
            # Fallback: show at center of screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geom = screen.availableGeometry()
                center_x = (screen_geom.width() - self.keyboard.width()) // 2
                center_y = (screen_geom.height() - self.keyboard.height()) // 2
                self.keyboard.show_at_position(center_x, center_y)

        logger.debug("Keyboard shown for widget: %s", type(widget).__name__)

    def hide_keyboard(self):
        """Hide the keyboard."""
        if self.keyboard:
            self.keyboard.hide_keyboard()
        self.current_widget = None
        logger.debug("Keyboard hidden")

    def check_focus_and_hide(self):
        """Check if focus is still on a text widget, hide keyboard if not."""
        try:
            app = QApplication.instance()
            if app:
                focused_widget = app.focusWidget()
                if not isinstance(focused_widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
                    self.hide_keyboard()
        except Exception as e:
            logger.warning("Error checking focus: %s", e)
            self.hide_keyboard()

    def _on_key_pressed(self, text: str):
        """Handle key press from keyboard."""
        logger.info("_on_key_pressed called with text: '%s'", text)
        if not self.current_widget:
            logger.warning("No current widget to insert text into")
            return

        logger.info("Current widget: %s, type: %s", self.current_widget, type(self.current_widget).__name__)

        try:
            if isinstance(self.current_widget, QLineEdit):
                # Insert character at cursor position
                cursor_pos = self.current_widget.cursorPosition()
                current_text = self.current_widget.text()
                logger.debug("Before: cursor_pos=%d, text='%s'", cursor_pos, current_text)
                new_text = current_text[:cursor_pos] + text + current_text[cursor_pos:]
                self.current_widget.setText(new_text)
                self.current_widget.setCursorPosition(cursor_pos + len(text))
                logger.debug("After: text='%s'", new_text)

            elif isinstance(self.current_widget, (QTextEdit, QPlainTextEdit)):
                # Insert text at cursor
                cursor = self.current_widget.textCursor()
                cursor.insertText(text)
                self.current_widget.setTextCursor(cursor)
                logger.debug("Inserted text into QTextEdit/QPlainTextEdit")

            elif isinstance(self.current_widget, QSpinBox):
                # For spin boxes, we might need special handling
                logger.debug("SpinBox key press - not implemented yet")

            elif isinstance(self.current_widget, QComboBox):
                # For combo boxes, only handle if editable
                if self.current_widget.isEditable():
                    logger.debug("Editable ComboBox key press - not implemented yet")
                else:
                    logger.debug("Non-editable ComboBox - ignoring key press")

            logger.info("Successfully inserted text: '%s'", text)
        except Exception as e:
            logger.error("Error inserting text: %s", e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())

    def _on_backspace_pressed(self):
        """Handle backspace press."""
        if not self.current_widget:
            return

        if isinstance(self.current_widget, QLineEdit):
            # Remove character before cursor
            cursor_pos = self.current_widget.cursorPosition()
            if cursor_pos > 0:
                current_text = self.current_widget.text()
                new_text = current_text[:cursor_pos-1] + current_text[cursor_pos:]
                self.current_widget.setText(new_text)
                self.current_widget.setCursorPosition(cursor_pos - 1)

        elif isinstance(self.current_widget, (QTextEdit, QPlainTextEdit)):
            # Delete character before cursor
            cursor = self.current_widget.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()
            else:
                cursor.deletePreviousChar()
            self.current_widget.setTextCursor(cursor)

        logger.debug("Backspace pressed")

    def _on_enter_pressed(self):
        """Handle enter/return press."""
        if not self.current_widget:
            return

        if isinstance(self.current_widget, QLineEdit):
            # For single-line input, could hide keyboard or do nothing
            self.hide_keyboard()
        elif isinstance(self.current_widget, (QTextEdit, QPlainTextEdit)):
            # Insert newline
            cursor = self.current_widget.textCursor()
            cursor.insertText("\n")
            self.current_widget.setTextCursor(cursor)

        logger.debug("Enter pressed")

    def _on_dismiss_pressed(self):
        """Handle dismiss button press."""
        self.hide_keyboard()
        logger.debug("Keyboard dismissed")

    def _ensure_keyboard_visible(self):
        """Ensure the keyboard is visible and on top."""
        if self.keyboard and hasattr(self.keyboard, 'isVisible'):
            if not self.keyboard.isVisible():
                logger.warning("Keyboard was not visible after show(), forcing show again")
                self.keyboard.show()
                self.keyboard.raise_()
            else:
                logger.info("Keyboard is visible")
                # Make sure it's on top
                self.keyboard.raise_()

    def setup_widget(self, widget):
        """Setup keyboard handling for a widget by installing event filter.

        Args:
            widget: QLineEdit, QTextEdit, QSpinBox, or QComboBox widget
        """
        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
            try:
                # Install the event filter on the widget
                widget.installEventFilter(self.event_filter)
                logger.info("INSTALLED keyboard event filter on %s (object: %s)", type(widget).__name__, str(widget))
            except Exception as e:
                logger.warning("Failed to install keyboard event filter on %s: %s", type(widget).__name__, e)



