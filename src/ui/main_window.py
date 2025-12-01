"""
Main Application Window

The main window with page navigation, camera preview, and controls.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizePolicy,
    QButtonGroup, QSpacerItem, QSlider, QScrollArea, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QFont

from ..config.settings import Settings
from ..camera.stream import CameraStream, StreamConfig
from ..camera.multiview import MultiviewManager, CameraInfo
from ..atem.tally import ATEMTallyController, TallyState
from .preview_widget import PreviewWidget
from .settings_page import SettingsPage
from .camera_page import CameraPage
from .companion_page import CompanionPage
from .joystick_widget import JoystickWidget
from .keyboard_manager import KeyboardManager
from .styles import STYLESHEET, COLORS


class MainWindow(QMainWindow):
    """
    Main application window for PanaPiTouch.
    
    Layout:
    - Top: Page navigation buttons
    - Center: Page content (Preview, Companion, Settings)
    - Bottom: Camera selection buttons (on preview page)
    """
    
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = Settings.load()
        
        # Camera streams
        self.camera_streams: dict = {}
        self.current_camera_id = None
        
        # Demo mode state
        self._demo_running = False
        self._demo_thread = None
        
        # Multiview manager
        self.multiview_manager = MultiviewManager(output_size=(1920, 1080))
        self.multiview_manager.set_frame_callback(self._on_multiview_frame)
        self._multiview_active = False
        
        # OSD state tracking
        self._osd_active = False
        
        # Split view state
        self._split_enabled = False
        self._split_camera_id = None
        self._split_mode = 'side'  # 'side' or 'top'
        
        # ATEM controller
        self.atem_controller = ATEMTallyController()
        
        # Keyboard manager for on-screen keyboard
        self.keyboard_manager = None
        
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        
        # Initialize ATEM connection if configured
        if self.settings.atem.enabled and self.settings.atem.ip_address:
            self.atem_controller.connect(self.settings.atem.ip_address)
        
        # Select first camera if available
        if self.settings.cameras:
            self._select_camera(self.settings.cameras[0].id)
    
    def _setup_window(self):
        """Setup window properties"""
        self.setWindowTitle("PanaPiTouch - PTZ Camera Monitor")
        
        # Set window size based on display
        self.setMinimumSize(1280, 720)
        
        # Set stylesheet
        self.setStyleSheet(STYLESHEET)
        
        # Fullscreen if configured
        if self.settings.fullscreen:
            self.showFullScreen()
        else:
            self.resize(self.settings.display_width, self.settings.display_height)
    
    def _setup_ui(self):
        """Setup the main UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top navigation bar
        nav_bar = self._create_nav_bar()
        main_layout.addWidget(nav_bar)
        
        # Page stack
        self.page_stack = QStackedWidget()
        
        # Create pages
        self.preview_page = self._create_preview_page()
        self.camera_page = CameraPage(self.settings)
        self.companion_page = CompanionPage(self.settings.companion_url)
        self.companion_page.update_available.connect(self._on_companion_update_available)
        self.companion_page.update_cleared.connect(self._on_companion_update_cleared)
        self.settings_page = SettingsPage(self.settings)
        
        self.page_stack.addWidget(self.preview_page)       # 0
        self.page_stack.addWidget(self.camera_page)        # 1
        self.page_stack.addWidget(self.companion_page)     # 2
        self.page_stack.addWidget(self.settings_page)      # 3
        
        main_layout.addWidget(self.page_stack, stretch=1)
        
        # Setup keyboard manager and overlay (as floating overlay, not in layout)
        self.keyboard_manager = KeyboardManager(self)
        self.keyboard_manager.setup_keyboard_overlay(central_widget)
    
    def _create_nav_bar(self) -> QWidget:
        """Create the top navigation bar"""
        nav_bar = QFrame()
        nav_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        nav_bar.setFixedHeight(70)
        
        layout = QHBoxLayout(nav_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)
        
        # App title/logo
        title = QLabel("PanaPiTouch")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {COLORS['primary']};
            padding-right: 30px;
        """)
        layout.addWidget(title)
        
        # Add 25px spacing after title
        layout.addSpacing(25)
        
        # Navigation buttons container (centered)
        nav_buttons_container = QWidget()
        nav_buttons_container.setStyleSheet("background: transparent;")
        nav_buttons_layout = QHBoxLayout(nav_buttons_container)
        nav_buttons_layout.setContentsMargins(0, 0, 0, 0)
        nav_buttons_layout.setSpacing(0)
        
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        
        nav_buttons = [
            ("📺  Live Page", 0),
            ("📷  Cameras", 1),
            ("🎛️  Companion", 2),
            ("⚙️  Settings", 3),
        ]
        
        for text, page_idx in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setFixedHeight(70)
            btn.setMinimumWidth(150)
            
            self.nav_button_group.addButton(btn, page_idx)
            nav_buttons_layout.addWidget(btn)
            
            if page_idx == 0:
                btn.setChecked(True)
        
        self.nav_button_group.idClicked.connect(self._on_nav_clicked)
        
        layout.addWidget(nav_buttons_container)
        
        # Companion update button (hidden by default, shown when update available)
        self.companion_update_btn = QPushButton("⬆️ Companion Update")
        self.companion_update_btn.setFixedHeight(50)
        self.companion_update_btn.setToolTip("Companion update available")
        self.companion_update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #22c55e;
                border: none;
                border-radius: 8px;
                color: #0a0a0f;
                font-size: 13px;
                font-weight: 600;
                padding: 0px;
                margin: 0px;
                margin-left: 12px;
            }}
            QPushButton:hover {{
                background-color: #16a34a;
            }}
            QPushButton:pressed {{
                background-color: #15803d;
            }}
        """)
        self.companion_update_btn.clicked.connect(self._on_companion_update_clicked)
        self.companion_update_btn.hide()
        layout.addWidget(self.companion_update_btn)
        
        # Add stretch before system menu button
        layout.addStretch()
        
        # System menu button - text only, no icons
        system_menu_btn = QPushButton("X")
        system_menu_btn.setFixedSize(50, 50)
        system_menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                border-radius: 10px;
                color: {COLORS['text']};
                font-size: 18px;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton::menu-indicator {{
                image: none;
                width: 0px;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
                border-color: {COLORS['text']};
                color: {COLORS['text']};
            }}
        """)
        
        # Connect button click to show popup instead of menu
        system_menu_btn.clicked.connect(self._show_system_popup)
        layout.addWidget(system_menu_btn)
        
        return nav_bar
    
    def _create_preview_page(self) -> QWidget:
        """Create the preview page with tally bar, side panel, and camera bar (16:10 optimized)"""
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)
        
        # Middle: Preview + Side panel
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)
        
        # Left: Preview container + Camera bar (same width)
        preview_column = QWidget()
        preview_column_layout = QVBoxLayout(preview_column)
        preview_column_layout.setContentsMargins(0, 0, 0, 0)
        preview_column_layout.setSpacing(12)
        
        # Preview container with FPS overlay
        preview_container = QFrame()
        preview_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        preview_inner_layout = QVBoxLayout(preview_container)
        preview_inner_layout.setContentsMargins(0, 0, 0, 0)
        preview_inner_layout.setSpacing(0)
        
        # Preview with FPS overlay in top-left
        preview_wrapper = QWidget()
        preview_wrapper_layout = QVBoxLayout(preview_wrapper)
        preview_wrapper_layout.setContentsMargins(8, 8, 8, 8)
        preview_wrapper_layout.setSpacing(0)
        
        # FPS label (top-left, overlaid)
        self.fps_label = QLabel("-- fps")
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.fps_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: 11px;
            font-weight: 600;
            background-color: rgba(0, 0, 0, 0.5);
            padding: 2px 6px;
            border-radius: 4px;
        """)
        self.fps_label.setFixedHeight(20)
        preview_wrapper_layout.addWidget(self.fps_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        self.preview_widget = PreviewWidget()
        preview_wrapper_layout.addWidget(self.preview_widget, stretch=1)
        
        preview_inner_layout.addWidget(preview_wrapper)
        preview_column_layout.addWidget(preview_container, stretch=1)
        
        # Camera selection bar (same width as preview)
        camera_bar = self._create_camera_bar()
        preview_column_layout.addWidget(camera_bar)
        
        middle_layout.addWidget(preview_column, stretch=1)
        
        # Right: Side panel (overlays + PTZ + multiview)
        side_panel = self._create_side_panel()
        middle_layout.addWidget(side_panel)
        
        main_layout.addLayout(middle_layout, stretch=1)
        
        return page
    
    def _create_side_panel(self) -> QWidget:
        """Create right side panel with collapsible PTZ controls, OSD menu, overlays, and multiview"""
        # Outer container with fixed width
        panel = QFrame()
        panel.setFixedWidth(200)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {COLORS['surface']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Content widget inside scroll area
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)
        
        # Button style for toggle buttons
        toggle_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:checked {{
                background-color: #FF9500;
                color: white;
            }}
        """
        
        # Shared touch-friendly combo box style
        from PyQt6.QtWidgets import QComboBox, QListView
        touch_combo_style = f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 8px;
                color: {COLORS['text']};
                font-size: 11px;
                min-height: 20px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                background-color: {COLORS['surface']};
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: none;
                color: {COLORS['text']};
                selection-background-color: {COLORS['primary']};
                padding: 2px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 36px;
                padding: 6px 8px;
                font-size: 11px;
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLORS['surface_light']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLORS['primary']};
            }}
        """
        
        def setup_combo_view(combo: QComboBox):
            """Set up a dark styled view for combo box"""
            view = QListView()
            view.setStyleSheet(f"""
                QListView {{
                    background-color: {COLORS['surface']};
                    border: none;
                    outline: none;
                }}
                QListView::item {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['text']};
                    min-height: 36px;
                    padding: 6px 8px;
                }}
                QListView::item:hover {{
                    background-color: {COLORS['surface_light']};
                }}
                QListView::item:selected {{
                    background-color: {COLORS['primary']};
                }}
            """)
            combo.setView(view)
        
        # ===== PTZ Control Toggle Button =====
        self.ptz_toggle_btn = QPushButton("▼ PTZ Control")
        self.ptz_toggle_btn.setCheckable(True)
        self.ptz_toggle_btn.setFixedHeight(36)
        self.ptz_toggle_btn.setStyleSheet(toggle_btn_style)
        self.ptz_toggle_btn.clicked.connect(self._toggle_ptz_panel)
        layout.addWidget(self.ptz_toggle_btn)
        
        # PTZ Control Panel (collapsible)
        self.ptz_panel = QFrame()
        self.ptz_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        ptz_layout = QVBoxLayout(self.ptz_panel)
        ptz_layout.setContentsMargins(8, 8, 8, 8)
        ptz_layout.setSpacing(8)
        
        # Virtual Joystick
        joystick_container = QWidget()
        joystick_layout = QHBoxLayout(joystick_container)
        joystick_layout.setContentsMargins(0, 0, 0, 0)
        joystick_layout.addStretch()
        
        self.ptz_joystick = JoystickWidget()
        self.ptz_joystick.setFixedSize(140, 140)
        self.ptz_joystick.position_changed.connect(self._on_joystick_move)
        self.ptz_joystick.released.connect(self._on_joystick_release)
        joystick_layout.addWidget(self.ptz_joystick)
        joystick_layout.addStretch()
        ptz_layout.addWidget(joystick_container)
        
        # Zoom Slider
        zoom_label = QLabel("Zoom")
        zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_dim']}; background: transparent; border: none;")
        ptz_layout.addWidget(zoom_label)
        
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(4)
        
        zoom_out_label = QLabel("−")
        zoom_out_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']}; background: transparent; border: none;")
        zoom_row.addWidget(zoom_out_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(-50, 50)
        self.zoom_slider.setValue(0)
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['surface']};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['primary']};
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
        """)
        self.zoom_slider.sliderPressed.connect(self._on_zoom_pressed)
        self.zoom_slider.sliderMoved.connect(self._on_zoom_moved)
        self.zoom_slider.sliderReleased.connect(self._on_zoom_released)
        zoom_row.addWidget(self.zoom_slider, stretch=1)
        
        zoom_in_label = QLabel("+")
        zoom_in_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']}; background: transparent; border: none;")
        zoom_row.addWidget(zoom_in_label)
        
        ptz_layout.addLayout(zoom_row)
        
        self.ptz_panel.setVisible(False)
        layout.addWidget(self.ptz_panel)
        
        # ===== OSD Menu Toggle Button =====
        self.osd_toggle_btn = QPushButton("▼ OSD Menu")
        self.osd_toggle_btn.setCheckable(True)
        self.osd_toggle_btn.setFixedHeight(36)
        self.osd_toggle_btn.setStyleSheet(toggle_btn_style)
        self.osd_toggle_btn.clicked.connect(self._toggle_osd_panel)
        layout.addWidget(self.osd_toggle_btn)
        
        # OSD Menu Panel (collapsible) - matches app style
        self.osd_panel = QFrame()
        self.osd_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        osd_layout = QVBoxLayout(self.osd_panel)
        osd_layout.setContentsMargins(6, 8, 6, 8)
        osd_layout.setSpacing(6)
        
        # ===== ON / OFF Segmented Toggle =====
        onoff_container = QWidget()
        onoff_layout = QHBoxLayout(onoff_container)
        onoff_layout.setContentsMargins(0, 0, 0, 0)
        onoff_layout.setSpacing(0)
        
        self.osd_on_btn = QPushButton("ON")
        self.osd_on_btn.setFixedSize(80, 25)
        self.osd_on_btn.setCheckable(True)
        self.osd_on_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-right: none;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                font-size: 11px;
                font-weight: 600;
                color: {COLORS['text_dim']};
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['surface_hover']};
                color: {COLORS['text']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        self.osd_on_btn.clicked.connect(self._osd_on)
        onoff_layout.addWidget(self.osd_on_btn)
        
        self.osd_off_btn = QPushButton("OFF")
        self.osd_off_btn.setFixedSize(80, 25)
        self.osd_off_btn.setCheckable(True)
        self.osd_off_btn.setChecked(True)
        self.osd_off_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-left: none;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                color: {COLORS['text_dim']};
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['surface_hover']};
                color: {COLORS['text']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        self.osd_off_btn.clicked.connect(self._osd_off)
        onoff_layout.addWidget(self.osd_off_btn)
        
        osd_layout.addWidget(onoff_container)
        
        # Spacing after ON/OFF (10px margin at bottom)
        osd_layout.addSpacing(10)
        
        # ===== D-Pad Navigation with OK in center =====
        dpad_total_width = 160  # Fixed container width
        dpad_spacing = 4
        
        # Calculate button size: (160px - 2 spacings × 4px) / 3 buttons = 50px
        dpad_btn_size = (dpad_total_width - (dpad_spacing * 2)) // 3
        
        dpad_style = f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['text']};
                padding: 0px;
                margin: 0px;
                min-width: {dpad_btn_size}px;
                max-width: {dpad_btn_size}px;
                min-height: {dpad_btn_size}px;
                max-height: {dpad_btn_size}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """
        
        # D-pad container (centered)
        dpad_container = QWidget()
        dpad_container_layout = QHBoxLayout(dpad_container)
        dpad_container_layout.setContentsMargins(0, 0, 0, 0)
        dpad_container_layout.addStretch()
        
        dpad_grid = QWidget()
        dpad_grid.setFixedWidth(dpad_total_width)
        dpad_grid_layout = QGridLayout(dpad_grid)
        dpad_grid_layout.setContentsMargins(0, 0, 0, 0)
        dpad_grid_layout.setSpacing(dpad_spacing)
        # Prevent columns from stretching
        dpad_grid_layout.setColumnStretch(0, 0)
        dpad_grid_layout.setColumnStretch(1, 0)
        dpad_grid_layout.setColumnStretch(2, 0)
        dpad_grid_layout.setRowStretch(0, 0)
        dpad_grid_layout.setRowStretch(1, 0)
        dpad_grid_layout.setRowStretch(2, 0)
        
        # Up arrow
        osd_up = QPushButton("▲")
        osd_up.setFixedSize(dpad_btn_size, dpad_btn_size)
        osd_up.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        osd_up.setStyleSheet(dpad_style)
        osd_up.clicked.connect(lambda: self._osd_navigate("up"))
        dpad_grid_layout.addWidget(osd_up, 0, 1)
        
        # Left arrow
        osd_left = QPushButton("◀")
        osd_left.setFixedSize(dpad_btn_size, dpad_btn_size)
        osd_left.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        osd_left.setStyleSheet(dpad_style)
        osd_left.clicked.connect(lambda: self._osd_navigate("left"))
        dpad_grid_layout.addWidget(osd_left, 1, 0)
        
        # OK button (center)
        osd_ok = QPushButton("OK")
        osd_ok.setFixedSize(dpad_btn_size, dpad_btn_size)
        osd_ok.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        osd_ok.setStyleSheet(dpad_style)
        osd_ok.clicked.connect(lambda: self._osd_navigate("ok"))
        dpad_grid_layout.addWidget(osd_ok, 1, 1)
        
        # Right arrow
        osd_right = QPushButton("▶")
        osd_right.setFixedSize(dpad_btn_size, dpad_btn_size)
        osd_right.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        osd_right.setStyleSheet(dpad_style)
        osd_right.clicked.connect(lambda: self._osd_navigate("right"))
        dpad_grid_layout.addWidget(osd_right, 1, 2)
        
        # Down arrow
        osd_down = QPushButton("▼")
        osd_down.setFixedSize(dpad_btn_size, dpad_btn_size)
        osd_down.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        osd_down.setStyleSheet(dpad_style)
        osd_down.clicked.connect(lambda: self._osd_navigate("down"))
        dpad_grid_layout.addWidget(osd_down, 2, 1)
        
        dpad_container_layout.addWidget(dpad_grid)
        dpad_container_layout.addStretch()
        osd_layout.addWidget(dpad_container)
        
        # Spacing before Cancel button
        osd_layout.addSpacing(6)
        
        # ===== Cancel Button =====
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(160, 25)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                color: {COLORS['text']};
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        cancel_btn.clicked.connect(lambda: self._osd_navigate("back"))
        osd_layout.addWidget(cancel_btn)
        
        # Spacing before Scene picker
        osd_layout.addSpacing(6)
        
        self.scene_combo = QComboBox()
        self.scene_combo.addItems(["Scene 1", "Scene 2", "Scene 3", "Scene 4"])
        self.scene_combo.setFixedSize(160, 32)
        self.scene_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['text']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid {COLORS['text']};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['primary']};
                color: {COLORS['text']};
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 36px;
                padding: 8px;
            }}
        """)
        self.scene_combo.currentIndexChanged.connect(self._on_scene_changed)
        osd_layout.addWidget(self.scene_combo)
        
        # Add spacing at bottom after Scene dropdown
        osd_layout.addSpacing(12)
        
        self.osd_panel.setVisible(False)
        layout.addWidget(self.osd_panel)
        
        # ===== Overlays Toggle Button =====
        self.overlays_toggle_btn = QPushButton("▼ Overlays")
        self.overlays_toggle_btn.setCheckable(True)
        self.overlays_toggle_btn.setFixedHeight(36)
        self.overlays_toggle_btn.setStyleSheet(toggle_btn_style)
        self.overlays_toggle_btn.clicked.connect(self._toggle_overlays_panel)
        layout.addWidget(self.overlays_toggle_btn)
        
        # Overlays Panel (collapsible)
        self.overlays_panel = QFrame()
        self.overlays_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        overlays_layout = QVBoxLayout(self.overlays_panel)
        overlays_layout.setContentsMargins(8, 8, 8, 8)
        overlays_layout.setSpacing(6)
        
        # Overlay toggle buttons
        self.overlay_buttons = {}
        overlays = [
            ("False Color", "false_color"),
            ("Waveform", "waveform"),
            ("Vectorscope", "vectorscope"),
            ("Focus Assist", "focus_assist"),
        ]
        
        for name, key in overlays:
            btn = QPushButton(name)
            btn.setObjectName("overlayButton")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, k=key: self._toggle_overlay(k))
            self.overlay_buttons[key] = btn
            overlays_layout.addWidget(btn)
        
        self.overlays_panel.setVisible(False)
        layout.addWidget(self.overlays_panel)
        
        # ===== Grid Overlay Toggle Button =====
        self.grid_toggle_btn = QPushButton("▼ Grid/Guides")
        self.grid_toggle_btn.setCheckable(True)
        self.grid_toggle_btn.setFixedHeight(36)
        self.grid_toggle_btn.setStyleSheet(toggle_btn_style)
        self.grid_toggle_btn.clicked.connect(self._toggle_grid_panel)
        layout.addWidget(self.grid_toggle_btn)
        
        # Grid Panel (collapsible)
        self.grid_panel = QFrame()
        self.grid_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        grid_layout = QVBoxLayout(self.grid_panel)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        grid_layout.setSpacing(6)
        
        # Grid type buttons
        self.grid_buttons = {}
        grid_types = [
            ("Rule of Thirds", "thirds"),
            ("Full Grid", "grid"),
        ]
        
        for name, key in grid_types:
            btn = QPushButton(name)
            btn.setObjectName("overlayButton")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, k=key: self._toggle_grid_type(k))
            self.grid_buttons[key] = btn
            grid_layout.addWidget(btn)
        
        self.grid_panel.setVisible(False)
        layout.addWidget(self.grid_panel)
        
        # ===== Frame Guides Toggle Button =====
        self.frame_guide_toggle_btn = QPushButton("▼ Frame Guides")
        self.frame_guide_toggle_btn.setCheckable(True)
        self.frame_guide_toggle_btn.setFixedHeight(36)
        self.frame_guide_toggle_btn.setStyleSheet(toggle_btn_style)
        self.frame_guide_toggle_btn.clicked.connect(self._toggle_frame_guide_panel)
        layout.addWidget(self.frame_guide_toggle_btn)
        
        # Frame Guides Panel (collapsible)
        self.frame_guide_panel = QFrame()
        self.frame_guide_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        frame_guide_layout = QVBoxLayout(self.frame_guide_panel)
        frame_guide_layout.setContentsMargins(6, 6, 6, 6)
        frame_guide_layout.setSpacing(4)
        
        # Template category dropdown - touch friendly
        self.frame_category_combo = QComboBox()
        self.frame_category_combo.setFixedHeight(38)
        self.frame_category_combo.setStyleSheet(touch_combo_style)
        setup_combo_view(self.frame_category_combo)
        self.frame_category_combo.addItems(["Social", "Cinema", "TV/Broadcast", "Custom"])
        self.frame_category_combo.currentTextChanged.connect(self._on_frame_category_changed)
        frame_guide_layout.addWidget(self.frame_category_combo)
        
        # Template selection dropdown - touch friendly
        self.frame_template_combo = QComboBox()
        self.frame_template_combo.setFixedHeight(38)
        self.frame_template_combo.setStyleSheet(touch_combo_style)
        setup_combo_view(self.frame_template_combo)
        self.frame_template_combo.currentTextChanged.connect(self._on_frame_template_changed)
        frame_guide_layout.addWidget(self.frame_template_combo)
        
        # Color picker buttons - 25x25px, centered, rounded
        self._frame_colors = {
            "White": ((255, 255, 255), "#FFFFFF"),
            "Red": ((0, 0, 255), "#FF0000"),      # BGR for OpenCV
            "Green": ((0, 255, 0), "#00FF00"),    # BGR for OpenCV
            "Blue": ((255, 0, 0), "#0000FF"),     # BGR for OpenCV
            "Yellow": ((0, 255, 255), "#FFFF00"), # BGR for OpenCV
        }
        
        color_row = QWidget()
        color_row.setFixedHeight(45)
        color_row_layout = QHBoxLayout(color_row)
        color_row_layout.setContentsMargins(0, 5, 0, 20)
        color_row_layout.setSpacing(8)
        color_row_layout.addStretch()
        
        self._color_buttons = {}
        for name, (bgr, hex_color) in self._frame_colors.items():
            btn = QPushButton()
            btn.setFixedSize(25, 25)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['text']};
                }}
                QPushButton:checked {{
                    border-color: {COLORS['primary']};
                    border-width: 3px;
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self._on_frame_color_clicked(n))
            color_row_layout.addWidget(btn)
            self._color_buttons[name] = btn
        
        color_row_layout.addStretch()
        # Default to white selected
        self._color_buttons["White"].setChecked(True)
        frame_guide_layout.addWidget(color_row)
        frame_guide_layout.addSpacing(8)  # Space after color buttons
        
        # Button style for Save/Clear/Custom Frame
        action_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 10px;
                font-weight: 600;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
            }}
        """
        
        # Custom Frame button - same style as Save/Clear
        self.drag_mode_btn = QPushButton("Custom Frame")
        self.drag_mode_btn.setCheckable(True)
        self.drag_mode_btn.setFixedHeight(30)
        self.drag_mode_btn.setStyleSheet(action_btn_style)
        self.drag_mode_btn.clicked.connect(self._toggle_drag_mode)
        frame_guide_layout.addWidget(self.drag_mode_btn)
        
        # Save and Clear buttons - side by side
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        
        save_custom_btn = QPushButton("Save")
        save_custom_btn.setFixedHeight(30)
        save_custom_btn.setStyleSheet(action_btn_style)
        save_custom_btn.clicked.connect(self._save_custom_frame_guide)
        btn_row.addWidget(save_custom_btn)
        
        clear_guide_btn = QPushButton("Clear")
        clear_guide_btn.setFixedHeight(30)
        clear_guide_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 10px;
                font-weight: 600;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:pressed {{
                background-color: #ff4444;
            }}
        """)
        clear_guide_btn.clicked.connect(self._clear_frame_guide)
        btn_row.addWidget(clear_guide_btn)
        
        frame_guide_layout.addLayout(btn_row)
        
        # Add spacing at bottom
        frame_guide_layout.addSpacing(20)
        
        self.frame_guide_panel.setVisible(False)
        layout.addWidget(self.frame_guide_panel)
        
        # Initialize frame guide templates
        self._on_frame_category_changed("Social")
        
        # Define action button style for use in split panel
        action_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 10px;
                font-weight: 600;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
            }}
        """
        
        # ===== Split Screen Toggle Button =====
        self.split_toggle_btn = QPushButton("▼ Split Compare")
        self.split_toggle_btn.setCheckable(True)
        self.split_toggle_btn.setFixedHeight(36)
        self.split_toggle_btn.setStyleSheet(toggle_btn_style)
        self.split_toggle_btn.clicked.connect(self._toggle_split_panel)
        layout.addWidget(self.split_toggle_btn)
        
        # Split Screen Panel (collapsible)
        self.split_panel = QFrame()
        self.split_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        split_layout = QVBoxLayout(self.split_panel)
        split_layout.setContentsMargins(6, 6, 6, 6)
        split_layout.setSpacing(4)
        
        # Camera selection dropdown - touch friendly
        split_label = QLabel("Compare with:")
        split_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 9px; background: transparent; border: none;")
        split_layout.addWidget(split_label)
        
        self.split_camera_combo = QComboBox()
        self.split_camera_combo.setFixedHeight(38)
        self.split_camera_combo.setStyleSheet(touch_combo_style)
        setup_combo_view(self.split_camera_combo)
        split_layout.addWidget(self.split_camera_combo)
        
        # Split mode buttons - side by side
        split_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """
        split_mode_row = QHBoxLayout()
        split_mode_row.setSpacing(4)
        
        self.split_side_btn = QPushButton("SBS")
        self.split_side_btn.setCheckable(True)
        self.split_side_btn.setChecked(True)
        self.split_side_btn.setFixedHeight(30)
        self.split_side_btn.setStyleSheet(split_btn_style)
        self.split_side_btn.clicked.connect(lambda: self._set_split_mode('side'))
        split_mode_row.addWidget(self.split_side_btn)
        
        self.split_top_btn = QPushButton("T/B")
        self.split_top_btn.setCheckable(True)
        self.split_top_btn.setFixedHeight(30)
        self.split_top_btn.setStyleSheet(split_btn_style)
        self.split_top_btn.clicked.connect(lambda: self._set_split_mode('top'))
        split_mode_row.addWidget(self.split_top_btn)
        
        split_layout.addLayout(split_mode_row)
        
        # Enable split button - same style as other action buttons
        self.split_enable_btn = QPushButton("Enable")
        self.split_enable_btn.setCheckable(True)
        self.split_enable_btn.setFixedHeight(30)
        self.split_enable_btn.setStyleSheet(action_btn_style)
        self.split_enable_btn.clicked.connect(self._toggle_split_view)
        split_layout.addWidget(self.split_enable_btn)
        
        # Add spacing at bottom
        split_layout.addSpacing(20)
        
        self.split_panel.setVisible(False)
        layout.addWidget(self.split_panel)
        
        # Multiview button (full width like overlay buttons)
        self.multiview_btn = QPushButton("Quad Split")
        self.multiview_btn.setObjectName("overlayButton")
        self.multiview_btn.setCheckable(True)
        self.multiview_btn.setFixedHeight(36)
        multiview_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 80px;
                color: {COLORS['text']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['surface']};
                color: #FF9500;
            }}
        """
        self.multiview_btn.setStyleSheet(multiview_btn_style)
        self.multiview_btn.clicked.connect(self._toggle_multiview)
        layout.addWidget(self.multiview_btn)
        
        layout.addStretch()
        
        # Set up scroll area with content
        scroll.setWidget(content)
        panel_layout.addWidget(scroll)
        
        # Status indicators at bottom of sidebar
        status_container = QWidget()
        status_container.setStyleSheet(f"""
            background-color: {COLORS['surface']};
            border-top: 1px solid {COLORS['border']};
            border-radius: 0;
        """)
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(6)
        
        self.connection_status = QLabel("CAM: ● Disconnected")
        self.connection_status.setTextFormat(Qt.TextFormat.RichText)
        self.connection_status.setStyleSheet(f"""
            color: {COLORS['text']}; 
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        self.connection_status.setToolTip("Camera disconnected")
        status_layout.addWidget(self.connection_status)
        
        self.atem_status = QLabel("ATEM: ● Not Configured")
        self.atem_status.setTextFormat(Qt.TextFormat.RichText)
        self.atem_status.setStyleSheet(f"""
            color: {COLORS['text']}; 
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        self.atem_status.setToolTip("ATEM not configured")
        status_layout.addWidget(self.atem_status)
        
        panel_layout.addWidget(status_container)
        
        return panel
    
    def _toggle_ptz_panel(self):
        """Toggle PTZ control panel visibility"""
        visible = self.ptz_toggle_btn.isChecked()
        self.ptz_panel.setVisible(visible)
        self.ptz_toggle_btn.setText("▲ PTZ Control" if visible else "▼ PTZ Control")
    
    def _toggle_osd_panel(self):
        """Toggle OSD menu panel visibility"""
        visible = self.osd_toggle_btn.isChecked()
        self.osd_panel.setVisible(visible)
        self.osd_toggle_btn.setText("▲ OSD Menu" if visible else "▼ OSD Menu")
    
    def _toggle_overlays_panel(self):
        """Toggle Overlays panel visibility"""
        visible = self.overlays_toggle_btn.isChecked()
        self.overlays_panel.setVisible(visible)
        self.overlays_toggle_btn.setText("▲ Overlays" if visible else "▼ Overlays")
    
    def _toggle_grid_panel(self):
        """Toggle Grid panel visibility"""
        visible = self.grid_toggle_btn.isChecked()
        self.grid_panel.setVisible(visible)
        self.grid_toggle_btn.setText("▲ Grid/Guides" if visible else "▼ Grid/Guides")
    
    def _toggle_frame_guide_panel(self):
        """Toggle Frame Guides panel visibility"""
        visible = self.frame_guide_toggle_btn.isChecked()
        self.frame_guide_panel.setVisible(visible)
        self.frame_guide_toggle_btn.setText("▲ Frame Guides" if visible else "▼ Frame Guides")
        
        # When opening, enable the last used frame guide if one exists
        if visible and self.preview_widget.frame_guide.active_guide is not None:
            self.preview_widget.frame_guide.enabled = True
    
    def _toggle_split_panel(self):
        """Toggle Split Compare panel visibility"""
        visible = self.split_toggle_btn.isChecked()
        self.split_panel.setVisible(visible)
        self.split_toggle_btn.setText("▲ Split Compare" if visible else "▼ Split Compare")
        
        # Populate camera dropdown when opening
        if visible:
            self._populate_split_cameras()
    
    def _toggle_grid_type(self, grid_type: str):
        """Toggle specific grid type"""
        if grid_type == "thirds":
            enabled = self.preview_widget.toggle_rule_of_thirds()
            self.grid_buttons["thirds"].setChecked(enabled)
        elif grid_type == "grid":
            enabled = self.preview_widget.toggle_full_grid()
            self.grid_buttons["grid"].setChecked(enabled)
    
    def _on_frame_category_changed(self, category: str):
        """Handle frame guide category change"""
        # Block signals to prevent auto-enabling frame guides when populating dropdown
        self.frame_template_combo.blockSignals(True)
        self.frame_template_combo.clear()
        
        templates = self.preview_widget.frame_guide.get_all_templates()
        if category in templates:
            for guide in templates[category]:
                self.frame_template_combo.addItem(guide.name)
        elif category == "Custom":
            # Show custom guides
            custom_guides = self.preview_widget.frame_guide.custom_guides
            for guide in custom_guides:
                self.frame_template_combo.addItem(guide.name)
            if not custom_guides:
                self.frame_template_combo.addItem("(No custom guides)")
        
        # Unblock signals
        self.frame_template_combo.blockSignals(False)
    
    def _on_frame_template_changed(self, template_name: str):
        """Handle frame guide template selection"""
        if not template_name or template_name == "(No custom guides)":
            return
        
        category = self.frame_category_combo.currentText()
        if self.preview_widget.frame_guide.set_guide_by_name(category, template_name):
            # Enable frame guide when user explicitly selects from dropdown
            self.preview_widget.frame_guide.enabled = True
            # Update Custom Frame button state based on whether guide has custom_rect
            if self.preview_widget.frame_guide.drag_mode:
                self.drag_mode_btn.setChecked(True)
            else:
                self.drag_mode_btn.setChecked(False)
    
    def _toggle_drag_mode(self):
        """Toggle drag/resize mode for frame guide"""
        if self.drag_mode_btn.isChecked():
            self.preview_widget.frame_guide.enable_drag_mode()
            self.preview_widget.frame_guide.enabled = True
        else:
            self.preview_widget.frame_guide.disable_drag_mode()
    
    def _on_frame_color_clicked(self, color_name: str):
        """Handle frame guide color button click"""
        # Uncheck all other color buttons
        for name, btn in self._color_buttons.items():
            btn.setChecked(name == color_name)
        
        # Apply color
        if color_name in self._frame_colors:
            bgr_color, hex_color = self._frame_colors[color_name]
            self.preview_widget.frame_guide.line_color = bgr_color
    
    def _save_custom_frame_guide(self):
        """Save current frame guide as custom preset"""
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self, "Save Custom Guide",
            "Enter a name for this frame guide:"
        )
        
        if ok and name:
            if self.preview_widget.frame_guide.save_current_as_custom(name):
                # Uncheck Custom Frame button and disable drag mode
                self.drag_mode_btn.setChecked(False)
                self.preview_widget.frame_guide.disable_drag_mode()
                
                # Switch to Custom category and select the saved guide
                self.frame_category_combo.setCurrentText("Custom")
                self._on_frame_category_changed("Custom")
                
                # Select the newly saved guide in the template dropdown
                index = self.frame_template_combo.findText(name)
                if index >= 0:
                    self.frame_template_combo.setCurrentIndex(index)
    
    def _clear_frame_guide(self):
        """Clear the active frame guide"""
        self.preview_widget.frame_guide.clear()
        self.preview_widget.frame_guide.enabled = False
        self.drag_mode_btn.setChecked(False)
    
    def _populate_split_cameras(self):
        """Populate split screen camera dropdown"""
        self.split_camera_combo.clear()
        
        for camera in self.settings.cameras:
            if camera.id != self.current_camera_id:
                self.split_camera_combo.addItem(camera.name, camera.id)
    
    def _set_split_mode(self, mode: str):
        """Set split screen mode (side or top)"""
        self.split_side_btn.setChecked(mode == 'side')
        self.split_top_btn.setChecked(mode == 'top')
        self._split_mode = mode
    
    def _toggle_split_view(self):
        """Toggle split screen view"""
        enabled = self.split_enable_btn.isChecked()
        
        # Update button text
        if enabled:
            self.split_enable_btn.setText("Disable")
        else:
            self.split_enable_btn.setText("Enable")
        
        if enabled:
            # Get selected camera
            camera_id = self.split_camera_combo.currentData()
            if camera_id is None:
                self.split_enable_btn.setChecked(False)
                self.split_enable_btn.setText("Enable")
                return
            
            # Start split view
            self._split_camera_id = camera_id
            self._split_enabled = True
            
            # Start stream for second camera if not already running
            if camera_id not in self.camera_streams:
                camera = self.settings.get_camera(camera_id)
                if camera:
                    config = StreamConfig(
                        ip_address=camera.ip_address,
                        port=camera.port,
                        username=camera.username,
                        password=camera.password,
                        resolution=(1280, 720)  # Lower res for split
                    )
                    stream = CameraStream(config)
                    stream.start()
                    self.camera_streams[camera_id] = stream
        else:
            self._split_enabled = False
            self._split_camera_id = None
    
    def _on_joystick_move(self, x: float, y: float):
        """Handle joystick movement - send PTZ commands"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            # Convert joystick position to PTZ speed (1-49)
            # x: -1 (left) to 1 (right)
            # y: -1 (up) to 1 (down)
            pan_speed = int(abs(x) * 49)
            tilt_speed = int(abs(y) * 49)
            
            if pan_speed > 0 or tilt_speed > 0:
                # Determine direction
                pan_cmd = "R" if x > 0 else "L" if x < 0 else ""
                tilt_cmd = "t" if y > 0 else "T" if y < 0 else ""  # t=down, T=up
                
                # Send combined pan/tilt command
                if pan_cmd and tilt_cmd:
                    # Use PTS command for combined movement
                    pan_value = 50 + int(x * 49)  # 1-99, 50 = stop
                    tilt_value = 50 - int(y * 49)  # 1-99, 50 = stop (inverted)
                    url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23PTS{pan_value:02d}{tilt_value:02d}&res=1"
                elif pan_cmd:
                    url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23{pan_cmd}{pan_speed:02d}&res=1"
                else:
                    url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23{tilt_cmd}{tilt_speed:02d}&res=1"
                
                requests.get(url, auth=(camera.username, camera.password), timeout=0.3)
        except Exception as e:
            print(f"PTZ joystick error: {e}")
    
    def _on_joystick_release(self):
        """Handle joystick release - stop PTZ movement"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            # Stop all PTZ movement
            url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23PTS5050&res=1"
            requests.get(url, auth=(camera.username, camera.password), timeout=0.3)
        except Exception as e:
            print(f"PTZ stop error: {e}")
    
    def _on_zoom_pressed(self):
        """Handle zoom slider press"""
        pass  # Will start zoom on move
    
    def _on_zoom_moved(self, value: int):
        """Handle zoom slider movement"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            if abs(value) > 5:  # Deadzone
                # Zoom speed based on slider position
                speed = int(abs(value) * 49 / 50)
                cmd = "zi" if value > 0 else "zo"
                url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23{cmd}{speed:02d}&res=1"
                requests.get(url, auth=(camera.username, camera.password), timeout=0.3)
        except Exception as e:
            print(f"PTZ zoom error: {e}")
    
    def _on_zoom_released(self):
        """Handle zoom slider release - stop zoom and reset slider"""
        if self.current_camera_id is not None:
            camera = self.settings.get_camera(self.current_camera_id)
            if camera:
                import requests
                try:
                    url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23zS&res=1"
                    requests.get(url, auth=(camera.username, camera.password), timeout=0.3)
                except Exception as e:
                    print(f"PTZ zoom stop error: {e}")
        
        # Reset slider to center
        self.zoom_slider.setValue(0)
    
    def _osd_toggle_menu(self):
        """Toggle camera OSD on/off"""
        if self.current_camera_id is None:
            print("OSD toggle: No camera selected")
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            print("OSD toggle: Camera not found")
            return
        
        import requests
        try:
            # Try multiple OSD command formats - different camera models may use different formats
            base_url = f"http://{camera.ip_address}"
            auth = (camera.username, camera.password)
            
            # Try multiple OSD command formats - different camera models may use different formats
            osd_commands = [
                f"{base_url}/cgi-bin/aw_ptz?cmd=%23DA1&res=1",  # Standard format with URL encoding
                f"{base_url}/cgi-bin/aw_ptz?cmd=%23DA1",        # Without res parameter
                f"{base_url}/cgi-bin/aw_ptz?cmd=#DA1&res=1",   # Without URL encoding
                f"{base_url}/cgi-bin/aw_cam?cmd=%23DA1&res=1", # Alternative endpoint
            ]
            
            success = False
            for url in osd_commands:
                try:
                    response = requests.get(url, auth=auth, timeout=2.0)
                    if response.status_code == 200:
                        print(f"OSD command sent successfully: {url}")
                        success = True
                        break
                    else:
                        print(f"OSD command returned status {response.status_code}: {url}")
                except requests.exceptions.RequestException as e:
                    print(f"OSD command failed: {url} - {e}")
                    continue
            
            if success:
                # Toggle OSD state and update button appearance
                self._osd_active = not self._osd_active
                self._update_osd_button_style()
                
                # Delay tally off command to avoid interfering with OSD opening
                # Send tally off command after a short delay to prevent tally from getting stuck
                QTimer.singleShot(500, self._tally_off)
            else:
                print("OSD toggle: All command attempts failed")
        except Exception as e:
            print(f"OSD toggle error: {e}")
    
    def _tally_off(self):
        """Turn off camera tally light to fix stuck tally issue"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        import time
        try:
            # Try multiple Panasonic tally off commands
            # Different camera models may use different commands
            tally_commands = [
                "%23TAL0",  # Tally off (common command)
                "%23TL0",   # Alternative format
            ]
            
            base_url = f"http://{camera.ip_address}/cgi-bin/aw_ptz"
            auth = (camera.username, camera.password)
            
            # Try each command (some cameras may respond to different formats)
            for cmd in tally_commands:
                try:
                    url = f"{base_url}?cmd={cmd}&res=1"
                    requests.get(url, auth=auth, timeout=0.5)
                    # Small delay between commands
                    time.sleep(0.1)
                except:
                    pass
                    
            print("Tally off command sent")
        except Exception as e:
            print(f"Tally off error: {e}")
    
    def _on_scene_changed(self, index: int):
        """Load scene file on camera"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            # Panasonic scene file recall: XSF:scene_number (0-3 for scenes 1-4)
            scene_num = index
            url = f"http://{camera.ip_address}/cgi-bin/aw_cam?cmd=XSF:{scene_num}&res=1"
            requests.get(url, auth=(camera.username, camera.password), timeout=1.0)
            print(f"Scene {index + 1} loaded")
        except Exception as e:
            print(f"Scene load error: {e}")
    
    def _update_osd_button_style(self):
        """Update OSD ON/OFF toggle based on active state"""
        self.osd_on_btn.setChecked(self._osd_active)
        self.osd_off_btn.setChecked(not self._osd_active)
    
    def _osd_on(self):
        """Turn OSD ON"""
        if not self._osd_active:
            self._osd_toggle_menu()
        else:
            self._update_osd_button_style()
    
    def _osd_off(self):
        """Turn OSD OFF"""
        if self._osd_active:
            self._osd_toggle_menu()
        else:
            self._update_osd_button_style()
    
    def _osd_navigate(self, direction: str):
        """Navigate camera OSD menu"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            # Panasonic OSD navigation commands
            cmd_map = {
                "up": "#TAU",      # Menu up
                "down": "#TAD",    # Menu down
                "left": "#TAL",    # Menu left
                "right": "#TAR",   # Menu right
                "ok": "#TAA",      # Menu enter/select
                "back": "#TAB",    # Menu back
            }
            
            if direction in cmd_map:
                url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23{cmd_map[direction][1:]}&res=1"
                requests.get(url, auth=(camera.username, camera.password), timeout=0.5)
        except Exception as e:
            print(f"OSD navigate error: {e}")
    
    def _create_camera_bar(self) -> QWidget:
        """Create bottom camera selection bar"""
        # Outer scroll area for the entire bar
        bar_scroll = QScrollArea()
        bar_scroll.setWidgetResizable(True)
        bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bar_scroll.setFixedHeight(140)
        bar_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QScrollBar:horizontal {{
                background: {COLORS['surface']};
                height: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        
        # Inner bar frame
        bar = QFrame()
        bar.setFixedHeight(140)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
            }}
        """)
        
        layout = QHBoxLayout(bar)
        # Calculate vertical margins to center buttons (bar height 140, button height 80, so (140-80)/2 = 30)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)
        
        # Center all buttons
        layout.addStretch()
        
        # Demo button (25% bigger: 70*1.25=88, 50*1.25=63)
        self.demo_btn = QPushButton("D")
        self.demo_btn.setObjectName("demoButton")
        self.demo_btn.setCheckable(True)
        self.demo_btn.setFixedSize(88, 80)
        self.demo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 3px solid {COLORS['border']};
                border-radius: 10px;
                padding: 4px;
                color: {COLORS['text']};
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: #FF9500;
                border-color: #FF9500;
                color: white;
            }}
        """)
        self.demo_btn.setToolTip("Demo Video")
        self.demo_btn.clicked.connect(self._toggle_demo_mode)
        layout.addWidget(self.demo_btn)
        
        # Camera buttons container (no scroll area here, bar itself scrolls)
        self.camera_buttons_container = QWidget()
        self.camera_buttons_container.setStyleSheet("background-color: transparent;")
        self.camera_buttons_layout = QHBoxLayout(self.camera_buttons_container)
        self.camera_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_buttons_layout.setSpacing(10)
        
        # Camera buttons group
        self.camera_button_group = QButtonGroup(self)
        self.camera_button_group.setExclusive(True)
        self.camera_buttons: dict = {}
        self.camera_button_group.idClicked.connect(self._on_camera_button_clicked)
        
        # Build initial camera buttons
        self._rebuild_camera_buttons()
        
        layout.addWidget(self.camera_buttons_container)
        
        layout.addStretch()
        
        bar_scroll.setWidget(bar)
        
        return bar_scroll
    
    def _rebuild_camera_buttons(self):
        """Rebuild camera buttons - horizontal in bottom bar"""
        # Clear existing camera buttons
        for btn in self.camera_buttons.values():
            self.camera_button_group.removeButton(btn)
            self.camera_buttons_layout.removeWidget(btn)
            btn.deleteLater()
        self.camera_buttons.clear()
        
        # Create button for each configured camera
        num_cameras = len(self.settings.cameras)
        for i, camera in enumerate(self.settings.cameras):
            # Truncate name to fit
            label = camera.name[:8] if len(camera.name) > 8 else camera.name
            btn = QPushButton(label)
            btn.setObjectName("cameraButton")
            btn.setCheckable(True)
            btn.setProperty("tallyState", "off")
            btn.setFixedSize(88, 80)
            btn.setToolTip(f"{camera.name}\n{camera.ip_address}")
            
            self.camera_button_group.addButton(btn, i)
            self.camera_buttons[i] = btn
            
            # If 10 or fewer cameras, use stretch to spread them out
            # If more than 10, they'll naturally overflow and scroll
            if num_cameras <= 10:
                self.camera_buttons_layout.addWidget(btn, stretch=1)
            else:
                self.camera_buttons_layout.addWidget(btn)
    
    def _toggle_demo_mode(self):
        """Toggle demo video mode"""
        if self.demo_btn.isChecked():
            # Stop multiview if running
            if self._multiview_active:
                self._stop_multiview()
            
            # Stop current camera stream
            if self.current_camera_id is not None:
                if self.current_camera_id in self.camera_streams:
                    self.camera_streams[self.current_camera_id].stop()
            
            # Uncheck all camera buttons
            checked_btn = self.camera_button_group.checkedButton()
            if checked_btn:
                self.camera_button_group.setExclusive(False)
                checked_btn.setChecked(False)
                self._set_camera_button_unchecked_style(checked_btn)
                checked_btn.update()
                self.camera_button_group.setExclusive(True)
            
            self.current_camera_id = None
            
            # Start demo mode
            self._start_demo_video()
        else:
            # Stop demo mode
            self._stop_demo_video()
    
    def _start_demo_video(self):
        """Start playing demo video with test pattern"""
        import threading
        
        self._demo_running = True
        self._demo_thread = threading.Thread(target=self._demo_video_loop, daemon=True)
        self._demo_thread.start()
    
    def _stop_demo_video(self):
        """Stop demo video"""
        self._demo_running = False
        if hasattr(self, '_demo_thread') and self._demo_thread:
            self._demo_thread.join(timeout=1)
        self.preview_widget.clear_frame()
    
    def _demo_video_loop(self):
        """Generate demo video frames with test pattern"""
        import cv2
        import numpy as np
        import time
        import math
        
        width, height = 1920, 1080
        frame_count = 0
        start_time = time.time()
        
        while self._demo_running:
            # Create test pattern frame
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Color bars (top 2/3)
            bar_height = int(height * 0.67)
            bar_width = width // 8
            colors = [
                (192, 192, 192),  # White/Gray
                (0, 192, 192),    # Yellow
                (192, 192, 0),    # Cyan
                (0, 192, 0),      # Green
                (192, 0, 192),    # Magenta
                (0, 0, 192),      # Red
                (192, 0, 0),      # Blue
                (16, 16, 16),     # Black
            ]
            for i, color in enumerate(colors):
                x1 = i * bar_width
                x2 = (i + 1) * bar_width
                frame[0:bar_height, x1:x2] = color
            
            # Moving gradient bar (bottom 1/3)
            t = time.time() - start_time
            offset = int((t * 100) % width)
            for x in range(width):
                intensity = int(128 + 127 * math.sin((x + offset) * 0.02))
                frame[bar_height:, x] = (intensity, intensity, intensity)
            
            # Add timestamp and info text
            timestamp = time.strftime("%H:%M:%S")
            fps_text = f"DEMO MODE | {timestamp} | Frame: {frame_count}"
            
            # Text background
            cv2.rectangle(frame, (50, height - 80), (600, height - 30), (0, 0, 0), -1)
            
            # Text
            cv2.putText(frame, fps_text, (60, height - 45), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            
            # PanaPiTouch logo text
            cv2.putText(frame, "PanaPiTouch", (width // 2 - 200, height // 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 4)
            cv2.putText(frame, "Demo Video", (width // 2 - 150, height // 2 + 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 2)
            
            # Send frame to preview
            self.preview_widget.update_frame(frame)
            
            frame_count += 1
            
            # Target 30fps
            time.sleep(0.033)
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Settings changed (from both camera page and settings page)
        self.camera_page.settings_changed.connect(self._on_settings_changed)
        self.settings_page.settings_changed.connect(self._on_settings_changed)
        
        # ATEM tally callback
        self.atem_controller.add_tally_callback(self._on_tally_changed)
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)
        
        # FPS update timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(500)
    
    @pyqtSlot(int)
    def _on_nav_clicked(self, page_idx: int):
        """Handle navigation button click"""
        # Hide keyboard when switching pages
        if self.keyboard_manager:
            self.keyboard_manager._hide_keyboard()
        
        self.page_stack.setCurrentIndex(page_idx)
        # Refresh keyboard manager to find new line edits
        if self.keyboard_manager:
            QTimer.singleShot(100, lambda: self.keyboard_manager._find_line_edits(self))
    
    @pyqtSlot(str)
    def _on_companion_update_available(self, version: str):
        """Handle companion update available signal"""
        self.companion_update_btn.setText(f"⬆️ Companion Update")
        self.companion_update_btn.setToolTip(f"Update Companion to v{version}")
        self.companion_update_btn.show()
    
    @pyqtSlot()
    def _on_companion_update_cleared(self):
        """Handle companion update completed/cleared"""
        self.companion_update_btn.hide()
    
    def _on_companion_update_clicked(self):
        """Handle companion update button click"""
        self.companion_page.update_companion()
    
    @pyqtSlot(int)
    def _on_camera_button_clicked(self, button_id: int):
        """Handle camera button click"""
        # Stop demo mode if running
        if self._demo_running:
            self._stop_demo_video()
            self.demo_btn.setChecked(False)
        
        # Stop multiview if running
        if self._multiview_active:
            self._stop_multiview()
        
        # Find camera by button index
        if button_id < len(self.settings.cameras):
            camera = self.settings.cameras[button_id]
            self._select_camera(camera.id)
    
    def _toggle_overlay(self, overlay_key: str):
        """Toggle an overlay"""
        if overlay_key == "false_color":
            enabled = self.preview_widget.toggle_false_color()
        elif overlay_key == "waveform":
            enabled = self.preview_widget.toggle_waveform()
        elif overlay_key == "vectorscope":
            enabled = self.preview_widget.toggle_vectorscope()
        elif overlay_key == "focus_assist":
            enabled = self.preview_widget.toggle_focus_assist()
        else:
            return
        
        self.overlay_buttons[overlay_key].setChecked(enabled)
    
    def _ptz_home(self):
        """Send PTZ home/preset 1 command"""
        if self.current_camera_id is None:
            return
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return
        
        import requests
        try:
            # Recall preset 1 (home position)
            url = f"http://{camera.ip_address}/cgi-bin/aw_ptz?cmd=%23R00&res=1"
            requests.get(url, auth=(camera.username, camera.password), timeout=1.0)
        except Exception as e:
            print(f"PTZ home error: {e}")
    
    def _toggle_multiview(self):
        """Toggle multiview display (2x2 grid, 4 cameras)"""
        if self.multiview_btn.isChecked():
            self._start_multiview(2, 2)
        else:
            self._stop_multiview()
    
    def _start_multiview(self, cols: int, rows: int):
        """Start multiview with given grid"""
        # Stop current single camera stream
        if self.current_camera_id is not None:
            if self.current_camera_id in self.camera_streams:
                self.camera_streams[self.current_camera_id].stop()
        
        # Stop demo if running
        if self._demo_running:
            self._stop_demo_video()
            self.demo_btn.setChecked(False)
        
        # Uncheck camera buttons
        checked_btn = self.camera_button_group.checkedButton()
        if checked_btn:
            self.camera_button_group.setExclusive(False)
            checked_btn.setChecked(False)
            self._set_camera_button_unchecked_style(checked_btn)
            checked_btn.update()
            self.camera_button_group.setExclusive(True)
        
        # Build camera list for multiview
        cameras = []
        for cam in self.settings.cameras:
            camera_info = CameraInfo(
                id=cam.id,
                name=cam.name,
                ip_address=cam.ip_address,
                username=cam.username,
                password=cam.password
            )
            cameras.append(camera_info)
        
        if not cameras:
            return
        
        # Start multiview manager
        self.multiview_manager.start(cameras, cols, rows)
        self._multiview_active = True
        self.current_camera_id = None
        
        print(f"Started multiview with {len(cameras)} cameras")
    
    def _stop_multiview(self):
        """Stop multiview and return to single camera view"""
        if self._multiview_active:
            self.multiview_manager.stop()
            self._multiview_active = False
        
        # Uncheck multiview button
        self.multiview_btn.setChecked(False)
        
        # Clear preview
        self.preview_widget.clear_frame()
        
        print("Stopped multiview")
    
    def _on_multiview_frame(self, frame):
        """Handle composite frame from multiview manager"""
        if self._multiview_active:
            self.preview_widget.update_frame(frame)
    
    def _select_camera(self, camera_id: int):
        """Select a camera to preview"""
        # Stop current stream
        if self.current_camera_id is not None:
            if self.current_camera_id in self.camera_streams:
                self.camera_streams[self.current_camera_id].stop()
        
        self.current_camera_id = camera_id
        camera = self.settings.get_camera(camera_id)
        
        if not camera:
            self.preview_widget.clear_frame()
            return
        
        # Create or reuse stream
        if camera_id not in self.camera_streams:
            # Use 1280x720 for better performance on Raspberry Pi
            # This reduces processing overhead by ~56% (fewer pixels to process)
            config = StreamConfig(
                ip_address=camera.ip_address,
                port=camera.port,
                username=camera.username,
                password=camera.password,
                resolution=(1280, 720)  # Reduced from 1920x1080 for better framerate
            )
            stream = CameraStream(config)
            stream.add_frame_callback(self._on_frame_received)
            self.camera_streams[camera_id] = stream
        
        # Start stream
        self.camera_streams[camera_id].start()
        
        # Update UI
        self._update_camera_selection_ui(camera_id)
        
        # Update tally state for preview
        self._update_preview_tally()
    
    def _on_frame_received(self, frame):
        """Handle received frame from camera"""
        import cv2
        import numpy as np
        
        # Handle split view if enabled
        if self._split_enabled and self._split_camera_id is not None:
            split_frame = self._get_split_frame(frame)
            if split_frame is not None:
                frame = split_frame
        
        self.preview_widget.update_frame(frame)
    
    def _get_split_frame(self, main_frame):
        """Combine main frame with split camera frame"""
        import cv2
        import numpy as np
        
        # Get frame from second camera
        if self._split_camera_id not in self.camera_streams:
            return None
        
        split_stream = self.camera_streams[self._split_camera_id]
        split_frame = split_stream.get_frame()
        
        if split_frame is None:
            return None
        
        h, w = main_frame.shape[:2]
        
        if self._split_mode == 'side':
            # Side by side - each camera gets half width
            half_w = w // 2
            
            # Resize both frames to half width
            main_resized = cv2.resize(main_frame, (half_w, h), interpolation=cv2.INTER_AREA)
            split_resized = cv2.resize(split_frame, (half_w, h), interpolation=cv2.INTER_AREA)
            
            # Combine horizontally
            combined = np.hstack([main_resized, split_resized])
            
            # Draw divider line
            cv2.line(combined, (half_w, 0), (half_w, h), (255, 255, 255), 2)
            
            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            main_camera = self.settings.get_camera(self.current_camera_id)
            split_camera = self.settings.get_camera(self._split_camera_id)
            
            if main_camera:
                cv2.putText(combined, main_camera.name, (10, 30), font, 0.7, (255, 255, 255), 2)
            if split_camera:
                cv2.putText(combined, split_camera.name, (half_w + 10, 30), font, 0.7, (255, 255, 255), 2)
            
            return combined
        
        else:  # top/bottom
            # Top and bottom - each camera gets half height
            half_h = h // 2
            
            # Resize both frames to half height
            main_resized = cv2.resize(main_frame, (w, half_h), interpolation=cv2.INTER_AREA)
            split_resized = cv2.resize(split_frame, (w, half_h), interpolation=cv2.INTER_AREA)
            
            # Combine vertically
            combined = np.vstack([main_resized, split_resized])
            
            # Draw divider line
            cv2.line(combined, (0, half_h), (w, half_h), (255, 255, 255), 2)
            
            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            main_camera = self.settings.get_camera(self.current_camera_id)
            split_camera = self.settings.get_camera(self._split_camera_id)
            
            if main_camera:
                cv2.putText(combined, main_camera.name, (10, 30), font, 0.7, (255, 255, 255), 2)
            if split_camera:
                cv2.putText(combined, split_camera.name, (10, half_h + 30), font, 0.7, (255, 255, 255), 2)
            
            return combined
    
    def _update_camera_buttons(self):
        """Update camera buttons - rebuild to match settings"""
        self._rebuild_camera_buttons()
    
    def _set_camera_button_unchecked_style(self, btn):
        """Set transparent background style for unchecked camera button"""
        tally_state = btn.property("tallyState") or "off"
        border_color = COLORS['tally_off']
        if tally_state == "program":
            border_color = COLORS['tally_program']
        elif tally_state == "preview":
            border_color = COLORS['tally_preview']
        
        btn.setStyleSheet(f"""
            QPushButton#cameraButton {{
                background-color: transparent;
                border: 3px solid {border_color};
                border-radius: 10px;
                padding: 4px;
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['text']};
            }}
        """)
    
    def _update_camera_selection_ui(self, camera_id: int):
        """Update UI to reflect selected camera"""
        # Uncheck all buttons first and ensure transparent background
        for btn in self.camera_buttons.values():
            btn.setChecked(False)
            self._set_camera_button_unchecked_style(btn)
            btn.update()
        
        # Find and check the selected camera button
        for i, camera in enumerate(self.settings.cameras):
            if camera.id == camera_id:
                if i in self.camera_buttons:
                    btn = self.camera_buttons[i]
                    # Temporarily disable button group to avoid conflicts
                    was_exclusive = self.camera_button_group.exclusive()
                    self.camera_button_group.setExclusive(False)
                    btn.setChecked(True)
                    self.camera_button_group.setExclusive(was_exclusive)
                    
                    # Get tally state for border color
                    tally_state = btn.property("tallyState") or "off"
                    border_color = COLORS['tally_off']
                    if tally_state == "program":
                        border_color = COLORS['tally_program']
                    elif tally_state == "preview":
                        border_color = COLORS['tally_preview']
                    
                    # Apply inline style to ensure FF9500 background takes precedence
                    # Include hover state to maintain interactivity
                    btn.setStyleSheet(f"""
                        QPushButton#cameraButton {{
                            background-color: #FF9500;
                            border: 3px solid {border_color};
                            border-radius: 10px;
                            padding: 4px;
                            font-size: 12px;
                            font-weight: 600;
                            color: white;
                        }}
                        QPushButton#cameraButton:pressed {{
                            background-color: #FF9500;
                            border-color: {border_color};
                        }}
                    """)
                    btn.update()
                    btn.repaint()
                break
    
    def _update_preview_tally(self):
        """Update preview tally based on ATEM state"""
        if self.current_camera_id is None:
            self.preview_widget.set_tally_state(TallyState.OFF)
            return
        
        # Get ATEM input for current camera
        atem_input = self.settings.atem.input_mapping.get(str(self.current_camera_id))
        if atem_input:
            state = self.atem_controller.get_tally_state(atem_input)
            self.preview_widget.set_tally_state(state)
        else:
            self.preview_widget.set_tally_state(TallyState.OFF)
    
    def _on_tally_changed(self, input_id: int, state: TallyState):
        """Handle ATEM tally change"""
        # Update camera buttons
        for i, camera in enumerate(self.settings.cameras):
            atem_input = self.settings.atem.input_mapping.get(str(camera.id))
            if atem_input == input_id:
                btn = self.camera_buttons[i]
                
                if state == TallyState.PROGRAM:
                    btn.setProperty("tallyState", "program")
                elif state == TallyState.PREVIEW:
                    btn.setProperty("tallyState", "preview")
                else:
                    btn.setProperty("tallyState", "off")
                
                # If button is checked, update inline style to maintain FF9500 background
                if btn.isChecked():
                    tally_state = btn.property("tallyState") or "off"
                    border_color = COLORS['tally_off']
                    if tally_state == "program":
                        border_color = COLORS['tally_program']
                    elif tally_state == "preview":
                        border_color = COLORS['tally_preview']
                    
                    btn.setStyleSheet(f"""
                        QPushButton#cameraButton {{
                            background-color: #FF9500;
                            border: 3px solid {border_color};
                            border-radius: 10px;
                            padding: 4px;
                            font-size: 12px;
                            font-weight: 600;
                            color: white;
                        }}
                        QPushButton#cameraButton:pressed {{
                            background-color: #FF9500;
                            border-color: {border_color};
                        }}
                    """)
                else:
                    # Not checked, set transparent background
                    self._set_camera_button_unchecked_style(btn)
                    btn.update()
        
        # Update preview tally
        self._update_preview_tally()
        
    
    def _on_settings_changed(self):
        """Handle settings change"""
        # Reload settings
        self.settings = Settings.load()
        
        # Update camera buttons
        self._update_camera_buttons()
        
        # Reconnect ATEM if needed
        if self.settings.atem.enabled and self.settings.atem.ip_address:
            self.atem_controller.disconnect()
            self.atem_controller.connect(self.settings.atem.ip_address)
        else:
            self.atem_controller.disconnect()
        
        # Update companion URL
        self.companion_page.set_url(self.settings.companion_url)
    
    def _update_status(self):
        """Update status indicators"""
        # Camera connection status
        status_style = f"""
            color: {COLORS['text']}; 
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """
        status_style_dim = f"""
            color: {COLORS['text_dim']}; 
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """
        
        if self.current_camera_id is not None and self.current_camera_id in self.camera_streams:
            stream = self.camera_streams[self.current_camera_id]
            if stream.is_connected:
                self.connection_status.setText(f"CAM: <span style='color:{COLORS['success']}'>●</span> Connected")
                self.connection_status.setStyleSheet(status_style)
                self.connection_status.setToolTip("Camera connected")
            else:
                self.connection_status.setText(f"CAM: <span style='color:{COLORS['error']}'>●</span> Disconnected")
                self.connection_status.setStyleSheet(status_style)
                self.connection_status.setToolTip(f"Camera disconnected: {stream.error_message}")
        else:
            self.connection_status.setText(f"CAM: <span style='color:{COLORS['text_dark']}'>●</span> No Camera")
            self.connection_status.setStyleSheet(status_style_dim)
            self.connection_status.setToolTip("No camera selected")
        
        # ATEM connection status
        if self.atem_controller.is_connected:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['success']}'>●</span> Connected")
            self.atem_status.setStyleSheet(status_style)
            self.atem_status.setToolTip("ATEM connected")
        elif self.settings.atem.enabled:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['error']}'>●</span> Disconnected")
            self.atem_status.setStyleSheet(status_style)
            self.atem_status.setToolTip("ATEM disconnected")
        else:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['text_dark']}'>●</span> Not Configured")
            self.atem_status.setStyleSheet(status_style_dim)
            self.atem_status.setToolTip("ATEM not configured")
    
    def _update_fps(self):
        """Update FPS display"""
        if self._multiview_active:
            # Show multiview FPS
            self.fps_label.setText(f"{self.multiview_manager.fps:.1f} fps")
        elif self.current_camera_id is not None and self.current_camera_id in self.camera_streams:
            stream = self.camera_streams[self.current_camera_id]
            self.fps_label.setText(f"{stream.fps:.1f} fps")
        else:
            self.fps_label.setText("-- fps")
    
    def _show_system_popup(self):
        """Show system popup with Reboot, Shutdown, and Close options"""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setWindowTitle("System Options")
        msg.setText("Choose an action:")
        msg.setIcon(QMessageBox.Icon.Question)
        
        reboot_btn = msg.addButton("Reboot", QMessageBox.ButtonRole.AcceptRole)
        shutdown_btn = msg.addButton("Shutdown", QMessageBox.ButtonRole.AcceptRole)
        close_btn = msg.addButton("Close", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(cancel_btn)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == reboot_btn:
            self._reboot_system()
        elif clicked == shutdown_btn:
            self._shutdown_system()
        elif clicked == close_btn:
            self._confirm_close()
        # If cancel, do nothing
    
    def _confirm_close(self):
        """Show confirmation dialog before closing"""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Close PanaPiTouch",
            "Are you sure you want to close the application?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
    
    def _reboot_system(self):
        """Show confirmation dialog with save option and reboot the system"""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Reboot System")
        msg.setText("Do you want to save settings before rebooting?")
        msg.setIcon(QMessageBox.Icon.Question)
        
        save_btn = msg.addButton("Save && Reboot", QMessageBox.ButtonRole.AcceptRole)
        no_save_btn = msg.addButton("Reboot Without Saving", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(save_btn)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == cancel_btn:
            return
        
        if clicked == save_btn:
            self.settings.save()
        
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        
        try:
            subprocess.run(['sudo', 'reboot'], check=True)
        except Exception as e:
            print(f"Reboot failed: {e}")
    
    def _shutdown_system(self):
        """Show confirmation dialog with save option and shutdown the system"""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Shutdown System")
        msg.setText("Do you want to save settings before shutting down?")
        msg.setIcon(QMessageBox.Icon.Question)
        
        save_btn = msg.addButton("Save && Shutdown", QMessageBox.ButtonRole.AcceptRole)
        no_save_btn = msg.addButton("Shutdown Without Saving", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(save_btn)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == cancel_btn:
            return
        
        if clicked == save_btn:
            self.settings.save()
        
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        
        try:
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except Exception as e:
            print(f"Shutdown failed: {e}")
    
    def closeEvent(self, event):
        """Handle window close with save confirmation"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Skip dialog if already handled by reboot/shutdown
        if not getattr(self, '_skip_close_dialog', False):
            # Ask user about saving settings
            msg = QMessageBox(self)
            msg.setWindowTitle("Close Application")
            msg.setText("Do you want to save settings before closing?")
            msg.setIcon(QMessageBox.Icon.Question)
            
            save_btn = msg.addButton("Save && Close", QMessageBox.ButtonRole.AcceptRole)
            no_save_btn = msg.addButton("Close Without Saving", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg.setDefaultButton(save_btn)
            msg.exec()
            
            clicked = msg.clickedButton()
            
            if clicked == cancel_btn:
                event.ignore()
                return
            
            # Save settings only if user chose to save
            if clicked == save_btn:
                self.settings.save()
        
        # Stop demo mode if running
        if self._demo_running:
            self._stop_demo_video()
        
        # Stop multiview if running
        if self._multiview_active:
            self.multiview_manager.stop()
        
        # Stop all camera streams
        for stream in self.camera_streams.values():
            stream.stop()
        
        # Disconnect ATEM
        self.atem_controller.disconnect()
        
        event.accept()
    
    def keyPressEvent(self, event):
        """Handle key presses"""
        # F11 - Toggle fullscreen
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        
        # Escape - Exit fullscreen or close
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        
        # Number keys 1-9, 0 - Select camera
        elif Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_9:
            idx = event.key() - Qt.Key.Key_1
            if idx < len(self.settings.cameras):
                self._select_camera(self.settings.cameras[idx].id)
        elif event.key() == Qt.Key.Key_0:
            if len(self.settings.cameras) >= 10:
                self._select_camera(self.settings.cameras[9].id)
        
        # F1-F4 - Toggle overlays
        elif event.key() == Qt.Key.Key_F1:
            self._toggle_overlay("false_color")
        elif event.key() == Qt.Key.Key_F2:
            self._toggle_overlay("waveform")
        elif event.key() == Qt.Key.Key_F3:
            self._toggle_overlay("vectorscope")
        elif event.key() == Qt.Key.Key_F4:
            self._toggle_overlay("focus_assist")
        
        # M - Toggle multiview
        elif event.key() == Qt.Key.Key_M:
            self.multiview_btn.setChecked(not self.multiview_btn.isChecked())
            self._toggle_multiview()
        
        else:
            super().keyPressEvent(event)

