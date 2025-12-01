"""
Camera Page

Configuration for Panasonic PTZ cameras.
"""
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QGroupBox, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QFrame, QApplication, QProgressBar,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

from ..config.settings import Settings, CameraConfig
from ..camera.discovery import CameraDiscovery, DiscoveredCamera
from ..camera.stream import CameraStream, StreamConfig


class DiscoveryWorker(QThread):
    """Worker thread for Panasonic camera discovery"""
    camera_found = pyqtSignal(object)  # DiscoveredCamera
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int)  # 0-100
    finished_signal = pyqtSignal(int)  # Total count
    
    def __init__(self, adapter_ip: str = None):
        super().__init__()
        self.discovery = CameraDiscovery()
        self._adapter_ip = adapter_ip
    
    def run(self):
        """Run Panasonic UDP discovery in background thread"""
        # Set network adapter if specified
        if self._adapter_ip:
            self.discovery.set_network_adapter(self._adapter_ip)
        
        self.discovery.set_progress_callback(self._on_progress)
        self.progress_value.emit(10)
        cameras = self.discovery.discover()
        self.progress_value.emit(100)
        
        # Emit cameras as they're found (for real-time updates)
        for cam in cameras:
            self.camera_found.emit(cam)
        
        self.finished_signal.emit(len(cameras))
    
    def _on_progress(self, message: str):
        """Handle progress updates"""
        self.progress.emit(message)


