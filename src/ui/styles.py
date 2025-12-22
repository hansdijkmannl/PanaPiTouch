"""
Application styles and theming for PanaPiTouch

Canon RC-IP100 inspired dark theme with orange/blue accents.
Optimized for touchscreen use and broadcast monitoring.
"""

# Color palette - Dark Teal/Amber theme
COLORS = {
    # Backgrounds - Dark tones
    'background': '#17191C',        # Primary background
    'surface': '#1A1D21',           # Secondary background
    'panel_bg': '#1E2126',          # Panel background
    'preview_bg': '#0C0D0F',        # Preview background
    'surface_light': '#262A32',     # Elevated surfaces
    'surface_hover': '#2e2e3a',     # Hover state
    'surface_active': '#363644',    # Active/pressed state

    # Borders
    'border': '#2B2F36',            # Default border
    'border_light': '#3D4450',      # Light border
    'border_focus': '#D9A042',      # Focus border (amber)

    # Primary - Teal accent
    'primary': '#20C7C7',           # Teal accent - active states
    'primary_dark': '#17A5A5',      # Darker teal for pressed
    'primary_light': '#2DD4D4',     # Lighter teal for hover
    'primary_glow': 'rgba(32, 199, 199, 0.3)',  # Teal glow effect

    # Secondary - Amber accent
    'secondary': '#D9A042',         # Amber accent - focus/selection
    'secondary_dark': '#B8860B',    # Darker amber
    'secondary_light': '#E6B85C',   # Lighter amber
    'secondary_glow': 'rgba(217, 160, 66, 0.3)',  # Amber glow effect

    # Text
    'text': '#E9E9E9',              # Primary text
    'text_dim': '#B9BCC1',          # Secondary text
    'text_dark': '#555568',         # Disabled text
    'text_info': '#2DD4D4',         # Info text (teal)

    # Tally indicators (broadcast standard)
    'tally_program': '#ff3333',     # Red - On Air
    'tally_preview': '#33cc33',     # Green - Preview
    'tally_off': '#3D4450',         # Off state

    # Status colors
    'success': '#22c55e',           # Green
    'warning': '#D9A042',           # Amber
    'error': '#ef4444',             # Red
    'info': '#20C7C7',              # Teal

    # Button states
    'button_active': '#20C7C7',     # Teal active
    'button_inactive': '#1A1D21',   # Inactive background
    'button_disabled': '#2B2F36',   # Disabled state
}

