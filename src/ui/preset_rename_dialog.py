"""
Preset Rename Dialog with On-Screen Keyboard

Dialog for renaming presets on the Live/Preview page with OSK sliding from top.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent

from .osk_widget import OSKWidget
from .styles import COLORS


class PresetRenameDialog(QDialog):
    """Dialog for renaming presets with embedded OSK"""
    
    accepted = pyqtSignal(str)  # Emitted when OK is clicked with the new name
    
    def __init__(self, preset_num: int, current_name: str = "", parent=None):
        super().__init__(parent)
        self.preset_num = preset_num
        self.setWindowTitle(f"Rename Preset {preset_num}")
        self.setModal(True)
        
        # Setup UI
        self._setup_ui(current_name)
        
        # Create OSK (slides from top) - parent to dialog
        # Get preset texts from parent's settings if available, otherwise use empty
        preset_texts = ["", "", "", "", "", ""]
        try:
            if parent and hasattr(parent, 'settings'):
                preset_texts = getattr(parent.settings, 'osk_presets', ["", "", "", "", "", ""])
                if not isinstance(preset_texts, list) or len(preset_texts) != 6:
                    preset_texts = ["", "", "", "", "", ""]
        except (AttributeError, TypeError):
            preset_texts = ["", "", "", "", "", ""]
        self.osk = OSKWidget(self, slide_from_top=True, preset_texts=preset_texts)
        self.osk.key_pressed.connect(self._on_osk_key)
        self.osk.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Allow mouse events
        
        # Show OSK when dialog opens
        QTimer.singleShot(200, self._show_osk)
    
    def _setup_ui(self, current_name: str):
        """Setup dialog UI"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: 600;
                padding: 12px;
            }}
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
                color: {COLORS['text']};
                font-size: 20px;
                min-height: 60px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 16px;
                font-weight: 600;
                padding: 12px 24px;
                min-height: 50px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Title
        title = QLabel(f"Rename Preset {self.preset_num}")
        layout.addWidget(title)
        
        # Input field
        self.name_input = QLineEdit()
        self.name_input.setText(current_name)
        self.name_input.selectAll()
        self.name_input.setFocus()
        layout.addWidget(self.name_input)
        
        # Connect input focus to show OSK
        original_focus_in = self.name_input.focusInEvent
        def focus_in_with_osk(event):
            original_focus_in(event)
            QTimer.singleShot(50, self._show_osk)
        self.name_input.focusInEvent = focus_in_with_osk
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        ok_btn.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Add stretch to push content up (OSK will be at bottom)
        layout.addStretch()
    
    def _show_osk(self):
        """Show OSK"""
        if self.osk:
            self.osk.show_keyboard(self.name_input)
    
    def resizeEvent(self, event):
        """Handle dialog resize - update OSK position"""
        super().resizeEvent(event)
        if self.osk and self.osk._is_visible:
            # Reposition OSK
            keyboard_height = self.osk.height()
            self.osk.setGeometry(0, 0, self.width(), keyboard_height)
    
    def _on_osk_key(self, key: str):
        """Handle OSK key press"""
        # OSK already sends events to the input field, this is just for logging
        pass
    
    def _on_ok_clicked(self):
        """Handle OK button click"""
        name = self.name_input.text().strip()
        if name:
            self.accepted.emit(name)
            self.accept()
        else:
            self.reject()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._on_ok_clicked()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle dialog close"""
        self.osk.hide_keyboard()
        super().closeEvent(event)










