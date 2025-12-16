"""
Application styles and theming for PanaPiTouch

Canon RC-IP100 inspired dark theme with orange/blue accents.
Optimized for touchscreen use and broadcast monitoring.
"""

# Color palette - Canon RC-IP100 inspired dark theme
COLORS = {
    # Backgrounds - Charcoal tones (Canon-style)
    'background': '#121218',        # Main background (charcoal)
    'surface': '#1a1a22',           # Card/panel background
    'surface_light': '#242430',     # Elevated surfaces
    'surface_hover': '#2e2e3a',     # Hover state
    'surface_active': '#363644',    # Active/pressed state
    
    # Borders
    'border': '#2a2a38',            # Default border
    'border_light': '#3a3a4a',      # Light border
    'border_focus': '#FF9500',      # Focus border (orange)
    
    # Primary - Orange (Canon RC-IP100 style)
    'primary': '#FF9500',           # Orange accent - active states
    'primary_dark': '#CC7700',      # Darker orange for pressed
    'primary_light': '#FFAA33',     # Lighter orange for hover
    'primary_glow': 'rgba(255, 149, 0, 0.3)',  # Orange glow effect
    
    # Secondary - Blue (Canon RC-IP100 style)
    'secondary': '#3498db',         # Blue accent - info/selection
    'secondary_dark': '#2980b9',    # Darker blue
    'secondary_light': '#5dade2',   # Lighter blue
    'secondary_glow': 'rgba(52, 152, 219, 0.3)',  # Blue glow effect
    
    # Text
    'text': '#e8e8f0',              # Primary text (white)
    'text_dim': '#8888a0',          # Secondary text (gray)
    'text_dark': '#555568',         # Disabled text
    'text_info': '#5dade2',         # Info text (blue)
    
    # Tally indicators (broadcast standard)
    'tally_program': '#ff3333',     # Red - On Air
    'tally_preview': '#33cc33',     # Green - Preview  
    'tally_off': '#3a3a48',         # Off state
    
    # Status colors
    'success': '#22c55e',           # Green
    'warning': '#f59e0b',           # Amber
    'error': '#ef4444',             # Red
    'info': '#3498db',              # Blue
    
    # Button states
    'button_active': '#FF9500',     # Orange active
    'button_inactive': '#1a1a22',   # Inactive background
    'button_disabled': '#2a2a38',   # Disabled state
}

