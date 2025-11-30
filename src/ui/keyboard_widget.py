"""
On-Screen Keyboard Widget

Touchscreen-friendly keyboard and numpad for text input.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from .styles import COLORS


class NumpadWidget(QWidget):
    """Numeric keypad for IP addresses and numbers"""
    
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    enter_pressed = pyqtSignal()
    close_pressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the numpad UI - dark theme, full width"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Keypad grid - centered with stretches
        grid_wrapper = QHBoxLayout()
        grid_wrapper.addStretch()
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Number buttons
        numbers = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('.', 3, 0), ('0', 3, 1),
        ]
        
        for text, row, col in numbers:
            btn = self._create_key_button(text)
            btn.clicked.connect(lambda checked, t=text: self.key_pressed.emit(t))
            grid.addWidget(btn, row, col)
        
        grid_wrapper.addLayout(grid)
        grid_wrapper.addStretch()
        
        # Control buttons row - full width with spacing
        control_row = QHBoxLayout()
        control_row.setSpacing(10)
        control_row.addStretch()
        
        backspace_btn = self._create_key_button("⌫", large=True)
        backspace_btn.clicked.connect(self.backspace_pressed.emit)
        control_row.addWidget(backspace_btn)
        
        enter_btn = self._create_key_button("Done", large=True)
        enter_btn.clicked.connect(self.enter_pressed.emit)
        control_row.addWidget(enter_btn)
        
        close_btn = self._create_key_button("Hide", large=True)
        close_btn.clicked.connect(self.close_pressed.emit)
        control_row.addWidget(close_btn)
        
        control_row.addStretch()
        
        layout.addLayout(grid_wrapper)
        layout.addLayout(control_row)
    
    def _create_key_button(self, text, large=False):
        """Create a key button - dark theme"""
        btn = QPushButton(text)
        if large:
            btn.setFixedSize(120, 55)
        else:
            btn.setFixedSize(90, 55)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                color: {COLORS['text']};
                font-size: 22px;
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background-color: #FF9500;
                border-color: #FF9500;
                color: white;
            }}
        """)
        return btn


class KeyboardWidget(QWidget):
    """Full on-screen keyboard"""
    
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    space_pressed = pyqtSignal()
    enter_pressed = pyqtSignal()
    shift_pressed = pyqtSignal()
    close_pressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._shift_active = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the keyboard UI - dark theme, full width"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Row 1: Numbers
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addStretch()
        for char in '1234567890':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row1.addWidget(btn)
        row1.addStretch()
        layout.addLayout(row1)
        
        # Row 2: Q-P
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addStretch()
        for char in 'qwertyuiop':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row2.addWidget(btn)
        row2.addStretch()
        layout.addLayout(row2)
        
        # Row 3: A-L
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        row3.addStretch()
        for char in 'asdfghjkl':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row3.addWidget(btn)
        row3.addStretch()
        layout.addLayout(row3)
        
        # Row 4: Z-M
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        row4.addStretch()
        
        shift_btn = self._create_key_button("⇧", large=True)
        shift_btn.setCheckable(True)
        shift_btn.clicked.connect(self._toggle_shift)
        row4.addWidget(shift_btn)
        
        for char in 'zxcvbnm':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row4.addWidget(btn)
        row4.addStretch()
        layout.addLayout(row4)
        
        # Row 5: Controls
        row5 = QHBoxLayout()
        row5.setSpacing(10)
        row5.addStretch()
        
        backspace_btn = self._create_key_button("⌫", large=True)
        backspace_btn.clicked.connect(self.backspace_pressed.emit)
        row5.addWidget(backspace_btn)
        
        space_btn = self._create_key_button("space", extra_large=True)
        space_btn.clicked.connect(self.space_pressed.emit)
        row5.addWidget(space_btn)
        
        enter_btn = self._create_key_button("return", large=True)
        enter_btn.clicked.connect(self.enter_pressed.emit)
        row5.addWidget(enter_btn)
        
        close_btn = self._create_key_button("Hide", large=True)
        close_btn.clicked.connect(self.close_pressed.emit)
        row5.addWidget(close_btn)
        
        row5.addStretch()
        layout.addLayout(row5)
    
    def _toggle_shift(self):
        """Toggle shift state"""
        self._shift_active = not self._shift_active
        # Update button states if needed
    
    def _create_key_button(self, text, large=False, extra_large=False):
        """Create a key button - dark theme"""
        btn = QPushButton(text)
        if extra_large:
            btn.setFixedSize(400, 55)
        elif large:
            btn.setFixedSize(100, 55)
        else:
            btn.setFixedSize(70, 55)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background-color: #FF9500;
                border-color: #FF9500;
                color: white;
            }}
            QPushButton:checked {{
                background-color: #FF9500;
                border-color: #FF9500;
                color: white;
            }}
        """)
        return btn
    
    def get_char(self, char):
        """Get character with shift applied"""
        if self._shift_active:
            return char.upper()
        return char.lower()

