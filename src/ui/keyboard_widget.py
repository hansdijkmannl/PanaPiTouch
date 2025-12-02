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
    """Full on-screen keyboard with iOS-style text and numbers layouts"""
    
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    space_pressed = pyqtSignal()
    enter_pressed = pyqtSignal()
    shift_pressed = pyqtSignal()
    close_pressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._shift_active = False
        self._numbers_mode = False  # False = letters, True = numbers/symbols
        self.layout_toggle_btn_letters = None
        self.layout_toggle_btn_numbers = None
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
        
        # Create container widgets for letters and numbers layouts
        self.letters_container = QWidget()
        self.letters_container.setStyleSheet("background: transparent;")
        self.letters_layout = QVBoxLayout(self.letters_container)
        self.letters_layout.setContentsMargins(0, 0, 0, 0)
        self.letters_layout.setSpacing(10)
        
        self.numbers_container = QWidget()
        self.numbers_container.setStyleSheet("background: transparent;")
        self.numbers_container.setVisible(False)  # Hidden by default
        self.numbers_layout = QVBoxLayout(self.numbers_container)
        self.numbers_layout.setContentsMargins(0, 0, 0, 0)
        self.numbers_layout.setSpacing(10)
        
        # Build letters layout
        self._build_letters_layout()
        
        # Build numbers/symbols layout
        self._build_numbers_layout()
        
        # Add both containers to main layout
        layout.addWidget(self.letters_container)
        layout.addWidget(self.numbers_container)
    
    def _build_letters_layout(self):
        """Build the letters (QWERTY) keyboard layout"""
        # Row 1: Q-P
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addStretch()
        for char in 'qwertyuiop':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row1.addWidget(btn)
        row1.addStretch()
        self.letters_layout.addLayout(row1)
        
        # Row 2: A-L
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addStretch()
        for char in 'asdfghjkl':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row2.addWidget(btn)
        row2.addStretch()
        self.letters_layout.addLayout(row2)
        
        # Row 3: Z-M + Shift
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addStretch()
        
        shift_btn = self._create_key_button("⇧", large=True)
        shift_btn.setCheckable(True)
        shift_btn.clicked.connect(self._toggle_shift)
        self.shift_button = shift_btn
        row3.addWidget(shift_btn)
        
        for char in 'zxcvbnm':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row3.addWidget(btn)
        row3.addStretch()
        self.letters_layout.addLayout(row3)
        
        # Row 4: Controls (shared with numbers layout)
        self._add_control_row(self.letters_layout)
    
    def _build_numbers_layout(self):
        """Build the numbers/symbols keyboard layout (iOS-style)"""
        # Row 1: Numbers
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addStretch()
        for char in '1234567890':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row1.addWidget(btn)
        row1.addStretch()
        self.numbers_layout.addLayout(row1)
        
        # Row 2: Common symbols
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addStretch()
        for char in '-/:.()':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row2.addWidget(btn)
        row2.addStretch()
        self.numbers_layout.addLayout(row2)
        
        # Row 3: More symbols
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addStretch()
        for char in '@#$%&*':
            btn = self._create_key_button(char)
            btn.clicked.connect(lambda checked, c=char: self.key_pressed.emit(c))
            row3.addWidget(btn)
        row3.addStretch()
        self.numbers_layout.addLayout(row3)
        
        # Row 4: Controls
        self._add_control_row(self.numbers_layout, is_numbers_layout=True)
    
    def _add_control_row(self, parent_layout, is_numbers_layout=False):
        """Add control buttons row (backspace, space, enter, hide, layout toggle)"""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        
        backspace_btn = self._create_key_button("⌫", large=True)
        backspace_btn.clicked.connect(self.backspace_pressed.emit)
        row.addWidget(backspace_btn)
        
        space_btn = self._create_key_button("space", extra_large=True)
        space_btn.clicked.connect(self.space_pressed.emit)
        row.addWidget(space_btn)
        
        # Layout toggle button (123/ABC) - create separate buttons for each layout
        if is_numbers_layout:
            self.layout_toggle_btn_numbers = self._create_key_button("ABC", large=True)
            self.layout_toggle_btn_numbers.clicked.connect(self._toggle_layout)
            row.addWidget(self.layout_toggle_btn_numbers)
        else:
            self.layout_toggle_btn_letters = self._create_key_button("123", large=True)
            self.layout_toggle_btn_letters.clicked.connect(self._toggle_layout)
            row.addWidget(self.layout_toggle_btn_letters)
        
        enter_btn = self._create_key_button("return", large=True)
        enter_btn.clicked.connect(self.enter_pressed.emit)
        row.addWidget(enter_btn)
        
        close_btn = self._create_key_button("Hide", large=True)
        close_btn.clicked.connect(self.close_pressed.emit)
        row.addWidget(close_btn)
        
        row.addStretch()
        parent_layout.addLayout(row)
    
    def _toggle_layout(self):
        """Toggle between letters and numbers/symbols layout"""
        self._numbers_mode = not self._numbers_mode
        
        # Show/hide container widgets
        self.letters_container.setVisible(not self._numbers_mode)
        self.numbers_container.setVisible(self._numbers_mode)
        
        # Update toggle button texts
        if self._numbers_mode:
            if self.layout_toggle_btn_numbers:
                self.layout_toggle_btn_numbers.setText("ABC")
            if self.layout_toggle_btn_letters:
                self.layout_toggle_btn_letters.setText("ABC")
        else:
            if self.layout_toggle_btn_numbers:
                self.layout_toggle_btn_numbers.setText("123")
            if self.layout_toggle_btn_letters:
                self.layout_toggle_btn_letters.setText("123")
    
    def _toggle_shift(self):
        """Toggle shift state"""
        self._shift_active = not self._shift_active
        # Update shift button state
        if hasattr(self, 'shift_button'):
            self.shift_button.setChecked(self._shift_active)
    
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

