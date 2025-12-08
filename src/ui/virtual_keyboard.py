"""
Virtual Keyboard Widget

iOS/Android-style on-screen keyboard with smooth animations.
Full-width, slides up from bottom, hides when clicking outside.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt6.QtGui import QFont

from .styles import COLORS


class VirtualKeyboard(QWidget):
    """iOS/Android-style virtual keyboard"""
    
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    enter_pressed = pyqtSignal()
    hide_requested = pyqtSignal()
    
    def __init__(self, numpad_mode=False, parent=None):
        super().__init__(parent)
        self.numpad_mode = numpad_mode
        self._is_visible = False
        self._setup_ui()
        self._setup_animations()
        self.hide()  # Start hidden
    
    def _setup_ui(self):
        """Setup keyboard UI"""
        # Get screen width for full-width keyboard
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and app.primaryScreen():
            screen_width = app.primaryScreen().geometry().width()
        else:
            screen_width = 1920
        
        # Set as top-level window that stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        # Full width, appropriate height
        height = 240 if self.numpad_mode else 320
        self.setFixedSize(screen_width, height)
        
        # Style
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
            }}
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: 600;
                min-height: 60px;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_light']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        if self.numpad_mode:
            self._setup_numpad(layout)
        else:
            self._setup_keyboard(layout)
    
    def _setup_numpad(self, layout):
        """Setup numpad layout"""
        # Row 1: 7 8 9
        row1 = self._create_row(['7', '8', '9'], layout)
        
        # Row 2: 4 5 6
        row2 = self._create_row(['4', '5', '6'], layout)
        
        # Row 3: 1 2 3
        row3 = self._create_row(['1', '2', '3'], layout)
        
        # Row 4: . 0 ⌫
        row4 = QHBoxLayout()
        row4.setSpacing(8)
        self._add_button(row4, '.', '.')
        self._add_button(row4, '0', '0')
        self._add_button(row4, '⌫', 'backspace', flex=2)
        layout.addLayout(row4)
    
    def _setup_keyboard(self, layout):
        """Setup full QWERTY keyboard"""
        # Row 1: 1 2 3 4 5 6 7 8 9 0
        row1 = self._create_row(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'], layout)
        
        # Row 2: q w e r t y u i o p
        row2 = self._create_row(['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'], layout)
        
        # Row 3: a s d f g h j k l
        row3 = self._create_row(['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'], layout)
        
        # Row 4: z x c v b n m
        row4 = self._create_row(['z', 'x', 'c', 'v', 'b', 'n', 'm'], layout)
        
        # Row 5: Space ⌫ Enter
        row5 = QHBoxLayout()
        row5.setSpacing(8)
        self._add_button(row5, 'Space', ' ', flex=5)
        self._add_button(row5, '⌫', 'backspace', flex=2)
        self._add_button(row5, 'Enter', 'enter', flex=2)
        layout.addLayout(row5)
    
    def _create_row(self, keys, parent_layout):
        """Create a row of buttons"""
        row = QHBoxLayout()
        row.setSpacing(8)
        for key in keys:
            self._add_button(row, key.upper() if len(key) == 1 and key.isalpha() else key, key.lower() if key.isalpha() else key)
        parent_layout.addLayout(row)
        return row
    
    def _add_button(self, layout, label, value, flex=1):
        """Add a button to layout"""
        btn = QPushButton(label)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda checked=False, v=value: self._on_key_clicked(v))
        layout.addWidget(btn, flex)
        return btn
    
    def _on_key_clicked(self, value):
        """Handle key press"""
        if value == 'backspace':
            self.backspace_pressed.emit()
        elif value == 'enter':
            self.enter_pressed.emit()
        else:
            self.key_pressed.emit(value)
    
    def _setup_animations(self):
        """Setup slide animations"""
        self._show_animation = QPropertyAnimation(self, b"pos")
        self._show_animation.setDuration(250)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._hide_animation = QPropertyAnimation(self, b"pos")
        self._hide_animation.setDuration(200)
        self._hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._hide_animation.finished.connect(self._on_hide_animation_finished)
    
    def show_keyboard(self):
        """Show keyboard with slide-up animation"""
        if self._is_visible:
            return
        
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and app.primaryScreen():
            screen_geom = app.primaryScreen().geometry()
            x = screen_geom.x()
            y_hidden = screen_geom.y() + screen_geom.height()
            y_visible = screen_geom.y() + screen_geom.height() - self.height()
        else:
            x = 0
            y_hidden = 1080
            y_visible = 1080 - self.height()
        
        # Start position (below screen)
        self.move(x, y_hidden)
        self.show()
        self.raise_()
        self._is_visible = True
        
        # Animate slide up
        self._show_animation.setStartValue(QPoint(x, y_hidden))
        self._show_animation.setEndValue(QPoint(x, y_visible))
        self._show_animation.start()
    
    def hide_keyboard(self):
        """Hide keyboard with slide-down animation"""
        if not self._is_visible:
            return
        
        current_pos = self.pos()
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and app.primaryScreen():
            screen_geom = app.primaryScreen().geometry()
            y_hidden = screen_geom.y() + screen_geom.height()
        else:
            y_hidden = 1080
        
        # Animate slide down
        self._hide_animation.setStartValue(current_pos)
        self._hide_animation.setEndValue(QPoint(current_pos.x(), y_hidden))
        self._hide_animation.start()
    
    def _on_hide_animation_finished(self):
        """Called when hide animation completes"""
        self.hide()
        self._is_visible = False
    
    def is_keyboard_visible(self):
        """Check if keyboard is currently visible"""
        return self._is_visible