# Main application stylesheet
STYLESHEET = f"""
/* ============================================
   GLOBAL STYLES - Canon RC-IP100 Inspired
   ============================================ */

QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

QStackedWidget {{
    background-color: {COLORS['background']};
}}

/* ============================================
   BUTTONS - Touch-friendly with glow effects
   ============================================ */

QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 0px;
    margin: 0px;
    font-size: 15px;
    font-weight: 500;
    min-height: 48px;
}}

QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:disabled {{
    background-color: {COLORS['button_disabled']};
    color: {COLORS['text_dark']};
    border-color: {COLORS['border']};
}}

/* Active Button with Glow Effect */
QPushButton#activeGlow {{
    background-color: {COLORS['primary']};
    border: 2px solid {COLORS['primary']};
    color: {COLORS['background']};
}}

/* Info/Selection Button (Blue) */
QPushButton#infoButton {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['secondary']};
    color: {COLORS['secondary']};
}}

QPushButton#infoButton:hover {{
    background-color: {COLORS['secondary']};
    color: {COLORS['background']};
}}

QPushButton#infoButton:checked {{
    background-color: {COLORS['secondary']};
    border-color: {COLORS['secondary']};
    color: {COLORS['background']};
}}

/* ============================================
   NAVIGATION BUTTONS - Canon-style tabs
   ============================================ */

QPushButton#navButton {{
    background-color: {COLORS['surface']};
    border-radius: 0px;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 0px;
    margin: 0px;
    font-size: 16px;
    font-weight: 600;
}}

QPushButton#navButton:hover {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['text']};
}}

QPushButton#navButton:pressed {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton#navButton:checked {{
    background-color: {COLORS['surface_light']};
    border-bottom: 3px solid {COLORS['primary']};
    color: {COLORS['primary']};
}}

/* ============================================
   CAMERA BUTTONS - Tally-aware with glow
   ============================================ */

QPushButton#cameraButton {{
    background-color: transparent;
    border: 3px solid {COLORS['tally_off']};
    border-radius: 10px;
    padding: 0px;
    margin: 0px;
    font-size: 12px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QPushButton#cameraButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton#cameraButton:pressed {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

QPushButton#cameraButton:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['tally_off']};
    color: white;
}}

/* Camera Button - Tally States */
QPushButton#cameraButton:checked[tallyState="program"] {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['tally_program']};
    color: white;
}}

QPushButton#cameraButton:checked[tallyState="preview"] {{
    background-color: {COLORS['primary']};
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

/* ============================================
   OVERLAY TOGGLE BUTTONS
   ============================================ */

QPushButton#overlayButton {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 0px;
    margin: 0px;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
    color: {COLORS['text']};
}}

QPushButton#overlayButton:hover {{
    border-color: {COLORS['primary']};
}}

QPushButton#overlayButton:checked {{
    background-color: {COLORS['surface_light']};
    border-color: {COLORS['primary']};
    color: {COLORS['primary']};
}}

/* ============================================
   PRESET BUTTONS - Canon-style grid
   ============================================ */

QPushButton#presetButton {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QPushButton#presetButton:hover {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['surface_hover']};
}}

QPushButton#presetButton:pressed {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton#presetButton[hasPreset="true"] {{
    border-color: {COLORS['secondary']};
}}

QPushButton#presetButton[hasPreset="true"]:hover {{
    border-color: {COLORS['primary']};
}}

/* ============================================
   PREVIEW FRAME - Tally borders
   ============================================ */

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

/* ============================================
   LABELS
   ============================================ */

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

QLabel#infoLabel {{
    font-size: 12px;
    color: {COLORS['text_info']};
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

QLabel#statusLabel[status="info"] {{
    background-color: rgba(52, 152, 219, 0.2);
    color: {COLORS['info']};
}}

/* Section Header Labels */
QLabel#sectionHeader {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS['text']};
    background-color: {COLORS['surface_light']};
    border: 2px solid {COLORS['border_light']};
    padding: 6px 10px;
    border-radius: 4px;
}}

/* ============================================
   INPUT FIELDS
   ============================================ */

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

/* ============================================
   SPIN BOX
   ============================================ */

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

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS['surface_hover']};
}}

/* ============================================
   COMBO BOX
   ============================================ */

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

QComboBox:hover {{
    border-color: {COLORS['border_light']};
}}

QComboBox::drop-down {{
    border: none;
    width: 40px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']} !important;
    border: 2px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    color: {COLORS['text']};
    padding: 4px;
    font-size: 16px;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    background-color: {COLORS['surface']} !important;
    min-height: 56px;
    padding: 16px 20px;
    border-radius: 4px;
    color: {COLORS['text']} !important;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {COLORS['surface_hover']} !important;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {COLORS['primary']} !important;
    color: {COLORS['background']} !important;
}}

/* ============================================
   SLIDERS - Canon-style with orange accent
   ============================================ */

QSlider::groove:horizontal {{
    background: {COLORS['surface_light']};
    height: 8px;
    border-radius: 4px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['primary']};
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['primary_light']};
}}

QSlider::handle:horizontal:pressed {{
    background: {COLORS['primary_dark']};
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['primary']};
    border-radius: 4px;
}}

QSlider::add-page:horizontal {{
    background: {COLORS['surface_light']};
    border-radius: 4px;
}}

/* Vertical Slider */
QSlider::groove:vertical {{
    background: {COLORS['surface_light']};
    width: 8px;
    border-radius: 4px;
}}

QSlider::handle:vertical {{
    background: {COLORS['primary']};
    width: 20px;
    height: 20px;
    margin: 0 -6px;
    border-radius: 10px;
}}

/* ============================================
   PROGRESS BAR
   ============================================ */

QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text']};
    font-size: 12px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

/* ============================================
   SCROLL AREA
   ============================================ */

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

QScrollBar:horizontal {{
    background-color: {COLORS['surface']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border_light']};
    border-radius: 6px;
    min-width: 40px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['primary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ============================================
   GROUP BOX
   ============================================ */

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

/* ============================================
   LIST WIDGET
   ============================================ */

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

/* ============================================
   TAB WIDGET
   ============================================ */

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

/* ============================================
   RADIO BUTTONS - Canon-style
   ============================================ */

QRadioButton {{
    color: {COLORS['text']};
    font-size: 14px;
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    background-color: {COLORS['surface']};
}}

QRadioButton::indicator:hover {{
    border-color: {COLORS['primary']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

/* ============================================
   CHECK BOX
   ============================================ */

QCheckBox {{
    color: {COLORS['text']};
    font-size: 14px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['surface']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

/* ============================================
   WEB VIEW
   ============================================ */

QWebEngineView {{
    background-color: {COLORS['background']};
}}

/* ============================================
   MESSAGE BOX
   ============================================ */

QMessageBox {{
    background-color: {COLORS['surface']};
}}

QMessageBox QPushButton {{
    min-width: 100px;
}}

/* ============================================
   TOOL TIP
   ============================================ */

QToolTip {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px;
}}

/* ============================================
   FRAMES / PANELS
   ============================================ */

QFrame#panelFrame {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QFrame#headerFrame {{
    background-color: {COLORS['surface_light']};
    border-bottom: 1px solid {COLORS['border']};
}}

QFrame#controlPanel {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
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


def get_active_button_style() -> str:
    """Get style for active/selected buttons with glow effect"""
    return f"""
        QPushButton {{
            background-color: {COLORS['primary']};
            border: 2px solid {COLORS['primary']};
            color: {COLORS['background']};
            font-weight: 600;
        }}
    """


def get_info_button_style() -> str:
    """Get style for info/secondary buttons (blue accent)"""
    return f"""
        QPushButton {{
            background-color: {COLORS['surface']};
            border: 2px solid {COLORS['secondary']};
            color: {COLORS['secondary']};
        }}
        QPushButton:hover {{
            background-color: {COLORS['secondary']};
            color: {COLORS['background']};
        }}
    """


def get_section_header_style() -> str:
    """Get style for section header labels (Canon-style)"""
    return f"""
        QLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {COLORS['text']};
            background-color: {COLORS['surface_light']};
            border: 2px solid {COLORS['border_light']};
            padding: 6px 10px;
            border-radius: 4px;
        }}
    """


def get_control_slider_style() -> str:
    """Get style for control panel sliders"""
    return f"""
        QSlider::groove:horizontal {{
            background: {COLORS['surface_light']};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {COLORS['primary']};
            width: 24px;
            height: 24px;
            margin: -8px 0;
            border-radius: 12px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {COLORS['primary_light']};
        }}
        QSlider::sub-page:horizontal {{
            background: {COLORS['primary']};
            border-radius: 4px;
        }}
    """
