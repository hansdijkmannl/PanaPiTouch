"""
Camera Page

Configuration for Panasonic PTZ cameras.
"""
import re
import socket
from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QFrame, QApplication, QProgressBar,
    QComboBox, QStackedWidget, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

from ..config.settings import Settings, CameraConfig
from ..camera.discovery import CameraDiscovery, DiscoveredCamera
from ..camera.stream import CameraStream, StreamConfig
from ..network.manager import NetworkManager, NetworkDiagnostics
from .widgets import TouchScrollArea


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
    fix_network_clicked = pyqtSignal(object)  # DiscoveredCamera
    
    def __init__(self, camera: DiscoveredCamera, parent=None, network_info=None):
        super().__init__(parent)
        self.camera = camera
        self.network_info = network_info  # dict with 'ip', 'subnet', 'gateway' from eth0
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
        
        # IP address with network status
        ip_row = QHBoxLayout()
        ip_row.setSpacing(6)
        ip_label = QLabel(f"{self.camera.ip_address}")
        ip_label.setStyleSheet("font-size: 11px; color: #888898;")
        ip_label.setWordWrap(False)
        ip_row.addWidget(ip_label)
        
        # Network status indicator (wrong subnet warning)
        self._network_status_label = None
        if self.network_info and self._is_wrong_subnet():
            network_warning = QLabel("⚠ Wrong Subnet")
            network_warning.setStyleSheet("font-size: 9px; color: #ef4444; font-weight: 600;")
            ip_row.addWidget(network_warning)
            self._network_status_label = network_warning
        ip_row.addStretch()
        info_layout.addLayout(ip_row)
        
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
                padding: 0px;
                margin: 0px;
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
        
        # Fix Network button (if wrong subnet)
        if self.network_info and self._is_wrong_subnet():
            fix_network_btn = QPushButton("🔧")
            fix_network_btn.setFixedSize(32, 28)
            fix_network_btn.setToolTip("Fix network settings")
            fix_network_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
                QPushButton:pressed {
                    background-color: #b91c1c;
                }
            """)
            fix_network_btn.clicked.connect(lambda: self.fix_network_clicked.emit(self.camera))
            btn_layout.addWidget(fix_network_btn)
        
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
                padding: 0px;
                margin: 0px;
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
    
    def _is_wrong_subnet(self) -> bool:
        """Check if camera IP is in wrong subnet compared to eth0"""
        if not self.network_info or not self.camera.ip_address:
            return False
        
        try:
            camera_ip = self.camera.ip_address
            eth0_ip = self.network_info.get('ip', '')
            eth0_subnet = self.network_info.get('subnet', '255.255.255.0')
            
            if not eth0_ip or not camera_ip:
                return False
            
            # Check if camera IP is in same subnet as eth0
            return not self._same_subnet(camera_ip, eth0_ip, eth0_subnet)
        except:
            return False
    
    def _same_subnet(self, ip1: str, ip2: str, subnet: str) -> bool:
        """Check if two IPs are in the same subnet"""
        try:
            def ip_to_int(ip):
                parts = ip.split('.')
                return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
            
            def subnet_to_mask(subnet):
                parts = subnet.split('.')
                return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
            
            mask = subnet_to_mask(subnet)
            return (ip_to_int(ip1) & mask) == (ip_to_int(ip2) & mask)
        except:
            return False
    
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
    
    def __init__(self, camera: CameraConfig, atem_input: int, compact: bool = False, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.atem_input = atem_input
        self.compact = compact
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
        
        if not self.compact:
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
                padding: 0px;
                margin: 0px;
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
        
        # Initialize badge count
        QTimer.singleShot(100, self._update_configured_badge)
        
        # Start thumbnail update timer (update every 2 minutes)
        self._thumbnail_timer.start(120000)
    
    def resizeEvent(self, event):
        """Handle window resize to reposition badge"""
        super().resizeEvent(event)
        if self.configured_badge:
            QTimer.singleShot(10, self._update_badge_position)
    
    def _setup_ui(self):
        """Setup the camera page UI with sidebar navigation"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0a0a0f;
                border-right: 1px solid #2a2a38;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(8)
        
        self.sidebar_buttons = []
        self.configured_badge = None  # Badge for Configured button
        self.configured_button_wrapper = None  # Wrapper for Configured button
        self.configured_button = None  # Configured button reference
        sections = [
            ("➕", "Add Camera"),
            ("📋", "Configured"),
            ("🔧", "Network Management"),
        ]
        for idx, (icon, name) in enumerate(sections):
            # Create wrapper widget for Configured button to hold badge
            if idx == 1:  # Configured button
                wrapper = QFrame()
                wrapper.setStyleSheet("background-color: transparent;")
                wrapper_layout = QVBoxLayout(wrapper)
                wrapper_layout.setContentsMargins(0, 0, 0, 0)
                wrapper_layout.setSpacing(0)
                
                btn = QPushButton(f"{icon}\n{name}")
                btn.setCheckable(True)
                btn.setMinimumHeight(80)
                btn.setStyleSheet(self._get_sidebar_button_style())
                btn.clicked.connect(lambda checked, i=idx: self._on_section_clicked(i))
                wrapper_layout.addWidget(btn)
                
                # Create badge label positioned absolutely on the button
                badge = QLabel("0", btn)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet("""
                    QLabel {
                        background-color: #ef4444;
                        color: #ffffff;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 6px;
                        min-width: 20px;
                    }
                """)
                badge.setFixedSize(24, 20)
                badge.hide()  # Hide if count is 0
                badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # Don't block button clicks
                self.configured_badge = badge
                self.configured_button_wrapper = wrapper
                self.configured_button = btn  # Store button reference
                
                sidebar_layout.addWidget(wrapper)
                self.sidebar_buttons.append(btn)
                
                # Update badge position after widget is shown
                QTimer.singleShot(100, self._update_badge_position)
            else:
                btn = QPushButton(f"{icon}\n{name}")
                btn.setCheckable(True)
                btn.setMinimumHeight(80)
                btn.setStyleSheet(self._get_sidebar_button_style())
                btn.clicked.connect(lambda checked, i=idx: self._on_section_clicked(i))
                sidebar_layout.addWidget(btn)
                self.sidebar_buttons.append(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        
        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #0a0a0f;")
        self.content_stack.addWidget(self._create_add_content())
        self.content_stack.addWidget(self._create_configured_content())
        self.content_stack.addWidget(self._create_network_management_content())
        main_layout.addWidget(self.content_stack, 1)
        
        # Default selection
        self._on_section_clicked(0)

    def _get_sidebar_button_style(self):
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 12px;
                color: #888898;
                font-size: 13px;
                font-weight: 500;
                padding: 12px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #1a1a24;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #FF9500;
                color: #0a0a0f;
                font-weight: 600;
            }
            QPushButton:pressed {
                background-color: #CC7700;
            }
        """
    
    def _update_badge_position(self):
        """Update badge position on Configured button"""
        if self.configured_badge and self.configured_button:
            # Position badge at top-right of button, 15px from right edge
            btn_width = self.configured_button.width()
            if btn_width > 0:
                badge_x = btn_width - 43  # 28 (original) + 15 (move left)
                badge_y = 8
                self.configured_badge.move(badge_x, badge_y)
                self.configured_badge.raise_()  # Ensure badge is on top
    
    def _update_configured_badge(self):
        """Update the badge count on Configured button"""
        if self.configured_badge:
            count = len(self.settings.cameras)
            self.configured_badge.setText(str(count))
            if count > 0:
                self.configured_badge.show()
            else:
                self.configured_badge.hide()
            # Update position after text change
            QTimer.singleShot(10, self._update_badge_position)

    def _on_section_clicked(self, index: int):
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(getattr(self, 'sidebar_buttons', [])):
            btn.setChecked(i == index)
        
        # Hide edit form when switching away from Configured page
        if index != 1 and hasattr(self, 'edit_form_panel'):
            self.edit_form_panel.hide()
            self._editing_camera_id = None

    def _create_add_content(self) -> QWidget:
        """Add/discover cameras page"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)
        wrapper_layout.setSpacing(0)
        
        # Full-width left panel (no right column)
        left_panel = self._create_left_panel()
        wrapper_layout.addWidget(left_panel, stretch=1)
        
        return wrapper

    def _create_configured_content(self) -> QWidget:
        """Configured cameras with inline edit column"""
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Left: Camera list
        left_panel = self._create_camera_list_panel(compact=True)
        layout.addWidget(left_panel, stretch=1)
        
        # Right: Edit form panel (initially hidden)
        self.edit_form_panel = self._create_edit_form_panel()
        layout.addWidget(self.edit_form_panel, stretch=1)
        
        return wrapper
    
    def _create_network_management_content(self) -> QWidget:
        """Network Management page"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)
        wrapper_layout.setSpacing(20)
        
        # Scroll area for network management content
        scroll_area = TouchScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Container widget for network management
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # Network Management panel
        self.network_group = self._create_network_management_panel()
        content_layout.addWidget(self.network_group)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        wrapper_layout.addWidget(scroll_area)
        
        return wrapper
    
    def _create_edit_form_panel(self) -> QWidget:
        """Create edit form panel for inline editing"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        panel.hide()  # Hidden until edit is clicked
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Edit Camera")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff; border: none;")
        layout.addWidget(header)
        
        # Form fields (reuse same style as add form)
        # Name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(6)
        name_label = QLabel("Camera Name:")
        name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        name_layout.addWidget(name_label)
        self.edit_name_input = QLineEdit()
        self.edit_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: #FFFFFF;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #FF9500;
            }
        """)
        name_layout.addWidget(self.edit_name_input)
        layout.addLayout(name_layout)
        
        # IP Address
        ip_layout = QVBoxLayout()
        ip_layout.setSpacing(6)
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        ip_layout.addWidget(ip_label)
        self.edit_ip_input = QLineEdit()
        self.edit_ip_input.setStyleSheet(self.edit_name_input.styleSheet())
        ip_layout.addWidget(self.edit_ip_input)
        layout.addLayout(ip_layout)
        
        # Port
        port_layout = QVBoxLayout()
        port_layout.setSpacing(6)
        port_label = QLabel("Port:")
        port_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        port_layout.addWidget(port_label)
        self.edit_port_input = QSpinBox()
        self.edit_port_input.setRange(1, 65535)
        self.edit_port_input.setValue(80)
        self.edit_port_input.setStyleSheet("""
            QSpinBox {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: #FFFFFF;
                min-height: 20px;
            }
            QSpinBox:focus {
                border-color: #FF9500;
            }
        """)
        port_layout.addWidget(self.edit_port_input)
        layout.addLayout(port_layout)
        
        # Username
        user_layout = QVBoxLayout()
        user_layout.setSpacing(6)
        user_label = QLabel("Username:")
        user_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        user_layout.addWidget(user_label)
        self.edit_user_input = QLineEdit()
        self.edit_user_input.setStyleSheet(self.edit_name_input.styleSheet())
        self.edit_user_input.setText("admin")
        user_layout.addWidget(self.edit_user_input)
        layout.addLayout(user_layout)
        
        # Password
        pass_layout = QVBoxLayout()
        pass_layout.setSpacing(6)
        pass_label = QLabel("Password:")
        pass_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        pass_layout.addWidget(pass_label)
        self.edit_pass_input = QLineEdit()
        self.edit_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass_input.setStyleSheet(self.edit_name_input.styleSheet())
        self.edit_pass_input.setText("12345")
        pass_layout.addWidget(self.edit_pass_input)
        layout.addLayout(pass_layout)
        
        # ATEM Input
        atem_layout = QVBoxLayout()
        atem_layout.setSpacing(6)
        atem_label = QLabel("ATEM Input:")
        atem_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; border: none;")
        atem_layout.addWidget(atem_label)
        self.edit_atem_combo = QComboBox()
        self.edit_atem_combo.addItem("No ATEM mapping", 0)
        for i in range(1, 21):
            self.edit_atem_combo.addItem(f"Input {i}", i)
        self.edit_atem_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: #FFFFFF;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #FF9500;
            }
        """)
        atem_layout.addWidget(self.edit_atem_combo)
        layout.addLayout(atem_layout)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(48)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 2px solid #3a3a48;
                border-radius: 8px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a3a48;
                border-color: #FF9500;
            }
            QPushButton:pressed {
                background-color: #FF9500;
                border-color: #FF9500;
                color: #0a0a0f;
            }
        """)
        cancel_btn.clicked.connect(self._cancel_inline_edit)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setFixedHeight(48)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 8px;
                color: #0a0a0f;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #FFAA33;
            }
            QPushButton:pressed {
                background-color: #CC7700;
            }
        """)
        save_btn.clicked.connect(self._save_inline_edit)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _cancel_inline_edit(self):
        """Cancel inline editing"""
        if hasattr(self, 'edit_form_panel'):
            self.edit_form_panel.hide()
            self._editing_camera_id = None
    
    def _save_inline_edit(self):
        """Save changes from inline edit form"""
        if not hasattr(self, '_editing_camera_id') or self._editing_camera_id is None:
            return
        
        camera = self.settings.get_camera(self._editing_camera_id)
        if not camera:
            return
        
        name = self.edit_name_input.text().strip()
        ip = self.edit_ip_input.text().strip()
        port = self.edit_port_input.value()
        username = self.edit_user_input.text().strip()
        password = self.edit_pass_input.text().strip()
        
        if not name or not ip:
            QMessageBox.warning(self, "Error", "Name and IP address are required")
            return
        
        # Update camera
        camera.name = name
        camera.ip_address = ip
        camera.port = port
        camera.username = username
        camera.password = password
        
        self.settings.update_camera(camera)
        
        # Update ATEM mapping
        atem_input = self.edit_atem_combo.currentData()
        if atem_input and atem_input > 0:
            self.settings.atem.input_mapping[str(camera.id)] = atem_input
        elif str(camera.id) in self.settings.atem.input_mapping:
            del self.settings.atem.input_mapping[str(camera.id)]
        
        self.settings.save()
        self._refresh_camera_list()
        self.edit_form_panel.hide()
        self._editing_camera_id = None
        self.settings_changed.emit()
        
        QMessageBox.information(self, "Success", f"Camera '{name}' updated successfully!")
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with unified discovery and manual add (full width)"""
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
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
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
        
        # Discovered cameras scroll area with touch scrolling
        discovered_scroll = TouchScrollArea()
        discovered_scroll.setWidgetResizable(True)
        discovered_scroll.setFixedHeight(180)
        discovered_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 6px;
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
        
        # Network Configuration Section
        network_group = QGroupBox("🌐 Network Configuration")
        network_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
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
        network_layout = QVBoxLayout(network_group)
        network_layout.setSpacing(12)
        
        # IP Address (already have camera_ip_input, but add it here for network section)
        # We'll keep IP in basic section, but add subnet/gateway/DHCP here
        
        # Subnet Mask
        subnet_layout = QVBoxLayout()
        subnet_layout.setSpacing(4)
        subnet_label = QLabel("Subnet Mask:")
        subnet_layout.addWidget(subnet_label)
        self.camera_subnet_input = QComboBox()
        self.camera_subnet_input.setEditable(True)
        self.camera_subnet_input.setFixedHeight(40)
        self.camera_subnet_input.addItems([
            "255.255.255.0",
            "255.255.0.0",
            "255.0.0.0",
            "255.255.255.128",
            "255.255.255.192",
            "255.255.255.224",
            "255.255.255.240",
            "255.255.255.248",
            "255.255.255.252"
        ])
        self.camera_subnet_input.setCurrentText("255.255.255.0")
        self.camera_subnet_input.currentTextChanged.connect(self._on_form_changed)
        subnet_layout.addWidget(self.camera_subnet_input)
        network_layout.addLayout(subnet_layout)
        
        # Gateway
        gateway_layout = QVBoxLayout()
        gateway_layout.setSpacing(4)
        gateway_label = QLabel("Gateway (optional):")
        gateway_layout.addWidget(gateway_label)
        self.camera_gateway_input = QLineEdit()
        self.camera_gateway_input.setFixedHeight(40)
        self.camera_gateway_input.setPlaceholderText("e.g. 192.168.1.1")
        self.camera_gateway_input.textChanged.connect(self._on_form_changed)
        gateway_layout.addWidget(self.camera_gateway_input)
        network_layout.addLayout(gateway_layout)
        
        # DHCP Toggle
        dhcp_layout = QHBoxLayout()
        dhcp_layout.setSpacing(12)
        dhcp_label = QLabel("DHCP:")
        dhcp_layout.addWidget(dhcp_label)
        self.camera_dhcp_checkbox = QCheckBox("Enable DHCP (auto-assign IP)")
        self.camera_dhcp_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #2a2a38;
                border-radius: 4px;
                background-color: #1a1a24;
            }
            QCheckBox::indicator:checked {
                background-color: #FF9500;
                border-color: #FF9500;
            }
        """)
        self.camera_dhcp_checkbox.toggled.connect(self._on_dhcp_toggled)
        self.camera_dhcp_checkbox.toggled.connect(self._on_form_changed)
        dhcp_layout.addWidget(self.camera_dhcp_checkbox)
        dhcp_layout.addStretch()
        network_layout.addLayout(dhcp_layout)
        
        # Auto-fill from network button
        autofill_btn = QPushButton("🔧 Auto-fill from eth0")
        autofill_btn.setFixedHeight(36)
        autofill_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 1px solid #3a3a48;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3a3a48;
                border-color: #FF9500;
            }
        """)
        autofill_btn.clicked.connect(self._autofill_network_settings)
        network_layout.addWidget(autofill_btn)
        
        manual_layout.addWidget(network_group)
        
        # Add spacing
        manual_layout.addSpacing(20)
        
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
    
    def _create_camera_list_panel(self, compact: bool = False) -> QWidget:
        """Create camera list panel with search and bulk operations.
        
        Args:
            compact: when True, show a simple edit column header (configured page).
        """
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
        
        # Store compact flag for use when creating items
        self._list_compact = compact
        
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
        
        # Hide sort in compact mode
        if compact:
            self.sort_combo.hide()
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        if compact:
            column_header = QHBoxLayout()
            label_left = QLabel("Configured Camera")
            label_left.setStyleSheet("color: #888898; font-size: 12px; font-weight: 600;")
            column_header.addWidget(label_left)
            column_header.addStretch()
            label_right = QLabel("Edit")
            label_right.setStyleSheet("color: #888898; font-size: 12px; font-weight: 600;")
            column_header.addWidget(label_right, 0, Qt.AlignmentFlag.AlignRight)
            layout.addLayout(column_header)
        
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
        
        # Hide bulk operations in compact mode (no checkboxes)
        if compact:
            bulk_container.hide()
        
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
        
        # Scroll area for camera list with touch scrolling
        self.camera_scroll = TouchScrollArea()
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
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
            item = CameraListItem(camera, atem_input, compact=getattr(self, "_list_compact", False))
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
        
        # Update badge on Configured button
        self._update_configured_badge()
        
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
        stream.start(use_rtsp=False, use_snapshot=True)  # Use snapshot mode for thumbnails
    
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
        """Populate ATEM input dropdown - deprecated, ATEM removed from Add Camera form"""
        # This method is kept for compatibility but does nothing
        # ATEM mapping is only available in Configured cameras edit form
        pass
    
    def _get_selected_atem_input(self) -> int:
        """Get the currently selected ATEM input value - deprecated"""
        # ATEM removed from Add Camera form, always return 0
        return 0
    
    def _set_atem_input_by_value(self, value: int):
        """Set the ATEM combo box - deprecated"""
        # ATEM removed from Add Camera form, do nothing
        pass
    
    def _use_defaults(self):
        """Reset form to Panasonic defaults"""
        self.camera_user_input.setText("admin")
        self.camera_pass_input.setText("12345")
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
        
        # Get eth0 IP for discovery
        network_info = self._get_eth0_network_info()
        eth0_ip = network_info.get('ip') if network_info else None
        
        # Create and start worker thread (always use eth0)
        self._discovery_worker = DiscoveryWorker(adapter_ip=eth0_ip)
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
        # Get network info from eth0
        network_info = self._get_eth0_network_info()
        card = DiscoveredCameraCard(camera, network_info=network_info)
        card.add_clicked.connect(self._on_discovered_card_add_clicked)
        card.identify_clicked.connect(self._on_identify_camera)
        card.fix_network_clicked.connect(self._on_fix_network_clicked)
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
    
    def _on_fix_network_clicked(self, camera: DiscoveredCamera):
        """Handle fix network button click on discovered camera card"""
        try:
            from .network_fix_dialog import NetworkFixDialog
        except ImportError:
            QMessageBox.warning(self, "Error", "Network fix dialog not available")
            return
        
        network_info = self._get_eth0_network_info()
        if not network_info:
            QMessageBox.warning(self, "Error", "Could not detect eth0 network settings")
            return
        
        dialog = NetworkFixDialog(camera, network_info, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Network was changed, refresh discovery
            QTimer.singleShot(2000, self._discover_cameras)  # Wait 2 seconds for camera to reboot
    
    def _add_discovered_camera(self, camera: DiscoveredCamera):
        """Add discovered camera to form with visual feedback"""
        self.camera_name_input.setText(camera.name or camera.model or "Camera")
        self.camera_ip_input.setText(camera.ip_address)
        self.camera_user_input.setText("admin")
        self.camera_pass_input.setText("12345")  # Panasonic default
        
        # Auto-fill network settings from eth0 if available
        network_info = self._get_eth0_network_info()
        if network_info:
            if network_info.get('subnet'):
                self.camera_subnet_input.setCurrentText(network_info['subnet'])
            if network_info.get('gateway'):
                self.camera_gateway_input.setText(network_info['gateway'])
        
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
            
            # No ATEM mapping in Add Camera form
            
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
            
            # No ATEM mapping in Add Camera form
        
        self.settings.save()
        self._refresh_camera_list()
        self._clear_camera_form()
        self.settings_changed.emit()
        
        # Show success feedback
        QMessageBox.information(self, "Success", f"Camera '{name}' saved successfully!")
    
    def _edit_camera(self, camera_id: int):
        """Edit existing camera - show inline edit form"""
        camera = self.settings.get_camera(camera_id)
        if not camera:
            return
        
        self._editing_camera_id = camera_id
        
        # Switch to Configured page if not already there
        if self.content_stack.currentIndex() != 1:
            self._on_section_clicked(1)
        
        # Populate edit form
        if hasattr(self, 'edit_form_panel'):
            self.edit_name_input.setText(camera.name)
            self.edit_ip_input.setText(camera.ip_address)
            self.edit_port_input.setValue(camera.port)
            self.edit_user_input.setText(camera.username)
            self.edit_pass_input.setText(camera.password)
        
            # Load ATEM mapping
            atem_input = self.settings.atem.input_mapping.get(str(camera_id), 0)
            index = self.edit_atem_combo.findData(atem_input)
            if index >= 0:
                self.edit_atem_combo.setCurrentIndex(index)
            
            # Show the edit form panel
            self.edit_form_panel.show()
    
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
        self.camera_subnet_input.setCurrentText("255.255.255.0")
        self.camera_gateway_input.clear()
        self.camera_dhcp_checkbox.setChecked(False)
        self.form_error_label.hide()
        self.test_status_label.hide()
        self.name_validator.hide()
        self.ip_validator.hide()
        self.save_camera_btn.setEnabled(True)
        self.test_camera_btn.setEnabled(True)
        self._form_has_changes = False
    
    def _on_dhcp_toggled(self, checked: bool):
        """Handle DHCP checkbox toggle"""
        # Disable IP/subnet/gateway fields when DHCP is enabled
        self.camera_ip_input.setEnabled(not checked)
        self.camera_subnet_input.setEnabled(not checked)
        self.camera_gateway_input.setEnabled(not checked)
        
        if checked:
            # Clear fields when enabling DHCP
            self.camera_ip_input.clear()
            self.camera_subnet_input.setCurrentText("255.255.255.0")
            self.camera_gateway_input.clear()
    
    def _get_eth0_network_info(self):
        """Get network information from eth0 interface"""
        try:
            import netifaces
            if 'eth0' in netifaces.interfaces():
                addrs = netifaces.ifaddresses('eth0')
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get('addr', '')
                        netmask = addr.get('netmask', '255.255.255.0')
                        # Try to get gateway
                        gateway = ''
                        try:
                            gateways = netifaces.gateways()
                            if netifaces.AF_INET in gateways:
                                for gw_info in gateways[netifaces.AF_INET]:
                                    if gw_info[1] == 'eth0':
                                        gateway = gw_info[0]
                                        break
                        except:
                            pass
                        
                        if ip and not ip.startswith('127.'):
                            return {
                                'ip': ip,
                                'subnet': netmask,
                                'gateway': gateway or self._calculate_default_gateway(ip, netmask)
                            }
        except ImportError:
            pass
        except Exception as e:
            print(f"Error getting eth0 network info: {e}")
        
        # Fallback: try socket method
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return {
                'ip': local_ip,
                'subnet': '255.255.255.0',
                'gateway': self._calculate_default_gateway(local_ip, '255.255.255.0')
            }
        except Exception as e:
            print(f"Error getting network info via socket: {e}")
            return None
    
    def _calculate_default_gateway(self, ip: str, subnet: str) -> str:
        """Calculate default gateway (usually .1 of the network)"""
        try:
            ip_parts = ip.split('.')
            if subnet == '255.255.255.0':
                return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
            elif subnet == '255.255.0.0':
                return f"{ip_parts[0]}.{ip_parts[1]}.0.1"
            elif subnet == '255.0.0.0':
                return f"{ip_parts[0]}.0.0.1"
        except:
            pass
        return ""
    
    def _autofill_network_settings(self):
        """Auto-fill network settings from eth0"""
        network_info = self._get_eth0_network_info()
        if network_info:
            self.camera_subnet_input.setCurrentText(network_info['subnet'])
            if network_info['gateway']:
                self.camera_gateway_input.setText(network_info['gateway'])
            
            # Suggest an IP in the same subnet
            if not self.camera_dhcp_checkbox.isChecked():
                suggested_ip = self._suggest_ip_address(network_info['ip'], network_info['subnet'])
                if suggested_ip:
                    self.camera_ip_input.setText(suggested_ip)
            
            QMessageBox.information(self, "Network Settings", 
                                   f"Auto-filled from eth0:\n"
                                   f"Subnet: {network_info['subnet']}\n"
                                   f"Gateway: {network_info['gateway']}")
        else:
            QMessageBox.warning(self, "Error", "Could not detect eth0 network settings")
    
    def _suggest_ip_address(self, current_ip: str, subnet: str) -> str:
        """Suggest an IP address in the same subnet"""
        try:
            ip_parts = current_ip.split('.')
            if subnet == '255.255.255.0':
                # Suggest .100-.200 range
                base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                # Check existing cameras to avoid conflicts
                used_ips = {c.ip_address for c in self.settings.cameras}
                for i in range(100, 201):
                    suggested = f"{base}.{i}"
                    if suggested not in used_ips and suggested != current_ip:
                        return suggested
                # Fallback to .50
                return f"{base}.50"
        except:
            pass
        return ""
    
    def _create_network_management_panel(self) -> QGroupBox:
        """Create network management panel with diagnostics and tools"""
        network_group = QGroupBox("🔧 Network Management")
        network_group.setStyleSheet("""
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
        network_layout = QVBoxLayout(network_group)
        network_layout.setSpacing(12)
        network_layout.setContentsMargins(16, 16, 16, 16)
        
        # Initialize network manager
        self.network_manager = NetworkManager()
        
        # Network info display
        network_info_frame = QFrame()
        network_info_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 6px;
            }
        """)
        network_info_layout = QVBoxLayout(network_info_frame)
        network_info_layout.setContentsMargins(12, 12, 12, 12)
        network_info_layout.setSpacing(6)
        
        info_title = QLabel("Network Interface (eth0)")
        info_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        network_info_layout.addWidget(info_title)
        
        self.network_info_label = QLabel("Loading...")
        self.network_info_label.setStyleSheet("font-size: 11px; color: #888898;")
        self.network_info_label.setWordWrap(True)
        network_info_layout.addWidget(self.network_info_label)
        
        # Update network info
        self._update_network_info_display()
        
        network_layout.addWidget(network_info_frame)
        
        # Diagnostics section
        diagnostics_title = QLabel("Camera Diagnostics")
        diagnostics_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff; margin-top: 8px;")
        network_layout.addWidget(diagnostics_title)
        
        # IP input for diagnostics
        diag_input_layout = QHBoxLayout()
        diag_input_layout.setSpacing(8)
        
        self.diag_ip_input = QLineEdit()
        self.diag_ip_input.setPlaceholderText("Camera IP address")
        self.diag_ip_input.setFixedHeight(40)
        self.diag_ip_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #FF9500;
            }
        """)
        diag_input_layout.addWidget(self.diag_ip_input)
        
        self.run_diagnostics_btn = QPushButton("🔍 Run Diagnostics")
        self.run_diagnostics_btn.setFixedHeight(40)
        self.run_diagnostics_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 6px;
                color: #0a0a0f;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #CC7700;
            }
            QPushButton:disabled {
                background-color: #2a2a38;
                color: #888898;
            }
        """)
        self.run_diagnostics_btn.clicked.connect(self._run_camera_diagnostics)
        diag_input_layout.addWidget(self.run_diagnostics_btn)
        
        network_layout.addLayout(diag_input_layout)
        
        # Diagnostics results display
        self.diagnostics_results = QLabel("Enter IP address and click 'Run Diagnostics'")
        self.diagnostics_results.setStyleSheet("""
            font-size: 11px; 
            color: #888898; 
            padding: 8px;
            background-color: #1a1a24;
            border: 1px solid #2a2a38;
            border-radius: 6px;
        """)
        self.diagnostics_results.setWordWrap(True)
        self.diagnostics_results.setMinimumHeight(80)
        network_layout.addWidget(self.diagnostics_results)
        
        # Port scan section
        port_scan_title = QLabel("Network Port Scan")
        port_scan_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff; margin-top: 8px;")
        network_layout.addWidget(port_scan_title)
        
        port_scan_layout = QHBoxLayout()
        port_scan_layout.setSpacing(8)
        
        # Get base IP for scanning
        network_info = self._get_eth0_network_info()
        base_ip = ""
        if network_info and network_info.get('ip'):
            ip_parts = network_info['ip'].split('.')
            base_ip = '.'.join(ip_parts[:-1])
        
        self.port_scan_base_input = QLineEdit()
        self.port_scan_base_input.setPlaceholderText("192.168.1")
        self.port_scan_base_input.setText(base_ip)
        self.port_scan_base_input.setFixedHeight(40)
        self.port_scan_base_input.setStyleSheet(self.diag_ip_input.styleSheet())
        port_scan_layout.addWidget(self.port_scan_base_input)
        
        self.scan_ports_btn = QPushButton("🔍 Scan Range")
        self.scan_ports_btn.setFixedHeight(40)
        self.scan_ports_btn.setStyleSheet(self.run_diagnostics_btn.styleSheet())
        self.scan_ports_btn.clicked.connect(self._scan_network_range)
        port_scan_layout.addWidget(self.scan_ports_btn)
        
        network_layout.addLayout(port_scan_layout)
        
        # Port scan results
        self.port_scan_results = QLabel("Enter network base IP (e.g., 192.168.1) and click 'Scan Range'")
        self.port_scan_results.setStyleSheet(self.diagnostics_results.styleSheet())
        self.port_scan_results.setWordWrap(True)
        self.port_scan_results.setMinimumHeight(60)
        network_layout.addWidget(self.port_scan_results)
        
        # Backup/Restore section
        backup_title = QLabel("Configuration Backup")
        backup_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff; margin-top: 8px;")
        network_layout.addWidget(backup_title)
        
        backup_layout = QHBoxLayout()
        backup_layout.setSpacing(8)
        
        self.backup_configs_btn = QPushButton("💾 Backup Configs")
        self.backup_configs_btn.setFixedHeight(40)
        self.backup_configs_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 2px solid #3a3a48;
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #FF9500;
                background-color: #3a3a48;
            }
        """)
        self.backup_configs_btn.clicked.connect(self._backup_network_configs)
        backup_layout.addWidget(self.backup_configs_btn)
        
        self.restore_configs_btn = QPushButton("📥 Restore Configs")
        self.restore_configs_btn.setFixedHeight(40)
        self.restore_configs_btn.setStyleSheet(self.backup_configs_btn.styleSheet())
        self.restore_configs_btn.clicked.connect(self._restore_network_configs)
        backup_layout.addWidget(self.restore_configs_btn)
        
        network_layout.addLayout(backup_layout)
        
        return network_group
    
    def _update_network_info_display(self):
        """Update network info display"""
        network_info = self._get_eth0_network_info()
        if network_info:
            info_text = f"IP: {network_info.get('ip', 'Unknown')}\n"
            info_text += f"Subnet: {network_info.get('subnet', 'Unknown')}\n"
            info_text += f"Gateway: {network_info.get('gateway', 'Unknown')}"
            self.network_info_label.setText(info_text)
        else:
            self.network_info_label.setText("Could not detect network settings")
    
    def _run_camera_diagnostics(self):
        """Run diagnostics on a camera IP"""
        ip = self.diag_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter a camera IP address")
            return
        
        if not self._is_valid_ip(ip):
            QMessageBox.warning(self, "Error", "Invalid IP address format")
            return
        
        self.run_diagnostics_btn.setEnabled(False)
        self.run_diagnostics_btn.setText("⏳ Running...")
        self.diagnostics_results.setText("Running diagnostics...")
        self.diagnostics_results.setStyleSheet(self.diagnostics_results.styleSheet().replace("#888898", "#FF9500"))
        
        # Get credentials from form if available
        username = "admin"
        password = "12345"
        if hasattr(self, 'camera_user_input') and self.camera_user_input:
            username = self.camera_user_input.text().strip() or "admin"
        if hasattr(self, 'camera_pass_input') and self.camera_pass_input:
            password = self.camera_pass_input.text().strip() or "12345"
        
        # Run diagnostics in background thread
        def run_diagnostics():
            diagnostics = self.network_manager.run_diagnostics(ip, username, password)
            QTimer.singleShot(0, lambda: self._display_diagnostics_results(diagnostics))
        
        import threading
        thread = threading.Thread(target=run_diagnostics, daemon=True)
        thread.start()
    
    def _display_diagnostics_results(self, diagnostics: NetworkDiagnostics):
        """Display diagnostics results"""
        self.run_diagnostics_btn.setEnabled(True)
        self.run_diagnostics_btn.setText("🔍 Run Diagnostics")
        
        results_text = f"<b>Diagnostics for {diagnostics.ip_address}</b><br><br>"
        
        # Ping results
        if diagnostics.ping_success:
            results_text += f"✅ Ping: {diagnostics.ping_time_ms:.1f} ms<br>"
        else:
            results_text += f"❌ Ping: Failed<br>"
        
        # HTTP results
        if diagnostics.http_reachable:
            status_text = "OK" if diagnostics.http_status_code == 200 else f"Code {diagnostics.http_status_code}"
            results_text += f"✅ HTTP ({status_text}): {diagnostics.http_response_time_ms:.1f} ms<br>"
        else:
            results_text += f"❌ HTTP: Not reachable<br>"
        
        # Port results
        results_text += "<br><b>Ports:</b><br>"
        results_text += f"{'✅' if diagnostics.port_80_open else '❌'} Port 80 (HTTP)<br>"
        results_text += f"{'✅' if diagnostics.port_554_open else '❌'} Port 554 (RTSP)<br>"
        results_text += f"{'✅' if diagnostics.port_10669_open else '❌'} Port 10669 (Panasonic)<br>"
        results_text += f"{'✅' if diagnostics.port_10670_open else '❌'} Port 10670 (Panasonic)<br>"
        
        if diagnostics.error_message:
            results_text += f"<br><span style='color: #ef4444;'>{diagnostics.error_message}</span>"
        
        self.diagnostics_results.setText(results_text)
        self.diagnostics_results.setStyleSheet(self.diagnostics_results.styleSheet().replace("#FF9500", "#888898"))
    
    def _scan_network_range(self):
        """Scan network range for cameras"""
        base_ip = self.port_scan_base_input.text().strip()
        if not base_ip:
            QMessageBox.warning(self, "Error", "Please enter network base IP (e.g., 192.168.1)")
            return
        
        # Validate base IP format
        parts = base_ip.split('.')
        if len(parts) != 3:
            QMessageBox.warning(self, "Error", "Invalid network base IP format. Use format like '192.168.1'")
            return
        
        self.scan_ports_btn.setEnabled(False)
        self.scan_ports_btn.setText("⏳ Scanning...")
        self.port_scan_results.setText("Scanning network range...")
        self.port_scan_results.setStyleSheet(self.port_scan_results.styleSheet().replace("#888898", "#FF9500"))
        
        # Run scan in background thread
        def run_scan():
            results = self.network_manager.scan_network_range(base_ip, start=1, end=254)
            QTimer.singleShot(0, lambda: self._display_port_scan_results(results))
        
        import threading
        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()
    
    def _display_port_scan_results(self, results: List[Dict]):
        """Display port scan results"""
        self.scan_ports_btn.setEnabled(True)
        self.scan_ports_btn.setText("🔍 Scan Range")
        
        if not results:
            self.port_scan_results.setText("No devices found with open ports (80, 554)")
            self.port_scan_results.setStyleSheet(self.port_scan_results.styleSheet().replace("#FF9500", "#888898"))
            return
        
        results_text = f"<b>Found {len(results)} device(s):</b><br><br>"
        for result in results[:10]:  # Show first 10
            ip = result['ip']
            ports = result.get('ports_open', [])
            port_str = ', '.join(map(str, ports))
            results_text += f"✅ {ip} - Ports: {port_str}<br>"
        
        if len(results) > 10:
            results_text += f"<br>... and {len(results) - 10} more"
        
        self.port_scan_results.setText(results_text)
        self.port_scan_results.setStyleSheet(self.port_scan_results.styleSheet().replace("#FF9500", "#888898"))
    
    def _backup_network_configs(self):
        """Backup camera network configurations"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Network Configurations",
            "camera_network_backup.json",
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        success = NetworkManager.backup_network_configs(self.settings.cameras, filepath)
        if success:
            QMessageBox.information(self, "Success", f"Network configurations backed up to:\n{filepath}")
        else:
            QMessageBox.warning(self, "Error", "Failed to backup network configurations")
    
    def _restore_network_configs(self):
        """Restore camera network configurations"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Network Configurations",
            "",
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        backup_data = NetworkManager.restore_network_configs(filepath)
        if not backup_data:
            QMessageBox.warning(self, "Error", "Failed to restore network configurations")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Restore {len(backup_data.get('cameras', []))} camera configuration(s)?\n\n"
            "This will update existing cameras with matching IDs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        restored_count = 0
        for camera_data in backup_data.get('cameras', []):
            camera_id = camera_data.get('id')
            if camera_id:
                camera = self.settings.get_camera(camera_id)
                if camera:
                    # Update network settings
                    camera.ip_address = camera_data.get('ip_address', camera.ip_address)
                    camera.port = camera_data.get('port', camera.port)
                    camera.username = camera_data.get('username', camera.username)
                    camera.password = camera_data.get('password', camera.password)
                    self.settings.update_camera(camera)
                    restored_count += 1
        
        if restored_count > 0:
            self.settings.save()
            self._refresh_camera_list()
            self.settings_changed.emit()
            QMessageBox.information(self, "Success", f"Restored {restored_count} camera configuration(s)")
        else:
            QMessageBox.warning(self, "Warning", "No matching cameras found to restore")
