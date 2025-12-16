"""
Main Application Window

The main window with page navigation, camera preview, and controls.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizePolicy,
    QButtonGroup, QSpacerItem, QSlider, QMenu, QDialog, QComboBox,
    QApplication, QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox,
    QDoubleSpinBox, QGroupBox, QRadioButton, QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize, QEvent, QRect, QPoint
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QPixmap, QIcon, QImage, QCursor

from ..config.settings import Settings
from ..camera.stream import CameraStream, StreamConfig
from ..camera.multiview import MultiviewManager, CameraInfo
from ..atem.tally import ATEMTallyController, TallyState
from .preview_widget import PreviewWidget
from .settings_page import SettingsPage
from .widgets import TouchScrollArea
from .camera_page import CameraPage
from .companion_page import CompanionPage
from .joystick_widget import JoystickWidget
# OSK disabled - using Pi OS built-in keyboard instead
# from .keyboard_manager import KeyboardManager
from .toast import ToastWidget
from .osk_widget import OSKWidget
from .preset_rename_dialog import PresetRenameDialog
from .styles import STYLESHEET, COLORS
from ..core.logging_config import get_logger

import shutil
import subprocess
import cv2
import numpy as np
from pathlib import Path
import json

logger = get_logger(__name__)


class PresetButton(QPushButton):
    """Custom preset button with thumbnail support and long press detection"""
    
    long_press_timeout = 500  # milliseconds
    
    def __init__(self, preset_num: int, camera_id: int, main_window, parent=None):
        super().__init__(parent)
        self.preset_num = preset_num
        self.camera_id = camera_id
        self.main_window = main_window
        self.thumbnail_path = self._get_thumbnail_path()
        self.preset_name_path = self._get_preset_name_path()
        self.has_thumbnail = False
        self.preset_name = self._load_preset_name()
        
        # Long press detection
        self._press_timer = QTimer()
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(self._on_long_press)
        self._pressed = False
        
        # Setup button - ensure truly square 80x80px
        self.setFixedSize(80, 80)
        self.setMinimumSize(80, 80)
        self.setMaximumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setObjectName("cameraButton")
        self.setCheckable(False)
        self.setText("")  # No text on button itself
        
        # Load thumbnail if exists
        self._load_thumbnail()
        
        # Connect click
        self.clicked.connect(self._on_click)
    
    def _get_thumbnail_path(self) -> Path:
        """Get thumbnail file path for this preset"""
        preset_dir = Path.home() / ".config" / "panapitouch" / "presets" / str(self.camera_id)
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir / f"preset_{self.preset_num:02d}.jpg"
    
    def _get_preset_name_path(self) -> Path:
        """Get preset name JSON file path"""
        preset_dir = Path.home() / ".config" / "panapitouch" / "presets" / str(self.camera_id)
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir / "preset_names.json"
    
    def _load_preset_name(self) -> str:
        """Load preset name from JSON file"""
        if self.preset_name_path.exists():
            try:
                with open(self.preset_name_path, 'r') as f:
                    names = json.load(f)
                    return names.get(str(self.preset_num), "")
            except Exception as e:
                logger.error(f"Error loading preset name: {e}")
        return ""
    
    def _save_preset_name(self, name: str):
        """Save preset name to JSON file"""
        try:
            names = {}
            if self.preset_name_path.exists():
                with open(self.preset_name_path, 'r') as f:
                    names = json.load(f)
            names[str(self.preset_num)] = name
            with open(self.preset_name_path, 'w') as f:
                json.dump(names, f, indent=2)
            self.preset_name = name
        except Exception as e:
            logger.error(f"Error saving preset name: {e}")
    
    def _load_thumbnail(self):
        """Load thumbnail image if it exists"""
        if self.thumbnail_path.exists():
            try:
                pixmap = QPixmap(str(self.thumbnail_path))
                if not pixmap.isNull():
                    # Thumbnails are saved as 16:9 (80x45px), scale to fit button (80x80)
                    # Keep 16:9 aspect ratio, will fit within 80x80 button
                    scaled = pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    icon = QIcon(scaled)
                    self.setIcon(icon)
                    self.setIconSize(QSize(80, 45))  # 16:9 aspect ratio
                    self.has_thumbnail = True
                    # Ensure button stays square 80x80px - enforce size
                    self.setFixedSize(80, 80)
                    self.setMinimumSize(80, 80)
                    self.setMaximumSize(80, 80)
                    self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                    # Canon-style: saved presets have blue border (secondary color)
                    self.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border: 2px solid {COLORS['secondary']};
                            border-radius: 8px;
                            color: white;
                            font-size: 14px;
                            font-weight: 700;
                            text-align: center;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            border-color: {COLORS['primary']};
                            border-width: 3px;
                        }}
                        QPushButton:pressed {{
                            border-color: {COLORS['primary']};
                            background-color: rgba(255, 149, 0, 0.3);
                        }}
                    """)
                    return
            except Exception as e:
                logger.error(f"Error loading thumbnail for preset {self.preset_num}: {e}")
        
        # No thumbnail - use Canon-inspired empty preset style
        self.has_thumbnail = False
        self.setIcon(QIcon())  # Clear icon
        # Ensure button stays square 80x80px - enforce size
        self.setFixedSize(80, 80)
        self.setMinimumSize(80, 80)
        self.setMaximumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_dim']};
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
                border-color: {COLORS['primary']};
                color: {COLORS['text']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
    
    def mousePressEvent(self, event):
        """Handle mouse press for long press detection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._press_timer.start(self.long_press_timeout)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - cancel long press if released early"""
        if event.button() == Qt.MouseButton.LeftButton:
            was_pressed = self._pressed
            timer_was_active = self._press_timer.isActive()
            self._press_timer.stop()
            self._pressed = False
            
            # If released before long press timeout, treat as short click
            if was_pressed and not timer_was_active:
                # Timer already fired (long press happened)
                pass  # Long press menu was shown
            elif was_pressed:
                # Released early - this was a short click
                self._on_click()
        super().mouseReleaseEvent(event)
    
    def _on_click(self):
        """Handle short click - recall preset"""
        if self.main_window.current_camera_id == self.camera_id:
            self.main_window._send_camera_command(f"R{self.preset_num:02d}", endpoint="aw_ptz")
            if hasattr(self.main_window, "toast") and self.main_window.toast:
                self.main_window.toast.show_message(f"Recalled Preset {self.preset_num}", duration=1500)
    
    def _on_long_press(self):
        """Handle long press - show context menu"""
        if not self._pressed:
            return
        
        menu = QMenu(self)
        # Make menu touch-friendly with larger items
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 18px;
                font-weight: 600;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 16px 24px;
                border-radius: 6px;
                min-width: 200px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['surface_hover']};
                color: {COLORS['primary']};
            }}
        """)
        
        save_action = menu.addAction("💾 Save Preset")
        save_action.triggered.connect(self._save_preset)
        
        if self.has_thumbnail:
            rename_action = menu.addAction("✏️ Rename Preset")
            rename_action.triggered.connect(self._rename_preset)
            
            delete_action = menu.addAction("🗑️ Delete Preset")
            delete_action.triggered.connect(self._delete_preset)
        
        # Show menu below button
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        menu.exec(global_pos)
        self._pressed = False
    
    def _save_preset(self):
        """Save current camera position as preset with thumbnail"""
        if self.main_window.current_camera_id != self.camera_id:
            if hasattr(self.main_window, "toast") and self.main_window.toast:
                self.main_window.toast.show_message("Please select the correct camera first", duration=2000)
            return
        
        # Save preset position
        success = self.main_window._send_camera_command(f"M{self.preset_num:02d}", endpoint="aw_ptz")
        if not success:
            if hasattr(self.main_window, "toast") and self.main_window.toast:
                self.main_window.toast.show_message("Failed to save preset", duration=2000, error=True)
            return
        
        # Capture thumbnail from current camera frame
        thumbnail_saved = self.main_window._capture_preset_thumbnail(self.camera_id, self.preset_num)
        
        if thumbnail_saved:
            self._load_thumbnail()
            # Update label if it exists
            if hasattr(self, '_name_label'):
                display_name = self.preset_name if self.preset_name else str(self.preset_num)
                self._name_label.setText(display_name)
            if hasattr(self.main_window, "toast") and self.main_window.toast:
                self.main_window.toast.show_message(f"Preset {self.preset_num} saved", duration=2000)
        else:
            if hasattr(self.main_window, "toast") and self.main_window.toast:
                self.main_window.toast.show_message(f"Preset {self.preset_num} saved (no thumbnail)", duration=2000)

        # Prompt for name immediately after saving (custom OSK dialog)
        # (Works even if thumbnail capture failed.)
        QTimer.singleShot(150, self._rename_preset)
    
    def _rename_preset(self):
        """Rename preset"""
        current_name = self.preset_name if self.preset_name else f"Preset {self.preset_num}"
        
        # Use custom dialog with OSK for Live/Preview page
        dialog = PresetRenameDialog(self.preset_num, current_name, self.main_window)
        dialog.accepted.connect(lambda name: self._on_preset_renamed(name))
        dialog.exec()
    
    def _on_preset_renamed(self, name: str):
        """Handle preset rename from dialog"""
        self._save_preset_name(name)
        # Update the label above button if it exists
        if hasattr(self, '_name_label'):
            self._name_label.setText(name if name else str(self.preset_num))
        if hasattr(self.main_window, "toast") and self.main_window.toast:
            self.main_window.toast.show_message(f"Preset {self.preset_num} renamed", duration=2000)
    
    def _delete_preset(self):
        """Delete preset and thumbnail"""
        # Delete camera's internal preset thumbnail (OSJ:3A command)
        # Note: Preset numbers are 0-indexed for OSJ:3A (00-99), so preset 1 = 00, preset 2 = 01, etc.
        preset_index = self.preset_num - 1  # Convert to 0-indexed
        self.main_window._send_camera_command(f"OSJ:3A:{preset_index:02d}", endpoint="aw_cam")
        
        # Delete local thumbnail file
        if self.thumbnail_path.exists():
            try:
                self.thumbnail_path.unlink()
            except Exception as e:
                logger.error(f"Error deleting thumbnail: {e}")
        
        # Delete preset name
        try:
            if self.preset_name_path.exists():
                with open(self.preset_name_path, 'r') as f:
                    names = json.load(f)
                if str(self.preset_num) in names:
                    del names[str(self.preset_num)]
                    with open(self.preset_name_path, 'w') as f:
                        json.dump(names, f, indent=2)
        except Exception as e:
            logger.error(f"Error deleting preset name: {e}")
        
        self.preset_name = ""
        
        # Reload button (will show empty state)
        self._load_thumbnail()
        # Update the label above button if it exists
        if hasattr(self, '_name_label'):
            self._name_label.setText(str(self.preset_num))
        if hasattr(self.main_window, "toast") and self.main_window.toast:
            self.main_window.toast.show_message(f"Preset {self.preset_num} deleted", duration=2000)


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
        
        
        # Split view state
        self._split_enabled = False
        self._split_camera_id = None
        self._split_mode = 'side'  # 'side' or 'top'
        
        # ATEM controller
        self.atem_controller = ATEMTallyController()
        
        # Toast notification widget
        self.toast = ToastWidget(self)
        
        # On-Screen Keyboard (slides from bottom for settings pages)
        self.osk = None  # Will be created after UI setup
        
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._setup_osk()
        
        # Initialize ATEM connection if configured
        if self.settings.atem.enabled and self.settings.atem.ip_address:
            self.atem_controller.connect(self.settings.atem.ip_address)
        
        # Start with demo mode to give services time to initialize
        # This ensures all system services are ready before connecting to cameras
        # Delay ensures UI is fully set up before starting demo
        QTimer.singleShot(500, self._start_demo_on_init)
        
        # Switch to first camera after delay (gives services time to start)
        if self.settings.cameras:
            # Longer delay to ensure services are fully initialized
            QTimer.singleShot(3000, lambda: self._switch_from_demo_to_camera(self.settings.cameras[0].id))
    
    def _setup_window(self):
        """Setup window properties"""
        self.setWindowTitle("PanaPiTouch - PTZ Camera Monitor")
        
        # Remove window decorations for fullscreen app look (no title bar, no borders)
        # But allow keyboard to appear on top by not using WindowStaysOnTopHint
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Enable touch events on main window
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        
        # Set stylesheet
        self.setStyleSheet(STYLESHEET)
        
        # Show window first to ensure screen geometry is available
        self.show()
        
        # Set window to fullscreen at native resolution
        self.setWindowState(Qt.WindowState.WindowFullScreen)
    
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
        self.nav_bar = nav_bar
        main_layout.addWidget(nav_bar)
        
        # Page stack
        self.page_stack = QStackedWidget()
        
        # Create pages
        self.preview_page = self._create_preview_page()
        self.camera_page = CameraPage(self.settings)
        self.companion_page = CompanionPage(self.settings.companion_url)
        self.companion_page.update_available.connect(self._on_companion_update_available)
        self.companion_page.update_cleared.connect(self._on_companion_update_cleared)
        self.settings_page = SettingsPage(self.settings, parent=self)
        
        self.page_stack.addWidget(self.preview_page)       # 0
        self.page_stack.addWidget(self.camera_page)        # 1
        self.page_stack.addWidget(self.companion_page)     # 2
        self.page_stack.addWidget(self.settings_page)      # 3
        
        main_layout.addWidget(self.page_stack, stretch=1)
        
    
    def _create_nav_bar(self) -> QWidget:
        """Create the top navigation bar"""
        nav_bar = QFrame()
        # Add border-bottom for separation
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
        
        # Add stretch to center buttons
        layout.addStretch()
        
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
        
        # Add stretch after buttons to keep them centered
        layout.addStretch()
        
        # Companion update is surfaced in Settings → Companion (not in top nav).
        self.companion_update_btn = None
        
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
        """Create the preview page - landscape or portrait based on settings"""
        if self.settings.portrait_mode:
            return self._create_preview_page_portrait()
        else:
            return self._create_preview_page_landscape()
    
    def _create_preview_page_landscape(self) -> QWidget:
        """Create the landscape preview page with side panel (16:10 optimized)"""
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

    def _create_preview_page_portrait(self) -> QWidget:
        """Create the portrait preview page with bottom panel (vertical layout)"""
        page = QWidget()
        page.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['surface']};
            }}
        """)
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)  # No margins - full screen
        main_layout.setSpacing(0)  # No spacing between elements
        
        # Preview container - full width, no border, 16:9 aspect ratio
        preview_container = QFrame()
        preview_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: none;
            }}
        """)
        # Maintain 16:9 aspect ratio - Expanding horizontally, Preferred vertically (will be constrained by aspect ratio)
        preview_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        preview_inner_layout = QVBoxLayout(preview_container)
        preview_inner_layout.setContentsMargins(0, 0, 0, 0)
        preview_inner_layout.setSpacing(0)
        
        # Preview wrapper (for FPS overlay positioning)
        preview_wrapper = QWidget()
        preview_wrapper.setStyleSheet("background: transparent;")
        preview_wrapper_layout = QVBoxLayout(preview_wrapper)
        preview_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        preview_wrapper_layout.setSpacing(0)
        
        self.preview_widget = PreviewWidget()
        preview_wrapper_layout.addWidget(self.preview_widget, stretch=1)
        
        # FPS label (top-left corner overlay) - absolutely positioned
        self.fps_label = QLabel("-- fps", preview_wrapper)
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.fps_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: 11px;
            font-weight: 600;
            background-color: rgba(0, 0, 0, 0.5);
            padding: 2px 6px;
            border-radius: 4px;
        """)
        self.fps_label.setFixedHeight(20)
        self.fps_label.setFixedWidth(60)  # Fixed width so it doesn't resize
        # Position at top-left corner (8px from top and left)
        self.fps_label.move(8, 8)
        self.fps_label.raise_()  # Bring to front
        
        preview_inner_layout.addWidget(preview_wrapper, stretch=1)
        
        # Store reference for aspect ratio calculation
        self.preview_container_portrait = preview_container
        
        # Add to layout without stretch - preview will size to its 16:9 aspect ratio
        main_layout.addWidget(preview_container)
        
        # Install event filter to maintain 16:9 aspect ratio
        preview_container.installEventFilter(self)
        
        # Overlay buttons bar at bottom of preview (full width, app-wide)
        overlay_buttons_bar = self._create_overlay_buttons_bar()
        main_layout.addWidget(overlay_buttons_bar)
        
        # Bottom menu bar (horizontal buttons)
        bottom_menu = self._create_bottom_menu_bar()
        main_layout.addWidget(bottom_menu)
        
        # Bottom panel (QStackedWidget with all panels) - expands to fill remaining space
        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel, stretch=1)  # Give it stretch to fill remaining space
        
        # Camera selection bar (moved to bottom)
        camera_bar = self._create_camera_bar()
        main_layout.addWidget(camera_bar)
        
        # Set initial aspect ratio after a short delay to ensure widget is sized
        QTimer.singleShot(100, lambda: self._update_preview_aspect_ratio())
        
        return page
    
    def _update_preview_aspect_ratio(self):
        """Update preview container height to maintain 16:9 aspect ratio"""
        if hasattr(self, 'preview_container_portrait') and self.preview_container_portrait:
            width = self.preview_container_portrait.width()
            if width > 0:
                height_16_9 = int(width * 9 / 16)
                # Set both min and max height to maintain aspect ratio
                self.preview_container_portrait.setMinimumHeight(height_16_9)
                self.preview_container_portrait.setMaximumHeight(height_16_9)
    
    def _show_margin_debug_overlay(self):
        """Show or cycle display mode of visual overlay lines displaying all margins/padding for debugging"""
        if not hasattr(self, 'settings') or not self.settings.portrait_mode:
            print("Margin debug overlay only available in portrait mode")
            return
        
        # Cycle mode if overlay exists and is visible
        if hasattr(self, 'margin_debug_overlay') and self.margin_debug_overlay:
            if self.margin_debug_overlay.isVisible():
                # Cycle to next display mode
                self.margin_debug_overlay.cycle_display_mode()
            else:
                # Show overlay with current mode
                self.margin_debug_overlay.setVisible(True)
            return
        
        # Create custom widget that draws margin/padding lines
        class MarginDebugOverlay(QWidget):
            # Display modes: 0=all, 1=borders only, 2=margins only, 3=padding only
            DISPLAY_MODE_ALL = 0
            DISPLAY_MODE_BORDERS = 1
            DISPLAY_MODE_MARGINS = 2
            DISPLAY_MODE_PADDING = 3
            
            def __init__(self, parent, main_window):
                super().__init__(parent)
                self.main_window = main_window
                self.display_mode = self.DISPLAY_MODE_ALL  # Start with all visible
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.setStyleSheet("background: transparent;")
                self.drawn_labels = []  # Track drawn label rectangles to prevent overlap
            
            def cycle_display_mode(self):
                """Cycle through display modes"""
                self.display_mode = (self.display_mode + 1) % 4
                self.update()  # Trigger repaint
                mode_names = ["All", "Borders Only", "Margins Only", "Padding Only"]
                print(f"Display mode: {mode_names[self.display_mode]}")
            
            def get_widget_rect(self, widget):
                """Get widget rectangle in preview_page coordinates"""
                try:
                    widget_global_pos = widget.mapToGlobal(widget.rect().topLeft())
                    overlay_global_pos = self.main_window.preview_page.mapToGlobal(self.main_window.preview_page.rect().topLeft())
                    dx = widget_global_pos.x() - overlay_global_pos.x()
                    dy = widget_global_pos.y() - overlay_global_pos.y()
                    return QRect(dx, dy, widget.width(), widget.height())
                except Exception:
                    try:
                        widget_pos = widget.mapTo(self.main_window.preview_page, widget.rect().topLeft())
                        return QRect(widget_pos.x(), widget_pos.y(), widget.width(), widget.height())
                    except:
                        return widget.geometry()
            
            def get_widget_attribute_name(self, widget):
                """Find the attribute name of a widget in main_window"""
                try:
                    for attr_name in dir(self.main_window):
                        if not attr_name.startswith('_'):
                            attr_value = getattr(self.main_window, attr_name, None)
                            if attr_value is widget:
                                return attr_name
                    # Try to find in parent's children
                    if widget.parent():
                        parent = widget.parent()
                        for attr_name in dir(parent):
                            if not attr_name.startswith('_'):
                                try:
                                    attr_value = getattr(parent, attr_name, None)
                                    if attr_value is widget:
                                        return attr_name
                                except:
                                    pass
                except:
                    pass
                return None
            
            def draw_widget_margins(self, painter, widget, widget_rect, margin_pen, padding_pen, border_pen, widget_name=None, draw_children=True):
                """Draw margins, padding, and border for a widget"""
                is_small_widget = widget.width() < 200 or widget.height() < 50
                pen_width = 1 if is_small_widget else 2
                
                # Get widget name if not provided
                if widget_name is None:
                    widget_name = self.get_widget_attribute_name(widget)
                    if widget_name is None:
                        widget_name = widget.__class__.__name__
                
                # Check layout properties first to determine what will be drawn
                layout = widget.layout()
                will_draw_border = (self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_BORDERS)
                will_draw_margins = False
                will_draw_padding = False
                
                if layout:
                    margins = layout.getContentsMargins()
                    has_margins = any(m > 0 for m in margins)
                    has_padding = any(m > 0 for m in margins)  # Padding area exists if margins exist
                    
                    # Check if margins will actually be drawn
                    if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS:
                        will_draw_margins = has_margins
                    
                    # Check if padding area will actually be drawn
                    if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_PADDING:
                        will_draw_padding = has_padding
                
                # Determine if we should show labels - only when the relevant visual element is being drawn
                should_show_label = False
                
                if self.display_mode == self.DISPLAY_MODE_ALL:
                    # In "All" mode, show labels for all widgets
                    should_show_label = True
                elif self.display_mode == self.DISPLAY_MODE_BORDERS:
                    # In "Borders Only" mode, show labels only when borders are drawn (all widgets)
                    should_show_label = will_draw_border
                elif self.display_mode == self.DISPLAY_MODE_MARGINS:
                    # In "Margins Only" mode, only show labels when margin lines are actually drawn
                    should_show_label = will_draw_margins
                elif self.display_mode == self.DISPLAY_MODE_PADDING:
                    # In "Padding Only" mode, only show labels when padding area is actually drawn
                    should_show_label = will_draw_padding
                
                # Draw widget name and height label (only if relevant and widget is large enough)
                if should_show_label and widget_rect.width() > 50 and widget_rect.height() > 30:
                    painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                    font_size = 8 if is_small_widget else 9
                    painter.setFont(QFont("Courier New", font_size))
                    
                    # In Borders Only mode, only show name and height (no width)
                    if self.display_mode == self.DISPLAY_MODE_BORDERS:
                        label_text = f"{widget_name}\nH:{widget.height()}px"
                    else:
                        label_text = f"{widget_name}\nH:{widget.height()}px"
                        if widget.width() > 150:  # Only show width if widget is large enough
                            label_text += f" W:{widget.width()}px"
                    
                    # Calculate actual label size
                    fm = painter.fontMetrics()
                    # Find the widest line for multi-line text
                    lines = label_text.split('\n')
                    text_width = max([fm.horizontalAdvance(line) for line in lines])
                    text_height = fm.height() * len(lines)
                    label_size = QSize(text_width + 6, text_height + 6)  # Add padding
                    
                    # Find a non-overlapping position
                    label_pos = self.find_non_overlapping_position(widget_rect, label_size, padding=5)
                    
                    if label_pos:
                        # Ensure label stays within widget bounds
                        label_x = max(widget_rect.left() + 2, min(label_pos.x(), widget_rect.right() - label_size.width() - 2))
                        label_y = max(widget_rect.top() + 2, min(label_pos.y(), widget_rect.bottom() - label_size.height() - 2))
                        
                        label_bg = QRect(label_x, label_y, label_size.width(), label_size.height())
                        
                        # Draw background and text
                        painter.fillRect(label_bg, QColor(0, 0, 0, 220))
                        painter.drawText(label_x + 3, label_y + 3, label_text)
                        
                        # Record this label to prevent future overlaps
                        self.drawn_labels.append(label_bg)
                
                # Draw widget border (green) - if mode is ALL or BORDERS_ONLY
                if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_BORDERS:
                    painter.setPen(QPen(QColor(0, 255, 0, 150), pen_width, Qt.PenStyle.SolidLine))
                    painter.drawRect(widget_rect)
                
                # Get layout margins
                layout = widget.layout()
                if layout:
                    margins = layout.getContentsMargins()
                    left_margin, top_margin, right_margin, bottom_margin = margins
                    spacing = layout.spacing()
                    
                    # Draw margin lines (red dashed) - if mode is ALL or MARGINS_ONLY
                    if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS:
                        margin_line_width = 1 if is_small_widget else 2
                        margin_pen_thin = QPen(QColor(255, 0, 0, 200), margin_line_width, Qt.PenStyle.DashLine)
                        
                        # Left margin
                        if left_margin > 0:
                            painter.setPen(margin_pen_thin)
                            painter.drawLine(
                                widget_rect.left() - left_margin, widget_rect.top(),
                                widget_rect.left() - left_margin, widget_rect.bottom()
                            )
                            # Only draw margin text when in MARGINS_ONLY or ALL mode
                            if (not is_small_widget) and (self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS):
                                painter.setPen(QPen(QColor(255, 0, 0, 255), 1))
                                painter.drawText(
                                    widget_rect.left() - left_margin - 30, widget_rect.top() + 15,
                                    f"M:{left_margin}"
                                )
                        
                        # Top margin
                        if top_margin > 0:
                            painter.setPen(margin_pen_thin)
                            painter.drawLine(
                                widget_rect.left(), widget_rect.top() - top_margin,
                                widget_rect.right(), widget_rect.top() - top_margin
                            )
                            # Only draw margin text when in MARGINS_ONLY or ALL mode
                            if (not is_small_widget) and (self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS):
                                painter.setPen(QPen(QColor(255, 0, 0, 255), 1))
                                painter.drawText(
                                    widget_rect.left() + 5, widget_rect.top() - top_margin - 5,
                                    f"M:{top_margin}"
                                )
                        
                        # Right margin
                        if right_margin > 0:
                            painter.setPen(margin_pen_thin)
                            painter.drawLine(
                                widget_rect.right() + right_margin, widget_rect.top(),
                                widget_rect.right() + right_margin, widget_rect.bottom()
                            )
                            # Only draw margin text when in MARGINS_ONLY or ALL mode
                            if (not is_small_widget) and (self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS):
                                painter.setPen(QPen(QColor(255, 0, 0, 255), 1))
                                painter.drawText(
                                    widget_rect.right() + right_margin + 5, widget_rect.top() + 15,
                                    f"M:{right_margin}"
                                )
                        
                        # Bottom margin
                        if bottom_margin > 0:
                            painter.setPen(margin_pen_thin)
                            painter.drawLine(
                                widget_rect.left(), widget_rect.bottom() + bottom_margin,
                                widget_rect.right(), widget_rect.bottom() + bottom_margin
                            )
                            # Only draw margin text when in MARGINS_ONLY or ALL mode
                            if (not is_small_widget) and (self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS):
                                painter.setPen(QPen(QColor(255, 0, 0, 255), 1))
                                painter.drawText(
                                    widget_rect.left() + 5, widget_rect.bottom() + bottom_margin + 15,
                                    f"M:{bottom_margin}"
                                )
                    
                    # Draw padding lines (blue dotted) - if mode is ALL or PADDING_ONLY
                    if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_PADDING:
                        if left_margin > 0 or top_margin > 0 or right_margin > 0 or bottom_margin > 0:
                            padding_line_width = 1 if is_small_widget else 2
                            padding_pen_thin = QPen(QColor(0, 0, 255, 200), padding_line_width, Qt.PenStyle.DotLine)
                            painter.setPen(padding_pen_thin)
                            padding_rect = QRect(
                                widget_rect.left() + left_margin,
                                widget_rect.top() + top_margin,
                                widget_rect.width() - left_margin - right_margin,
                                widget_rect.height() - top_margin - bottom_margin
                            )
                            painter.drawRect(padding_rect)
                    
                    # Draw spacing between items (yellow)
                    if spacing > 0 and draw_children:
                        spacing_pen = QPen(QColor(255, 255, 0, 150), 1, Qt.PenStyle.DashDotLine)
                        painter.setPen(spacing_pen)
                        # This is approximate - spacing is between items
                        # We'll draw it when we process children
                
                # Draw children widgets recursively
                if draw_children:
                    for child in widget.findChildren(QWidget):
                        if child.isVisible() and child.parent() == widget:
                            child_rect = self.get_widget_rect(child)
                            # Only draw if child is reasonably sized (not too small)
                            if child_rect.width() > 10 and child_rect.height() > 10:
                                child_name = self.get_widget_attribute_name(child)
                                if child_name is None:
                                    child_name = child.objectName() or child.__class__.__name__
                                self.draw_widget_margins(painter, child, child_rect, margin_pen, padding_pen, border_pen, widget_name=child_name, draw_children=True)
            
            def check_label_overlap(self, label_rect, padding=5):
                """Check if a label rectangle would overlap with existing labels"""
                expanded_rect = label_rect.adjusted(-padding, -padding, padding, padding)
                for existing_rect in self.drawn_labels:
                    if expanded_rect.intersects(existing_rect):
                        return True
                return False
            
            def find_non_overlapping_position(self, widget_rect, label_size, padding=5):
                """Find a non-overlapping position for a label within or near the widget"""
                label_width, label_height = label_size.width(), label_size.height()
                
                # Try different positions: top-left, top-right, bottom-left, bottom-right, center
                positions = [
                    (widget_rect.left() + 5, widget_rect.top() + 5),  # Top-left
                    (widget_rect.right() - label_width - 5, widget_rect.top() + 5),  # Top-right
                    (widget_rect.left() + 5, widget_rect.bottom() - label_height - 5),  # Bottom-left
                    (widget_rect.right() - label_width - 5, widget_rect.bottom() - label_height - 5),  # Bottom-right
                    (widget_rect.left() + (widget_rect.width() - label_width) // 2, 
                     widget_rect.top() + (widget_rect.height() - label_height) // 2),  # Center
                ]
                
                for x, y in positions:
                    test_rect = QRect(x, y, label_width, label_height)
                    if not self.check_label_overlap(test_rect, padding):
                        return test_rect
                
                # If all positions overlap, return None to skip this label
                return None
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Clear drawn labels at start of paint
                self.drawn_labels = []
                
                # Red pen for margins
                margin_pen = QPen(QColor(255, 0, 0, 200), 2, Qt.PenStyle.DashLine)
                # Blue pen for padding
                padding_pen = QPen(QColor(0, 0, 255, 200), 2, Qt.PenStyle.DotLine)
                # Green pen for widget borders
                border_pen = QPen(QColor(0, 255, 0, 150), 1, Qt.PenStyle.SolidLine)
                
                # Draw margins and padding for each widget
                widgets_to_check = []
                
                # Main page layout
                if hasattr(self.main_window, 'preview_page') and self.main_window.preview_page:
                    widgets_to_check.append(('preview_page', self.main_window.preview_page))
                
                # Overlay buttons bar
                if hasattr(self.main_window, 'overlay_buttons_bar') and self.main_window.overlay_buttons_bar:
                    widgets_to_check.append(('overlay_buttons_bar', self.main_window.overlay_buttons_bar))
                
                # Preview container
                if hasattr(self.main_window, 'preview_container_portrait') and self.main_window.preview_container_portrait:
                    widgets_to_check.append(('preview_container_portrait', self.main_window.preview_container_portrait))
                
                # Camera bar
                if hasattr(self.main_window, 'camera_bar') and self.main_window.camera_bar:
                    widgets_to_check.append(('camera_bar', self.main_window.camera_bar))
                
                # Bottom menu bar
                if hasattr(self.main_window, 'bottom_menu_bar') and self.main_window.bottom_menu_bar:
                    widgets_to_check.append(('bottom_menu_bar', self.main_window.bottom_menu_bar))
                
                # Bottom panel
                if hasattr(self.main_window, 'bottom_panel') and self.main_window.bottom_panel:
                    widgets_to_check.append(('bottom_panel', self.main_window.bottom_panel))
                
                for attr_name, widget in widgets_to_check:
                    if not widget.isVisible():
                        continue
                    
                    # Get widget geometry in overlay's coordinate system (preview_page)
                    widget_rect = self.get_widget_rect(widget)
                    
                    # Draw widget margins/padding and all children recursively
                    self.draw_widget_margins(painter, widget, widget_rect, margin_pen, padding_pen, border_pen, widget_name=attr_name, draw_children=True)
                
                # Draw legend in top-right corner
                legend_y = 10
                legend_x = self.width() - 240
                painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                painter.setFont(QFont("Arial", 10))
                
                # Mode names
                mode_names = ["All", "Borders Only", "Margins Only", "Padding Only"]
                current_mode = mode_names[self.display_mode]
                
                # Adjust legend height based on what's visible
                legend_height = 110
                painter.fillRect(legend_x - 5, legend_y - 5, 235, legend_height, QColor(0, 0, 0, 200))
                
                # Current mode indicator
                painter.setPen(QPen(QColor(255, 255, 0, 255), 1))
                painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
                painter.drawText(legend_x, legend_y + 15, f"Mode: {current_mode}")
                
                painter.setFont(QFont("Arial", 10))
                painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                
                # Only show legend items that are visible in current mode
                y_offset = 30
                
                if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_BORDERS:
                    painter.setPen(QPen(QColor(0, 255, 0, 255), 2))
                    painter.drawLine(legend_x, legend_y + y_offset, legend_x + 20, legend_y + y_offset)
                    painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                    painter.drawText(legend_x + 25, legend_y + y_offset + 5, "Widget border")
                    y_offset += 20
                
                if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_MARGINS:
                    painter.setPen(QPen(QColor(255, 0, 0, 255), 2, Qt.PenStyle.DashLine))
                    painter.drawLine(legend_x, legend_y + y_offset, legend_x + 20, legend_y + y_offset)
                    painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                    painter.drawText(legend_x + 25, legend_y + y_offset + 5, "Margin")
                    y_offset += 20
                
                if self.display_mode == self.DISPLAY_MODE_ALL or self.display_mode == self.DISPLAY_MODE_PADDING:
                    painter.setPen(QPen(QColor(0, 0, 255, 255), 2, Qt.PenStyle.DotLine))
                    painter.drawLine(legend_x, legend_y + y_offset, legend_x + 20, legend_y + y_offset)
                    painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                    painter.drawText(legend_x + 25, legend_y + y_offset + 5, "Padding area")
                    y_offset += 20
                
                painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
                painter.drawText(legend_x, legend_y + y_offset + 5, "Press Ctrl+M to cycle modes")
        
        # Create overlay widget that covers the preview page
        overlay = MarginDebugOverlay(self.preview_page, self)
        
        # Make overlay cover entire preview page
        def update_overlay_geometry():
            if overlay and self.preview_page:
                overlay.setGeometry(0, 0, self.preview_page.width(), self.preview_page.height())
                overlay.update()  # Trigger repaint
        
        update_overlay_geometry()
        
        # Update geometry periodically to handle resizes
        resize_timer = QTimer()
        resize_timer.timeout.connect(update_overlay_geometry)
        resize_timer.start(100)
        overlay.resize_timer = resize_timer  # Keep reference
        
        overlay.setParent(self.preview_page)
        overlay.raise_()
        overlay.show()
        
        self.margin_debug_overlay = overlay
        
        # Auto-hide after 15 seconds
        QTimer.singleShot(15000, lambda: overlay.hide() if hasattr(self, 'margin_debug_overlay') and self.margin_debug_overlay else None)
        
        print("Margin debug overlay shown. Press Ctrl+M to cycle display modes.")
        print("Modes: All → Borders Only → Margins Only → Padding Only")
    
    def _create_bottom_menu_bar(self) -> QWidget:
        """Create horizontal menu bar for bottom panel tabs - matches top menu style"""
        menu_bar = QFrame()
        menu_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        menu_bar.setFixedHeight(60)  # Reduced height - less padding
        
        layout = QHBoxLayout(menu_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)
        
        # Camera name label on the left (Canon-style blue accent)
        self.bottom_menu_camera_label = QLabel("📹 No Camera")
        self.bottom_menu_camera_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Left align, vertically center
        self.bottom_menu_camera_label.setWordWrap(True)  # Allow word wrapping if needed
        self.bottom_menu_camera_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['secondary']};
                font-weight: 600;
                padding: 0 8px;
            }}
        """)
        self.bottom_menu_camera_label.setMinimumWidth(80)  # Half width to prevent overflow
        self.bottom_menu_camera_label.setMaximumWidth(80)  # Fixed width to prevent expansion
        self.bottom_menu_camera_label.setMinimumHeight(30)  # Minimum height for word wrapping
        layout.addWidget(self.bottom_menu_camera_label)
        
        # Add stretch to center buttons
        layout.addStretch()
        
        # Menu buttons container (centered)
        menu_buttons_container = QWidget()
        menu_buttons_container.setStyleSheet("background: transparent;")
        menu_buttons_layout = QHBoxLayout(menu_buttons_container)
        menu_buttons_layout.setContentsMargins(0, 0, 0, 0)
        menu_buttons_layout.setSpacing(0)
        
        self.bottom_menu_button_group = QButtonGroup(self)
        self.bottom_menu_button_group.setExclusive(True)
        
        # Menu buttons: Presets, Camera Control, Guides, Multiview
        menu_buttons = [
            ("🎮 Presets", 0),
            ("⚙️ Camera Control", 1),
            ("📐 Guides", 2),
            ("📺 Multiview", 3),
        ]
        
        for text, panel_idx in menu_buttons:
            btn = QPushButton(text)
            btn.setObjectName("navButton")  # Use same style as top menu
            btn.setCheckable(True)
            btn.setFixedHeight(60)  # Match menu bar height - reduced padding
            btn.setMinimumWidth(150)
            
            self.bottom_menu_button_group.addButton(btn, panel_idx)
            menu_buttons_layout.addWidget(btn)
            
            if panel_idx == 0:
                btn.setChecked(True)  # Default to Presets
        
        self.bottom_menu_button_group.idClicked.connect(self._switch_bottom_panel)
        
        layout.addWidget(menu_buttons_container)
        
        # Add stretch after buttons to balance layout
        layout.addStretch()
        
        # Empty spacer on right to balance with camera label
        right_spacer = QWidget()
        right_spacer.setMinimumWidth(80)  # Half width to match camera label
        right_spacer.setStyleSheet("background: transparent;")
        layout.addWidget(right_spacer)
        
        return menu_bar
    
    def _create_bottom_panel(self) -> QWidget:
        """Create bottom panel with QStackedWidget containing all control panels"""
        # Container frame
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        # Minimum height of 300px, but allow expansion to fill remaining space
        container.setMinimumHeight(300)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stacked widget for panels
        self.bottom_panel_stack = QStackedWidget()
        self.bottom_panel_stack.setStyleSheet("QStackedWidget { background: transparent; }")
        
        # Create and add panels
        # Panel 0: Presets
        presets_panel = self._create_presets_panel()
        self.bottom_panel_stack.addWidget(presets_panel)
        
        # Panel 1: Camera Control
        camera_control_panel = self._create_camera_control_panel_content()
        self.bottom_panel_stack.addWidget(camera_control_panel)
        
        # Panel 2: Guides (includes Grid options)
        guides_panel = self._create_frame_guides_panel_content()
        self.bottom_panel_stack.addWidget(guides_panel)
        
        # Panel 3: Multiview
        multiview_panel = self._create_multiview_panel_content()
        self.bottom_panel_stack.addWidget(multiview_panel)
        
        layout.addWidget(self.bottom_panel_stack)
        
        return container
    
    def _switch_bottom_panel(self, index: int):
        """Switch bottom panel content based on menu button selection"""
        self.bottom_panel_stack.setCurrentIndex(index)
        # Refresh preset panel if switching to it (to ensure correct camera presets are shown)
        if index == 0:  # Presets panel
            self._refresh_presets_panel()
    
    def _refresh_camera_dependent_panels(self):
        """Refresh panels that depend on the current camera selection"""
        # Refresh preset panel if it's currently visible
        if hasattr(self, 'bottom_panel_stack') and self.bottom_panel_stack.currentIndex() == 0:
            self._refresh_presets_panel()
    
    def _refresh_presets_panel(self):
        """Refresh the presets panel to show presets for the current camera"""
        if not hasattr(self, 'bottom_panel_stack'):
            return
        
        # Store current index to restore it
        current_index = self.bottom_panel_stack.currentIndex()
        was_on_presets = (current_index == 0)
        
        # Get current presets panel widget
        presets_panel_widget = self.bottom_panel_stack.widget(0)
        if presets_panel_widget is None:
            return
        
        # Remove old panel
        self.bottom_panel_stack.removeWidget(presets_panel_widget)
        presets_panel_widget.deleteLater()
        
        # Create new panel with current camera
        new_presets_panel = self._create_presets_panel()
        self.bottom_panel_stack.insertWidget(0, new_presets_panel)
        
        # Restore current index
        self.bottom_panel_stack.setCurrentIndex(current_index)
    
    def _create_ptz_panel_content(self) -> QWidget:
        """Create PTZ control panel content (for portrait bottom panel)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Virtual Joystick
        joystick_container = QWidget()
        joystick_layout = QHBoxLayout(joystick_container)
        joystick_layout.setContentsMargins(0, 0, 0, 0)
        joystick_layout.addStretch()
        
        # Reuse existing joystick if available, otherwise create new
        if not hasattr(self, 'ptz_joystick'):
            self.ptz_joystick = JoystickWidget()
            self.ptz_joystick.setFixedSize(140, 140)
            self.ptz_joystick.position_changed.connect(self._on_joystick_move)
            self.ptz_joystick.released.connect(self._on_joystick_release)
        
        joystick_layout.addWidget(self.ptz_joystick)
        joystick_layout.addStretch()
        layout.addWidget(joystick_container)
        
        # Zoom Slider
        zoom_label = QLabel("Zoom")
        zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_dim']}; background: transparent; border: none;")
        layout.addWidget(zoom_label)
        
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
        
        layout.addLayout(zoom_row)
        layout.addStretch()
        
        return widget
    
    def _create_overlay_buttons_bar(self) -> QWidget:
        """Create overlay buttons bar at bottom of preview - full width app-wide"""
        bar = QWidget()
        bar.setFixedHeight(50)  # Bar height with reduced padding
        bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['surface']};
                border: none;
            }}
        """)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins - full width
        layout.setSpacing(0)
        
        # Add stretch to center buttons
        layout.addStretch()
        
        # Overlay toggle buttons container (centered, with padding)
        buttons_container = QWidget()
        buttons_container.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(20, 0, 20, 0)  # Horizontal padding for buttons
        buttons_layout.setSpacing(0)
        
        # Overlay toggle buttons
        if not hasattr(self, 'overlay_buttons'):
            self.overlay_buttons = {}
        
        overlays = [
            ("False Color", "false_color"),
            ("Waveform", "waveform"),
            ("Vectorscope", "vectorscope"),
            ("Focus Assist", "focus_assist"),
        ]
        
        # Button style with 2/3 font size (16px * 2/3 = ~11px)
        # No background, only text color change and orange line when checked
        overlay_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border-radius: 0px;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 0px;
                margin: 0px;
                font-size: 11px;
                font-weight: 600;
                color: {COLORS['text']};
            }}
            QPushButton:checked {{
                background-color: transparent;
                border-bottom: 3px solid {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """
        
        for name, key in overlays:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(50)  # Match bar height
            btn.setMinimumWidth(120)  # Smaller width for smaller text
            btn.setStyleSheet(overlay_btn_style)
            btn.clicked.connect(lambda checked, k=key: self._toggle_overlay(k))
            self.overlay_buttons[key] = btn
            buttons_layout.addWidget(btn)
        
        layout.addWidget(buttons_container)
        
        # Add stretch after buttons to keep them centered
        layout.addStretch()
        
        return bar
    
    def _create_grid_panel_content(self) -> QWidget:
        """Create grid/guides panel content (for portrait bottom panel)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Grid mode radios (Off / Thirds / Full / Both)
        layout.addWidget(self._ensure_grid_mode_radio_list(context_key="portrait_grid"))
        
        layout.addStretch()
        return widget
    
    def _create_frame_guides_panel_content(self) -> QWidget:
        """Create frame guides panel content (includes Grid options)"""
        widget = QWidget()
        outer = QHBoxLayout(widget)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(16)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        outer.addWidget(left_col, 1)
        outer.addWidget(right_col, 1)
        
        grid_label = QLabel("Grid")
        grid_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0px;
            }}
        """)
        left_layout.addWidget(grid_label)

        # Grid mode radios (Off / Thirds / Full / Both)
        left_layout.addWidget(self._ensure_grid_mode_radio_list(context_key="guides_bottom"))
        
        left_layout.addStretch()

        # Add separator (between columns visually)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"QFrame {{ color: {COLORS['border']}; max-height: 1px; }}")
        right_layout.addWidget(separator)
        
        # Frame Guides section
        guides_label = QLabel("Frame Guides")
        guides_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0px;
            }}
        """)
        right_layout.addWidget(guides_label)
        
        # Category + Template selection (radio buttons instead of dropdowns)
        category_row = self._ensure_frame_category_radio_row(context_key="guides_bottom")
        right_layout.addWidget(category_row)

        templates_list = self._ensure_frame_template_radio_list(context_key="guides_bottom")
        right_layout.addWidget(templates_list)
        
        # Color picker radios (orange only when selected) + small swatch
        if not hasattr(self, '_frame_colors'):
            self._frame_colors = {
                "White": ((255, 255, 255), "#FFFFFF"),
                "Red": ((0, 0, 255), "#FF0000"),
                "Green": ((0, 255, 0), "#00FF00"),
                "Blue": ((255, 0, 0), "#0000FF"),
                "Yellow": ((0, 255, 255), "#FFFF00"),
            }

        # Create (or reuse) radio group
        if not hasattr(self, '_frame_color_group'):
            self._frame_color_group = QButtonGroup(widget)
            self._frame_color_group.setExclusive(True)
            self._color_radios = {}

        radio_style = f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 12px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['border']};
                border-radius: 9px;
                background-color: {COLORS['surface']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """

        color_grid = QGridLayout()
        color_grid.setHorizontalSpacing(16)
        color_grid.setVerticalSpacing(10)

        # determine current color to avoid resetting selection every rebuild
        current_bgr = None
        try:
            current_bgr = getattr(self.preview_widget.frame_guide, 'line_color', None)
        except Exception:
            current_bgr = None

        for idx, (name, (bgr, hex_color)) in enumerate(self._frame_colors.items()):
            row = idx // 2
            col = idx % 2

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            radio = self._color_radios.get(name)
            if radio is None:
                radio = QRadioButton(name)
                radio.setStyleSheet(radio_style)
                radio.toggled.connect(lambda checked, n=name: self._on_frame_color_clicked(n) if checked else None)
                self._frame_color_group.addButton(radio)
                self._color_radios[name] = radio

            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background-color: {hex_color}; border: 1px solid {COLORS['border']}; border-radius: 3px;")

            row_layout.addWidget(radio)
            row_layout.addWidget(swatch)
            row_layout.addStretch()
            color_grid.addWidget(row_widget, row, col)

            if current_bgr == bgr:
                radio.setChecked(True)

        # Default to white if nothing matched
        if hasattr(self, '_color_radios') and self._color_radios.get("White") and not any(r.isChecked() for r in self._color_radios.values()):
            self._color_radios["White"].setChecked(True)
            # Apply immediately so UI and overlay are in sync
            self._on_frame_color_clicked("White")

        right_layout.addLayout(color_grid)
        
        # Custom Frame button (Guides bottom panel)
        if not hasattr(self, 'drag_mode_btn_guides'):
            self.drag_mode_btn_guides = QPushButton("Custom Frame")
            self.drag_mode_btn_guides.setCheckable(True)
            self.drag_mode_btn_guides.setFixedHeight(36)
            self.drag_mode_btn_guides.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                    color: {COLORS['text']};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:checked {{
                    background-color: {COLORS['primary']};
                    color: white;
                }}
            """)
            # Option A: tap to toggle; when turning OFF, show naming row
            self.drag_mode_btn_guides.toggled.connect(lambda checked: self._on_custom_frame_toggled("bottom", checked))

        # Clear button (Guides bottom panel) - side by side with Custom Frame
        if not hasattr(self, "_clear_guide_btn_guides"):
            self._clear_guide_btn_guides = QPushButton("Clear")
            self._clear_guide_btn_guides.setFixedHeight(36)
            self._clear_guide_btn_guides.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                    color: {COLORS['text']};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:pressed {{
                    background-color: #ff4444;
                }}
            """)
            self._clear_guide_btn_guides.clicked.connect(self._clear_frame_guide)

        top_btn_row = QHBoxLayout()
        top_btn_row.setSpacing(8)
        top_btn_row.addWidget(self.drag_mode_btn_guides)
        top_btn_row.addWidget(self._clear_guide_btn_guides)
        right_layout.addLayout(top_btn_row)

        # Inline "Save name" row (Option A) for Custom Guide saving
        if not hasattr(self, "_custom_guide_name_row_bottom"):
            self._custom_guide_name_row_bottom = QWidget()
            name_row_layout = QHBoxLayout(self._custom_guide_name_row_bottom)
            name_row_layout.setContentsMargins(0, 0, 0, 0)
            name_row_layout.setSpacing(8)

            self._custom_guide_name_input_bottom = QLineEdit()
            self._custom_guide_name_input_bottom.setPlaceholderText("Custom guide name…")
            self._custom_guide_name_input_bottom.setFixedHeight(36)
            self._custom_guide_name_input_bottom.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 8px 10px;
                    color: {COLORS['text']};
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border-color: {COLORS['primary']};
                }}
            """)
            # Allow OSK on Live page for this specific field
            self._custom_guide_name_input_bottom._osk_allow_on_live = True
            self._connect_field_to_osk(self._custom_guide_name_input_bottom)
            name_row_layout.addWidget(self._custom_guide_name_input_bottom, 1)

            self._custom_guide_name_cancel_bottom = QPushButton("Cancel")
            self._custom_guide_name_cancel_bottom.setFixedHeight(36)
            self._custom_guide_name_cancel_bottom.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    color: {COLORS['text']};
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0px 10px;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['surface_hover']};
                }}
            """)
            self._custom_guide_name_cancel_bottom.clicked.connect(lambda: self._hide_custom_guide_name_row("bottom"))
            name_row_layout.addWidget(self._custom_guide_name_cancel_bottom)

            self._custom_guide_name_save_bottom = QPushButton("Save")
            self._custom_guide_name_save_bottom.setFixedHeight(36)
            self._custom_guide_name_save_bottom.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    border: 1px solid {COLORS['primary']};
                    border-radius: 6px;
                    color: {COLORS['background']};
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0px 12px;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary_dark'] if 'primary_dark' in COLORS else COLORS['primary']};
                }}
            """)
            self._custom_guide_name_save_bottom.clicked.connect(lambda: self._commit_custom_guide_name("bottom"))
            name_row_layout.addWidget(self._custom_guide_name_save_bottom)

            self._custom_guide_name_row_bottom.setVisible(False)

        right_layout.addWidget(self._custom_guide_name_row_bottom)
        # Extra breathing room so the bottom of the row/buttons never clip
        right_layout.addSpacing(6)
        
        # Initialize frame guide templates
        QTimer.singleShot(100, lambda: self._on_frame_category_changed(getattr(self, "_frame_category_selected", "Social")))
        
        right_layout.addStretch()
        return widget
    
    def _create_multi_camera_presets_panel(self) -> QWidget:
        """Create Multi-Camera Presets panel with dynamic grid layouts"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Get configured cameras
        configured_cameras = []
        for cam_id, config in self.settings.multi_camera_presets.items():
            if config.get('enabled', False):
                camera = self.settings.get_camera(int(cam_id))
                if camera:
                    configured_cameras.append({
                        'camera': camera,
                        'layout': config.get('layout', '4×3 (12 presets)'),
                        'preset_count': config.get('preset_count', 12)
                    })

        if not configured_cameras:
            # No cameras configured - show setup message
            empty_frame = QFrame()
            empty_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 2px dashed {COLORS['border']};
                    border-radius: 12px;
                }}
            """)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(40, 60, 40, 60)

            no_config_label = QLabel("No Multi-Camera Configuration")
            no_config_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_config_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 18px; font-weight: 500;")
            empty_layout.addWidget(no_config_label)

            setup_label = QLabel("Configure cameras in Settings → Camera Control → Multi-Cam")
            setup_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setup_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 14px;")
            empty_layout.addWidget(setup_label)

            layout.addWidget(empty_frame)
            layout.addStretch()

        else:
            # Create sections for each configured camera
            for cam_config in configured_cameras:
                camera = cam_config['camera']
                layout_type = cam_config['layout']
                preset_count = cam_config['preset_count']

                # Camera header
                header_frame = QFrame()
                header_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['surface_light']};
                        border: 1px solid {COLORS['border']};
                        border-radius: 6px;
                    }}
                """)
                header_layout = QHBoxLayout(header_frame)
                header_layout.setContentsMargins(12, 8, 12, 8)

                camera_label = QLabel(f"📹 {camera.name}")
                camera_label.setStyleSheet(f"""
                    color: {COLORS['secondary']};
                    font-size: 14px;
                    font-weight: 600;
                """)
                header_layout.addWidget(camera_label)

                header_layout.addStretch()

                layout_type_label = QLabel(layout_type)
                layout_type_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
                header_layout.addWidget(layout_type_label)

                layout.addWidget(header_frame)

                # Preset grid for this camera
                grid_frame = QFrame()
                grid_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['surface']};
                        border: 1px solid {COLORS['border']};
                        border-radius: 8px;
                    }}
                """)
                grid_layout = QVBoxLayout(grid_frame)
                grid_layout.setContentsMargins(12, 12, 12, 12)

                # Calculate grid dimensions
                if "4×3" in layout_type:
                    rows, cols = 3, 4  # 4 columns, 3 rows
                elif "1×8" in layout_type:
                    rows, cols = 1, 8  # 1 row, 8 columns
                elif "4×2" in layout_type:
                    rows, cols = 2, 4  # 4 columns, 2 rows
                else:
                    rows, cols = 3, 4  # Default to 4x3

                # Create grid layout
                preset_grid = QGridLayout()
                preset_grid.setSpacing(4)
                preset_grid.setVerticalSpacing(6)

                # Create preset buttons (1 to preset_count)
                for preset_num in range(1, min(preset_count, 12) + 1):  # Max 12 presets per camera
                    row = (preset_num - 1) // cols
                    col = (preset_num - 1) % cols

                    # Create preset button
                    preset_btn = PresetButton(preset_num, camera.id, self)
                    preset_grid.addWidget(preset_btn, row, col)

                grid_layout.addLayout(preset_grid)
                layout.addWidget(grid_frame)

                # Add some spacing between camera sections
                layout.addSpacing(8)

        scroll.setWidget(widget)
        return scroll

    def _create_multiview_panel_content(self) -> QWidget:
        """Create multiview panel content (for portrait bottom panel)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Quad Split button
        if not hasattr(self, 'multiview_btn'):
            self.multiview_btn = QPushButton("Quad Split")
            self.multiview_btn.setCheckable(True)
            self.multiview_btn.setFixedHeight(50)
            multiview_btn_style = f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                    color: {COLORS['text']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
            """
            self.multiview_btn.setStyleSheet(multiview_btn_style)
            self.multiview_btn.clicked.connect(self._toggle_multiview)
        
        layout.addWidget(self.multiview_btn)
        layout.addStretch()
        return widget
    
    def _send_camera_command(self, command: str, endpoint: str = "aw_cam") -> bool:
        """
        Send HTTP command to current camera.
        
        Args:
            command: Command string (e.g., "OSD:48:0" or "R01")
            endpoint: CGI endpoint ("aw_cam" or "aw_ptz")
            
        Returns:
            True if command sent successfully
        """
        if self.current_camera_id is None:
            return False
        
        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return False
        
        import requests
        try:
            url = f"http://{camera.ip_address}/cgi-bin/{endpoint}?cmd={command}&res=1"
            response = requests.get(url, auth=(camera.username, camera.password), timeout=2.0)
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Camera command failed: {command} (status {response.status_code})")
                return False
        except Exception as e:
            logger.error(f"Camera command error: {e}")
            if hasattr(self, "toast") and self.toast:
                self.toast.show_message("Camera command failed", duration=2000, error=True)
            return False

    def _query_camera_setting(self, command: str, endpoint: str = "aw_cam") -> str:
        """
        Query a camera setting via CGI command.

        Args:
            command: Query command (e.g., "QSH", "QGA", etc.)
            endpoint: CGI endpoint ("aw_cam" or "aw_ptz")

        Returns:
            Response string, or empty string on failure
        """
        if self.current_camera_id is None:
            return ""

        camera = self.settings.get_camera(self.current_camera_id)
        if not camera:
            return ""

        import requests
        try:
            url = f"http://{camera.ip_address}/cgi-bin/{endpoint}?cmd={command}&res=1"
            response = requests.get(url, auth=(camera.username, camera.password), timeout=2.0)
            if response.status_code == 200:
                return response.text.strip()
            else:
                logger.warning(f"Camera query failed: {command} (status {response.status_code})")
                return ""
        except Exception as e:
            logger.error(f"Camera query error: {e}")
            return ""

    def _sync_camera_exposure_settings(self):
        """Sync exposure panel controls with current camera settings"""
        try:
            # For now, just query and show current camera settings in toast
            # TODO: Store control references during panel creation for direct UI updates

            # Query shutter speed (QSH)
            shutter_response = self._query_camera_setting("QSH")
            if shutter_response and shutter_response.startswith("qsh:"):
                try:
                    shutter_val = int(shutter_response.split(":")[1])
                    logger.debug(f"Camera shutter: {shutter_val}")
                except (ValueError, IndexError):
                    pass

            # Query gain (QGA)
            gain_response = self._query_camera_setting("QGA")
            if gain_response and gain_response.startswith("qga:"):
                try:
                    gain_val = int(gain_response.split(":")[1])
                    logger.debug(f"Camera gain: {gain_val}dB")
                except (ValueError, IndexError):
                    pass

            # Query iris (QIR)
            iris_response = self._query_camera_setting("QIR")
            if iris_response and iris_response.startswith("qir:"):
                try:
                    iris_val = int(iris_response.split(":")[1])
                    logger.debug(f"Camera iris: {iris_val}")
                except (ValueError, IndexError):
                    pass

        except Exception as e:
            logger.warning(f"Error syncing exposure settings: {e}")

    def _sync_camera_color_settings(self):
        """Sync color panel controls with current camera settings"""
        try:
            # Query white balance mode (QWB)
            wb_response = self._query_camera_setting("QWB")
            if wb_response and wb_response.startswith("qwb:"):
                try:
                    wb_mode = int(wb_response.split(":")[1])
                    wb_mapping = {0: "Auto", 1: "Indoor", 2: "Outdoor", 3: "OnePush", 4: "Manual"}
                    wb_name = wb_mapping.get(wb_mode, f"Mode {wb_mode}")
                    logger.debug(f"Camera WB mode: {wb_name}")
                except (ValueError, IndexError):
                    pass

            # Query red gain (QRG) - only if manual WB
            rg_response = self._query_camera_setting("QRG")
            if rg_response and rg_response.startswith("qrg:"):
                try:
                    rg_val = int(rg_response.split(":")[1])
                    logger.debug(f"Camera red gain: {rg_val}")
                except (ValueError, IndexError):
                    pass

            # Query blue gain (QBG)
            bg_response = self._query_camera_setting("QBG")
            if bg_response and bg_response.startswith("qbg:"):
                try:
                    bg_val = int(bg_response.split(":")[1])
                    logger.debug(f"Camera blue gain: {bg_val}")
                except (ValueError, IndexError):
                    pass

        except Exception as e:
            logger.warning(f"Error syncing color settings: {e}")

    def _sync_camera_image_settings(self):
        """Sync image panel controls with current camera settings"""
        try:
            # Query gamma (QGM)
            gamma_response = self._query_camera_setting("QGM")
            if gamma_response and gamma_response.startswith("qgm:"):
                try:
                    gamma_val = int(gamma_response.split(":")[1])
                    gamma_modes = ["Normal", "Cinema", "Still", "ITU-R", "Extended"]
                    gamma_name = gamma_modes[gamma_val] if gamma_val < len(gamma_modes) else f"Mode {gamma_val}"
                    logger.debug(f"Camera gamma: {gamma_name}")
                except (ValueError, IndexError):
                    pass

            # Query detail level (QDT)
            detail_response = self._query_camera_setting("QDT")
            if detail_response and detail_response.startswith("qdt:"):
                try:
                    detail_val = int(detail_response.split(":")[1])
                    logger.debug(f"Camera detail level: {detail_val}")
                except (ValueError, IndexError):
                    pass

        except Exception as e:
            logger.warning(f"Error syncing image settings: {e}")

    def _sync_camera_operations_settings(self):
        """Sync operations panel controls with current camera settings"""
        try:
            # Query power status (QPW)
            power_response = self._query_camera_setting("QPW")
            if power_response and power_response.startswith("qpw:"):
                try:
                    power_val = int(power_response.split(":")[1])
                    # 0=standby, 1=on, 2=powering on/off
                    power_states = {0: "Standby", 1: "ON", 2: "Powering"}
                    power_name = power_states.get(power_val, f"State {power_val}")
                    logger.debug(f"Camera power: {power_name}")
                except (ValueError, IndexError):
                    pass

        except Exception as e:
            logger.warning(f"Error syncing operations settings: {e}")

    def _sync_camera_controls_with_current_camera(self):
        """Sync all camera control panels with current camera settings"""
        if self.current_camera_id is None:
            return

        try:
            # Show sync feedback
            if hasattr(self, 'toast'):
                self.toast.show_message("Syncing camera settings...", duration=1000)

            # Sync each panel based on what's currently visible
            current_category = getattr(self, 'camera_control_stack', None)
            if current_category:
                current_index = current_category.currentIndex()
                if current_index == 0:  # Exposure
                    self._sync_camera_exposure_settings()
                elif current_index == 1:  # Color
                    self._sync_camera_color_settings()
                elif current_index == 2:  # Image
                    self._sync_camera_image_settings()
                elif current_index == 3:  # Operations
                    self._sync_camera_operations_settings()

            # Also sync other panels that might be visible
            self._sync_camera_exposure_settings()
            self._sync_camera_color_settings()
            self._sync_camera_image_settings()
            self._sync_camera_operations_settings()

        except Exception as e:
            logger.warning(f"Error syncing camera controls: {e}")
            if hasattr(self, 'toast'):
                self.toast.show_message("Failed to sync camera settings", duration=2000, error=True)

    def _capture_preset_thumbnail(self, camera_id: int, preset_num: int) -> bool:
        """
        Capture current camera frame as preset thumbnail.
        
        Args:
            camera_id: Camera ID
            preset_num: Preset number (1-32)
            
        Returns:
            True if thumbnail captured successfully
        """
        try:
            # Get current frame from preview widget
            if not hasattr(self, 'preview_widget') or self.preview_widget is None:
                return False
            
            # Try to get frame from preview widget's current frame
            frame = None
            if hasattr(self.preview_widget, '_current_frame'):
                frame = self.preview_widget._current_frame
            
            # Fallback: try display frame
            if frame is None and hasattr(self.preview_widget, '_display_frame'):
                frame = self.preview_widget._display_frame
            
            # Fallback: try to get from camera stream
            if frame is None and camera_id in self.camera_streams:
                stream = self.camera_streams[camera_id]
                if hasattr(stream, 'current_frame'):
                    frame = stream.current_frame
            
            if frame is None:
                logger.warning("No frame available for thumbnail capture")
                return False
            
            # Convert numpy frame to QPixmap
            h, w = frame.shape[:2]
            if len(frame.shape) == 3:
                # BGR to RGB conversion
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                bytes_per_line = 3 * w
                q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            else:
                # Grayscale
                bytes_per_line = w
                q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(q_img)
            
            # Resize to 16:9 aspect ratio (80x45px to fit in 80x80 button)
            thumbnail = pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            # Crop to center if needed (to maintain 16:9 aspect ratio)
            if thumbnail.width() / thumbnail.height() != 16 / 9:
                # Calculate 16:9 crop
                target_width = thumbnail.width()
                target_height = int(target_width * 9 / 16)
                if target_height > thumbnail.height():
                    target_height = thumbnail.height()
                    target_width = int(target_height * 16 / 9)
                
                x = (thumbnail.width() - target_width) // 2
                y = (thumbnail.height() - target_height) // 2
                thumbnail = thumbnail.copy(x, y, target_width, target_height)
            
            # Save to file
            preset_dir = Path.home() / ".config" / "panapitouch" / "presets" / str(camera_id)
            preset_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = preset_dir / f"preset_{preset_num:02d}.jpg"
            
            thumbnail.save(str(thumbnail_path), "JPEG", quality=85)
            logger.info(f"Thumbnail saved for preset {preset_num} (camera {camera_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error capturing thumbnail: {e}", exc_info=True)
            return False
    
    def _create_camera_control_panel_content(self) -> QWidget:
        """Create camera control panel with category submenu and control panels"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Category submenu bar
        category_menu = QFrame()
        category_menu.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        category_menu.setFixedHeight(60)
        
        category_layout = QHBoxLayout(category_menu)
        category_layout.setContentsMargins(20, 0, 20, 0)
        category_layout.setSpacing(0)
        category_layout.addStretch()
        
        # Category buttons container
        category_buttons_container = QWidget()
        category_buttons_container.setStyleSheet("background: transparent;")
        category_buttons_layout = QHBoxLayout(category_buttons_container)
        category_buttons_layout.setContentsMargins(0, 0, 0, 0)
        category_buttons_layout.setSpacing(0)
        
        self.camera_control_category_group = QButtonGroup(self)
        self.camera_control_category_group.setExclusive(True)
        
        # Category buttons: Exposure, Color, Image, Operations, Multi-Cam
        category_buttons = [
            ("Exposure", 0),
            ("Color", 1),
            ("Image", 2),
            ("Operations", 3),
            ("🎬 Multi-Cam", 4),
        ]
        
        for text, cat_idx in category_buttons:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setFixedHeight(60)
            btn.setMinimumWidth(100)
            
            self.camera_control_category_group.addButton(btn, cat_idx)
            category_buttons_layout.addWidget(btn)
            
            if cat_idx == 0:
                btn.setChecked(True)  # Default to Exposure
        
        self.camera_control_category_group.idClicked.connect(self._switch_camera_control_category)
        
        category_layout.addWidget(category_buttons_container)
        category_layout.addStretch()
        
        layout.addWidget(category_menu)
        
        # Stacked widget for category panels
        self.camera_control_stack = QStackedWidget()
        self.camera_control_stack.setStyleSheet("QStackedWidget { background: transparent; }")
        
        # Create and add category panels
        self.camera_control_stack.addWidget(self._create_exposure_panel())
        self.camera_control_stack.addWidget(self._create_color_panel())
        self.camera_control_stack.addWidget(self._create_image_panel())  # Includes Advanced features
        self.camera_control_stack.addWidget(self._create_operations_panel())
        self.camera_control_stack.addWidget(self._create_multi_camera_panel())
        
        layout.addWidget(self.camera_control_stack)
        
        return widget
    
    def _switch_camera_control_category(self, index: int):
        """Switch camera control category panel"""
        self.camera_control_stack.setCurrentIndex(index)
    
    def _create_slider_with_buttons(self, label_text: str, min_val: int, max_val: int, default_val: int, 
                                     value_format: callable, command_template: str, step: int = 1, endpoint: str = "aw_cam") -> tuple:
        """Create a slider with +/- buttons and value display above"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
        
        # Label
        label = QLabel(label_text.upper())
        label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        container_layout.addWidget(label)
        
        # Value display box (above slider)
        value_label = QLabel(value_format(default_val))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text']};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                min-width: 80px;
            }}
        """)
        container_layout.addWidget(value_label)
        
        # Slider row with +/- buttons
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        
        # Minus button
        minus_btn = QPushButton("−")
        minus_btn.setFixedSize(40, 40)
        minus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['surface']};
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
                background: {COLORS['primary_dark']};
            }}
        """)
        
        # Plus button
        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(40, 40)
        plus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        # Connect slider value changes
        def update_value(val):
            value_label.setText(value_format(val))
            if '{' in command_template:
                self._send_camera_command(command_template.format(val), endpoint=endpoint)
            else:
                self._send_camera_command(command_template, endpoint=endpoint)
        
        slider.valueChanged.connect(update_value)
        
        # Connect +/- buttons
        def decrement():
            if slider.value() > min_val:
                slider.setValue(max(min_val, slider.value() - step))
        
        def increment():
            if slider.value() < max_val:
                slider.setValue(min(max_val, slider.value() + step))
        
        minus_btn.clicked.connect(decrement)
        plus_btn.clicked.connect(increment)
        
        slider_row.addWidget(minus_btn)
        slider_row.addWidget(slider, stretch=1)
        slider_row.addWidget(plus_btn)
        
        container_layout.addLayout(slider_row)
        
        return container, slider, value_label
    
    def _create_radio_group(self, label_text: str, options: list, default_idx: int, command_template: str, endpoint: str = "aw_cam") -> QWidget:
        """Create a radio button group"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Label
        if label_text:  # Only add label if text provided
            label = QLabel(label_text.upper())
            label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text']};
                    font-size: 14px;
                    font-weight: bold;
                    background-color: {COLORS['surface_light']};
                    border: 2px solid {COLORS['border_light']};
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
            """)
            layout.addWidget(label)
        
        # Radio button group
        radio_group = QButtonGroup(container)
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(16)
        
        for idx, option_text in enumerate(options):
            radio = QRadioButton(option_text)
            radio.setStyleSheet(f"""
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
                QRadioButton::indicator:checked {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
            """)
            if idx == default_idx:
                radio.setChecked(True)
            
            def make_handler(i, text):
                return lambda checked: self._send_camera_command(command_template.format(i), endpoint=endpoint) if checked else None
            
            radio.toggled.connect(make_handler(idx, option_text))
            radio_group.addButton(radio, idx)
            radio_layout.addWidget(radio)
        
        radio_layout.addStretch()
        layout.addLayout(radio_layout)
        
        return container
    
    def _create_separator(self) -> QFrame:
        """Create a Canon-style horizontal separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['border']};
                border: none;
            }}
        """)
        return separator

    def _create_section_header(self, title: str) -> QLabel:
        """Create a Canon-style section header label"""
        label = QLabel(title.upper())
        label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
            }}
        """)
        return label
    
    def _create_two_column_layout(self) -> tuple:
        """Create a Canon-style two-column layout container"""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        columns_widget = QWidget()
        columns_layout = QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(16)
        
        # Left column with Canon-style panel
        left_column = QFrame()
        left_column.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        
        # Right column with Canon-style panel
        right_column = QFrame()
        right_column.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)
        
        columns_layout.addWidget(left_column, stretch=1)
        columns_layout.addWidget(right_column, stretch=1)
        
        main_layout.addWidget(columns_widget)
        
        return container, main_layout, left_layout, right_layout
    
    def _create_exposure_panel(self) -> QWidget:
        """Create Exposure Control panel (Category 1) - two columns"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        container, main_layout, left_layout, right_layout = self._create_two_column_layout()
        
        # LEFT COLUMN
        
        # Picture Level slider
        picture_level_container, picture_slider, picture_label = self._create_slider_with_buttons(
            "Picture Level", 0, 100, 0,
            lambda v: str(v),
            "OSD:48:{}"
        )
        left_layout.addWidget(picture_level_container)
        
        left_layout.addWidget(self._create_separator())
        
        # Iris Mode radio buttons
        iris_mode_container = self._create_radio_group(
            "Iris Mode",
            ["Manual", "Auto"],
            0,
            "OSD:48:{}"
        )
        left_layout.addWidget(iris_mode_container)
        
        # Auto Iris Speed radio buttons
        iris_speed_container = self._create_radio_group(
            "Auto Iris Speed",
            ["Slow", "Normal", "Fast"],
            1,
            "OSD:50:{}"
        )
        left_layout.addWidget(iris_speed_container)
        
        # Auto Iris Window radio buttons
        iris_window_container = self._create_radio_group(
            "Auto Iris Window",
            ["Normal1", "Normal2", "Center"],
            0,
            "OSD:51:{}"
        )
        left_layout.addWidget(iris_window_container)
        
        left_layout.addWidget(self._create_separator())
        
        # Shutter Mode radio buttons (2 rows)
        shutter_mode_label = QLabel("Shutter Mode")
        shutter_mode_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 600;")
        left_layout.addWidget(shutter_mode_label)
        
        shutter_mode_group = QButtonGroup(container)
        shutter_mode_layout = QGridLayout()
        shutter_options = ["Off", "Step", "Synchro", "ELC"]
        for idx, option in enumerate(shutter_options):
            radio = QRadioButton(option)
            radio.setStyleSheet(f"""
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
                QRadioButton::indicator:checked {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
            """)
            if idx == 0:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, i=idx: self._send_camera_command(f"OSD:52:{i}") if checked else None)
            shutter_mode_group.addButton(radio, idx)
            shutter_mode_layout.addWidget(radio, idx // 2, idx % 2)
        left_layout.addLayout(shutter_mode_layout)
        
        # Step slider (indented)
        shutter_speeds = [100, 250, 500, 1000, 2000, 4000, 8000, 10000]
        step_container, step_slider, step_label = self._create_slider_with_buttons(
            "Step", 0, 7, 0,
            lambda v: f"1/{shutter_speeds[v] if v < len(shutter_speeds) else 100}",
            "OSD:53:{}"
        )
        step_container.layout().setContentsMargins(20, 0, 0, 0)
        left_layout.addWidget(step_container)
        
        # Synchro slider (indented)
        synchro_container, synchro_slider, synchro_label = self._create_slider_with_buttons(
            "Synchro", 50, 60, 60,
            lambda v: str(v),
            "OSD:54:{}"
        )
        synchro_container.layout().setContentsMargins(20, 0, 0, 0)
        left_layout.addWidget(synchro_container)
        
        # ELC Limit radio buttons (indented)
        elc_limit_container = self._create_radio_group(
            "ELC Limit",
            ["1/100", "1/120", "1/250"],
            2,
            "OSD:55:{}"
        )
        elc_limit_container.layout().setContentsMargins(20, 0, 0, 0)
        left_layout.addWidget(elc_limit_container)
        
        left_layout.addStretch()
        
        # RIGHT COLUMN
        
        # Gain slider with Auto button
        gain_label = QLabel("GAIN")
        gain_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(gain_label)
        
        gain_value_label = QLabel("0dB")
        gain_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gain_value_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text']};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                min-width: 80px;
            }}
        """)
        right_layout.addWidget(gain_value_label)
        
        gain_row = QHBoxLayout()
        gain_row.setSpacing(8)
        
        gain_minus_btn = QPushButton("−")
        gain_minus_btn.setFixedSize(40, 40)
        gain_minus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        gain_slider = QSlider(Qt.Orientation.Horizontal)
        gain_slider.setRange(-3, 42)
        gain_slider.setValue(0)
        gain_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['surface']};
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
        """)
        
        gain_plus_btn = QPushButton("+")
        gain_plus_btn.setFixedSize(40, 40)
        gain_plus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        gain_auto_btn = QPushButton("Auto")
        gain_auto_btn.setCheckable(True)
        gain_auto_btn.setFixedSize(60, 40)
        gain_auto_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        
        def update_gain(val):
            gain_value_label.setText(f"{val}dB")
            self._send_camera_command(f"OSD:51:{val}")
        
        gain_slider.valueChanged.connect(update_gain)
        gain_minus_btn.clicked.connect(lambda: gain_slider.setValue(max(-3, gain_slider.value() - 1)))
        gain_plus_btn.clicked.connect(lambda: gain_slider.setValue(min(42, gain_slider.value() + 1)))
        gain_auto_btn.toggled.connect(lambda checked: self._send_camera_command(f"OSD:50:{'1' if checked else '0'}"))
        
        gain_row.addWidget(gain_minus_btn)
        gain_row.addWidget(gain_slider, stretch=1)
        gain_row.addWidget(gain_plus_btn)
        gain_row.addWidget(gain_auto_btn)
        right_layout.addLayout(gain_row)
        
        # Super Gain radio buttons
        super_gain_container = self._create_radio_group(
            "Super Gain",
            ["Off", "On"],
            0,
            "OSD:56:{}"
        )
        right_layout.addWidget(super_gain_container)
        
        # AGC Max Gain radio buttons
        agc_max_container = self._create_radio_group(
            "AGC Max Gain",
            ["6dB", "12dB", "18dB"],
            2,
            "OSD:57:{}"
        )
        right_layout.addWidget(agc_max_container)
        
        right_layout.addWidget(self._create_separator())
        
        # ND Filter radio buttons (2 rows)
        nd_label = QLabel("ND FILTER")
        nd_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(nd_label)
        
        nd_group = QButtonGroup(container)
        nd_layout = QGridLayout()
        nd_options = ["Through", "1/4", "1/16", "1/64"]
        for idx, option in enumerate(nd_options):
            radio = QRadioButton(option)
            radio.setStyleSheet(f"""
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
                QRadioButton::indicator:checked {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
            """)
            if idx == 0:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, i=idx: self._send_camera_command(f"OSD:55:{i}") if checked else None)
            nd_group.addButton(radio, idx)
            nd_layout.addWidget(radio, idx // 2, idx % 2)
        right_layout.addLayout(nd_layout)
        
        # Day/Night radio buttons
        day_night_container = self._create_radio_group(
            "Day/Night",
            ["Day", "Night"],
            0,
            "OSD:58:{}"
        )
        right_layout.addWidget(day_night_container)
        
        # Frame Mix radio buttons
        frame_mix_container = self._create_radio_group(
            "FRAME MIX",
            ["Off", "On"],
            0,
            "OSD:59:{}"
        )
        right_layout.addWidget(frame_mix_container)
        
        right_layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_color_panel(self) -> QWidget:
        """Create Color & White Balance panel (Category 2) - redesigned with two columns"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        container, main_layout, left_layout, right_layout = self._create_two_column_layout()
        
        # LEFT COLUMN
        
        # White Balance Mode
        wb_mode_container = self._create_radio_group(
            "White Balance Mode",
            ["Auto", "Indoor", "Outdoor", "Manual", "ATW"],
            0,
            "OSD:54:{}"
        )
        left_layout.addWidget(wb_mode_container)
        
        # Color Temperature slider
        color_temp_container, _, _ = self._create_slider_with_buttons(
            "Color Temperature", 2000, 15000, 5600,
            lambda v: f"{v}K",
            "OSD:55:{}"
        )
        left_layout.addWidget(color_temp_container)
        
        # Red Gain slider
        red_gain_container, _, _ = self._create_slider_with_buttons(
            "Red Gain", -99, 99, 0,
            lambda v: str(v),
            "OSD:56:{}"
        )
        left_layout.addWidget(red_gain_container)
        
        # Blue Gain slider
        blue_gain_container, _, _ = self._create_slider_with_buttons(
            "Blue Gain", -99, 99, 0,
            lambda v: str(v),
            "OSD:57:{}"
        )
        left_layout.addWidget(blue_gain_container)
        
        # WB Speed
        wb_speed_container = self._create_radio_group(
            "WB Speed",
            ["Fast", "Normal", "Slow"],
            1,
            "OSD:58:{}"
        )
        left_layout.addWidget(wb_speed_container)
        
        left_layout.addWidget(self._create_separator())
        
        # Color Matrix Type
        matrix_type_container = self._create_radio_group(
            "Matrix Type",
            ["Normal", "EBU", "NTSC", "User"],
            0,
            "OSD:59:{}"
        )
        left_layout.addWidget(matrix_type_container)
        
        # Saturation slider
        saturation_container, _, _ = self._create_slider_with_buttons(
            "Saturation", -99, 99, 0,
            lambda v: str(v),
            "OSD:60:{}"
        )
        left_layout.addWidget(saturation_container)
        
        # Hue slider
        hue_container, _, _ = self._create_slider_with_buttons(
            "Hue", -99, 99, 0,
            lambda v: str(v),
            "OSD:61:{}"
        )
        left_layout.addWidget(hue_container)
        
        left_layout.addStretch()
        
        # RIGHT COLUMN
        
        # Gamma Mode
        gamma_label = QLabel("GAMMA MODE")
        gamma_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(gamma_label)
        
        gamma_group = QButtonGroup(container)
        gamma_layout = QGridLayout()
        gamma_options = ["Standard", "Cinema", "Wide", "HD", "FILMLIKE1", "FILMLIKE2", "FILMLIKE3", "FILM-REC", "VIDEO-REC", "HLG"]
        for idx, option in enumerate(gamma_options):
            radio = QRadioButton(option)
            radio.setStyleSheet(f"""
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
                QRadioButton::indicator:checked {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                }}
            """)
            if idx == 0:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, i=idx: self._send_camera_command(f"OSD:62:{i}") if checked else None)
            gamma_group.addButton(radio, idx)
            gamma_layout.addWidget(radio, idx // 2, idx % 2)
        right_layout.addLayout(gamma_layout)
        
        # Gamma Level
        gamma_level_container = self._create_radio_group(
            "Gamma Level",
            ["Low", "Mid", "High"],
            1,
            "OSD:63:{}"
        )
        right_layout.addWidget(gamma_level_container)
        
        right_layout.addWidget(self._create_separator())
        
        # Black Balance
        black_balance_container = self._create_radio_group(
            "Black Balance",
            ["Auto", "Manual"],
            0,
            "OSD:64:{}"
        )
        right_layout.addWidget(black_balance_container)
        
        # Master Black slider
        master_black_container, _, _ = self._create_slider_with_buttons(
            "Master Black", -99, 99, 0,
            lambda v: str(v),
            "OSD:65:{}"
        )
        right_layout.addWidget(master_black_container)
        
        right_layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_image_panel(self) -> QWidget:
        """Create Image Enhancement panel (Category 3) - includes Advanced features, two columns"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        container, main_layout, left_layout, right_layout = self._create_two_column_layout()
        
        # LEFT COLUMN
        
        # Detail Level slider
        detail_level_container, _, _ = self._create_slider_with_buttons(
            "Detail Level", -99, 99, 0,
            lambda v: str(v),
            "OSD:64:{}"
        )
        left_layout.addWidget(detail_level_container)
        
        # H/V Ratio slider
        hv_ratio_container, _, _ = self._create_slider_with_buttons(
            "H/V Ratio", 0, 100, 50,
            lambda v: str(v),
            "OSD:65:{}"
        )
        left_layout.addWidget(hv_ratio_container)
        
        left_layout.addWidget(self._create_separator())
        
        # Knee Mode
        knee_mode_container = self._create_radio_group(
            "Knee Mode",
            ["Off", "Auto", "Manual"],
            0,
            "OSD:66:{}"
        )
        left_layout.addWidget(knee_mode_container)
        
        # Knee Point slider
        knee_point_container, _, _ = self._create_slider_with_buttons(
            "Knee Point", 70, 105, 95,
            lambda v: f"{v}%",
            "OSD:67:{}"
        )
        left_layout.addWidget(knee_point_container)
        
        left_layout.addWidget(self._create_separator())
        
        # DNR Level
        dnr_level_container = self._create_radio_group(
            "DNR Level",
            ["Off", "Low", "High"],
            0,
            "OSD:68:{}"
        )
        left_layout.addWidget(dnr_level_container)
        
        # White Clip slider
        white_clip_container, _, _ = self._create_slider_with_buttons(
            "White Clip", 100, 109, 109,
            lambda v: f"{v}%",
            "OSD:69:{}"
        )
        left_layout.addWidget(white_clip_container)
        
        # Chroma Level slider
        chroma_container, _, _ = self._create_slider_with_buttons(
            "Chroma Level", -99, 99, 0,
            lambda v: str(v),
            "OSD:70:{}"
        )
        left_layout.addWidget(chroma_container)
        
        left_layout.addStretch()
        
        # RIGHT COLUMN - Advanced Features
        
        # Image Transform
        transform_label = QLabel("IMAGE TRANSFORM")
        transform_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(transform_label)
        
        # Flip Horizontal
        flip_h_btn = QPushButton("Flip Horizontal")
        flip_h_btn.setCheckable(True)
        flip_h_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
                padding: 8px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        flip_h_btn.clicked.connect(lambda checked: self._send_camera_command(f"OSD:80:{'1' if checked else '0'}"))
        right_layout.addWidget(flip_h_btn)
        
        # Flip Vertical
        flip_v_btn = QPushButton("Flip Vertical")
        flip_v_btn.setCheckable(True)
        flip_v_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
                padding: 8px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        flip_v_btn.clicked.connect(lambda checked: self._send_camera_command(f"OSD:81:{'1' if checked else '0'}"))
        right_layout.addWidget(flip_v_btn)
        
        # Rotation
        rotation_label = QLabel("ROTATION")
        rotation_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(rotation_label)
        
        rotation_container = self._create_radio_group(
            "",
            ["0°", "90°", "180°", "270°"],
            0,
            "OSD:82:{}"
        )
        right_layout.addWidget(rotation_container)
        
        right_layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_presets_panel(self) -> QWidget:
        """Create Presets panel with 48-button grid (8×6) - Canon RC-IP100 inspired"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Get current camera ID (or use first camera if none selected)
        camera_id = self.current_camera_id
        if camera_id is None and self.settings.cameras:
            camera_id = self.settings.cameras[0].id
        
        if camera_id is None:
            # No cameras configured - Canon-style empty state
            empty_frame = QFrame()
            empty_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 2px dashed {COLORS['border']};
                    border-radius: 12px;
                }}
            """)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setContentsMargins(40, 60, 40, 60)
            
            no_cameras_label = QLabel("No cameras configured")
            no_cameras_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_cameras_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 18px; font-weight: 500;")
            empty_layout.addWidget(no_cameras_label)
            
            hint_label = QLabel("Add cameras in the Cameras menu to use presets")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 14px;")
            empty_layout.addWidget(hint_label)
            
            layout.addWidget(empty_frame)
            layout.addStretch()
            scroll.setWidget(widget)
            return scroll
        
        # Create 8×6 grid (48 presets) in a panel
        presets_frame = QFrame()
        presets_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        presets_frame_layout = QVBoxLayout(presets_frame)
        presets_frame_layout.setContentsMargins(12, 12, 12, 12)
        presets_frame_layout.setSpacing(0)

        presets_grid = QGridLayout()
        presets_grid.setSpacing(6)
        presets_grid.setVerticalSpacing(8)

        # Prevent columns from stretching
        for col in range(8):
            presets_grid.setColumnStretch(col, 0)

        # Store preset buttons for potential refresh
        preset_buttons = []
        for preset_num in range(1, 49):  # Presets 1-48
            row = (preset_num - 1) // 8  # 6 rows (0-5)
            col = (preset_num - 1) % 8   # 8 columns (0-7)

            # Create container widget with label above and button below
            container = QWidget()
            container.setFixedWidth(80)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)
            
            # Label above button (smaller, dimmer for empty presets)
            preset_btn = PresetButton(preset_num, camera_id, self)
            name_label = QLabel()
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Use different styling based on whether preset has content
            if preset_btn.has_thumbnail:
                name_label.setStyleSheet(f"""
                    QLabel {{
                        color: {COLORS['text']};
                        font-size: 12px;
                        font-weight: 600;
                        padding: 0px;
                        margin: 0px;
                        border: none;
                    }}
                """)
            else:
                name_label.setStyleSheet(f"""
                    QLabel {{
                        color: {COLORS['text_dim']};
                        font-size: 11px;
                        font-weight: 500;
                        padding: 0px;
                        margin: 0px;
                        border: none;
                    }}
                """)
            
            # Set label text (use preset name if available, otherwise preset number)
            display_name = preset_btn.preset_name if preset_btn.preset_name else str(preset_num)
            name_label.setText(display_name)
            preset_btn._name_label = name_label
            
            container_layout.addWidget(name_label)
            container_layout.addWidget(preset_btn)
            container_layout.addStretch()
            
            preset_buttons.append(preset_btn)
            presets_grid.addWidget(container, row, col)
        
        presets_frame_layout.addLayout(presets_grid)
        layout.addWidget(presets_frame)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    
    def _create_multi_camera_panel(self) -> QWidget:
        """Create Multi-Camera Presets Configuration panel"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)

        container, main_layout, left_layout, right_layout = self._create_two_column_layout()

        # LEFT COLUMN - Camera Selection
        cameras_label = self._create_section_header("CAMERA SELECTION")
        left_layout.addWidget(cameras_label)

        # Instructions
        instructions = QLabel("Select cameras to include in the multi-camera preset view.\nEach camera can have a different preset grid layout.")
        instructions.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; padding: 8px 0;")
        instructions.setWordWrap(True)
        left_layout.addWidget(instructions)

        # Camera checkboxes container
        cameras_frame = QFrame()
        cameras_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        cameras_layout = QVBoxLayout(cameras_frame)
        cameras_layout.setContentsMargins(12, 12, 12, 12)
        cameras_layout.setSpacing(8)

        # Store checkboxes for later access
        self.multi_camera_checkboxes = {}
        self.multi_camera_layout_combos = {}

        for camera in self.settings.cameras:
            # Camera row container
            camera_row = QHBoxLayout()
            camera_row.setSpacing(12)

            # Checkbox
            checkbox = QCheckBox(f"📹 {camera.name}")
            checkbox.setChecked(self.settings.multi_camera_presets.get(str(camera.id), {}).get('enabled', False))
            checkbox.stateChanged.connect(lambda state, cam_id=camera.id: self._on_multi_camera_toggle(cam_id, state))
            self.multi_camera_checkboxes[camera.id] = checkbox
            camera_row.addWidget(checkbox)

            # Layout combo (only enabled when checked)
            layout_combo = QComboBox()
            layout_combo.addItems(["4×3 (12 presets)", "1×8 (8 presets)", "4×2 (8 presets)"])
            current_layout = self.settings.multi_camera_presets.get(str(camera.id), {}).get('layout', '4×3 (12 presets)')
            layout_combo.setCurrentText(current_layout)
            layout_combo.setEnabled(checkbox.isChecked())
            layout_combo.currentTextChanged.connect(lambda text, cam_id=camera.id: self._on_multi_camera_layout_change(cam_id, text))
            self.multi_camera_layout_combos[camera.id] = layout_combo
            camera_row.addWidget(layout_combo)

            camera_row.addStretch()
            cameras_layout.addLayout(camera_row)

        left_layout.addWidget(cameras_frame)

        # RIGHT COLUMN - Preview and Actions
        preview_label = self._create_section_header("PREVIEW & ACTIONS")
        right_layout.addWidget(preview_label)

        # Current configuration preview
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        self.multi_camera_preview_label = QLabel("No cameras selected")
        self.multi_camera_preview_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px;")
        self.multi_camera_preview_label.setWordWrap(True)
        preview_layout.addWidget(self.multi_camera_preview_label)

        right_layout.addWidget(preview_frame)

        # Action buttons
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_dark']};
            }}
        """)
        save_btn.clicked.connect(self._save_multi_camera_config)
        actions_layout.addWidget(save_btn)

        reset_btn = QPushButton("🔄 Reset to Default")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
        """)
        reset_btn.clicked.connect(self._reset_multi_camera_config)
        actions_layout.addWidget(reset_btn)

        right_layout.addLayout(actions_layout)
        right_layout.addStretch()

        # Update preview initially
        self._update_multi_camera_preview()

        scroll.setWidget(container)
        return scroll

    def _on_multi_camera_toggle(self, camera_id: int, state: int):
        """Handle camera checkbox toggle"""
        enabled = state == Qt.CheckState.Checked.value
        self.multi_camera_layout_combos[camera_id].setEnabled(enabled)
        self._update_multi_camera_preview()

    def _on_multi_camera_layout_change(self, camera_id: int, layout_text: str):
        """Handle layout combo change"""
        self._update_multi_camera_preview()

    def _update_multi_camera_preview(self):
        """Update the preview of current multi-camera configuration"""
        selected_cameras = []
        total_presets = 0

        for camera_id, checkbox in self.multi_camera_checkboxes.items():
            if checkbox.isChecked():
                camera = self.settings.get_camera(camera_id)
                if camera:
                    layout_combo = self.multi_camera_layout_combos[camera_id]
                    layout_text = layout_combo.currentText()

                    if "12 presets" in layout_text:
                        preset_count = 12
                    elif "8 presets" in layout_text:
                        preset_count = 8
                    else:
                        preset_count = 8  # Default fallback

                    selected_cameras.append(f"{camera.name}: {layout_text}")
                    total_presets += preset_count

        if selected_cameras:
            preview_text = f"Selected Cameras ({len(selected_cameras)}):\n" + "\n".join(selected_cameras)
            preview_text += f"\n\nTotal Presets: {total_presets}/48"
            if total_presets > 48:
                preview_text += " ⚠️ Over limit!"
        else:
            preview_text = "No cameras selected"

        self.multi_camera_preview_label.setText(preview_text)

    def _save_multi_camera_config(self):
        """Save the current multi-camera configuration"""
        config = {}

        for camera_id, checkbox in self.multi_camera_checkboxes.items():
            if checkbox.isChecked():
                layout_combo = self.multi_camera_layout_combos[camera_id]
                layout_text = layout_combo.currentText()

                # Determine preset count from layout
                if "12 presets" in layout_text:
                    preset_count = 12
                elif "8 presets" in layout_text:
                    preset_count = 8
                else:
                    preset_count = 8

                config[str(camera_id)] = {
                    'enabled': True,
                    'layout': layout_text,
                    'preset_count': preset_count
                }

        self.settings.multi_camera_presets = config
        self.settings.save()

        if hasattr(self, 'toast') and self.toast:
            self.toast.show_message("Multi-camera configuration saved!", duration=2000)

    def _reset_multi_camera_config(self):
        """Reset multi-camera configuration to default (all disabled)"""
        for checkbox in self.multi_camera_checkboxes.values():
            checkbox.setChecked(False)

        for combo in self.multi_camera_layout_combos.values():
            combo.setCurrentText("4×3 (12 presets)")
            combo.setEnabled(False)

        self.settings.multi_camera_presets = {}
        self.settings.save()
        self._update_multi_camera_preview()

        if hasattr(self, 'toast') and self.toast:
            self.toast.show_message("Configuration reset to default", duration=2000)

    def _create_operations_panel(self) -> QWidget:
        """Create Camera Operations panel (Category 6) - two columns"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        container, main_layout, left_layout, right_layout = self._create_two_column_layout()
        
        # LEFT COLUMN
        
        power_label = QLabel("POWER CONTROL")
        power_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        left_layout.addWidget(power_label)
        
        power_on_btn = QPushButton("Power ON")
        power_on_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        power_on_btn.clicked.connect(lambda: self._send_camera_command("O", endpoint="aw_cam"))
        left_layout.addWidget(power_on_btn)
        
        power_standby_btn = QPushButton("Standby")
        power_standby_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        power_standby_btn.clicked.connect(lambda: self._send_camera_command("S", endpoint="aw_cam"))
        left_layout.addWidget(power_standby_btn)
        
        left_layout.addStretch()
        
        # RIGHT COLUMN
        
        status_label = QLabel("STATUS")
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: bold;
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border_light']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right_layout.addWidget(status_label)
        
        query_status_btn = QPushButton("Query Status")
        query_status_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 14px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        query_status_btn.clicked.connect(lambda: self._send_camera_command("QID", endpoint="aw_cam"))
        right_layout.addWidget(query_status_btn)
        
        right_layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_advanced_panel(self) -> QWidget:
        """Create Advanced Features panel (Category 7)"""
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Image Transform Group
        transform_group = QGroupBox("Image Transform")
        transform_layout = QVBoxLayout(transform_group)
        transform_layout.setSpacing(8)
        
        flip_h_btn = QPushButton("Flip Horizontal")
        flip_h_btn.setCheckable(True)
        flip_h_btn.clicked.connect(lambda checked: self._send_camera_command(f"OSD:80:{'1' if checked else '0'}"))
        transform_layout.addWidget(flip_h_btn)
        
        flip_v_btn = QPushButton("Flip Vertical")
        flip_v_btn.setCheckable(True)
        flip_v_btn.clicked.connect(lambda checked: self._send_camera_command(f"OSD:81:{'1' if checked else '0'}"))
        transform_layout.addWidget(flip_v_btn)
        
        rotation_combo = QComboBox()
        rotation_combo.addItems(["0°", "90°", "180°", "270°"])
        rotation_combo.currentTextChanged.connect(lambda v: self._send_camera_command(f"OSD:82:{['0°', '90°', '180°', '270°'].index(v)}"))
        transform_layout.addWidget(QLabel("Rotation:"))
        transform_layout.addWidget(rotation_combo)
        
        layout.addWidget(transform_group)
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_side_panel(self) -> QWidget:
        """Create right side panel with collapsible PTZ controls, OSD menu, overlays, and multiview"""
        # Outer container with fixed width
        panel = QFrame()
        panel.setFixedWidth(250)
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
        
        # Scroll area for content with touch scrolling
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
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
            view.setAutoFillBackground(True)
            view.setStyleSheet(f"""
                QListView, QListView::viewport, QAbstractScrollArea, QAbstractScrollArea::viewport, QWidget, QFrame {{
                    background-color: {COLORS['surface']};
                }}
                QListView {{
                    border: none;
                    outline: none;
                    padding: 0px;
                    margin: 0px;
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
        
        # Camera Control UI removed
        
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
        
        # Overlay disable all button (for performance)
        disable_all_btn = QPushButton("Disable All Overlays")
        disable_all_btn.setObjectName("overlayButton")
        disable_all_btn.setFixedHeight(32)
        disable_all_btn.setStyleSheet(f"""
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
        """)
        disable_all_btn.clicked.connect(self._disable_all_overlays)
        overlays_layout.addWidget(disable_all_btn)
        
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
        
        # Grid mode radios (Off / Thirds / Full / Both)
        grid_layout.addWidget(self._ensure_grid_mode_radio_list(context_key="live_overlay_grid"))
        
        self.grid_panel.setVisible(False)
        layout.addWidget(self.grid_panel)
        
        # ===== Frame Guides Toggle Button =====
        self.frame_guide_toggle_btn = QPushButton("▼ Frame Guides")
        self.frame_guide_toggle_btn.setCheckable(True)
        self.frame_guide_toggle_btn.setFixedHeight(36)
        self.frame_guide_toggle_btn.setStyleSheet(toggle_btn_style)
        self.frame_guide_toggle_btn.clicked.connect(self._toggle_frame_guide_panel)
        layout.addWidget(self.frame_guide_toggle_btn)
        
        # Frame Guides Panel (collapsible) - scrollable (Option B) to avoid clipping
        self.frame_guide_panel = TouchScrollArea()
        self.frame_guide_panel.setWidgetResizable(True)
        self.frame_guide_panel.setStyleSheet("background: transparent; border: none;")
        self.frame_guide_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._frame_guide_panel_inner = QFrame()
        self._frame_guide_panel_inner.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        self.frame_guide_panel.setWidget(self._frame_guide_panel_inner)

        frame_guide_layout = QVBoxLayout(self._frame_guide_panel_inner)
        frame_guide_layout.setContentsMargins(6, 6, 6, 6)
        frame_guide_layout.setSpacing(4)
        
        # Category + Template selection (radio buttons instead of dropdowns)
        frame_guide_layout.addWidget(self._ensure_frame_category_radio_row(context_key="live_overlay"))
        frame_guide_layout.addWidget(self._ensure_frame_template_radio_list(context_key="live_overlay"))
        
        # Color picker radios + small swatches (match Camera Control radio look)
        if not hasattr(self, '_frame_colors'):
            self._frame_colors = {
                "White": ((255, 255, 255), "#FFFFFF"),
                "Red": ((0, 0, 255), "#FF0000"),      # BGR for OpenCV
                "Green": ((0, 255, 0), "#00FF00"),    # BGR for OpenCV
                "Blue": ((255, 0, 0), "#0000FF"),     # BGR for OpenCV
                "Yellow": ((0, 255, 255), "#FFFF00"), # BGR for OpenCV
            }
        
        if not hasattr(self, '_frame_color_group'):
            self._frame_color_group = QButtonGroup(self._frame_guide_panel_inner)
            self._frame_color_group.setExclusive(True)
        if not hasattr(self, '_color_radios'):
            self._color_radios = {}

        radio_style = f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 12px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['border']};
                border-radius: 9px;
                background-color: {COLORS['surface']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """

        color_grid = QGridLayout()
        color_grid.setHorizontalSpacing(12)
        color_grid.setVerticalSpacing(6)

        current_bgr = None
        try:
            current_bgr = getattr(self.preview_widget.frame_guide, 'line_color', None)
        except Exception:
            current_bgr = None

        for idx, (name, (bgr, hex_color)) in enumerate(self._frame_colors.items()):
            row = idx // 2
            col = idx % 2

            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(6)

            radio = self._color_radios.get(name)
            if radio is None:
                radio = QRadioButton(name)
                radio.setStyleSheet(radio_style)
                radio.toggled.connect(lambda checked, n=name: self._on_frame_color_clicked(n) if checked else None)
                self._frame_color_group.addButton(radio)
                self._color_radios[name] = radio

            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f"background-color: {hex_color}; border: 1px solid {COLORS['border']}; border-radius: 3px;")

            item_layout.addWidget(radio)
            item_layout.addWidget(swatch)
            item_layout.addStretch()
            color_grid.addWidget(item, row, col)

            if current_bgr == bgr:
                radio.setChecked(True)

        if self._color_radios.get("White") and not any(r.isChecked() for r in self._color_radios.values()):
            self._color_radios["White"].setChecked(True)
            self._on_frame_color_clicked("White")

        frame_guide_layout.addLayout(color_grid)
        frame_guide_layout.addSpacing(8)
        
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
        
        # Custom Frame button (Live overlay panel)
        self.drag_mode_btn_overlay = QPushButton("Custom Frame")
        self.drag_mode_btn_overlay.setCheckable(True)
        self.drag_mode_btn_overlay.setFixedHeight(30)
        self.drag_mode_btn_overlay.setStyleSheet(action_btn_style)
        # Option A: tap to toggle; when turning OFF, show naming row
        self.drag_mode_btn_overlay.toggled.connect(lambda checked: self._on_custom_frame_toggled("overlay", checked))
        
        # Clear button (Live overlay panel) - side by side with Custom Frame
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

        # Custom Frame + Clear row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.addWidget(self.drag_mode_btn_overlay)
        btn_row.addWidget(clear_guide_btn)
        
        frame_guide_layout.addLayout(btn_row)

        # Inline "Save name" row (Option A) for overlay panel
        if not hasattr(self, "_custom_guide_name_row_overlay"):
            self._custom_guide_name_row_overlay = QWidget()
            self._custom_guide_name_row_overlay.setStyleSheet("background: transparent;")
            name_row_layout = QHBoxLayout(self._custom_guide_name_row_overlay)
            name_row_layout.setContentsMargins(0, 0, 0, 0)
            name_row_layout.setSpacing(6)

            self._custom_guide_name_input_overlay = QLineEdit()
            self._custom_guide_name_input_overlay.setPlaceholderText("Custom guide name…")
            self._custom_guide_name_input_overlay.setFixedHeight(30)
            self._custom_guide_name_input_overlay.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 6px 8px;
                    color: {COLORS['text']};
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border-color: {COLORS['primary']};
                }}
            """)
            self._custom_guide_name_input_overlay._osk_allow_on_live = True
            self._connect_field_to_osk(self._custom_guide_name_input_overlay)
            name_row_layout.addWidget(self._custom_guide_name_input_overlay, 1)

            cancel_btn = QPushButton("Cancel")
            cancel_btn.setFixedHeight(30)
            cancel_btn.setStyleSheet(action_btn_style)
            cancel_btn.clicked.connect(lambda: self._hide_custom_guide_name_row("overlay"))
            name_row_layout.addWidget(cancel_btn)

            ok_btn = QPushButton("Save")
            ok_btn.setFixedHeight(30)
            ok_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    border: 1px solid {COLORS['primary']};
                    border-radius: 4px;
                    color: {COLORS['background']};
                    font-size: 10px;
                    font-weight: 700;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary']};
                }}
            """)
            ok_btn.clicked.connect(lambda: self._commit_custom_guide_name("overlay"))
            name_row_layout.addWidget(ok_btn)

            self._custom_guide_name_row_overlay.setVisible(False)

        frame_guide_layout.addWidget(self._custom_guide_name_row_overlay)
        
        # Add spacing at bottom
        frame_guide_layout.addSpacing(32)
        
        self.frame_guide_panel.setVisible(False)
        # Give Frame Guides the remaining vertical space when expanded
        layout.addWidget(self.frame_guide_panel, 1)
        
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
    
    
    def _toggle_overlays_panel(self):
        """Toggle Overlays panel visibility"""
        visible = self.overlays_toggle_btn.isChecked()
        self.overlays_panel.setVisible(visible)
        self.overlays_toggle_btn.setText("▲ Overlays" if visible else "▼ Overlays")
    
    def _disable_all_overlays(self):
        """Disable all overlays for better performance"""
        try:
            # Disable all overlays
            self.preview_widget.false_color.disable()
            self.preview_widget.waveform.disable()
            self.preview_widget.vectorscope.disable()
            self.preview_widget.focus_assist.disable()
            self.preview_widget.grid_overlay.disable()
            self.preview_widget.frame_guide.disable()
            
            # Update worker state
            self.preview_widget._update_worker_state()
            
            # Update button states
            for btn in self.overlay_buttons.values():
                btn.setChecked(False)
            
            self.toast.show_message("All overlays disabled", duration=1500)
            logger.info("All overlays disabled for performance")
        except Exception as e:
            logger.error(f"Error disabling overlays: {e}")
            self.toast.show_message("Error disabling overlays", duration=2000, error=True)
    
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
            self.preview_widget.frame_guide.set_enabled(True)
    
    def _toggle_split_panel(self):
        """Toggle Split Compare panel visibility"""
        visible = self.split_toggle_btn.isChecked()
        self.split_panel.setVisible(visible)
        self.split_toggle_btn.setText("▲ Split Compare" if visible else "▼ Split Compare")
        
        # Populate camera dropdown when opening
        if visible:
            self._populate_split_cameras()
    
    def _toggle_grid_type(self, grid_type: str):
        """
        Legacy toggle entrypoint (kept for compatibility).

        We now expose a radio-group UI (Off / Thirds / Full / Both). This method
        preserves old behavior: toggling one flag while keeping the other.
        """
        overlay = getattr(self.preview_widget, "grid_overlay", None)
        if overlay is None:
            return

        thirds = bool(getattr(overlay, "rule_of_thirds", False))
        full = bool(getattr(overlay, "full_grid", False))

        if grid_type == "thirds":
            thirds = not thirds
        elif grid_type == "grid":
            full = not full
        else:
            return

        overlay.rule_of_thirds = thirds
        overlay.full_grid = full
        overlay.set_enabled(bool(thirds or full))
        self._sync_grid_mode_radios()

    # === Grid mode selectors (radio-based) ===

    def _current_grid_mode(self) -> str:
        """Return current grid mode: off | thirds | grid | both."""
        overlay = getattr(self.preview_widget, "grid_overlay", None)
        if overlay is None or not bool(getattr(overlay, "enabled", False)):
            return "off"

        thirds = bool(getattr(overlay, "rule_of_thirds", False))
        full = bool(getattr(overlay, "full_grid", False))

        if thirds and full:
            return "both"
        if thirds:
            return "thirds"
        if full:
            return "grid"
        return "off"

    def _apply_grid_mode(self, mode: str):
        """Apply grid mode to the underlying overlay and sync UIs."""
        overlay = getattr(self.preview_widget, "grid_overlay", None)
        if overlay is None:
            return

        mode = (mode or "off").lower()
        if mode == "off":
            overlay.rule_of_thirds = False
            overlay.full_grid = False
            overlay.set_enabled(False)
        elif mode == "thirds":
            overlay.rule_of_thirds = True
            overlay.full_grid = False
            overlay.set_enabled(True)
        elif mode == "grid":
            overlay.rule_of_thirds = False
            overlay.full_grid = True
            overlay.set_enabled(True)
        elif mode == "both":
            overlay.rule_of_thirds = True
            overlay.full_grid = True
            overlay.set_enabled(True)
        else:
            return

        self._sync_grid_mode_radios()

    def _sync_grid_mode_radios(self):
        """Sync grid radio selections across all contexts."""
        mode = self._current_grid_mode()
        for _, info in getattr(self, "_grid_mode_radios_by_ctx", {}).items():
            radios = info.get("radios", {})
            if mode in radios and not radios[mode].isChecked():
                radios[mode].blockSignals(True)
                radios[mode].setChecked(True)
                radios[mode].blockSignals(False)
    
    def _ensure_grid_mode_radio_list(self, context_key: str) -> QWidget:
        """Create (or reuse) a vertical radio list for grid modes."""
        if not hasattr(self, "_grid_mode_radios_by_ctx"):
            self._grid_mode_radios_by_ctx = {}

        if context_key in self._grid_mode_radios_by_ctx:
            return self._grid_mode_radios_by_ctx[context_key]["widget"]

        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)

        style = f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 12px;
                spacing: 10px;
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                background-color: {COLORS['surface']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """

        group = QButtonGroup(container)
        group.setExclusive(True)
        radios: dict[str, QRadioButton] = {}

        # Keep labels short and touch-friendly
        options = [
            ("Off", "off"),
            ("Thirds", "thirds"),
            ("Full Grid", "grid"),
            ("Both", "both"),
        ]

        current = self._current_grid_mode()
        for label, mode in options:
            r = QRadioButton(label)
            r.setStyleSheet(style)
            r.setMinimumHeight(32)
            r.setChecked(mode == current)
            r.toggled.connect(lambda checked, m=mode: self._apply_grid_mode(m) if checked else None)
            group.addButton(r)
            radios[mode] = r
            col.addWidget(r)

        self._grid_mode_radios_by_ctx[context_key] = {"widget": container, "group": group, "radios": radios}
        return container

    # === Frame guide selectors (radio-based, replaces dropdowns) ===

    def _ensure_frame_category_radio_row(self, context_key: str) -> QWidget:
        """Create (or reuse) a radio row for frame guide categories."""
        if not hasattr(self, "_frame_category_selected"):
            self._frame_category_selected = "Social"
        if not hasattr(self, "_frame_category_radios_by_ctx"):
            self._frame_category_radios_by_ctx = {}

        if context_key in self._frame_category_radios_by_ctx:
            return self._frame_category_radios_by_ctx[context_key]["widget"]

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        style = f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 12px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['border']};
                border-radius: 9px;
                background-color: {COLORS['surface']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """

        group = QButtonGroup(container)
        group.setExclusive(True)
        radios: dict[str, QRadioButton] = {}

        for cat in ["Social", "Cinema", "TV/Broadcast", "Custom"]:
            r = QRadioButton(cat)
            r.setStyleSheet(style)
            r.setChecked(cat == self._frame_category_selected)
            r.toggled.connect(lambda checked, c=cat: self._on_frame_category_changed(c) if checked else None)
            group.addButton(r)
            radios[cat] = r
            row.addWidget(r)

        row.addStretch()
        self._frame_category_radios_by_ctx[context_key] = {"widget": container, "group": group, "radios": radios}
        return container

    def _ensure_frame_template_radio_list(self, context_key: str) -> QWidget:
        """Create (or reuse) a scrollable radio list for templates."""
        if not hasattr(self, "_frame_template_lists_by_ctx"):
            self._frame_template_lists_by_ctx = {}

        if context_key in self._frame_template_lists_by_ctx:
            return self._frame_template_lists_by_ctx[context_key]["widget"]

        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        # Show 2 columns × 4 rows (8 items) with compact spacing
        scroll.setFixedHeight(132)  # ~4×28px rows + spacing

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        grid = QGridLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)
        scroll.setWidget(inner)

        info = {
            "widget": scroll,
            "inner": inner,
            "layout": grid,
            "group": QButtonGroup(inner),
            "radios": {},
        }
        info["group"].setExclusive(True)
        self._frame_template_lists_by_ctx[context_key] = info

        self._rebuild_frame_template_radios()
        return scroll

    def _get_frame_templates_for_category(self, category: str) -> list[str]:
        templates = self.preview_widget.frame_guide.get_all_templates()
        if category in templates:
            return [g.name for g in templates[category]]
        if category == "Custom":
            custom_guides = getattr(self.preview_widget.frame_guide, "custom_guides", [])
            if not custom_guides:
                return ["(No custom guides)"]
            return [g.name for g in custom_guides]
        return []

    def _rebuild_frame_template_radios(self):
        """Rebuild template radio lists for all contexts based on selected category."""
        if not hasattr(self, "_frame_category_selected"):
            self._frame_category_selected = "Social"
        if not hasattr(self, "_frame_template_selected"):
            self._frame_template_selected = ""

        names = self._get_frame_templates_for_category(self._frame_category_selected)
        if not names:
            names = ["(No custom guides)"]

        radio_style = f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 11px;
                spacing: 6px;
                padding: 0px;
                margin: 0px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['surface']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """

        is_custom_category = self._frame_category_selected == "Custom"

        for _, info in getattr(self, "_frame_template_lists_by_ctx", {}).items():
            layout: QGridLayout = info["layout"]
            while layout.count():
                item = layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            info["radios"].clear()

            info["group"] = QButtonGroup(info["inner"])
            info["group"].setExclusive(True)

            for idx, name in enumerate(names):
                row = idx // 2
                col = idx % 2
                r = QRadioButton(name)
                r.setStyleSheet(radio_style)
                r.setMinimumHeight(28)
                r.toggled.connect(lambda checked, n=name: self._on_frame_template_changed(n) if checked else None)
                info["group"].addButton(r)
                info["radios"][name] = r
                layout.addWidget(r, row, col)

                # Placeholder should not be selectable
                if name == "(No custom guides)":
                    r.setEnabled(False)
                # Long press on custom guides -> delete menu
                elif is_custom_category:
                    self._attach_custom_guide_long_press(r, name)
        
            # Preserve selection if it still exists in the new list.
            # Otherwise, leave unselected (matches old dropdown behavior: category change does not auto-enable).
            if self._frame_template_selected in info["radios"]:
                info["radios"][self._frame_template_selected].blockSignals(True)
                info["radios"][self._frame_template_selected].setChecked(True)
                info["radios"][self._frame_template_selected].blockSignals(False)

    def _attach_custom_guide_long_press(self, radio: QRadioButton, guide_name: str):
        """Attach long-press handler to a radio to delete a custom guide."""
        if hasattr(radio, "_has_long_press"):
            return
        radio._has_long_press = True

        timer = QTimer(radio)
        timer.setSingleShot(True)
        timer.setInterval(700)  # ms long-press

        def on_timeout():
            self._show_delete_custom_guide_menu(guide_name)

        def on_pressed():
            timer.start()

        def on_released():
            if timer.isActive():
                timer.stop()

        timer.timeout.connect(on_timeout)
        radio.pressed.connect(on_pressed)
        radio.released.connect(on_released)

    def _show_delete_custom_guide_menu(self, guide_name: str):
        """Show context menu for deleting a custom frame guide."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 16px;
                color: {COLORS['text']};
            }}
            QMenu::item {{
                padding: 10px 14px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
        """)
        delete_action = menu.addAction("Delete")

        action = menu.exec(QCursor.pos())
        if action != delete_action:
            return

        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Delete Custom Guide",
            f"Delete custom frame guide '{guide_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self.preview_widget.frame_guide.delete_custom_guide(guide_name)
            if deleted:
                # If we just deleted the selected guide, clear selection & disable
                if getattr(self.preview_widget.frame_guide.active_guide, "name", None) == guide_name:
                    self.preview_widget.frame_guide.clear()
                    self.preview_widget.frame_guide.set_enabled(False)
                    self._frame_template_selected = ""
                # Refresh lists
                self._rebuild_frame_template_radios()
                if hasattr(self, "toast") and self.toast:
                    # ToastWidget API is show_message(message, duration=..., error=...)
                    try:
                        self.toast.show_message("Custom guide deleted", duration=1500)
                    except TypeError:
                        # Fallback (older usage)
                        self.toast.show_message("Custom guide deleted", 1500)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete: {e}")
    
    def _on_frame_category_changed(self, category: str):
        """Handle frame guide category change"""
        self._frame_category_selected = category

        # Keep category radios in sync across contexts
        for _, info in getattr(self, "_frame_category_radios_by_ctx", {}).items():
            radios = info["radios"]
            if category in radios and not radios[category].isChecked():
                radios[category].blockSignals(True)
                radios[category].setChecked(True)
                radios[category].blockSignals(False)

        self._rebuild_frame_template_radios()
    
    def _on_frame_template_changed(self, template_name: str):
        """Handle frame guide template selection"""
        if not template_name or template_name == "(No custom guides)":
            return
        
        self._frame_template_selected = template_name
        category = getattr(self, "_frame_category_selected", "Social")

        # Sync selection across all template radio lists
        for _, info in getattr(self, "_frame_template_lists_by_ctx", {}).items():
            radios = info.get("radios", {})
            if template_name in radios and not radios[template_name].isChecked():
                radios[template_name].blockSignals(True)
                radios[template_name].setChecked(True)
                radios[template_name].blockSignals(False)

        if self.preview_widget.frame_guide.set_guide_by_name(category, template_name):
            # Enable frame guide when user explicitly selects from dropdown
            self.preview_widget.frame_guide.set_enabled(True)
            # Keep both Custom Frame buttons in sync
            self._set_drag_buttons_checked(bool(self.preview_widget.frame_guide.drag_mode))
    
    def _toggle_drag_mode(self):
        """Toggle drag/resize mode for frame guide"""
        btn = self.sender() if isinstance(self.sender(), QPushButton) else None
        checked = btn.isChecked() if btn is not None and btn.isCheckable() else False
        self._set_drag_buttons_checked(checked)
        if checked:
            self.preview_widget.frame_guide.enable_drag_mode()
            self.preview_widget.frame_guide.set_enabled(True)
        else:
            self.preview_widget.frame_guide.disable_drag_mode()

    def _on_custom_frame_toggled(self, which: str, checked: bool):
        """
        Option A (updated):
        - Tap 1: enable drag mode AND show inline name row
        - Tap 2: disable drag mode AND keep inline name row visible
        OSK only opens when the user taps the name field.
        """
        self._set_drag_buttons_checked(checked)
        if checked:
            self.preview_widget.frame_guide.enable_drag_mode()
            self.preview_widget.frame_guide.set_enabled(True)
            self._show_custom_guide_name_row(which, focus=False)
        else:
            self.preview_widget.frame_guide.disable_drag_mode()
            self._show_custom_guide_name_row(which, focus=False)
    
    def _on_frame_color_clicked(self, color_name: str):
        """Handle frame guide color button click"""
        # Sync UI state (support legacy square buttons and new radio buttons)
        if hasattr(self, '_color_buttons'):
            for name, btn in self._color_buttons.items():
                btn.setChecked(name == color_name)
        if hasattr(self, '_color_radios'):
            for name, radio in self._color_radios.items():
                if name == color_name and not radio.isChecked():
                    radio.setChecked(True)
        
        # Apply color
        if color_name in self._frame_colors:
            bgr_color, hex_color = self._frame_colors[color_name]
            self.preview_widget.frame_guide.line_color = bgr_color
    
    def _save_custom_frame_guide(self):
        """Deprecated entrypoint (kept for compatibility)."""
        self._show_custom_guide_name_row("bottom")

    def _show_custom_guide_name_row(self, which: str, focus: bool = False):
        """Show the inline name row. If focus=True, focus the input (will open OSK)."""
        row = getattr(self, f"_custom_guide_name_row_{which}", None)
        inp = getattr(self, f"_custom_guide_name_input_{which}", None)
        if row is None or inp is None:
            return

        row.setVisible(True)
        if focus:
            inp.setFocus()
            inp.selectAll()

    def _hide_custom_guide_name_row(self, which: str):
        """Hide inline name row and clear."""
        row = getattr(self, f"_custom_guide_name_row_{which}", None)
        inp = getattr(self, f"_custom_guide_name_input_{which}", None)
        if inp is not None:
            inp.setText("")
            inp.clearFocus()
        if row is not None:
            row.setVisible(False)
        # Hide OSK when cancelling
        if self.osk:
            self.osk.hide_keyboard()

    def _commit_custom_guide_name(self, which: str):
        """Save current frame guide as custom preset using the inline name."""
        inp = getattr(self, f"_custom_guide_name_input_{which}", None)
        if inp is None:
            return
        name = inp.text().strip()
        if not name:
            return
        # Important: don't hide the row synchronously while the Save button click
        # handler is still executing (can trigger Qt crashes on some builds).
        if not self.preview_widget.frame_guide.save_current_as_custom(name):
            if hasattr(self, "toast") and self.toast:
                self.toast.show_message("Nothing to save", duration=1500, error=True)
            return

        def _after_save():
            # Now safe to hide the row
            self._hide_custom_guide_name_row(which)

            # Uncheck Custom Frame button and disable drag mode
            self._set_drag_buttons_checked(False)
            self.preview_widget.frame_guide.disable_drag_mode()
                
            # Switch to Custom category and select the saved guide
            self._on_frame_category_changed("Custom")
            self._on_frame_template_changed(name)

            if hasattr(self, "toast") and self.toast:
                self.toast.show_message("Custom guide saved", duration=1500)

        QTimer.singleShot(0, _after_save)

    def _set_drag_buttons_checked(self, checked: bool):
        """Keep both Custom Frame buttons (if present) in sync."""
        for attr in ("drag_mode_btn_guides", "drag_mode_btn_overlay"):
            btn = getattr(self, attr, None)
            if btn is not None and btn.isCheckable():
                btn.blockSignals(True)
                btn.setChecked(checked)
                btn.blockSignals(False)

    def _attach_long_press(self, widget: QWidget, callback, ms: int = 700):
        """Attach a long-press callback to a widget with pressed/released."""
        if hasattr(widget, "_long_press_attached"):
            return
        widget._long_press_attached = True
        timer = QTimer(widget)
        timer.setSingleShot(True)
        timer.setInterval(ms)

        def on_timeout():
            callback()

        def on_pressed():
            timer.start()

        def on_released():
            if timer.isActive():
                timer.stop()

        timer.timeout.connect(on_timeout)
        if hasattr(widget, "pressed"):
            widget.pressed.connect(on_pressed)
        if hasattr(widget, "released"):
            widget.released.connect(on_released)

    # (Removed: 3-second auto-hide timer; inline row stays visible until user saves/cancels/clears.)
    
    def _clear_frame_guide(self):
        """Clear the active frame guide"""
        self.preview_widget.frame_guide.clear()
        self.preview_widget.frame_guide.set_enabled(False)
        self.preview_widget.frame_guide.disable_drag_mode()
        self._set_drag_buttons_checked(False)
        # Hide inline naming rows when clearing
        self._hide_custom_guide_name_row("bottom")
        self._hide_custom_guide_name_row("overlay")
    
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
            base_url = f"http://{camera.ip_address}"
            auth = (camera.username, camera.password)
            
            # Try multiple Panasonic tally/LED off commands
            # Different camera models and endpoints may use different commands
            # LED0/LED1 commands are often used for tally control
            tally_commands = [
                # aw_cam endpoint commands (often more reliable for tally)
                ("aw_cam", "%23LED0"),  # LED off (tally off) via aw_cam
                ("aw_cam", "LED0"),     # Without URL encoding
                ("aw_cam", "%23TAL0"), # Tally off via aw_cam
                ("aw_cam", "TAL0"),    # Without encoding
                
                # aw_ptz endpoint commands
                ("aw_ptz", "%23LED0"),  # LED off via aw_ptz
                ("aw_ptz", "LED0"),     # Without encoding
                ("aw_ptz", "%23TAL0"), # Tally off via aw_ptz
                ("aw_ptz", "TAL0"),     # Without encoding
                ("aw_ptz", "%23TL0"),   # Alternative format
                ("aw_ptz", "TL0"),      # Without encoding
            ]
            
            # Send each command multiple times with delays to ensure it's received
            for attempt in range(5):  # Send 5 times
                for endpoint, cmd in tally_commands:
                    try:
                        # Try with res parameter
                        url = f"{base_url}/cgi-bin/{endpoint}?cmd={cmd}&res=1"
                        response = requests.get(url, auth=auth, timeout=0.5)
                        if response.status_code == 200:
                            print(f"Tally off command sent successfully: {endpoint}?cmd={cmd}")
                        
                        # Also try without res parameter
                        url2 = f"{base_url}/cgi-bin/{endpoint}?cmd={cmd}"
                        response2 = requests.get(url2, auth=auth, timeout=0.5)
                        if response2.status_code == 200:
                            print(f"Tally off command sent successfully (no res): {endpoint}?cmd={cmd}")
                        
                        time.sleep(0.03)
                    except Exception as e:
                        pass
                
                if attempt < 4:  # Don't sleep after last attempt
                    time.sleep(0.15)  # Delay between batches
            
            print(f"Tally off commands sent (5 attempts, {len(tally_commands)} command variants)")
        except Exception as e:
            print(f"Tally off error: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    
    def _create_camera_bar(self) -> QWidget:
        """Create bottom camera selection bar"""
        # Outer scroll area for the entire bar with touch scrolling
        # In portrait mode: 100px height (80px button + 10px top margin + 10px bottom margin)
        bar_height = 100 if (hasattr(self, 'settings') and self.settings.portrait_mode) else 120
        bar_scroll = TouchScrollArea()
        bar_scroll.setWidgetResizable(True)
        bar_scroll.setFixedHeight(bar_height)  # Height with matching top/bottom padding in portrait
        # Add border-top for separation in portrait mode
        if hasattr(self, 'settings') and self.settings.portrait_mode:
            bar_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {COLORS['surface']};
                    border-top: 1px solid {COLORS['border']};
                }}
            """)
        else:
            bar_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                }}
            """)
        
        # Inner bar frame
        bar = QFrame()
        bar.setFixedHeight(bar_height)  # Match scroll area height
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
            }}
        """)
        
        layout = QHBoxLayout(bar)
        # Matching top and bottom padding in portrait mode
        if hasattr(self, 'settings') and self.settings.portrait_mode:
            # Bar height 100px, button height 80px, top margin 10px, bottom margin 10px
            layout.setContentsMargins(0, 10, 0, 10)
        else:
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
        """Rebuild camera buttons - Canon RC-IP100 inspired horizontal bar"""
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
            btn.setFixedSize(100, 72)  # Slightly wider for better touch
            btn.setToolTip(f"{camera.name}\n{camera.ip_address}")
            
            # Canon-style camera button with improved styling
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    color: {COLORS['text']};
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['surface_hover']};
                    border-color: {COLORS['secondary']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                    color: {COLORS['background']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary_dark']};
                }}
            """)
            
            self.camera_button_group.addButton(btn, i)
            self.camera_buttons[i] = btn
            
            # If 10 or fewer cameras, use stretch to spread them out
            if num_cameras <= 10:
                self.camera_buttons_layout.addWidget(btn, stretch=1)
            else:
                self.camera_buttons_layout.addWidget(btn)
    
    def _toggle_demo_mode(self):
        """Toggle demo video mode"""
        if self.demo_btn.isChecked():
            try:
                # Stop multiview if running
                if self._multiview_active:
                    self._stop_multiview()
                
                # Stop current camera stream and remove callbacks
                if self.current_camera_id is not None:
                    if self.current_camera_id in self.camera_streams:
                        stream = self.camera_streams[self.current_camera_id]
                        stream.remove_frame_callback(self._on_frame_received)
                        stream.stop()
                
                # Uncheck all camera buttons
                checked_btn = self.camera_button_group.checkedButton()
                if checked_btn:
                    self.camera_button_group.setExclusive(False)
                    checked_btn.setChecked(False)
                    self._set_camera_button_unchecked_style(checked_btn)
                    checked_btn.update()
                    self.camera_button_group.setExclusive(True)
                
                self.current_camera_id = None
                
                # Small delay to ensure camera streams are fully stopped
                QTimer.singleShot(100, self._start_demo_video)
            except Exception as e:
                logger.error(f"Error starting demo mode: {e}", exc_info=True)
                self.demo_btn.setChecked(False)
        else:
            # Stop demo mode
            try:
                self._stop_demo_video()
            except Exception as e:
                logger.error(f"Error stopping demo mode: {e}", exc_info=True)
    
    def _start_demo_video(self):
        """Start playing demo video with test pattern"""
        import threading
        
        # Ensure demo is not already running
        if self._demo_running:
            logger.warning("Demo mode already running, skipping start")
            return
        
        # Ensure preview widget exists
        if not hasattr(self, 'preview_widget') or self.preview_widget is None:
            logger.warning("Preview widget not available, cannot start demo")
            return
        
        try:
            self._demo_running = True
            self._demo_thread = threading.Thread(target=self._demo_video_loop, daemon=True)
            self._demo_thread.start()
        except Exception as e:
            logger.error(f"Error starting demo video thread: {e}", exc_info=True)
            self._demo_running = False
            self._demo_thread = None
            if hasattr(self, 'demo_btn'):
                self.demo_btn.setChecked(False)
    
    def _start_demo_on_init(self):
        """Start demo mode on initialization (called with delay to ensure UI is ready)"""
        try:
            # Ensure preview widget exists before starting demo
            if not hasattr(self, 'preview_widget') or self.preview_widget is None:
                logger.warning("Preview widget not ready, skipping demo mode start")
                return
            
            # Set demo button to checked state
            if hasattr(self, 'demo_btn'):
                self.demo_btn.setChecked(True)
            # Start demo video
            self._start_demo_video()
        except Exception as e:
            logger.error(f"Error starting demo mode on init: {e}", exc_info=True)
            # Don't crash - just skip demo mode
    
    def _switch_from_demo_to_camera(self, camera_id: int):
        """Switch from demo mode to a camera (called after initialization delay)"""
        try:
            # Stop demo mode if running
            if self._demo_running:
                self._stop_demo_video()
                if hasattr(self, 'demo_btn'):
                    self.demo_btn.setChecked(False)
            # Select the camera
            self._select_camera(camera_id)
        except Exception as e:
            logger.error(f"Error switching from demo to camera {camera_id}: {e}", exc_info=True)
            # Don't crash - camera selection will happen later if user manually selects
    
    def _stop_demo_video(self):
        """Stop demo video (thread-safe)"""
        # Set flag first to stop the loop
        self._demo_running = False
        
        # Wait for thread to finish (with timeout)
        if hasattr(self, '_demo_thread') and self._demo_thread:
            try:
                if self._demo_thread.is_alive():
                    self._demo_thread.join(timeout=2)  # Increased timeout
            except Exception as e:
                logger.warning(f"Error joining demo thread: {e}")
            finally:
                self._demo_thread = None
        
        # Clear preview after thread is stopped
        if hasattr(self, 'preview_widget') and self.preview_widget is not None:
            try:
                self.preview_widget.clear_frame()
            except Exception as e:
                logger.warning(f"Error clearing preview frame: {e}")
    
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
            
            # Send frame to preview (safety check - only if demo is still running)
            if self._demo_running and hasattr(self, 'preview_widget') and self.preview_widget is not None:
                try:
                    self.preview_widget.update_frame(frame)
                except Exception as e:
                    # If preview widget is destroyed or in bad state, stop demo
                    logger.warning(f"Error updating preview in demo mode: {e}")
                    self._demo_running = False
                    break
            
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

        # Page change - show/hide OSK based on page
        self.page_stack.currentChanged.connect(self._on_page_changed)
    
    def _setup_osk(self):
        """Setup On-Screen Keyboard for settings pages"""
        try:
            # Only create OSK if it doesn't exist yet
            if self.osk is not None:
                return
            
            # Create OSK widget (slides from bottom) - parent to central widget for proper positioning
            central_widget = self.centralWidget()
            # Safely get preset texts - ensure osk_presets exists
            try:
                preset_texts = getattr(self.settings, 'osk_presets', ["", "", "", "", "", ""])
                if not isinstance(preset_texts, list) or len(preset_texts) != 6:
                    preset_texts = ["", "", "", "", "", ""]
            except (AttributeError, TypeError):
                preset_texts = ["", "", "", "", "", ""]
            
            if central_widget:
                self.osk = OSKWidget(central_widget, slide_from_top=False, preset_texts=preset_texts)
            else:
                self.osk = OSKWidget(self, slide_from_top=False, preset_texts=preset_texts)
            # Remember the default parent so we can dock/undock OSK for Companion.
            self._osk_default_parent = self.osk.parent()
            self.osk.hide()
            
            # Connect OSK to text fields in Camera, Companion, and Settings pages
            self._connect_osk_to_fields()
            
            # Install event filter to hide OSK when clicking outside text fields
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
                # Also connect focus change signal
                app.focusChanged.connect(self._on_focus_changed)
        except Exception as e:
            print(f"Error setting up OSK: {e}")
            import traceback
            traceback.print_exc()
            self.osk = None  # Ensure osk is None if setup fails

    def eventFilter(self, obj, event):
        """Filter events to hide OSK when clicking outside text fields"""
        # Currently using focus change handler instead of mouse events
        # Mouse event handling was unreliable due to coordinate transformations
        return super().eventFilter(obj, event)

    def _on_focus_changed(self, old_widget, new_widget):
        """Handle focus changes to hide OSK when appropriate"""
        print(f"Focus changed: {old_widget} -> {new_widget}")
        if not self.osk or not self.osk._is_visible:
            print("OSK not visible or doesn't exist")
            return

        # If focus moved to OSK or its children, don't hide
        if new_widget and (new_widget == self.osk or self.osk.isAncestorOf(new_widget)):
            return

        # If focus moved to an input field, don't hide
        if new_widget and isinstance(new_widget, (QLineEdit, QSpinBox, QComboBox)):
            return

        # If focus moved to a text edit or other input widget, don't hide
        if new_widget and isinstance(new_widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
            return

        # If old widget was a text field and new widget is not input-related, hide OSK
        if old_widget and isinstance(old_widget, (QLineEdit, QSpinBox, QComboBox)) and new_widget:
            # Check if new widget is a button, label, or other non-input widget
            if isinstance(new_widget, (QPushButton, QLabel, QFrame, QWidget)):
                print(f"Hiding OSK - focus moved from text field to {type(new_widget).__name__}")
                # If OSK is docked on Cameras page, undock so layout returns to normal.
                try:
                    slot = getattr(self.camera_page, "osk_slot", None)
                    if slot is not None and self.osk.parent() is slot:
                        self._undock_osk_from_camera_page()
                except Exception:
                    pass
                self.osk.hide_keyboard()
                return

        # If focus moved to None or an unknown widget type, hide OSK
        if new_widget is None or not hasattr(new_widget, 'setFocus'):
            print("Hiding OSK - focus lost or moved to unknown widget")
            # If OSK is docked on Cameras page, undock so layout returns to normal.
            try:
                slot = getattr(self.camera_page, "osk_slot", None)
                if slot is not None and self.osk.parent() is slot:
                    self._undock_osk_from_camera_page()
            except Exception:
                pass
            self.osk.hide_keyboard()
    
    def _connect_osk_to_fields(self):
        """Connect OSK to text input fields in settings pages"""
        # Camera page fields
        if hasattr(self.camera_page, 'edit_name_input'):
            self._connect_field_to_osk(self.camera_page.edit_name_input)
        if hasattr(self.camera_page, 'edit_ip_input'):
            self._connect_field_to_osk(self.camera_page.edit_ip_input)
        if hasattr(self.camera_page, 'edit_port_input'):
            # Port is a QSpinBox, but we still want the OSK to target it.
            self._connect_field_to_osk(self.camera_page.edit_port_input)
        if hasattr(self.camera_page, 'edit_user_input'):
            self._connect_field_to_osk(self.camera_page.edit_user_input)
        if hasattr(self.camera_page, 'edit_pass_input'):
            self._connect_field_to_osk(self.camera_page.edit_pass_input)
        if hasattr(self.camera_page, 'easyip_search_input'):
            self._connect_field_to_osk(self.camera_page.easyip_search_input)
        
        # Settings page fields
        if hasattr(self.settings_page, 'atem_ip_input'):
            self._connect_field_to_osk(self.settings_page.atem_ip_input)
        if hasattr(self.settings_page, 'ip_input'):
            self._connect_field_to_osk(self.settings_page.ip_input)
        if hasattr(self.settings_page, 'subnet_input'):
            self._connect_field_to_osk(self.settings_page.subnet_input)
        if hasattr(self.settings_page, 'gateway_input'):
            self._connect_field_to_osk(self.settings_page.gateway_input)
        if hasattr(self.settings_page, 'backup_name_input'):
            self._connect_field_to_osk(self.settings_page.backup_name_input)
        
        # Find all QLineEdit widgets in settings pages
        for page in [self.camera_page, self.companion_page, self.settings_page]:
            for widget in page.findChildren(QLineEdit):
                if widget not in [getattr(self.camera_page, 'edit_name_input', None),
                                 getattr(self.camera_page, 'edit_ip_input', None),
                                 getattr(self.camera_page, 'edit_user_input', None),
                                 getattr(self.camera_page, 'edit_pass_input', None),
                                 getattr(self.camera_page, 'easyip_search_input', None)]:
                    self._connect_field_to_osk(widget)

        # Companion page (QWebEngineView) - show OSK when an HTML input is focused.
        try:
            web_view = getattr(self.companion_page, "web_view", None)
            if web_view is not None:
                self._connect_companion_webview_to_osk(web_view)
        except Exception:
            pass

    def _connect_companion_webview_to_osk(self, web_view):
        """Connect OSK to the Companion QWebEngineView (Option 1: always show on tap)."""
        if web_view is None or not self.osk:
            return
        if hasattr(web_view, "_osk_connected"):
            return

        original_event = web_view.event

        def wrapped_event(ev):
            try:
                # Only on Companion page
                if self.page_stack.currentIndex() == 2 and ev.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.TouchBegin):
                    # Option 1: always show OSK on any tap in Companion.
                    # Use a tiny delay so the page can update focus first.
                    QTimer.singleShot(0, lambda: self._show_osk_for_companion(web_view))
            except Exception:
                pass
            return original_event(ev)

        web_view.event = wrapped_event
        web_view._osk_connected = True

    def _show_osk_for_companion(self, web_view):
        """Show OSK targeting the Companion web view."""
        if not self.osk or web_view is None:
            return
        # Companion should use bottom keyboard
        self.osk.slide_from_top = False
        if hasattr(self.osk, "set_top_offset"):
            self.osk.set_top_offset(0)
        # Target the QWebEngineView itself so OSK can inject text via runJavaScript().
        target = web_view
        # If we're on Companion page, the OSK should be docked into the page layout.
        if self.page_stack.currentIndex() == 2:
            self._dock_osk_to_companion()
        self.osk.show_keyboard(target)

    def _dock_osk_to_companion(self):
        """Dock OSK into the Companion page bottom slot (always visible on Companion)."""
        if not self.osk or not hasattr(self, "companion_page"):
            return
        slot = getattr(self.companion_page, "osk_slot", None)
        if slot is None:
            return

        # Use a stable height; slot.height() can be 0 before layout runs.
        try:
            desired_h = int(getattr(self.osk, "_keyboard_height", OSKWidget.DEFAULT_HEIGHT))
        except Exception:
            desired_h = OSKWidget.DEFAULT_HEIGHT
        desired_h = max(1, desired_h)
        slot.setFixedHeight(desired_h)

        # Ensure slot has a layout.
        lay = slot.layout()
        if lay is None:
            lay = QVBoxLayout(slot)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)

        # Reparent into slot if needed.
        if self.osk.parent() is not slot:
            self.osk.setParent(slot)
            lay.addWidget(self.osk)

        # Enable docked mode so OSK doesn't reposition itself.
        if hasattr(self.osk, "set_docked"):
            self.osk.set_docked(True, height=desired_h, keep_visible=True)
        self.osk.show()
        self.osk.raise_()

    def _undock_osk_from_companion(self):
        """Return OSK to its default overlay parent."""
        if not self.osk:
            return
        # Disable docked mode first.
        if hasattr(self.osk, "set_docked"):
            self.osk.set_docked(False)

        default_parent = getattr(self, "_osk_default_parent", None)
        if default_parent is None:
            default_parent = self.centralWidget() or self

        # If currently inside Companion slot, remove from that layout to avoid stale layout items.
        try:
            slot = getattr(self.companion_page, "osk_slot", None)
            if slot is not None and self.osk.parent() is slot and slot.layout() is not None:
                slot.layout().removeWidget(self.osk)
        except Exception:
            pass

        # Reparent back.
        if self.osk.parent() is not default_parent:
            self.osk.setParent(default_parent)
        self.osk.hide()

    def _dock_osk_to_camera_page(self):
        """Dock OSK into the Cameras page slot so it doesn't cover the bottom sheet."""
        if not self.osk or not hasattr(self, "camera_page"):
            return
        slot = getattr(self.camera_page, "osk_slot", None)
        if slot is None:
            return

        # Use a stable height; slot.height() can be 0 before layout runs.
        try:
            desired_h = int(getattr(self.osk, "_keyboard_height", OSKWidget.DEFAULT_HEIGHT))
        except Exception:
            desired_h = OSKWidget.DEFAULT_HEIGHT
        desired_h = max(1, desired_h)
        slot.setFixedHeight(desired_h)
        # If the edit panel is open, clamp its height so the OSK remains fully visible.
        try:
            if hasattr(self.camera_page, "adjust_bottom_sheet_for_osk"):
                self.camera_page.adjust_bottom_sheet_for_osk()
        except Exception:
            pass

        lay = slot.layout()
        if lay is None:
            lay = QVBoxLayout(slot)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)

        if self.osk.parent() is not slot:
            self.osk.setParent(slot)
            lay.addWidget(self.osk)

        if hasattr(self.osk, "set_docked"):
            # Cameras: docked for layout, but NOT persistent (should hide on focus loss).
            self.osk.set_docked(True, height=desired_h, keep_visible=False)
        self.osk.show()
        self.osk.raise_()

    def _undock_osk_from_camera_page(self):
        """Return OSK to its default overlay parent from the Cameras page."""
        if not self.osk:
            return
        if hasattr(self.osk, "set_docked"):
            self.osk.set_docked(False)

        default_parent = getattr(self, "_osk_default_parent", None)
        if default_parent is None:
            default_parent = self.centralWidget() or self

        try:
            slot = getattr(self.camera_page, "osk_slot", None)
            if slot is not None and self.osk.parent() is slot and slot.layout() is not None:
                slot.layout().removeWidget(self.osk)
                slot.setFixedHeight(0)
        except Exception:
            pass

        if self.osk.parent() is not default_parent:
            self.osk.setParent(default_parent)
        self.osk.hide()
    
    def _connect_field_to_osk(self, field: QLineEdit):
        """Connect a text field to OSK"""
        if field is None:
            return

        # Check if already connected
        if hasattr(field, '_osk_connected'):
            return

        original_focus_in = field.focusInEvent
        original_focus_out = field.focusOutEvent
        
        def focus_in_event(event):
            original_focus_in(event)
            # Only show OSK on Camera, Companion, or Settings pages
            try:
                current_page = self.page_stack.currentIndex()
                allow_on_live = getattr(field, "_osk_allow_on_live", False)
                if current_page in [1, 2, 3] or allow_on_live:  # Camera, Companion, Settings (and selected Live fields)
                    # Show OSK for this field immediately
                    if self.osk:
                        # Live page should slide OSK from top so it doesn't cover bottom panel
                        self.osk.slide_from_top = bool(allow_on_live)
                        if allow_on_live:
                            top_h = 0
                            try:
                                top_h = int(getattr(self, "nav_bar", None).height()) if getattr(self, "nav_bar", None) else 0
                            except Exception:
                                top_h = 0
                            # Position under main menu, on top of preview
                            if hasattr(self.osk, "set_top_offset"):
                                self.osk.set_top_offset(top_h)
                        elif current_page == 1:
                            # Cameras page: dock OSK below the bottom sheet
                            self._dock_osk_to_camera_page()
                            if hasattr(self.osk, "set_top_offset"):
                                self.osk.set_top_offset(0)
                        self.osk.show_keyboard(field)
            except Exception as e:
                print(f"Error in focus_in_event: {e}")

        def focus_out_event(event):
            original_focus_out(event)
            # Don't hide OSK on focus out - let focus_in handle showing for new field
            # OSK will be hidden when clicking outside text fields via page change or Hide button
        
        field.focusInEvent = focus_in_event
        field.focusOutEvent = focus_out_event
        field._osk_connected = True  # Mark as connected

    
    def _on_page_changed(self, index: int):
        """Handle page change - hide OSK if on Live page"""
        if index == 0:  # Live/Preview page
            if self.osk:
                # Only hide if the currently targeted field is NOT explicitly allowed on Live page
                target = getattr(self.osk, "_target_widget", None)
                if not getattr(target, "_osk_allow_on_live", False):
                    self.osk.hide_keyboard()
                # Ensure OSK is not docked when leaving Companion
                self._undock_osk_from_companion()
                # Ensure OSK is not docked when leaving Cameras
                self._undock_osk_from_camera_page()
        elif index == 2:  # Companion page
            # Always show OSK docked at the bottom of Companion page.
            self._dock_osk_to_companion()
            # Target the web view by default
            try:
                self._show_osk_for_companion(getattr(self.companion_page, "web_view", None))
            except Exception:
                pass
        else:
            # Hide OSK when leaving Companion page if it was targeting the web view.
            if self.osk and index != 2:
                try:
                    target = getattr(self.osk, "_target_widget", None)
                    web_view = getattr(self.companion_page, "web_view", None)
                    if target is not None and (target == web_view):
                        self.osk.hide_keyboard()
                except Exception:
                    pass
            # If we are leaving the Companion page, undock the OSK.
            if index != 2:
                self._undock_osk_from_companion()
            # If we are leaving the Cameras page, undock the OSK.
            if index != 1:
                self._undock_osk_from_camera_page()
    
    @pyqtSlot(int)
    def _on_nav_clicked(self, page_idx: int):
        """Handle navigation button click"""
        self.page_stack.setCurrentIndex(page_idx)
    
    @pyqtSlot(str)
    def _on_companion_update_available(self, version: str):
        """Handle companion update available signal.

        Update UI is shown in Settings → Companion (not in top nav).
        """
        try:
            if hasattr(self, "settings_page") and self.settings_page:
                self.settings_page._companion_update_version = version
                # Refresh if the panel is visible
                if getattr(self.settings_page, "_current_section", None) == 3:
                    self.settings_page._refresh_companion_status_ui()
        except Exception:
            pass
    
    @pyqtSlot()
    def _on_companion_update_cleared(self):
        """Handle companion update completed/cleared"""
        try:
            if hasattr(self, "settings_page") and self.settings_page:
                self.settings_page._companion_update_version = None
                if getattr(self.settings_page, "_current_section", None) == 3:
                    self.settings_page._refresh_companion_status_ui()
        except Exception:
            pass
    
    def _on_companion_update_clicked(self):
        """Deprecated: update now initiated from Settings → Companion."""
        try:
            self.companion_page.update_companion()
        except Exception:
            pass
    
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
        """Toggle an overlay with visual feedback"""
        overlay_names = {
            "false_color": "False Color",
            "waveform": "Waveform",
            "vectorscope": "Vectorscope",
            "focus_assist": "Focus Assist"
        }
        
        try:
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
            
            # Show visual feedback
            name = overlay_names.get(overlay_key, overlay_key)
            status = "ON" if enabled else "OFF"
            self.toast.show_message(f"{name} {status}", duration=1500)
            logger.debug(f"Toggled {overlay_key}: {enabled}")
        except Exception as e:
            logger.error(f"Error toggling overlay {overlay_key}: {e}")
            self.toast.show_message(f"Error toggling overlay", duration=2000, error=True)
        
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
        """Handle composite frame from multiview manager (error-handled)"""
        try:
            if self._multiview_active and frame is not None:
                if hasattr(self, 'preview_widget') and self.preview_widget is not None:
                    self.preview_widget.update_frame(frame)
        except Exception as e:
            logger.warning(f"Error in multiview frame callback: {e}")
    
    def _select_camera(self, camera_id: int):
        """Select a camera to preview with visual feedback"""
        # Store previous camera ID BEFORE changing current_camera_id
        prev_camera_id = self.current_camera_id
        
        camera = self.settings.get_camera(camera_id)
        
        if not camera:
            # Only clear if no valid camera
            if prev_camera_id is not None and prev_camera_id in self.camera_streams:
                try:
                    self.camera_streams[prev_camera_id].remove_frame_callback(self._on_frame_received)
                    self.camera_streams[prev_camera_id].stop()
                except Exception as e:
                    logger.warning(f"Error stopping previous camera: {e}")
            self.current_camera_id = None
            if hasattr(self, 'preview_widget') and self.preview_widget is not None:
                self.preview_widget.clear_frame()
            logger.warning(f"Camera {camera_id} not found")
            if hasattr(self, 'toast'):
                self.toast.show_message("Camera not found", duration=2000, error=True)
            return
        
        try:
            logger.info(f"Selecting camera: {camera.name} ({camera.ip_address})")
            
            # Stop demo mode if running (must be done before starting camera)
            if self._demo_running:
                self._stop_demo_video()
                if hasattr(self, 'demo_btn'):
                    self.demo_btn.setChecked(False)
            
            # Stop multiview if running
            if self._multiview_active:
                self._stop_multiview()
            
            # Remove callback from previous stream immediately to prevent flashing
            # This stops old camera frames from updating the preview
            if prev_camera_id is not None and prev_camera_id != camera_id and prev_camera_id in self.camera_streams:
                prev_stream = self.camera_streams[prev_camera_id]
                prev_stream.remove_frame_callback(self._on_frame_received)
            
            # Update current camera ID
            self.current_camera_id = camera_id
            
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
                self.camera_streams[camera_id] = stream
            
            # Get stream for this camera
            stream = self.camera_streams[camera_id]
            
            # Remove callback first to prevent duplicates, then add it
            try:
                stream.remove_frame_callback(self._on_frame_received)
                stream.add_frame_callback(self._on_frame_received)
            except Exception as e:
                logger.warning(f"Error managing callbacks: {e}")
            
            # Start new stream
            # The start() method checks if already running and returns early if so
            # Ensure consistent streaming method - use RTSP with MJPEG fallback (not snapshot)
            try:
                stream.start(use_rtsp=True, use_snapshot=False, force_mjpeg=False)
            except Exception as e:
                logger.error(f"Error starting stream: {e}", exc_info=True)
                self.toast.show_message(f"Error starting {camera.name}", duration=2000, error=True)
                return
            
            # Stop previous stream after a delay (allows new stream to start)
            # This prevents resource waste but doesn't affect preview (callback already removed)
            if prev_camera_id is not None and prev_camera_id != camera_id and prev_camera_id in self.camera_streams:
                # Stop previous stream after 1000ms (gives new stream time to connect)
                QTimer.singleShot(1000, lambda: self._stop_previous_stream(prev_camera_id))
            
            # Update UI immediately
            try:
                self._update_camera_selection_ui(camera_id)
            except Exception as e:
                logger.warning(f"Error updating camera selection UI: {e}")
            
            # Update tally state for preview
            try:
                self._update_preview_tally()
            except Exception as e:
                logger.warning(f"Error updating preview tally: {e}")

            # Sync camera control panels with current camera settings
            try:
                self._sync_camera_controls_with_current_camera()
            except Exception as e:
                logger.warning(f"Error syncing camera controls: {e}")

            # Show visual feedback
            try:
                if hasattr(self, 'toast'):
                    self.toast.show_message(f"Switched to {camera.name}", duration=1500)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error selecting camera {camera_id}: {e}")
            camera_name = camera.name if camera else f"Camera {camera_id}"
            self.toast.show_message(f"Error connecting to {camera_name}", duration=2000, error=True)
    
    def _stop_previous_stream(self, camera_id: int):
        """Stop a previous camera stream (called with delay to prevent flash)"""
        try:
            if camera_id != self.current_camera_id and camera_id in self.camera_streams:
                stream = self.camera_streams[camera_id]
                # Remove callback before stopping
                stream.remove_frame_callback(self._on_frame_received)
                stream.stop()
        except Exception as e:
            logger.warning(f"Error stopping previous stream {camera_id}: {e}")
    
    def _on_frame_received(self, frame):
        """Handle received frame from camera (error-handled)"""
        try:
            if frame is None:
                return
            
            # Safety check - ensure preview widget exists
            if not hasattr(self, 'preview_widget') or self.preview_widget is None:
                return
            
            import cv2
            import numpy as np
            
            # Handle split view if enabled
            if self._split_enabled and self._split_camera_id is not None:
                try:
                    split_frame = self._get_split_frame(frame)
                    if split_frame is not None:
                        frame = split_frame
                except Exception as e:
                    logger.warning(f"Error in split view: {e}")
                    # Continue with main frame if split fails
            
            # Update preview widget (has its own error handling)
            if hasattr(self, 'preview_widget') and self.preview_widget is not None:
                self.preview_widget.update_frame(frame)
        except Exception as e:
            logger.error(f"Error in frame received callback: {e}", exc_info=True)
            # Don't crash - just skip this frame
    
    def _get_split_frame(self, main_frame):
        """Combine main frame with split camera frame (error-handled)"""
        try:
            import cv2
            import numpy as np
            
            if main_frame is None:
                return None
            
            # Get frame from second camera
            if self._split_camera_id not in self.camera_streams:
                return None
            
            split_stream = self.camera_streams[self._split_camera_id]
            if not hasattr(split_stream, 'current_frame'):
                return None
            
            split_frame = split_stream.current_frame
            
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
        except Exception as e:
            logger.error(f"Error in split frame generation: {e}", exc_info=True)
            return None
    
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
    
    def _update_bottom_menu_camera_label(self, text: str):
        """Update the bottom menu camera label with intelligent auto-sizing"""
        if not hasattr(self, 'bottom_menu_camera_label'):
            return

        self.bottom_menu_camera_label.setText(text)

        # Calculate text length without emoji
        text_length = len(text.replace("📹", "").strip())

        # For short names (<=3 chars), always use 28px - never scale down
        if text_length <= 3:  # C1, C2, Cam, etc.
            font = self.bottom_menu_camera_label.font()
            font.setWeight(QFont.Weight.Bold)
            font.setPointSize(28)
            self.bottom_menu_camera_label.setFont(font)
        else:
            # For longer names, auto-scale to fit
            if text_length <= 6:  # Camera1, Studio, etc.
                font_sizes = [24, 20, 18, 16, 14, 12]
            elif text_length <= 10:  # Production, Main Stage, etc.
                font_sizes = [20, 18, 16, 14, 12, 10]
            else:  # Very long names
                font_sizes = [18, 16, 14, 12, 10, 8]

            # Try font sizes from largest to smallest until it fits
            font = self.bottom_menu_camera_label.font()
            font.setWeight(QFont.Weight.Bold)

            for font_size in font_sizes:
                font.setPointSize(font_size)
                self.bottom_menu_camera_label.setFont(font)

                # Force layout update to get accurate size
                self.bottom_menu_camera_label.adjustSize()

                # Check if it fits within our 80px width
                if self.bottom_menu_camera_label.sizeHint().width() <= 80:
                    break  # Found a size that fits

        # Ensure center alignment for multiple lines, vertical centering for single line
        self.bottom_menu_camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    def _update_camera_selection_ui(self, camera_id: int):
        """Update UI to reflect selected camera"""
        # Update bottom menu camera label (Canon-style blue accent)
        camera = self.settings.get_camera(camera_id)
        if camera and hasattr(self, 'bottom_menu_camera_label'):
            self._update_bottom_menu_camera_label(f"📹 {camera.name}")
        elif hasattr(self, 'bottom_menu_camera_label'):
            self._update_bottom_menu_camera_label("📹 No Camera")

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
        """Update preview tally based on ATEM state (error-handled)"""
        try:
            if not hasattr(self, 'preview_widget') or self.preview_widget is None:
                return
            
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
        except Exception as e:
            logger.warning(f"Error updating preview tally: {e}")
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
        
        # Camera connection status (only if widget exists)
        if hasattr(self, 'connection_status') and self.connection_status is not None:
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
        
        # ATEM connection status (only if widget exists)
        if hasattr(self, 'atem_status') and self.atem_status is not None:
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
        """Update FPS display (error-handled)"""
        try:
            if not hasattr(self, 'fps_label') or self.fps_label is None:
                return
            
            if self._multiview_active:
                # Show multiview FPS
                if hasattr(self, 'multiview_manager'):
                    self.fps_label.setText(f"{self.multiview_manager.fps:.1f} fps")
                else:
                    self.fps_label.setText("-- fps")
            elif self.current_camera_id is not None and self.current_camera_id in self.camera_streams:
                stream = self.camera_streams[self.current_camera_id]
                self.fps_label.setText(f"{stream.fps:.1f} fps")
            else:
                self.fps_label.setText("-- fps")
        except Exception as e:
            # Don't crash on FPS update errors
            pass
    
    def _show_system_popup(self):
        """Show system popup with Reboot, Shutdown, and Close options"""
        # Create custom frameless dialog
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dialog.setModal(True)
        
        # Style the dialog
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        
        # Main vertical layout to center content
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addStretch()
        
        # Grid layout for proper alignment
        grid_layout = QGridLayout()
        # Consistent 5px spacing between buttons (horizontal and vertical)
        grid_layout.setSpacing(5)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setColumnStretch(3, 1)
        
        # Row 0 - actions without save
        reboot_btn = QPushButton("Reboot")
        reboot_btn.setStyleSheet(self._get_popup_button_style())
        reboot_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "reboot"))
        
        shutdown_btn = QPushButton("Shutdown")
        shutdown_btn.setStyleSheet(self._get_popup_button_style())
        shutdown_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "shutdown"))
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(self._get_popup_button_style())
        close_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "close"))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        grid_layout.addWidget(reboot_btn, 0, 0)
        grid_layout.addWidget(shutdown_btn, 0, 1)
        grid_layout.addWidget(close_btn, 0, 2)
        grid_layout.addWidget(cancel_btn, 0, 3, 2, 1)  # Span 2 rows, 1 column
        
        # Row 1 - actions with save (aligned underneath, multiline text)
        save_reboot_btn = QPushButton("Save &&\nReboot")
        save_reboot_btn.setStyleSheet(self._get_popup_button_style(multiline=True))
        save_reboot_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "save_reboot"))
        
        save_shutdown_btn = QPushButton("Save &&\nShutdown")
        save_shutdown_btn.setStyleSheet(self._get_popup_button_style(multiline=True))
        save_shutdown_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "save_shutdown"))
        
        save_close_btn = QPushButton("Save &&\nClose")
        save_close_btn.setStyleSheet(self._get_popup_button_style(multiline=True))
        save_close_btn.clicked.connect(lambda: self._handle_popup_action(dialog, "save_close"))
        
        grid_layout.addWidget(save_reboot_btn, 1, 0)
        grid_layout.addWidget(save_shutdown_btn, 1, 1)
        grid_layout.addWidget(save_close_btn, 1, 2)
        
        # Cancel button height: row 1 button height (44px) + spacing (5px) + row 2 button height (44px) = 93px
        cancel_btn.setStyleSheet(self._get_popup_button_style(tall=True, height=93))
        
        # Add grid to main layout
        main_layout.addLayout(grid_layout)
        main_layout.addStretch()
        
        # Size and position - adjust for two rows with spacing
        dialog.setFixedSize(650, 200)
        dialog.move(
            self.geometry().center().x() - dialog.width() // 2,
            self.geometry().center().y() - dialog.height() // 2
        )
        
        dialog.exec()
    
    def _get_popup_button_style(self, tall=False, height=None, multiline=False):
        """Get button style for popup with floating effect"""
        if tall and height:
            height_style = f"min-height: {height}px; max-height: {height}px;"
        elif tall:
            height_style = "min-height: 100px;"
        else:
            height_style = "min-height: 44px;"
        
        # Multiline buttons need different padding and alignment
        if multiline:
            padding_style = "padding: 8px 12px;"
            text_align = "text-align: center;"
        else:
            padding_style = "padding: 12px;"
            text_align = ""
            
        return f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
                {padding_style}
                {height_style}
                margin: 0px;
                {text_align}
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
                border-color: {COLORS['primary']};
                margin: 0px;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                color: {COLORS['background']};
                margin: 0px;
            }}
        """
    
    def _handle_popup_action(self, dialog, action):
        """Handle popup button action"""
        dialog.accept()
        if action == "reboot":
            self._reboot_without_save()
        elif action == "shutdown":
            self._shutdown_without_save()
        elif action == "close":
            self._close_without_save()
        elif action == "save_reboot":
            self._save_and_reboot()
        elif action == "save_shutdown":
            self._save_and_shutdown()
        elif action == "save_close":
            self._save_and_close()
    
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
    
    def _reboot_without_save(self):
        """Reboot system without saving"""
        import subprocess
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        try:
            subprocess.run(['sudo', 'reboot'], check=True)
        except Exception as e:
            print(f"Reboot failed: {e}")
    
    def _shutdown_without_save(self):
        """Shutdown system without saving"""
        import subprocess
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        try:
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except Exception as e:
            print(f"Shutdown failed: {e}")
    
    def _close_without_save(self):
        """Close application without saving"""
        self._skip_close_dialog = True
        self.close()
    
    def _save_and_reboot(self):
        """Save settings and reboot system"""
        import subprocess
        self.settings.save()
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        try:
            subprocess.run(['sudo', 'reboot'], check=True)
        except Exception as e:
            print(f"Reboot failed: {e}")
    
    def _save_and_shutdown(self):
        """Save settings and shutdown system"""
        import subprocess
        self.settings.save()
        # Perform cleanup without triggering closeEvent save dialog
        self._skip_close_dialog = True
        self.close()
        try:
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except Exception as e:
            print(f"Shutdown failed: {e}")
    
    def _save_and_close(self):
        """Save settings and close application"""
        self.settings.save()
        self._skip_close_dialog = True
        self.close()
    
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
        
        # Ctrl+M - Toggle margin debug overlay
        elif event.key() == Qt.Key.Key_M and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._show_margin_debug_overlay()
        
        # M - Toggle multiview
        elif event.key() == Qt.Key.Key_M:
            self.multiview_btn.setChecked(not self.multiview_btn.isChecked())
            self._toggle_multiview()
        
        else:
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Event filter to maintain 16:9 aspect ratio for portrait preview container"""
        if hasattr(self, 'preview_container_portrait') and obj == self.preview_container_portrait:
            if event.type() == QEvent.Type.Resize:
                # Calculate height for 16:9 aspect ratio
                width = event.size().width()
                if width > 0:
                    height_16_9 = int(width * 9 / 16)
                    # Set both min and max height to maintain aspect ratio
                    obj.setMinimumHeight(height_16_9)
                    obj.setMaximumHeight(height_16_9)
        return super().eventFilter(obj, event)
    
    # --------------------------
    # System OSK Support (Pi OS on-screen keyboard)
    # --------------------------
    # The system OSK (squeekboard) automatically appears when text fields get focus
    # on Wayland. No custom implementation needed - Qt handles it via input method framework.
    # No eventFilter needed - Qt's input method framework handles it automatically.
    def _find_keyboard_command_OLD(self):
        """Locate an available on-screen keyboard command."""
        keyboard_commands = [
            'squeekboard',        # Preferred on Wayland Pi images
            'matchbox-keyboard',  # Common on Raspberry Pi OS
            'onboard',            # Alternative keyboard
            'florence',           # Another alternative
        ]
        
        if shutil.which('busctl') and self._squeekboard_available():
            return 'squeekboard'
        
        for cmd in keyboard_commands[1:]:
            if shutil.which(cmd):
                return cmd
        
        if shutil.which('busctl'):
            return 'squeekboard'
        
        return None
    
    def _squeekboard_available_OLD(self) -> bool:
        """Check if squeekboard is present on D-Bus."""
        try:
            result = subprocess.run(
                ['busctl', '--user', '--no-pager', '--no-legend', 'list'],
                capture_output=True, text=True, timeout=0.5
            )
            return result.returncode == 0 and 'sm.puri.OSK0' in result.stdout
        except Exception:
            return False
    
    def _show_keyboard_OLD(self):
        """Show Pi OS on-screen keyboard - simplified and robust."""
        if not self._keyboard_command:
            logger.warning("Keyboard: No keyboard command available")
            return
        
        logger.info(f"Keyboard: Attempting to show {self._keyboard_command}")
        
        try:
            if self._keyboard_command == 'squeekboard':
                # Try to lower our window slightly to allow keyboard to appear on top
                # This is a workaround for Wayland compositor window stacking
                try:
                    # Temporarily lower window z-order (if possible)
                    self.lower()
                    QTimer.singleShot(100, lambda: self.raise_())
                except Exception:
                    pass
                
                # Call SetVisible via D-Bus
                result = subprocess.run(
                    ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'true'],
                    timeout=1, capture_output=True, text=True
                )
                if result.returncode == 0:
                    logger.info("Keyboard: ✅ SetVisible succeeded")
                    # Verify it's actually visible and try to raise keyboard window
                    QTimer.singleShot(200, self._verify_and_raise_keyboard)
                else:
                    logger.warning(f"Keyboard: SetVisible failed: {result.stderr}")
                    # Fallback: try system session
                    result2 = subprocess.run(
                        ['busctl', 'call', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'true'],
                        timeout=1, capture_output=True, text=True
                    )
                    if result2.returncode == 0:
                        logger.info("Keyboard: ✅ SetVisible (system) succeeded")
                        QTimer.singleShot(200, self._verify_and_raise_keyboard)
            else:
                # For other keyboards, just launch them
                try:
                    subprocess.run(['pkill', '-f', self._keyboard_command], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
                except Exception:
                    pass
                try:
                    self._keyboard_process = subprocess.Popen(
                        [self._keyboard_command],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    logger.info(f"Keyboard: ✅ {self._keyboard_command} launched")
                except Exception as e:
                    logger.error(f"Keyboard: ❌ Failed to launch {self._keyboard_command}: {e}")
        except Exception as e:
            logger.error(f"Keyboard: Error in _show_keyboard: {e}", exc_info=True)
    
    def _verify_and_raise_keyboard(self):
        """Verify keyboard is visible and try to raise it above our window"""
        try:
            result = subprocess.run(
                ['busctl', '--user', 'get-property', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'Visible'],
                timeout=1, capture_output=True, text=True
            )
            if result.returncode == 0:
                visible = 'true' in result.stdout.lower()
                logger.info(f"Keyboard: Visible property = {visible}")
                if visible:
                    # Keyboard reports visible - try to ensure it's on top
                    # On Wayland, we can't directly control z-order, but we can:
                    # 1. Lower our window temporarily
                    # 2. Call SetVisible again to trigger compositor to show keyboard
                    try:
                        self.lower()
                        QTimer.singleShot(50, lambda: self.raise_())
                        # Also call SetVisible again to ensure compositor shows it
                        subprocess.run(
                            ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'true'],
                            timeout=0.5, capture_output=True, text=True
                        )
                        logger.info("Keyboard: Attempted to raise keyboard above app window")
                    except Exception as e:
                        logger.warning(f"Keyboard: Could not adjust window z-order: {e}")
                else:
                    # Not visible - retry
                    logger.info("Keyboard: Not visible, retrying SetVisible...")
                    subprocess.run(
                        ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'true'],
                        timeout=1, capture_output=True, text=True
                    )
        except Exception as e:
            logger.warning(f"Keyboard: Could not verify visibility: {e}")
    
    def closeEvent(self, event):
        """Clean up on close"""
        super().closeEvent(event)
    
    
    def _hide_keyboard_OLD(self):
        """Hide Pi OS on-screen keyboard - simplified."""
        try:
            if self._keyboard_command == 'squeekboard':
                # Just hide via D-Bus - don't kill the process
                subprocess.run(
                    ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'false'],
                    timeout=1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            elif self._keyboard_process:
                # For other keyboards, terminate the process
                try:
                    self._keyboard_process.terminate()
                    self._keyboard_process.wait(timeout=0.5)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    try:
                        self._keyboard_process.kill()
                        self._keyboard_process.wait()
                    except Exception:
                        pass
                finally:
                    self._keyboard_process = None
        except Exception as e:
            logger.warning(f"Keyboard: Error hiding: {e}")

