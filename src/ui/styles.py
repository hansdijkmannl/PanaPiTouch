"""
Application styles and theming for PanaPiTouch

Modern dark theme optimized for touchscreen use and broadcast monitoring.
"""

# Color palette - Broadcast monitor inspired dark theme
COLORS = {
    'background': '#0a0a0f',
    'surface': '#12121a',
    'surface_light': '#1a1a24',
    'surface_hover': '#22222e',
    'border': '#2a2a38',
    'border_light': '#3a3a4a',
    
    'primary': '#00b4d8',      # Cyan accent
    'primary_dark': '#0090ad',
    'secondary': '#7b68ee',    # Purple accent
    
    'text': '#e8e8f0',
    'text_dim': '#888898',
    'text_dark': '#555566',
    
    'tally_program': '#ff3333',  # Red - On Air
    'tally_preview': '#33cc33',  # Green - Preview
    'tally_off': '#333340',
    
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    
    'button_active': '#00b4d8',
    'button_inactive': '#1a1a24',
}

# Main application stylesheet
STYLESHEET = f"""
/* Global */
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

/* Page Container */
QStackedWidget {{
    background-color: {COLORS['background']};
}}

/* Buttons - Large touch-friendly */
QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 15px;
    font-weight: 500;
    min-height: 48px;
}}

QPushButton:pressed {{
    background-color: {COLORS['primary_dark']};
    border-color: {COLORS['primary']};
}}

QPushButton:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_dark']};
    border-color: {COLORS['border']};
}}

/* Navigation Buttons */
QPushButton#navButton {{
    background-color: {COLORS['surface']};
    border-radius: 0px;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 16px 32px;
    font-size: 16px;
    font-weight: 600;
}}

QPushButton#navButton:checked {{
    background-color: {COLORS['surface_light']};
    border-bottom: 3px solid {COLORS['primary']};
    color: {COLORS['primary']};
}}

/* Camera Buttons */
QPushButton#cameraButton {{
    background-color: transparent;
    border: 3px solid {COLORS['tally_off']};
    border-radius: 10px;
    padding: 4px;
    font-size: 12px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QPushButton#cameraButton:checked {{
    background-color: #FF9500;
    border-color: {COLORS['tally_off']};
    color: white;
}}

QPushButton#cameraButton:checked[tallyState="program"] {{
    background-color: #FF9500;
    border-color: {COLORS['tally_program']};
    color: white;
}}

QPushButton#cameraButton:checked[tallyState="preview"] {{
    background-color: #FF9500;
    border-color: {COLORS['tally_preview']};
    color: white;
}}

QPushButton#cameraButton[tallyState="program"] {{
    border-color: {COLORS['tally_program']};
    background-color: transparent;
}}

QPushButton#cameraButton[tallyState="preview"] {{
    border-color: {COLORS['tally_preview']};
    background-color: transparent;
}}

/* Overlay Toggle Buttons */
QPushButton#overlayButton {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 8px;
    padding: 4px 16px;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
    color: {COLORS['text']};
}}

QPushButton#overlayButton:checked {{
    background-color: {COLORS['surface']};
    color: #FF9500;
}}

/* Preview Frame */
QFrame#previewFrame {{
    background-color: {COLORS['surface']};
    border: 4px solid {COLORS['border']};
    border-radius: 4px;
}}

QFrame#previewFrame[tallyState="program"] {{
    border-color: {COLORS['tally_program']};
}}

QFrame#previewFrame[tallyState="preview"] {{
    border-color: {COLORS['tally_preview']};
}}

/* Labels */
QLabel {{
    color: {COLORS['text']};
    background-color: transparent;
}}

QLabel#titleLabel {{
    font-size: 24px;
    font-weight: 700;
    color: {COLORS['text']};
}}

QLabel#subtitleLabel {{
    font-size: 14px;
    color: {COLORS['text_dim']};
}}

QLabel#statusLabel {{
    font-size: 10px;
    padding: 4px 8px;
    border-radius: 4px;
}}

QLabel#statusLabel[status="connected"] {{
    background-color: rgba(34, 197, 94, 0.2);
    color: {COLORS['success']};
}}

QLabel#statusLabel[status="disconnected"] {{
    background-color: rgba(239, 68, 68, 0.2);
    color: {COLORS['error']};
}}

/* Input Fields */
QLineEdit {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 6px;
    padding: 12px 16px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QLineEdit:focus {{
    border-color: {COLORS['primary']};
}}

QLineEdit:disabled {{
    background-color: {COLORS['background']};
    color: {COLORS['text_dark']};
}}

/* Spin Box */
QSpinBox {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QSpinBox:focus {{
    border-color: {COLORS['primary']};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 30px;
    background-color: {COLORS['surface_light']};
    border: none;
}}

/* Combo Box */
QComboBox {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 6px;
    padding: 12px 16px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QComboBox:focus {{
    border-color: {COLORS['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 40px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
}}

/* Scroll Area */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLORS['surface']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border_light']};
    border-radius: 6px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['primary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Group Box */
QGroupBox {{
    font-size: 16px;
    font-weight: 600;
    color: {COLORS['text']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: {COLORS['background']};
}}

/* List Widget */
QListWidget {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
    outline: none;
}}

QListWidget::item {{
    background-color: transparent;
    border-radius: 6px;
    padding: 12px;
    margin: 4px 0;
}}

QListWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QListWidget::item:hover {{
    background-color: {COLORS['surface_hover']};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['surface']};
}}

QTabBar::tab {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 12px 24px;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_hover']};
}}

/* Web View */
QWebEngineView {{
    background-color: {COLORS['background']};
}}

/* Message Box */
QMessageBox {{
    background-color: {COLORS['surface']};
}}

QMessageBox QPushButton {{
    min-width: 100px;
}}

/* Tool Tip */
QToolTip {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px;
}}
"""

# Additional styles for specific widgets
def get_tally_border_style(state: str) -> str:
    """Get border style for tally state"""
    if state == 'program':
        return f"border: 4px solid {COLORS['tally_program']};"
    elif state == 'preview':
        return f"border: 4px solid {COLORS['tally_preview']};"
    return f"border: 4px solid {COLORS['border']};"