# Main application stylesheet
STYLESHEET = f"""
/* ============================================
   GLOBAL STYLES - Dark Teal/Amber Theme
   ============================================ */

QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Inter', 'Roboto', 'Arial', sans-serif;
    font-size: 14px;
    letter-spacing: 0.5px;
}}

QMainWindow {{
    background-color: {COLORS['background']};
}}

QStackedWidget {{
    background-color: {COLORS['background']};
}}

/* ============================================
   BUTTONS - Dark fill with light stroke
   ============================================ */

QPushButton {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 0px;
    margin: 0px;
    font-size: 15px;
    font-weight: 500;
    min-height: 48px;
}}

QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['border']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:checked {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
   NAVIGATION BUTTONS - Theme tabs
   ============================================ */

QPushButton#navButton {{
    background-color: {COLORS['surface']};
    border-radius: 0px;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 0px;
    margin: 0px;
    font-size: 14px;
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
    background-color: {COLORS['panel_bg']};
    border-bottom: 3px solid {COLORS['primary']};
    color: {COLORS['primary']};
}}

/* ============================================
   CAMERA BUTTONS - Tally-aware with theme colors
   ============================================ */

QPushButton#cameraButton {{
    background-color: transparent;
    border: 3px solid {COLORS['tally_off']};
    border-radius: 12px;
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
    color: {COLORS['background']};
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
    background-color: {COLORS['surface_light']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 0px;
    margin: 0px;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
    color: {COLORS['text']};
}}

QPushButton#overlayButton:hover {{
    border-color: {COLORS['border']};
}}

QPushButton#overlayButton:checked {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton#overlayButton:focus {{
    border: 2.5px solid {COLORS['secondary']};
}}

/* ============================================
   PRESET BUTTONS - Theme grid
   ============================================ */

QPushButton#presetButton {{
    background-color: {COLORS['surface_light']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 4px;
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QPushButton#presetButton:hover {{
    border-color: {COLORS['border']};
    background-color: {COLORS['surface_hover']};
}}

QPushButton#presetButton:pressed {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton#presetButton:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
    background-color: {COLORS['preview_bg']};
    border: 4px solid {COLORS['border']};
    border-radius: 12px;
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 12px 16px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QLineEdit:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 8px 12px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QSpinBox:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    padding: 12px 16px;
    color: {COLORS['text']};
    font-size: 14px;
    min-height: 44px;
}}

QComboBox:focus {{
    border: 2.5px solid {COLORS['secondary']};
}}

QComboBox:hover {{
    border-color: {COLORS['border']};
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
   SLIDERS - Theme style with teal accent
   ============================================ */

QSlider::groove:horizontal {{
    background: {COLORS['surface_light']};
    height: 8px;
    border-radius: 6px;
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

QSlider::handle:horizontal:focus {{
    border: 2px solid {COLORS['secondary']};
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['primary']};
    border-radius: 6px;
}}

QSlider::add-page:horizontal {{
    background: {COLORS['surface_light']};
    border-radius: 6px;
}}

/* Vertical Slider */
QSlider::groove:vertical {{
    background: {COLORS['surface_light']};
    width: 8px;
    border-radius: 6px;
}}

QSlider::handle:vertical {{
    background: {COLORS['primary']};
    width: 20px;
    height: 20px;
    margin: 0 -6px;
    border-radius: 10px;
}}

QSlider::handle:vertical:focus {{
    border: 2px solid {COLORS['secondary']};
}}

/* ============================================
   PROGRESS BAR
   ============================================ */

QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    text-align: center;
    color: {COLORS['text']};
    font-size: 12px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 10px;
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 15px;
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 12px;
    background-color: {COLORS['panel_bg']};
}}

QTabBar::tab {{
    background-color: {COLORS['surface']};
    border: 1.5px solid {COLORS['border_light']};
    border-bottom: none;
    border-radius: 12px 12px 0 0;
    padding: 12px 24px;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
    border: 2.5px solid {COLORS['primary']};
}}

QTabBar::tab:focus {{
    border: 2.5px solid {COLORS['secondary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_hover']};
}}

/* ============================================
   RADIO BUTTONS - Theme style
   ============================================ */

QRadioButton {{
    color: {COLORS['text']};
    font-size: 14px;
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 10px;
    background-color: {COLORS['surface']};
}}

QRadioButton::indicator:hover {{
    border-color: {COLORS['border']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
}}

QRadioButton::indicator:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 6px;
    background-color: {COLORS['surface']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['border']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border: 2.5px solid {COLORS['primary']};
}}

QCheckBox::indicator:focus {{
    border: 2.5px solid {COLORS['secondary']};
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
    background-color: {COLORS['panel_bg']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 15px;
}}

QFrame#headerFrame {{
    background-color: {COLORS['panel_bg']};
    border-bottom: 1.5px solid {COLORS['border_light']};
}}

QFrame#controlPanel {{
    background-color: {COLORS['panel_bg']};
    border: 1.5px solid {COLORS['border_light']};
    border-radius: 15px;
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
    """Get style for active/selected buttons with theme colors"""
    return f"""
        QPushButton {{
            background-color: {COLORS['primary']};
            border: 2.5px solid {COLORS['primary']};
            color: {COLORS['background']};
            font-weight: 600;
        }}
    """


def get_info_button_style() -> str:
    """Get style for info/secondary buttons (amber accent)"""
    return f"""
        QPushButton {{
            background-color: {COLORS['surface_light']};
            border: 1.5px solid {COLORS['border_light']};
            color: {COLORS['text']};
        }}
        QPushButton:hover {{
            border-color: {COLORS['border']};
        }}
        QPushButton:focus {{
            border: 2.5px solid {COLORS['secondary']};
        }}
    """


def get_section_header_style() -> str:
    """Get style for section header labels (theme style)"""
    return f"""
        QLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {COLORS['text']};
            background-color: {COLORS['panel_bg']};
            border: 1.5px solid {COLORS['border_light']};
            padding: 6px 10px;
            border-radius: 12px;
        }}
    """


def get_control_slider_style() -> str:
    """Get style for control panel sliders"""
    return f"""
        QSlider::groove:horizontal {{
            background: {COLORS['surface_light']};
            height: 8px;
            border-radius: 6px;
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
        QSlider::handle:horizontal:focus {{
            border: 2px solid {COLORS['secondary']};
        }}
        QSlider::sub-page:horizontal {{
            background: {COLORS['primary']};
            border-radius: 6px;
        }}
    """