class DiscoveredCameraCard(QFrame):
    """Enhanced card widget for discovered cameras with status, identify, and preview"""
    
    add_clicked = pyqtSignal(object)  # DiscoveredCamera
    identify_clicked = pyqtSignal(str)  # IP address
    
    def __init__(self, camera: DiscoveredCamera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self._thumbnail_label = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #FF9500;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left side: Thumbnail preview
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setFixedSize(80, 45)
        self._thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #0a0a0f;
                border: 1px solid #2a2a38;
                border-radius: 4px;
            }
        """)
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_label.setText("📷")
        layout.addWidget(self._thumbnail_label)
        
        # Center: Camera info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Name/model row with status
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        name_label = QLabel(self.camera.name or self.camera.model or "Unknown Camera")
        name_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #ffffff;")
        name_label.setWordWrap(False)
        name_label.setMaximumWidth(140)
        header_layout.addWidget(name_label)
        
        # Status indicator with color based on status
        status = getattr(self.camera, 'status', 'Unknown')
        status_colors = {
            "Power ON": "#22c55e",      # Green
            "Standby": "#eab308",       # Yellow
            "Auth Required": "#f97316", # Orange
            "Offline": "#ef4444",       # Red
            "Unknown": "#6b7280",       # Gray
        }
        status_color = status_colors.get(status, "#6b7280")
        status_label = QLabel(f"● {status}")
        status_label.setStyleSheet(f"font-size: 9px; color: {status_color}; font-weight: 500;")
        header_layout.addWidget(status_label)
        header_layout.addStretch()
        
        info_layout.addLayout(header_layout)
        
        # IP address
        ip_label = QLabel(f"{self.camera.ip_address}")
        ip_label.setStyleSheet("font-size: 11px; color: #888898;")
        ip_label.setWordWrap(False)
        info_layout.addWidget(ip_label)
        
        # Model and MAC on same row
        details = []
        if self.camera.model and self.camera.model != (self.camera.name or ""):
            details.append(self.camera.model)
        if self.camera.mac_address:
            details.append(self.camera.mac_address[:8] + "...")
        if details:
            details_label = QLabel(" | ".join(details))
            details_label.setStyleSheet("font-size: 9px; color: #666676;")
            details_label.setWordWrap(False)
            info_layout.addWidget(details_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        # Right side: Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # Identify button (blink LED)
        identify_btn = QPushButton("💡")
        identify_btn.setFixedSize(32, 28)
        identify_btn.setToolTip("Identify camera (blink LED)")
        identify_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a48;
            }
            QPushButton:pressed {
                background-color: #4a4a58;
            }
        """)
        identify_btn.clicked.connect(lambda: self.identify_clicked.emit(self.camera.ip_address))
        btn_layout.addWidget(identify_btn)
        
        # Add button
        add_btn = QPushButton("➕")
        add_btn.setFixedSize(32, 28)
        add_btn.setToolTip("Add to form")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 6px;
                color: #0a0a0f;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #CC7700;
            }
            QPushButton:pressed {
                background-color: #AA6600;
            }
        """)
        add_btn.clicked.connect(lambda: self.add_clicked.emit(self.camera))
        btn_layout.addWidget(add_btn)
        
        layout.addLayout(btn_layout)
    
    def set_thumbnail(self, pixmap: 'QPixmap'):
        """Set the thumbnail image"""
        if self._thumbnail_label and pixmap:
            scaled = pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
            self._thumbnail_label.setPixmap(scaled)
            self._thumbnail_label.setText("")


class CameraListItem(QFrame):
    """Enhanced camera list item with status indicators and actions"""
    
    edit_clicked = pyqtSignal(int)
    selection_changed = pyqtSignal(int, bool)  # camera_id, selected
    
    def __init__(self, camera: CameraConfig, atem_input: int, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.atem_input = atem_input
        self.connection_status = "unknown"  # "online", "offline", "unknown", "testing"
        self.last_test_result = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)  # Add right margin to avoid scroll bar overlapping edit button
        layout.setSpacing(16)  # Increased spacing between elements
        
        # Checkbox for bulk selection
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(24, 24)
        self.checkbox.setStyleSheet("""
            QCheckBox {
                background-color: transparent;
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
                border: 2px solid #FFFFFF;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #FF9500;
                border-color: #FF9500;
            }
        """)
        self.checkbox.stateChanged.connect(
            lambda state: self.selection_changed.emit(self.camera.id, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.checkbox)
        
        # Status indicator (colored dot)
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #888898;
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.status_indicator)
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)  # 16:9 aspect ratio
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 6px;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._create_demo_thumbnail()
        layout.addWidget(self.thumbnail_label)
        
        # Camera info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_row = QHBoxLayout()
        name_label = QLabel(f"<b>{self.camera.name}</b>")
        name_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        name_row.addWidget(name_label)
        
        # ATEM input badge
        if self.atem_input > 0:
            atem_badge = QLabel(f"ATEM {self.atem_input}")
            atem_badge.setStyleSheet("""
                QLabel {
                    background-color: #FF9500;
                    color: #0a0a0f;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                    border-radius: 10px;
                }
            """)
            name_row.addWidget(atem_badge)
        
        name_row.addStretch()
        info_layout.addLayout(name_row)
        
        # IP address only
        ip_label = QLabel(self.camera.ip_address)
        ip_label.setStyleSheet("color: #888898; font-size: 13px;")
        info_layout.addWidget(ip_label)
        
        # Connection status text
        self.status_label = QLabel("Status: Unknown")
        self.status_label.setStyleSheet("color: #888898; font-size: 11px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Edit button - centered vertically
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(80, 40)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 6px;
                color: #0a0a0f;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.camera.id))
        layout.addWidget(edit_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        self.setStyleSheet("""
            CameraListItem {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 10px;
                padding: 0px;
            }
        """)
    
    def _create_demo_thumbnail(self):
        """Create a demo thumbnail image"""
        self._update_thumbnail_image()
    
    def _update_thumbnail_image(self, frame=None):
        """Update thumbnail with camera frame or 'No Connection' message"""
        pixmap = QPixmap(120, 68)
        pixmap.fill(QColor("#1a1a24"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw gradient background
        gradient = QLinearGradient(0, 0, 120, 68)
        gradient.setColorAt(0, QColor("#2a2a38"))
        gradient.setColorAt(1, QColor("#1a1a24"))
        painter.fillRect(0, 0, 120, 68, gradient)
        
        if frame is not None and self.connection_status == "online":
            # Convert numpy frame to QPixmap
            from PyQt6.QtGui import QImage
            import cv2
            import numpy as np
            
            # Resize frame to thumbnail size
            h, w = frame.shape[:2]
            scale = min(120 / w, 68 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Create QImage
            bytes_per_line = 3 * new_w
            q_img = QImage(rgb_frame.data, new_w, new_h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Draw centered
            x_offset = (120 - new_w) // 2
            y_offset = (68 - new_h) // 2
            painter.drawImage(x_offset, y_offset, q_img)
        else:
            # Draw "No Connection" message
            painter.setPen(QColor("#888898"))
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(0, 0, 120, 68, Qt.AlignmentFlag.AlignCenter, "No\nConnection")
        
        painter.end()
        self.thumbnail_label.setPixmap(pixmap)
    
    def update_thumbnail_frame(self, frame):
        """Update thumbnail with camera frame"""
        if frame is not None:
            self._update_thumbnail_image(frame)
    
    def update_status(self, status: str, message: str = ""):
        """Update connection status indicator"""
        self.connection_status = status
        # Update thumbnail when status changes
        if status != "online":
            self._update_thumbnail_image()
        if status == "online":
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #22c55e;
                    background-color: transparent;
                    border: none;
                }
            """)
            self.status_label.setText(f"Status: Online" + (f" - {message}" if message else ""))
            self.status_label.setStyleSheet("color: #22c55e; font-size: 11px;")
        elif status == "offline":
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #ef4444;
                    background-color: transparent;
                    border: none;
                }
            """)
            self.status_label.setText(f"Status: Offline" + (f" - {message}" if message else ""))
            self.status_label.setStyleSheet("color: #ef4444; font-size: 11px;")
        elif status == "testing":
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #FF9500;
                    background-color: transparent;
                    border: none;
                }
            """)
            self.status_label.setText("Status: Testing...")
            self.status_label.setStyleSheet("color: #FF9500; font-size: 11px;")
        else:  # unknown
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #888898;
                    background-color: transparent;
                    border: none;
                }
            """)
            self.status_label.setText("Status: Unknown")
            self.status_label.setStyleSheet("color: #888898; font-size: 11px;")


class CameraPage(QWidget):
    """
    Enhanced camera configuration page with improved UX and features.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._editing_camera_id = None
        self._discovery_worker = None
        self._discovered_cameras = []
        self._discovered_cards = {}  # ip -> DiscoveredCameraCard
        self._camera_items = {}  # camera_id -> CameraListItem
        self._selected_cameras = set()  # Set of selected camera IDs
        self._thumbnail_streams = {}  # camera_id -> CameraStream
        self._thumbnail_timer = QTimer()
        self._thumbnail_timer.timeout.connect(self._update_all_thumbnails)
        self._test_worker = None
        self._form_has_changes = False
        
        self._setup_ui()
        self._load_settings()
        
        # Start thumbnail update timer (update every 2 minutes)
        self._thumbnail_timer.start(120000)
    
    def _setup_ui(self):
        """Setup the camera page UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left panel - Discovery + Manual add
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, stretch=1)
        
        # Right panel - Camera list
        right_panel = self._create_camera_list_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addLayout(content_layout)
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with unified discovery and manual add"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Unified Add Camera section
        self.add_camera_group = QGroupBox("➕ Add Camera")
        self.add_camera_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #2a2a38;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        add_camera_layout = QVBoxLayout(self.add_camera_group)
        add_camera_layout.setSpacing(12)
        
        # Top buttons row: Scan Network and Add Manually toggle
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.setSpacing(8)
        
        # Scan Network button
        self.discover_btn = QPushButton("🔍  Scan Network")
        self.discover_btn.setFixedHeight(50)
        self.discover_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 8px;
                color: #0a0a0f;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:disabled {
                background-color: #2a2a38;
                color: #888898;
            }
        """)
        self.discover_btn.clicked.connect(self._discover_cameras)
        top_buttons_layout.addWidget(self.discover_btn)
        
        # Add Manually toggle button
        self.manual_toggle_btn = QPushButton("➕ Add Manually")
        self.manual_toggle_btn.setFixedHeight(50)
        self.manual_toggle_btn.setCheckable(True)
        self.manual_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 1px solid #3a3a48;
                border-radius: 8px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:checked {
                background-color: #FF9500;
                color: #0a0a0f;
            }
            QPushButton:hover {
                background-color: #3a3a48;
            }
            QPushButton:checked:hover {
                background-color: #CC7700;
            }
        """)
        self.manual_toggle_btn.toggled.connect(self._toggle_manual_form)
        top_buttons_layout.addWidget(self.manual_toggle_btn)
        
        add_camera_layout.addLayout(top_buttons_layout)
        
        # Progress bar with animation
        self.discovery_progress = QProgressBar()
        self.discovery_progress.setRange(0, 100)
        self.discovery_progress.setValue(0)
        self.discovery_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2a2a38;
                border-radius: 4px;
                text-align: center;
                background-color: #1a1a24;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #FF9500;
                border-radius: 3px;
            }
        """)
        self.discovery_progress.hide()
        add_camera_layout.addWidget(self.discovery_progress)
        
        # Status label with animation
        self.discovery_status = QLabel("Ready to scan or add manually")
        self.discovery_status.setStyleSheet("color: #888898; font-size: 12px; padding: 4px;")
        add_camera_layout.addWidget(self.discovery_status)
        
        # Discovered cameras scroll area
        discovered_scroll = QScrollArea()
        discovered_scroll.setWidgetResizable(True)
        discovered_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        discovered_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        discovered_scroll.setFixedHeight(180)
        discovered_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #1a1a24;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a38;
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        
        # Container widget for discovered cards
        self.discovered_container = QWidget()
        self.discovered_layout = QVBoxLayout(self.discovered_container)
        self.discovered_layout.setSpacing(8)
        self.discovered_layout.setContentsMargins(8, 8, 8, 8)
        self.discovered_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state for discovery (inside scroll area)
        self.discovery_empty_label = QLabel("No cameras discovered yet.\nClick 'Scan Network' to search for Panasonic cameras.")
        self.discovery_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.discovery_empty_label.setStyleSheet("color: #666676; font-size: 11px; padding: 20px;")
        self.discovery_empty_label.setWordWrap(True)
        self.discovered_layout.addWidget(self.discovery_empty_label)
        
        discovered_scroll.setWidget(self.discovered_container)
        add_camera_layout.addWidget(discovered_scroll)
        
        # Manual form container (initially hidden)
        self.manual_form_container = QWidget()
        self.manual_form_container.setStyleSheet("""
            QLineEdit, QComboBox {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #FFFFFF;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #FF9500;
            }
            QLineEdit::placeholder {
                color: #666676;
            }
            QComboBox::drop-down {
                border: none;
                width: 40px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                selection-background-color: #FF9500;
                color: #FFFFFF;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 44px;
                padding: 12px 16px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #FF9500;
                color: #0a0a0f;
            }
            QLabel {
                font-size: 11px;
                color: #FFFFFF;
                font-weight: 500;
                border: none;
                background: transparent;
            }
        """)
        manual_layout = QVBoxLayout(self.manual_form_container)
        manual_layout.setSpacing(12)
        manual_layout.setContentsMargins(0, 12, 0, 0)
        
        # Camera Name field
        name_container = QVBoxLayout()
        name_container.setSpacing(4)
        name_label = QLabel("Camera Name:")
        name_container.addWidget(name_label)
        
        name_input_row = QHBoxLayout()
        name_input_row.setSpacing(8)
        self.camera_name_input = QLineEdit()
        self.camera_name_input.setFixedHeight(40)
        self.camera_name_input.setPlaceholderText("e.g. Camera 1")
        self.camera_name_input.textChanged.connect(self._on_form_changed)
        self.camera_name_input.textChanged.connect(lambda: self._validate_field("name"))
        name_input_row.addWidget(self.camera_name_input)
        self.name_validator = QLabel("✓")
        self.name_validator.setFixedWidth(20)
        self.name_validator.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
        self.name_validator.hide()
        name_input_row.addWidget(self.name_validator)
        name_container.addLayout(name_input_row)
        manual_layout.addLayout(name_container)
        
        # IP Address field
        ip_container = QVBoxLayout()
        ip_container.setSpacing(4)
        ip_label = QLabel("IP Address:")
        ip_container.addWidget(ip_label)
        
        ip_input_row = QHBoxLayout()
        ip_input_row.setSpacing(8)
        self.camera_ip_input = QLineEdit()
        self.camera_ip_input.setFixedHeight(40)
        self.camera_ip_input.setPlaceholderText("e.g. 192.168.1.100")
        self.camera_ip_input.textChanged.connect(self._on_form_changed)
        self.camera_ip_input.textChanged.connect(lambda: self._validate_field("ip"))
        ip_input_row.addWidget(self.camera_ip_input)
        self.ip_validator = QLabel("✓")
        self.ip_validator.setFixedWidth(20)
        self.ip_validator.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
        self.ip_validator.hide()
        ip_input_row.addWidget(self.ip_validator)
        ip_container.addLayout(ip_input_row)
        manual_layout.addLayout(ip_container)
        
        # Username and Password in a row
        auth_row = QHBoxLayout()
        auth_row.setSpacing(12)
        
        # Username
        user_container = QVBoxLayout()
        user_container.setSpacing(4)
        user_label = QLabel("Username:")
        user_container.addWidget(user_label)
        self.camera_user_input = QLineEdit()
        self.camera_user_input.setFixedHeight(40)
        self.camera_user_input.setPlaceholderText("admin")
        self.camera_user_input.setText("admin")
        self.camera_user_input.textChanged.connect(self._on_form_changed)
        user_container.addWidget(self.camera_user_input)
        auth_row.addLayout(user_container)
        
        # Password
        pass_container = QVBoxLayout()
        pass_container.setSpacing(4)
        pass_label = QLabel("Password:")
        pass_container.addWidget(pass_label)
        self.camera_pass_input = QLineEdit()
        self.camera_pass_input.setFixedHeight(40)
        self.camera_pass_input.setPlaceholderText("12345")
        self.camera_pass_input.setText("12345")
        self.camera_pass_input.textChanged.connect(self._on_form_changed)
        pass_container.addWidget(self.camera_pass_input)
        auth_row.addLayout(pass_container)
        
        # Hidden password toggle for compatibility
        self.password_toggle = QPushButton()
        self.password_toggle.hide()
        
        manual_layout.addLayout(auth_row)
        
        # ATEM Input dropdown
        atem_container = QVBoxLayout()
        atem_container.setSpacing(4)
        atem_label = QLabel("ATEM Input:")
        atem_container.addWidget(atem_label)
        self.camera_atem_combo = QComboBox()
        self.camera_atem_combo.setFixedHeight(44)
        self._populate_atem_inputs()
        self.camera_atem_combo.currentIndexChanged.connect(self._on_form_changed)
        atem_container.addWidget(self.camera_atem_combo)
        manual_layout.addLayout(atem_container)
        
        # Add spacing below ATEM dropdown for dropdown list to expand
        manual_layout.addSpacing(60)
        
        # Form validation message
        self.form_error_label = QLabel("")
        self.form_error_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 4px 0;")
        self.form_error_label.hide()
        manual_layout.addWidget(self.form_error_label)
        
        # Connection test status
        self.test_status_label = QLabel("")
        self.test_status_label.setStyleSheet("font-size: 11px; padding: 4px 0;")
        self.test_status_label.hide()
        manual_layout.addWidget(self.test_status_label)
        
        # Add manual form container to main layout (initially hidden)
        self.manual_form_container.hide()
        add_camera_layout.addWidget(self.manual_form_container)
        
        # Buttons container (separate from form, always at bottom)
        self.manual_buttons_container = QWidget()
        btn_layout = QHBoxLayout(self.manual_buttons_container)
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 12, 0, 20)
        
        # Test button
        self.test_camera_btn = QPushButton("Test Connection")
        self.test_camera_btn.setFixedHeight(44)
        self.test_camera_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 2px solid #3a3a48;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                border-color: #FF9500;
                background-color: #3a3a48;
            }
            QPushButton:disabled {
                background-color: #1a1a24;
                border-color: #2a2a38;
                color: #666676;
            }
        """)
        self.test_camera_btn.clicked.connect(self._test_camera)
        btn_layout.addWidget(self.test_camera_btn)
        
        # Save button
        self.save_camera_btn = QPushButton("Save Camera")
        self.save_camera_btn.setFixedHeight(44)
        self.save_camera_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: 2px solid #FF9500;
                border-radius: 8px;
                color: #0a0a0f;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #CC7700;
                border-color: #CC7700;
            }
            QPushButton:disabled {
                background-color: #2a2a38;
                border-color: #2a2a38;
                color: #888898;
            }
        """)
        self.save_camera_btn.clicked.connect(self._save_camera)
        btn_layout.addWidget(self.save_camera_btn)
        
        # Cancel edit button
        self.cancel_edit_btn = QPushButton("Cancel")
        self.cancel_edit_btn.setFixedHeight(44)
        self.cancel_edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                border: 2px solid #ef4444;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #cc3333;
                border-color: #cc3333;
            }
        """)
        self.cancel_edit_btn.clicked.connect(self._cancel_edit)
        self.cancel_edit_btn.hide()
        btn_layout.addWidget(self.cancel_edit_btn)
        
        # Hidden buttons for compatibility
        self.clear_form_btn = QPushButton()
        self.clear_form_btn.hide()
        self.defaults_btn = QPushButton()
        self.defaults_btn.hide()
        
        # Add buttons container (initially hidden, shown with form)
        self.manual_buttons_container.hide()
        add_camera_layout.addWidget(self.manual_buttons_container)
        
        layout.addWidget(self.add_camera_group)
        layout.addStretch()
        
        return panel
    
    def _create_camera_list_panel(self) -> QWidget:
        """Create camera list panel with search and bulk operations"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header with count and progress
        header_layout = QHBoxLayout()
        
        self.camera_list_header = QLabel("Configured Cameras (0/30)")
        self.camera_list_header.setStyleSheet("font-size: 18px; font-weight: 600; border: none;")
        header_layout.addWidget(self.camera_list_header)
        
        header_layout.addStretch()
        
        # Progress bar for camera count
        self.camera_count_progress = QProgressBar()
        self.camera_count_progress.setRange(0, 30)
        self.camera_count_progress.setValue(0)
        self.camera_count_progress.setFixedWidth(120)
        self.camera_count_progress.setFormat("%v/30")
        self.camera_count_progress.setFixedHeight(24)
        self.camera_count_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2a2a38;
                border-radius: 4px;
                text-align: center;
                background-color: #1a1a24;
                height: 24px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #FF9500;
                border-radius: 3px;
            }
        """)
        header_layout.addWidget(self.camera_count_progress)
        
        # Sort dropdown with icon
        header_layout.addSpacing(12)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["⇅ Name", "⇅ IP Address", "⇅ ATEM Input", "⇅ Status"])
        self.sort_combo.setFixedHeight(24)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 4px;
                padding: 0px 8px;
                font-size: 12px;
                min-width: 140px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
        """)
        self.sort_combo.currentTextChanged.connect(self._refresh_camera_list)
        header_layout.addWidget(self.sort_combo)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Bulk operations bar - match camera row width
        bulk_container = QWidget()
        bulk_container.setContentsMargins(20, 0, 20, 0)  # Match camera row horizontal margins
        bulk_container.setStyleSheet("background-color: transparent;")
        bulk_layout = QHBoxLayout(bulk_container)
        bulk_layout.setContentsMargins(0, 4, 0, 4)  # Add vertical padding to prevent clipping
        bulk_layout.setSpacing(8)
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setFixedHeight(36)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 1px solid #3a3a48;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        self.select_all_btn.clicked.connect(self._select_all_cameras)
        bulk_layout.addWidget(self.select_all_btn, stretch=1)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setFixedHeight(36)
        self.deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 1px solid #3a3a48;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        self.deselect_all_btn.clicked.connect(self._deselect_all_cameras)
        bulk_layout.addWidget(self.deselect_all_btn, stretch=1)
        
        self.bulk_duplicate_btn = QPushButton("Duplicate Selected")
        self.bulk_duplicate_btn.setFixedHeight(36)
        self.bulk_duplicate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 1px solid #3a3a48;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        self.bulk_duplicate_btn.clicked.connect(self._bulk_duplicate_cameras)
        bulk_layout.addWidget(self.bulk_duplicate_btn, stretch=1)
        
        self.bulk_delete_btn = QPushButton("Delete Selected")
        self.bulk_delete_btn.setFixedHeight(36)
        self.bulk_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        self.bulk_delete_btn.clicked.connect(self._bulk_delete_cameras)
        bulk_layout.addWidget(self.bulk_delete_btn, stretch=1)
        
        layout.addWidget(bulk_container)
        
        # Add spacing between bulk operations and camera list
        layout.addSpacing(20)
        
        # Frame for camera list with scroll bar on outside
        camera_list_frame = QFrame()
        camera_list_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        camera_list_frame_layout = QVBoxLayout(camera_list_frame)
        camera_list_frame_layout.setContentsMargins(0, 0, 0, 0)
        camera_list_frame_layout.setSpacing(0)
        
        # Scroll area for camera list
        self.camera_scroll = QScrollArea()
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.camera_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.camera_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #1a1a24;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a38;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Camera list widget inside frame
        self.camera_list_widget = QWidget()
        self.camera_list_widget.setStyleSheet("background-color: transparent;")
        self.camera_list_layout = QVBoxLayout(self.camera_list_widget)
        self.camera_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.camera_list_layout.setSpacing(10)
        self.camera_list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.camera_scroll.setWidget(self.camera_list_widget)
        camera_list_frame_layout.addWidget(self.camera_scroll)
        
        layout.addWidget(camera_list_frame)
        
        # Empty state message
        self.empty_state_label = QLabel("No cameras configured.\nAdd cameras using discovery or manual entry.")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setStyleSheet("""
            QLabel {
                color: #888898;
                font-size: 14px;
                padding: 40px;
            }
        """)
        self.empty_state_label.hide()
        layout.addWidget(self.empty_state_label)
        
        return panel
    
    def _load_settings(self):
        """Load current settings into UI"""
        self._refresh_camera_list()
    
    def _refresh_camera_list(self):
        """Refresh the camera list display"""
        # Clear existing items
        for item in list(self._camera_items.values()):
            item.deleteLater()
        self._camera_items.clear()
        
        # Get cameras and sort
        cameras = list(self.settings.cameras)
        sort_by = self.sort_combo.currentText()
        if "Name" in sort_by:
            cameras.sort(key=lambda c: c.name.lower())
        elif "IP Address" in sort_by:
            cameras.sort(key=lambda c: c.ip_address)
        elif "ATEM Input" in sort_by:
            cameras.sort(key=lambda c: self.settings.atem.input_mapping.get(str(c.id), 0), reverse=True)
        # Status sorting would require connection status, skip for now
        
        # Add cameras
        for camera in cameras:
            atem_input = self.settings.atem.input_mapping.get(str(camera.id), 0)
            item = CameraListItem(camera, atem_input)
            item.edit_clicked.connect(self._edit_camera)
            item.selection_changed.connect(self._on_camera_selection_changed)
            self._camera_items[camera.id] = item
            self.camera_list_layout.addWidget(item)
            
            # Set up thumbnail stream for online cameras
            self._setup_thumbnail_stream(camera)
        
        # Update count and progress
        total = len(self.settings.cameras)
        self.camera_list_header.setText(f"Configured Cameras ({total}/30)")
        self.camera_count_progress.setValue(total)
        
        # Show/hide empty state
        if total == 0:
            self.empty_state_label.show()
        else:
            self.empty_state_label.hide()
    
    def _setup_thumbnail_stream(self, camera: CameraConfig):
        """Set up thumbnail stream for a camera"""
        # Stop existing stream if any
        if camera.id in self._thumbnail_streams:
            self._thumbnail_streams[camera.id].stop()
            del self._thumbnail_streams[camera.id]
        
        # Create stream config
        config = StreamConfig(
            ip_address=camera.ip_address,
            port=camera.port,
            username=camera.username,
            password=camera.password,
            resolution=(320, 180)  # Small resolution for thumbnails
        )
        
        # Create and start stream
        stream = CameraStream(config)
        self._thumbnail_streams[camera.id] = stream
        stream.start(use_mjpeg=False)  # Use snapshot mode for thumbnails
    
    def _update_all_thumbnails(self):
        """Update all camera thumbnails"""
        for camera_id, item in self._camera_items.items():
            if camera_id in self._thumbnail_streams:
                stream = self._thumbnail_streams[camera_id]
                if stream.is_connected:
                    frame = stream.current_frame
                    if frame is not None:
                        item.update_thumbnail_frame(frame)
                        if item.connection_status != "online":
                            item.update_status("online")
                else:
                    if item.connection_status == "online":
                        item.update_status("offline")
            else:
                # Set up stream if not exists
                camera = self.settings.get_camera(camera_id)
                if camera:
                    self._setup_thumbnail_stream(camera)
    
    def _validate_field(self, field_name: str):
        """Validate individual field and show visual feedback"""
        if field_name == "name":
            text = self.camera_name_input.text().strip()
            if text:
                self.name_validator.show()
                self.name_validator.setStyleSheet("color: #22c55e; font-size: 14px; font-weight: bold;")
            else:
                self.name_validator.hide()
        elif field_name == "ip":
            text = self.camera_ip_input.text().strip()
            if text and self._is_valid_ip(text):
                self.ip_validator.show()
                self.ip_validator.setStyleSheet("color: #22c55e; font-size: 14px; font-weight: bold;")
            elif text:
                self.ip_validator.show()
                self.ip_validator.setText("✗")
                self.ip_validator.setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold;")
            else:
                self.ip_validator.hide()
        
        self._validate_form()
    
    def _validate_form(self):
        """Validate form inputs"""
        name = self.camera_name_input.text().strip()
        ip = self.camera_ip_input.text().strip()
        
        errors = []
        
        if not name:
            errors.append("Name is required")
        
        if not ip:
            errors.append("IP address is required")
        elif not self._is_valid_ip(ip):
            errors.append("Invalid IP address format")
        
        if errors:
            self.form_error_label.setText(" • ".join(errors))
            self.form_error_label.show()
            self.save_camera_btn.setEnabled(False)
            self.test_camera_btn.setEnabled(False)
        else:
            self.form_error_label.hide()
            self.save_camera_btn.setEnabled(True)
            self.test_camera_btn.setEnabled(True)
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def _on_form_changed(self):
        """Handle form field changes"""
        self._form_has_changes = True
    
    def _toggle_manual_form(self, checked: bool):
        """Toggle manual form visibility"""
        if checked:
            self.manual_form_container.show()
            self.manual_buttons_container.show()
        else:
            self.manual_form_container.hide()
            self.manual_buttons_container.hide()
    
    def _toggle_password_visibility(self, checked: bool):
        """Toggle password visibility"""
        if checked:
            self.camera_pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.password_toggle.setText("🙈")
        else:
            self.camera_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_toggle.setText("👁")
    
    def _populate_atem_inputs(self):
        """Populate ATEM input dropdown based on detected ATEM type"""
        self.camera_atem_combo.clear()
        self.camera_atem_combo.addItem("None", 0)
        
        # Try to get ATEM info from main window's tally controller
        try:
            main_window = self.window()
            if hasattr(main_window, '_tally_controller') and main_window._tally_controller:
                tally = main_window._tally_controller
                if tally.is_connected:
                    # Get input names from connected ATEM
                    for i in range(1, 21):
                        name = tally.get_input_name(i)
                        if name and name != f"Input {i}":
                            self.camera_atem_combo.addItem(f"{i}: {name}", i)
                        else:
                            self.camera_atem_combo.addItem(f"Input {i}", i)
                    return
        except:
            pass
        
        # Fallback: Generic inputs 1-20
        for i in range(1, 21):
            self.camera_atem_combo.addItem(f"Input {i}", i)
    
    def _get_selected_atem_input(self) -> int:
        """Get the currently selected ATEM input value"""
        return self.camera_atem_combo.currentData() or 0
    
    def _set_atem_input_by_value(self, value: int):
        """Set the ATEM combo box to a specific input value"""
        for i in range(self.camera_atem_combo.count()):
            if self.camera_atem_combo.itemData(i) == value:
                self.camera_atem_combo.setCurrentIndex(i)
                return
        # If not found, set to None
        self.camera_atem_combo.setCurrentIndex(0)
    
    def _use_defaults(self):
        """Reset form to Panasonic defaults"""
        self.camera_user_input.setText("admin")
        self.camera_pass_input.setText("12345")
        self.camera_atem_combo.setCurrentIndex(0)
        self._on_form_changed()
    
    def _discover_cameras(self):
        """Discover cameras on the network using background thread"""
        if self._discovery_worker and self._discovery_worker.isRunning():
            return
        
        # Clear UI
        for card in list(self._discovered_cards.values()):
            card.deleteLater()
        self._discovered_cards.clear()
        self._discovered_cameras = []
        
        # Show empty state initially
        self.discovery_empty_label.show()
        self.discovery_empty_label.setText("🔍 Searching network for Panasonic cameras...")
        self.discovery_empty_label.setStyleSheet("color: #FF9500; font-size: 11px; padding: 20px;")
        
        # Update UI state
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("⏳ Scanning...")
        self.discovery_status.setText("🔍 Searching network for Panasonic cameras...")
        self.discovery_status.setStyleSheet("color: #FF9500; font-size: 12px; padding: 4px;")
        self.discovery_progress.show()
        self.discovery_progress.setValue(0)
        
        # Create and start worker thread
        self._discovery_worker = DiscoveryWorker()
        self._discovery_worker.camera_found.connect(self._on_camera_discovered)
        self._discovery_worker.progress.connect(self._on_discovery_progress)
        self._discovery_worker.progress_value.connect(self.discovery_progress.setValue)
        self._discovery_worker.finished_signal.connect(self._on_discovery_finished)
        self._discovery_worker.start()
    
    @pyqtSlot(object)
    def _on_camera_discovered(self, camera: DiscoveredCamera):
        """Handle discovered camera from worker thread - show in real-time"""
        # Check if already in list
        if camera.ip_address in self._discovered_cards:
            return
        
        # Hide empty state when first camera is found
        if len(self._discovered_cameras) == 0:
            self.discovery_empty_label.hide()
        
        self._discovered_cameras.append(camera)
        
        # Create and add card
        card = DiscoveredCameraCard(camera)
        card.add_clicked.connect(self._on_discovered_card_add_clicked)
        card.identify_clicked.connect(self._on_identify_camera)
        self._discovered_cards[camera.ip_address] = card
        
        # Add card to layout (before empty state if it exists)
        insert_index = self.discovered_layout.indexOf(self.discovery_empty_label)
        if insert_index >= 0:
            self.discovered_layout.insertWidget(insert_index, card)
        else:
            self.discovered_layout.addWidget(card)
        
        # Fetch thumbnail for this camera in background
        self._fetch_discovery_thumbnail(camera.ip_address, card)
        
        # Update status
        count = len(self._discovered_cameras)
        status = getattr(camera, 'status', 'Unknown')
        if status == "Auth Required":
            self.discovery_status.setText(f"✅ Found {count} camera(s) - Some require authentication")
            self.discovery_status.setStyleSheet("color: #f97316; font-size: 12px; padding: 4px;")
        else:
            self.discovery_status.setText(f"✅ Found {count} camera(s)...")
            self.discovery_status.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
    
    @pyqtSlot(str)
    def _on_discovery_progress(self, message: str):
        """Handle progress update from worker thread"""
        self.discovery_status.setText(message)
        QApplication.processEvents()
    
    @pyqtSlot(int)
    def _on_discovery_finished(self, count: int):
        """Handle discovery completion"""
        self.discover_btn.setEnabled(True)
        self.discover_btn.setText("🔍  Scan Network")
        self.discovery_progress.setValue(100)
        QTimer.singleShot(1000, lambda: self.discovery_progress.hide())
        
        if count == 0:
            self.discovery_status.setText("❌ No cameras found")
            self.discovery_status.setStyleSheet("color: #ef4444; font-size: 12px; padding: 4px;")
            self.discovery_empty_label.show()
            self.discovery_empty_label.setText(
                "❌ No Panasonic cameras found on network.\n\n"
                "Troubleshooting tips:\n"
                "• Ensure cameras are on the same network\n"
                "• Check firewall settings\n"
                "• Verify cameras support Panasonic Easy IP protocol"
            )
            self.discovery_empty_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 20px;")
        else:
            self.discovery_status.setText(f"✅ Discovery complete: Found {count} camera(s)")
            self.discovery_status.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
            # Empty state should already be hidden if cameras were found
    
    def _on_identify_camera(self, ip_address: str):
        """Handle identify camera button - make LED blink"""
        from src.camera.discovery import CameraDiscovery
        
        # Get credentials from form if available
        username = self.camera_user_input.text().strip() or "admin"
        password = self.camera_pass_input.text().strip() or "12345"
        
        # Update status
        self.discovery_status.setText(f"💡 Identifying camera at {ip_address}...")
        self.discovery_status.setStyleSheet("color: #eab308; font-size: 12px; padding: 4px;")
        
        # Run identify in background
        def identify_task():
            success = CameraDiscovery.identify_camera(ip_address, username, password, duration=5)
            return success
        
        def on_identify_complete(future):
            try:
                success = future.result()
                if success:
                    QTimer.singleShot(0, lambda: self._show_identify_result(ip_address, True))
                else:
                    QTimer.singleShot(0, lambda: self._show_identify_result(ip_address, False))
            except:
                QTimer.singleShot(0, lambda: self._show_identify_result(ip_address, False))
        
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(identify_task)
        future.add_done_callback(on_identify_complete)
    
    def _show_identify_result(self, ip_address: str, success: bool):
        """Show result of identify command"""
        if success:
            self.discovery_status.setText(f"💡 Camera {ip_address} LED is blinking for 5 seconds")
            self.discovery_status.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
        else:
            self.discovery_status.setText(f"⚠️ Could not identify camera {ip_address}")
            self.discovery_status.setStyleSheet("color: #f97316; font-size: 12px; padding: 4px;")
        
        # Clear status after a few seconds
        QTimer.singleShot(6000, lambda: self._reset_discovery_status())
    
    def _reset_discovery_status(self):
        """Reset discovery status to default"""
        count = len(self._discovered_cameras)
        if count > 0:
            self.discovery_status.setText(f"✅ {count} camera(s) found")
            self.discovery_status.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
        else:
            self.discovery_status.setText("Ready to scan or add manually")
            self.discovery_status.setStyleSheet("color: #888898; font-size: 12px; padding: 4px;")
    
    def _fetch_discovery_thumbnail(self, ip_address: str, card: 'DiscoveredCameraCard'):
        """Fetch thumbnail for discovered camera in background"""
        from src.camera.discovery import CameraDiscovery
        from PyQt6.QtGui import QPixmap, QImage
        
        def fetch_task():
            username = "admin"
            password = "12345"
            jpeg_data = CameraDiscovery.get_camera_thumbnail(ip_address, username, password, (160, 90))
            return jpeg_data
        
        def on_fetch_complete(future):
            try:
                jpeg_data = future.result()
                if jpeg_data:
                    # Convert to QPixmap on main thread
                    QTimer.singleShot(0, lambda: self._set_card_thumbnail(card, jpeg_data))
            except:
                pass
        
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fetch_task)
        future.add_done_callback(on_fetch_complete)
    
    def _set_card_thumbnail(self, card: 'DiscoveredCameraCard', jpeg_data: bytes):
        """Set thumbnail on card (must be called from main thread)"""
        from PyQt6.QtGui import QPixmap, QImage
        
        try:
            qimage = QImage.fromData(jpeg_data)
            if not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                card.set_thumbnail(pixmap)
        except Exception as e:
            print(f"[CameraPage] Error setting thumbnail: {e}")
    
    def _on_discovered_card_add_clicked(self, camera: DiscoveredCamera):
        """Handle add button click on discovered camera card"""
        self._add_discovered_camera(camera)
    
    def _add_discovered_camera(self, camera: DiscoveredCamera):
        """Add discovered camera to form with visual feedback"""
        self.camera_name_input.setText(camera.name or camera.model or "Camera")
        self.camera_ip_input.setText(camera.ip_address)
        self.camera_user_input.setText("admin")
        self.camera_pass_input.setText("12345")  # Panasonic default
        
        # Highlight fields that were auto-filled
        self._highlight_auto_filled_fields()
        self._validate_form()
    
    def _highlight_auto_filled_fields(self):
        """Temporarily highlight auto-filled fields"""
        # Flash effect could be added here with QPropertyAnimation
        pass
    
    def _test_camera(self):
        """Test camera connection from form with live status"""
        ip = self.camera_ip_input.text().strip()
        if not ip:
            self.test_status_label.setText("❌ Please enter an IP address")
            self.test_status_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 4px;")
            self.test_status_label.show()
            return
        
        if not self._is_valid_ip(ip):
            self.test_status_label.setText("❌ Invalid IP address format")
            self.test_status_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 4px;")
            self.test_status_label.show()
            return
        
        # Disable test button during test
        self.test_camera_btn.setEnabled(False)
        self.test_camera_btn.setText("⏳ Testing...")
        self.test_status_label.setText("🔄 Testing connection...")
        self.test_status_label.setStyleSheet("color: #FF9500; font-size: 11px; padding: 4px;")
        self.test_status_label.show()
        
        port = 80  # Default port
        username = self.camera_user_input.text() or "admin"
        password = self.camera_pass_input.text() or "12345"
        
        from ..camera.stream import CameraStream, StreamConfig
        
        config = StreamConfig(
            ip_address=ip,
            port=port,
            username=username,
            password=password
        )
        
        # Test in background thread
        def test_complete(success: bool, message: str):
            self.test_camera_btn.setEnabled(True)
            self.test_camera_btn.setText("🔌 Test")
            
            if success:
                self.test_status_label.setText(f"✅ Connection successful! {message}")
                self.test_status_label.setStyleSheet("color: #22c55e; font-size: 11px; padding: 4px;")
            else:
                # Provide specific error messages
                error_msg = message
                if "timeout" in message.lower():
                    error_msg = "Connection timeout - Check network and IP address"
                elif "401" in message or "authentication" in message.lower():
                    error_msg = "Authentication failed - Check username/password"
                elif "refused" in message.lower():
                    error_msg = "Connection refused - Check port number"
                else:
                    error_msg = f"Connection failed: {message}"
                
                self.test_status_label.setText(f"❌ {error_msg}")
                self.test_status_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 4px;")
        
        # Run test in thread
        def run_test():
            stream = CameraStream(config)
            success, message = stream.test_connection()
            QTimer.singleShot(0, lambda: test_complete(success, message))
        
        import threading
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def _save_camera(self):
        """Save camera configuration"""
        name = self.camera_name_input.text().strip()
        ip = self.camera_ip_input.text().strip()
        
        if not name or not ip:
            return
        
        port = 80  # Default port
        username = self.camera_user_input.text() or "admin"
        password = self.camera_pass_input.text() or "12345"
        
        if self._editing_camera_id is not None:
            # Update existing camera
            camera = CameraConfig(
                id=self._editing_camera_id,
                name=name,
                ip_address=ip,
                port=port,
                username=username,
                password=password
            )
            self.settings.update_camera(camera)
            
            # Update ATEM mapping
            atem_input = self._get_selected_atem_input()
            if atem_input > 0:
                self.settings.atem.input_mapping[str(camera.id)] = atem_input
            elif str(camera.id) in self.settings.atem.input_mapping:
                del self.settings.atem.input_mapping[str(camera.id)]
            
            self._editing_camera_id = None
            self.cancel_edit_btn.hide()
            self.save_camera_btn.setText("Save Camera")
        else:
            # Add new camera
            if len(self.settings.cameras) >= 30:
                QMessageBox.warning(self, "Error", "Maximum 30 cameras allowed")
                return
            
            # Generate new ID
            existing_ids = [c.id for c in self.settings.cameras]
            new_id = 1
            while new_id in existing_ids:
                new_id += 1
            
            camera = CameraConfig(
                id=new_id,
                name=name,
                ip_address=ip,
                port=port,
                username=username,
                password=password
            )
            self.settings.add_camera(camera)
            
            # Update ATEM mapping
            atem_input = self._get_selected_atem_input()
            if atem_input > 0:
                self.settings.atem.input_mapping[str(camera.id)] = atem_input
        
        self.settings.save()
        self._refresh_camera_list()
        self._clear_camera_form()
        self.settings_changed.emit()
        
        # Show success feedback
        QMessageBox.information(self, "Success", f"Camera '{name}' saved successfully!")
    
    def _edit_camera(self, camera_id: int):
        """Edit existing camera"""
        camera = self.settings.get_camera(camera_id)
        if not camera:
            return
        
        self._editing_camera_id = camera_id
        
        # Show the manual form if not already visible
        if not self.manual_toggle_btn.isChecked():
            self.manual_toggle_btn.setChecked(True)
        
        self.camera_name_input.setText(camera.name)
        self.camera_ip_input.setText(camera.ip_address)
        self.camera_user_input.setText(camera.username)
        self.camera_pass_input.setText(camera.password)
        
        # Load ATEM mapping
        atem_input = self.settings.atem.input_mapping.get(str(camera_id), 0)
        self._set_atem_input_by_value(atem_input)
        
        self.save_camera_btn.setText("Update Camera")
        self.cancel_edit_btn.show()
        self._validate_form()
        self._form_has_changes = False
        
        # Make the Add Camera section visible (don't focus to avoid keyboard popup)
        self.add_camera_group.setVisible(True)
    
    def _cancel_edit(self):
        """Cancel camera edit"""
        if self._form_has_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self._editing_camera_id = None
        self._clear_camera_form()
        self.cancel_edit_btn.hide()
        self.save_camera_btn.setText("💾 Save")
        self._form_has_changes = False
    
    def _on_camera_selection_changed(self, camera_id: int, selected: bool):
        """Handle camera selection checkbox change"""
        if selected:
            self._selected_cameras.add(camera_id)
        else:
            self._selected_cameras.discard(camera_id)
    
    def _select_all_cameras(self):
        """Select all cameras"""
        for item in self._camera_items.values():
            item.checkbox.setCheckState(Qt.CheckState.Checked)
    
    def _deselect_all_cameras(self):
        """Deselect all cameras"""
        for item in self._camera_items.values():
            item.checkbox.setCheckState(Qt.CheckState.Unchecked)
    
    def _bulk_duplicate_cameras(self):
        """Duplicate all selected cameras"""
        if not self._selected_cameras:
            QMessageBox.information(self, "No Selection", "Please select cameras to duplicate")
            return
        
        # Check if we have room for duplicates
        current_count = len(self.settings.cameras)
        selected_count = len(self._selected_cameras)
        if current_count + selected_count > 30:
            QMessageBox.warning(
                self, "Error",
                f"Cannot duplicate {selected_count} camera(s). Maximum 30 cameras allowed.\n"
                f"Current: {current_count}, Would be: {current_count + selected_count}"
            )
            return
        
        # Duplicate each selected camera
        for camera_id in list(self._selected_cameras):
            camera = self.settings.get_camera(camera_id)
            if not camera:
                continue
            
            # Generate new ID
            existing_ids = [c.id for c in self.settings.cameras]
            new_id = 1
            while new_id in existing_ids:
                new_id += 1
            
            # Create duplicate
            new_camera = CameraConfig(
                id=new_id,
                name=f"{camera.name} (Copy)",
                ip_address=camera.ip_address,
                port=camera.port,
                username=camera.username,
                password=camera.password
            )
            
            self.settings.add_camera(new_camera)
            
            # Copy ATEM mapping if exists
            if str(camera_id) in self.settings.atem.input_mapping:
                self.settings.atem.input_mapping[str(new_id)] = self.settings.atem.input_mapping[str(camera_id)]
        
        self.settings.save()
        self._selected_cameras.clear()
        self._refresh_camera_list()
        self.settings_changed.emit()
    
    def _bulk_delete_cameras(self):
        """Delete all selected cameras"""
        if not self._selected_cameras:
            QMessageBox.information(self, "No Selection", "Please select cameras to delete")
            return
        
        count = len(self._selected_cameras)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {count} camera(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for camera_id in list(self._selected_cameras):
                self.settings.remove_camera(camera_id)
                if str(camera_id) in self.settings.atem.input_mapping:
                    del self.settings.atem.input_mapping[str(camera_id)]
            
            self.settings.save()
            self._selected_cameras.clear()
            self._refresh_camera_list()
            self.settings_changed.emit()
    
    def _clear_camera_form(self):
        """Clear camera form inputs"""
        self.camera_name_input.clear()
        self.camera_ip_input.clear()
        self.camera_user_input.setText("admin")
        self.camera_pass_input.setText("12345")
        self.camera_atem_combo.setCurrentIndex(0)
        self.form_error_label.hide()
        self.test_status_label.hide()
        self.name_validator.hide()
        self.ip_validator.hide()
        self.save_camera_btn.setEnabled(True)
        self.test_camera_btn.setEnabled(True)
        self._form_has_changes = False
