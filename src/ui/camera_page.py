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
    QComboBox, QStackedWidget, QDialog, QSizePolicy, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient

from ..config.settings import Settings, CameraConfig
from ..camera.discovery import CameraDiscovery, DiscoveredCamera
from ..camera.stream import CameraStream, StreamConfig
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
                background-color: #242430;
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
                background-color: #121218;
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
        add_btn.setToolTip("Add to configured cameras")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 6px;
                color: #121218;
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
        self.delete_confirm_timer = None
        self.is_in_delete_confirm = False
        self.reorder_timer = None
        self.is_being_dragged = False
        self.drag_start_pos = None
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
                background-color: #242430;
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
        # Prevent long names from forcing the whole row/page wider than the window.
        name_label.setWordWrap(False)
        name_label.setMinimumWidth(0)
        name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name_row.addWidget(name_label)
        
        # ATEM input badge
        if self.atem_input > 0:
            atem_badge = QLabel(f"ATEM {self.atem_input}")
            atem_badge.setStyleSheet("""
                QLabel {
                    background-color: #FF9500;
                    color: #121218;
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
        ip_label.setWordWrap(False)
        ip_label.setMinimumWidth(0)
        ip_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info_layout.addWidget(ip_label)
        
        # Connection status text
        self.status_label = QLabel("Status: Unknown")
        self.status_label.setStyleSheet("color: #888898; font-size: 11px;")
        self.status_label.setWordWrap(False)
        self.status_label.setMinimumWidth(0)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, stretch=1)

        # Reorder buttons (hidden by default, shown on hover)
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedSize(30, 40)
        self.up_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.up_btn.clicked.connect(self._move_up)
        self.up_btn.hide()  # Hidden by default
        layout.addWidget(self.up_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedSize(30, 40)
        self.down_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.down_btn.clicked.connect(self._move_down)
        self.down_btn.hide()  # Hidden by default
        layout.addWidget(self.down_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Delete button - centered vertically
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedSize(80, 40)
        self._update_delete_button_style()
        self.delete_btn.setToolTip("Delete this camera")
        self.delete_btn.clicked.connect(self._handle_delete_click)
        layout.addWidget(self.delete_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Edit button - centered vertically
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(80, 40)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 6px;
                color: #121218;
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
                background-color: #242430;
                border: 1px solid #2a2a38;
                border-radius: 10px;
                padding: 0px;
            }
        """)

    def _update_delete_button_style(self):
        """Update delete button appearance based on confirm state"""
        if self.is_in_delete_confirm:
            self.delete_btn.setText("Confirm?")
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b0000;
                    border: 2px solid #ff4444;
                    border-radius: 6px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #a00000;
                }
                QPushButton:pressed {
                    background-color: #600000;
                }
            """)
        else:
            self.delete_btn.setText("Delete")
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    border-radius: 6px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """)

    def _handle_delete_click(self):
        """Handle delete button clicks - two-step confirmation"""
        if self.is_in_delete_confirm:
            # Second click - actually delete
            self._perform_delete()
        else:
            # First click - enter confirm mode
            self.is_in_delete_confirm = True
            self._update_delete_button_style()

            # Auto-revert after 3 seconds
            if self.delete_confirm_timer:
                self.delete_confirm_timer.stop()
            self.delete_confirm_timer = QTimer(self)
            self.delete_confirm_timer.setSingleShot(True)
            self.delete_confirm_timer.timeout.connect(self._cancel_delete_confirm)
            self.delete_confirm_timer.start(3000)

    def _cancel_delete_confirm(self):
        """Cancel delete confirmation and revert button"""
        self.is_in_delete_confirm = False
        self._update_delete_button_style()
        if self.delete_confirm_timer:
            self.delete_confirm_timer.stop()

    def _perform_delete(self):
        """Actually perform the delete operation"""
        # Cancel the timer
        if self.delete_confirm_timer:
            self.delete_confirm_timer.stop()

        # Find the parent camera page and call delete
        parent = self.parent()
        while parent and not hasattr(parent, '_delete_camera'):
            parent = parent.parent()

        if parent and hasattr(parent, '_delete_camera'):
            parent._delete_camera(self.camera.id)

    def mousePressEvent(self, event):
        """Handle mouse press for long press detection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

            # Start long press timer for reordering
            if self.reorder_timer:
                self.reorder_timer.stop()
            self.reorder_timer = QTimer(self)
            self.reorder_timer.setSingleShot(True)
            self.reorder_timer.timeout.connect(self._start_reorder_mode)
            self.reorder_timer.start(500)  # 500ms for long press

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release - cancel long press if released early"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.reorder_timer and self.reorder_timer.isActive():
                # Short press - cancel long press timer
                self.reorder_timer.stop()

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag detection"""
        if self.drag_start_pos and not self.is_being_dragged:
            # Check if moved enough to start dragging
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance > 10:  # 10px threshold
                if self.reorder_timer and self.reorder_timer.isActive():
                    self.reorder_timer.stop()
                self._start_drag_operation()

        super().mouseMoveEvent(event)

    def enterEvent(self, event):
        """Show reorder buttons on hover"""
        self.up_btn.show()
        self.down_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide reorder buttons when not hovering"""
        self.up_btn.hide()
        self.down_btn.hide()
        super().leaveEvent(event)

    def _move_up(self):
        """Move this camera up in the list"""
        parent = self.parent()
        while parent and not hasattr(parent, '_move_camera_up'):
            parent = parent.parent()

        if parent and hasattr(parent, '_move_camera_up'):
            parent._move_camera_up(self.camera.id)

    def _move_down(self):
        """Move this camera down in the list"""
        parent = self.parent()
        while parent and not hasattr(parent, '_move_camera_down'):
            parent = parent.parent()

        if parent and hasattr(parent, '_move_camera_down'):
            parent._move_camera_down(self.camera.id)

    def _start_reorder_mode(self):
        """Enter reorder mode after long press"""
        # Cancel delete confirm if active
        if self.is_in_delete_confirm:
            self._cancel_delete_confirm()

        # Show reorder buttons
        self.up_btn.show()
        self.down_btn.show()

    def _start_drag_operation(self):
        """Start drag operation for reordering"""
        self.is_being_dragged = True
        # For now, just show reorder buttons
        self.up_btn.show()
        self.down_btn.show()

    def _create_demo_thumbnail(self):
        """Create a demo thumbnail image"""
        self._update_thumbnail_image()
    
    def _update_thumbnail_image(self, frame=None):
        """Update thumbnail with camera frame or 'No Connection' message"""
        pixmap = QPixmap(120, 68)
        pixmap.fill(QColor("#242430"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw gradient background
        gradient = QLinearGradient(0, 0, 120, 68)
        gradient.setColorAt(0, QColor("#2a2a38"))
        gradient.setColorAt(1, QColor("#242430"))
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
        self._bottom_sheet_height = 460
        self._bottom_sheet_anim = None
        
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
        """Setup the camera page UI with top submenu + content"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top horizontal submenu (under MainWindow top menu)
        submenu = QFrame()
        submenu.setFixedHeight(60)
        submenu.setStyleSheet("""
            QFrame {
                background-color: #121218;
                border-bottom: 1px solid #2a2a38;
            }
        """)
        submenu_layout = QHBoxLayout(submenu)
        submenu_layout.setContentsMargins(20, 0, 20, 0)
        submenu_layout.setSpacing(0)

        submenu_layout.addStretch()

        buttons_container = QWidget()
        buttons_container.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)

        self.sidebar_buttons = []
        self.configured_badge = None
        self.configured_button = None

        self.submenu_button_group = QButtonGroup(self)
        self.submenu_button_group.setExclusive(True)

        sections = [("📋 Configured", 0), ("🌐 Discover", 1)]
        for text, idx in sections:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(60)
            btn.setMinimumWidth(170)
            btn.setStyleSheet(self._get_sidebar_button_style())
            btn.clicked.connect(lambda checked, i=idx: self._on_section_clicked(i))
            self.submenu_button_group.addButton(btn, idx)
            self.sidebar_buttons.append(btn)
            buttons_layout.addWidget(btn)

            if idx == 0:
                self.configured_button = btn
                # Badge inside the Configured button
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
                badge.hide()
                badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.configured_badge = badge
                QTimer.singleShot(100, self._update_badge_position)

        submenu_layout.addWidget(buttons_container)
        submenu_layout.addStretch()

        main_layout.addWidget(submenu)

        # Right side: content + bottom sheet + OSK slot (like Live bottom panel)
        right = QWidget()
        # Prevent the page from "growing" wider than the app when the bottom sheet / OSK appears.
        right.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        right.setMinimumWidth(0)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #121218;")
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.content_stack.setMinimumWidth(0)
        self.content_stack.addWidget(self._create_configured_content())
        self.content_stack.addWidget(self._create_easyip_tools_content())
        right_layout.addWidget(self.content_stack, 1)

        # Bottom sheet container (shared across tabs)
        self.bottom_sheet = QFrame()
        self.bottom_sheet.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border-top: 1px solid #2a2a38;
            }
        """)
        # Horizontal clamp: don't let minimumSizeHint force wider-than-window layouts.
        self.bottom_sheet.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bottom_sheet.setMinimumWidth(0)
        self.bottom_sheet.setMaximumHeight(0)
        self.bottom_sheet.setMinimumHeight(0)
        self.bottom_sheet.setVisible(False)

        sheet_layout = QVBoxLayout(self.bottom_sheet)
        sheet_layout.setContentsMargins(0, 0, 0, 0)
        sheet_layout.setSpacing(0)

        # Header row (title + close)
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("""
            QFrame {
                background-color: #121218;
                border-bottom: 1px solid #2a2a38;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(12)

        self.bottom_sheet_title = QLabel("Panel")
        self.bottom_sheet_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        header_layout.addWidget(self.bottom_sheet_title)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(44, 44)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover { border-color: #FF9500; color: #FF9500; }
            QPushButton:pressed { border-color: #CC7700; color: #CC7700; }
        """)
        close_btn.clicked.connect(self._close_bottom_sheet)
        header_layout.addWidget(close_btn)

        sheet_layout.addWidget(header)

        # Body stack
        self.bottom_sheet_stack = QStackedWidget()
        self.bottom_sheet_stack.setStyleSheet("QStackedWidget { background: transparent; }")
        sheet_layout.addWidget(self.bottom_sheet_stack, 1)

        # Panel 0: Edit camera form
        self.edit_form_panel = self._create_edit_form_panel()
        self.edit_form_panel.setStyleSheet("QFrame { background: transparent; border: none; }")
        # Make the edit form scrollable so we can shrink the bottom sheet when the OSK is visible
        # (prevents the OSK from being clipped off-screen).
        self.edit_form_scroll = TouchScrollArea()
        self.edit_form_scroll.setWidgetResizable(True)
        self.edit_form_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget { background: transparent; }
        """)
        _edit_wrapper = QWidget()
        _edit_wrapper.setStyleSheet("background: transparent;")
        _ew_layout = QVBoxLayout(_edit_wrapper)
        _ew_layout.setContentsMargins(0, 0, 0, 0)
        _ew_layout.setSpacing(0)
        _ew_layout.addWidget(self.edit_form_panel)
        self.edit_form_scroll.setWidget(_edit_wrapper)
        self.bottom_sheet_stack.addWidget(self.edit_form_scroll)

        # Panel 1: Discover details (placeholder)
        discover_details = QWidget()
        dd_layout = QVBoxLayout(discover_details)
        dd_layout.setContentsMargins(20, 16, 20, 20)
        dd_layout.setSpacing(12)
        dd_label = QLabel("Select a discovered camera to see actions here.")
        dd_label.setStyleSheet("color: #888898; font-size: 13px;")
        dd_layout.addWidget(dd_label)
        dd_layout.addStretch()
        self.bottom_sheet_stack.addWidget(discover_details)

        right_layout.addWidget(self.bottom_sheet, 0)

        # OSK slot (docked keyboard) - keeps bottom sheet visible when typing.
        self.osk_slot = QFrame()
        self.osk_slot.setStyleSheet("background-color: transparent; border: none;")
        # Horizontal clamp (same reasoning as bottom_sheet).
        self.osk_slot.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.osk_slot.setMinimumWidth(0)
        self.osk_slot.setFixedHeight(0)
        right_layout.addWidget(self.osk_slot, 0)

        main_layout.addWidget(right, 1)
        
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
                padding: 0px 16px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #242430;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #FF9500;
                color: #121218;
                font-weight: 600;
            }
            QPushButton:pressed {
                background-color: #CC7700;
            }
        """
    
    def _update_badge_position(self):
        """Update badge position on Configured button"""
        if self.configured_badge and self.configured_button:
            btn_width = self.configured_button.width()
            if btn_width > 0:
                # Top-right corner inside the horizontal button
                badge_x = btn_width - 36
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
        
        # Close bottom sheet when switching sections (like Live)
        self._close_bottom_sheet()
        self._editing_camera_id = None

    def _create_configured_content(self) -> QWidget:
        """Configured cameras list (edit opens bottom sheet)"""
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        # Make configured list panel app-wide (no extra outer left/right inset).
        # The panel itself already has its own internal padding.
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(12)
        
        panel = self._create_camera_list_panel(compact=True)
        layout.addWidget(panel, 1)
        
        return wrapper

    def _open_bottom_sheet(self, title: str, panel_index: int = 0):
        """Open the shared bottom sheet (slide up)."""
        if not hasattr(self, "bottom_sheet") or self.bottom_sheet is None:
            return
        try:
            self.bottom_sheet_title.setText(title)
            self.bottom_sheet_stack.setCurrentIndex(panel_index)
            self.bottom_sheet.setVisible(True)

            if self._bottom_sheet_anim is not None:
                try:
                    self._bottom_sheet_anim.stop()
                except Exception:
                    pass

            start_h = int(self.bottom_sheet.maximumHeight())
            end_h = int(min(self._bottom_sheet_height, self._max_bottom_sheet_height()))
            self._bottom_sheet_anim = QPropertyAnimation(self.bottom_sheet, b"maximumHeight")
            self._bottom_sheet_anim.setDuration(220)
            self._bottom_sheet_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._bottom_sheet_anim.setStartValue(start_h)
            self._bottom_sheet_anim.setEndValue(end_h)
            self._bottom_sheet_anim.start()

            self.bottom_sheet.setMinimumHeight(end_h)
        except Exception as e:
            print(f"Error opening bottom sheet: {e}")
            try:
                self.bottom_sheet.setVisible(True)
                end_h = int(min(self._bottom_sheet_height, self._max_bottom_sheet_height()))
                self.bottom_sheet.setMaximumHeight(end_h)
                self.bottom_sheet.setMinimumHeight(end_h)
            except Exception:
                pass

    def _close_bottom_sheet(self):
        """Close the shared bottom sheet (slide down)."""
        if not hasattr(self, "bottom_sheet") or self.bottom_sheet is None:
            return
        try:
            if self._bottom_sheet_anim is not None:
                try:
                    self._bottom_sheet_anim.stop()
                except Exception:
                    pass

            start_h = int(self.bottom_sheet.maximumHeight())
            self._bottom_sheet_anim = QPropertyAnimation(self.bottom_sheet, b"maximumHeight")
            self._bottom_sheet_anim.setDuration(180)
            self._bottom_sheet_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._bottom_sheet_anim.setStartValue(start_h)
            self._bottom_sheet_anim.setEndValue(0)

            def _after():
                try:
                    self.bottom_sheet.setVisible(False)
                    self.bottom_sheet.setMinimumHeight(0)
                except Exception:
                    pass

            self._bottom_sheet_anim.finished.connect(_after)
            self._bottom_sheet_anim.start()
            self.bottom_sheet.setMinimumHeight(0)
        except Exception as e:
            print(f"Error closing bottom sheet: {e}")
            try:
                self.bottom_sheet.setVisible(False)
                self.bottom_sheet.setMaximumHeight(0)
                self.bottom_sheet.setMinimumHeight(0)
            except Exception:
                pass

    def _max_bottom_sheet_height(self) -> int:
        """Compute the maximum bottom-sheet height while keeping the docked OSK fully visible."""
        try:
            # 'right' container height (bottom_sheet + osk_slot live inside it)
            parent = self.bottom_sheet.parentWidget() if hasattr(self, "bottom_sheet") else None
            available = int(parent.height()) if parent is not None else int(self.height())
        except Exception:
            available = int(self.height())

        try:
            osk_h = int(self.osk_slot.height()) if hasattr(self, "osk_slot") and self.osk_slot is not None else 0
        except Exception:
            osk_h = 0

        # Leave no fixed requirement for content_stack (it can shrink); just ensure fixed regions fit.
        return max(0, available - osk_h)

    def adjust_bottom_sheet_for_osk(self):
        """Clamp the open bottom-sheet height after OSK docking changes."""
        try:
            if not hasattr(self, "bottom_sheet") or self.bottom_sheet is None:
                return
            if not self.bottom_sheet.isVisible():
                return
            max_h = int(self._max_bottom_sheet_height())
            cur = int(self.bottom_sheet.maximumHeight())
            new_h = min(cur if cur > 0 else int(self._bottom_sheet_height), max_h)
            self.bottom_sheet.setMaximumHeight(new_h)
            self.bottom_sheet.setMinimumHeight(new_h)
        except Exception:
            pass
    
    def _create_easyip_tools_content(self) -> QWidget:
        """Discover page - Main screen with camera list, Identify, and Network Settings"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(20, 20, 20, 20)
        wrapper_layout.setSpacing(20)
        
        # Header
        header = QLabel("Discover")
        header.setStyleSheet("font-size: 24px; font-weight: 600; color: #ffffff;")
        wrapper_layout.addWidget(header)
        
        # Search and refresh controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align to top
        
        # Search input
        self.easyip_search_input = QLineEdit()
        self.easyip_search_input.setPlaceholderText("Search cameras...")
        self.easyip_search_input.setFixedHeight(44)
        self.easyip_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #242430;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #FFFFFF;
                margin: 0px;
            }
            QLineEdit:focus {
                border-color: #FF9500;
            }
        """)
        self.easyip_search_input.textChanged.connect(self._filter_easyip_cameras)
        controls_layout.addWidget(self.easyip_search_input, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Refresh button
        self.easyip_refresh_btn = QPushButton("🔍 Search")
        self.easyip_refresh_btn.setFixedHeight(44)
        self.easyip_refresh_btn.setFixedWidth(150)  # Fixed width, 50px wider than default
        self.easyip_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: 2px solid #FF9500;
                border-radius: 8px;
                color: #121218;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 12px;
                margin: 0px;
                min-width: 150px;
                max-width: 150px;
                min-height: 44px;
                max-height: 44px;
            }
            QPushButton:hover {
                background-color: #CC7700;
                border: 2px solid #CC7700;
                min-width: 150px;
                max-width: 150px;
                min-height: 44px;
                max-height: 44px;
            }
            QPushButton:pressed {
                background-color: #CC7700;
                border: 2px solid #CC7700;
                min-width: 150px;
                max-width: 150px;
                min-height: 44px;
                max-height: 44px;
            }
            QPushButton:disabled {
                background-color: #2a2a38;
                border: 2px solid #2a2a38;
                color: #888898;
                min-width: 150px;
                max-width: 150px;
                min-height: 44px;
                max-height: 44px;
            }
        """)
        self.easyip_refresh_btn.clicked.connect(self._easyip_discover_cameras)
        controls_layout.addWidget(self.easyip_refresh_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        wrapper_layout.addLayout(controls_layout)
        
        # Status label
        self.easyip_status_label = QLabel("Ready to search for cameras")
        self.easyip_status_label.setStyleSheet("color: #888898; font-size: 12px; padding: 4px;")
        wrapper_layout.addWidget(self.easyip_status_label)
        
        # Progress bar
        self.easyip_progress = QProgressBar()
        self.easyip_progress.setRange(0, 100)
        self.easyip_progress.setValue(0)
        self.easyip_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2a2a38;
                border-radius: 4px;
                text-align: center;
                background-color: #242430;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #FF9500;
                border-radius: 3px;
            }
        """)
        self.easyip_progress.hide()
        wrapper_layout.addWidget(self.easyip_progress)
        
        # Camera list scroll area
        camera_scroll = TouchScrollArea()
        camera_scroll.setWidgetResizable(True)
        camera_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        
        # Container for camera cards
        self.easyip_camera_container = QWidget()
        self.easyip_camera_layout = QVBoxLayout(self.easyip_camera_container)
        self.easyip_camera_layout.setSpacing(12)
        self.easyip_camera_layout.setContentsMargins(12, 12, 12, 12)
        self.easyip_camera_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Empty state
        self.easyip_empty_label = QLabel("No cameras discovered yet.\nClick 'Search' to find Panasonic cameras.")
        self.easyip_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.easyip_empty_label.setStyleSheet("color: #666676; font-size: 14px; padding: 40px;")
        self.easyip_empty_label.setWordWrap(True)
        self.easyip_camera_layout.addWidget(self.easyip_empty_label)
        
        camera_scroll.setWidget(self.easyip_camera_container)
        wrapper_layout.addWidget(camera_scroll, stretch=1)
        
        # Initialize EasyIP discovery state
        self._easyip_discovered_cameras = []
        self._easyip_camera_cards = {}
        self._easyip_discovery_worker = None
        
        return wrapper
    
    def _easyip_discover_cameras(self):
        """Discover cameras for Discover page"""
        if self._easyip_discovery_worker and self._easyip_discovery_worker.isRunning():
            return
        
        # Clear UI
        for card in list(self._easyip_camera_cards.values()):
            card.deleteLater()
        self._easyip_camera_cards.clear()
        self._easyip_discovered_cameras = []
        
        # Show empty state
        self.easyip_empty_label.show()
        self.easyip_empty_label.setText("🔍 Searching network for Panasonic cameras...")
        self.easyip_empty_label.setStyleSheet("color: #FF9500; font-size: 14px; padding: 40px;")
        
        # Update UI
        self.easyip_refresh_btn.setEnabled(False)
        self.easyip_refresh_btn.setText("⏳ Scanning...")
        self.easyip_status_label.setText("🔍 Searching network for Panasonic cameras...")
        self.easyip_status_label.setStyleSheet("color: #FF9500; font-size: 12px; padding: 4px;")
        self.easyip_progress.show()
        self.easyip_progress.setValue(0)
        
        # Get eth0 IP for discovery
        network_info = self._get_eth0_network_info()
        eth0_ip = network_info.get('ip') if network_info else None
        
        # Create and start worker thread
        self._easyip_discovery_worker = DiscoveryWorker(adapter_ip=eth0_ip)
        self._easyip_discovery_worker.camera_found.connect(self._on_easyip_camera_discovered)
        self._easyip_discovery_worker.progress.connect(self._on_easyip_discovery_progress)
        self._easyip_discovery_worker.progress_value.connect(self.easyip_progress.setValue)
        self._easyip_discovery_worker.finished_signal.connect(self._on_easyip_discovery_finished)
        self._easyip_discovery_worker.start()
    
    @pyqtSlot(object)
    def _on_easyip_camera_discovered(self, camera: DiscoveredCamera):
        """Handle discovered camera for Discover page"""
        if camera.ip_address in self._easyip_camera_cards:
            return
        
        # Hide empty state when first camera found
        if len(self._easyip_discovered_cameras) == 0:
            self.easyip_empty_label.hide()
        
        self._easyip_discovered_cameras.append(camera)
        
        # Create card with network info
        network_info = self._get_eth0_network_info()
        card = DiscoveredCameraCard(camera, network_info=network_info)
        card.identify_clicked.connect(self._on_easyip_identify_camera)
        card.fix_network_clicked.connect(self._on_easyip_fix_network)
        card.add_clicked.connect(self._on_easyip_add_camera)
        
        self._easyip_camera_cards[camera.ip_address] = card
        
        # Add to layout
        insert_index = self.easyip_camera_layout.indexOf(self.easyip_empty_label)
        if insert_index >= 0:
            self.easyip_camera_layout.insertWidget(insert_index, card)
        else:
            self.easyip_camera_layout.addWidget(card)
        
        # Fetch thumbnail
        self._fetch_discovery_thumbnail(camera.ip_address, card)
        
        # Update status
        count = len(self._easyip_discovered_cameras)
        self.easyip_status_label.setText(f"✅ Found {count} camera(s)...")
        self.easyip_status_label.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
    
    @pyqtSlot(str)
    def _on_easyip_discovery_progress(self, message: str):
        """Handle progress update for EasyIP discovery"""
        self.easyip_status_label.setText(message)
        QApplication.processEvents()
    
    @pyqtSlot(int)
    def _on_easyip_discovery_finished(self, count: int):
        """Handle EasyIP discovery completion"""
        self.easyip_refresh_btn.setEnabled(True)
        self.easyip_refresh_btn.setText("🔍 Search Network")
        self.easyip_progress.setValue(100)
        QTimer.singleShot(1000, lambda: self.easyip_progress.hide())
        
        if count == 0:
            self.easyip_status_label.setText("❌ No cameras found")
            self.easyip_status_label.setStyleSheet("color: #ef4444; font-size: 12px; padding: 4px;")
            self.easyip_empty_label.show()
            self.easyip_empty_label.setText(
                "❌ No Panasonic cameras found on network.\n\n"
                "Troubleshooting tips:\n"
                "• Ensure cameras are on the same network\n"
                "• Check firewall settings\n"
                "• Verify cameras support Panasonic Easy IP protocol"
            )
            self.easyip_empty_label.setStyleSheet("color: #ef4444; font-size: 14px; padding: 40px;")
        else:
            self.easyip_status_label.setText(f"✅ Discovery complete: Found {count} camera(s)")
            self.easyip_status_label.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
    
    def _on_easyip_identify_camera(self, ip_address: str):
        """Handle identify camera in Discover page"""
        from src.camera.discovery import CameraDiscovery
        
        # Get credentials - try from configured cameras first
        username = "admin"
        password = "12345"
        
        # Check if camera is configured
        for camera in self.settings.cameras:
            if camera.ip_address == ip_address:
                username = camera.username
                password = camera.password
                break
        
        # Update status
        self.easyip_status_label.setText(f"💡 Identifying camera at {ip_address}...")
        self.easyip_status_label.setStyleSheet("color: #eab308; font-size: 12px; padding: 4px;")
        
        # Run identify in background
        def identify_task():
            success = CameraDiscovery.identify_camera(ip_address, username, password, duration=5)
            return success
        
        def on_identify_complete(future):
            try:
                success = future.result()
                if success:
                    QTimer.singleShot(0, lambda: self._show_easyip_identify_result(ip_address, True))
                else:
                    QTimer.singleShot(0, lambda: self._show_easyip_identify_result(ip_address, False))
            except:
                QTimer.singleShot(0, lambda: self._show_easyip_identify_result(ip_address, False))
        
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(identify_task)
        future.add_done_callback(on_identify_complete)
    
    def _show_easyip_identify_result(self, ip_address: str, success: bool):
        """Show identify result for EasyIP Tools"""
        if success:
            self.easyip_status_label.setText(f"💡 Camera {ip_address} LED is blinking for 5 seconds")
            self.easyip_status_label.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
        else:
            self.easyip_status_label.setText(f"⚠️ Could not identify camera {ip_address}")
            self.easyip_status_label.setStyleSheet("color: #f97316; font-size: 12px; padding: 4px;")
        
        # Reset status after delay
        QTimer.singleShot(6000, self._reset_easyip_status)
    
    def _on_easyip_fix_network(self, camera: DiscoveredCamera):
        """Handle network settings in Discover page"""
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
            # Network was changed, refresh discovery after delay
            QTimer.singleShot(2000, self._easyip_discover_cameras)
    
    @pyqtSlot(object)
    def _on_easyip_add_camera(self, camera: DiscoveredCamera):
        """Add discovered camera to configured cameras list"""
        # Check if camera already exists
        for existing_camera in self.settings.cameras:
            if existing_camera.ip_address == camera.ip_address:
                QMessageBox.information(
                    self,
                    "Camera Already Added",
                    f"Camera at {camera.ip_address} is already in your configured list."
                )
                return
        
        # Check maximum limit
        if len(self.settings.cameras) >= 30:
            QMessageBox.warning(self, "Error", "Maximum 30 cameras allowed")
            return
        
        # Generate new ID
        existing_ids = [c.id for c in self.settings.cameras]
        new_id = 1
        while new_id in existing_ids:
            new_id += 1
        
        # Create camera config with default values
        camera_name = camera.name or camera.model or f"Camera ({camera.ip_address})"
        new_camera = CameraConfig(
            id=new_id,
            name=camera_name,
            ip_address=camera.ip_address,
            port=80,  # Default port
            username="admin",  # Default username
            password="12345"  # Default password
        )
        
        # Add to settings
        self.settings.add_camera(new_camera)
        self.settings.save()
        
        # Refresh camera list and update badge
        self._refresh_camera_list()
        self._update_configured_badge()
        self.settings_changed.emit()
        
        # Show success message
        QMessageBox.information(
            self,
            "Camera Added",
            f"Camera '{camera_name}' has been added to your configured list.\n\n"
            f"You can now switch to it on the live page."
        )
    
    def _reset_easyip_status(self):
        """Reset EasyIP status to default"""
        count = len(self._easyip_discovered_cameras)
        if count > 0:
            self.easyip_status_label.setText(f"✅ {count} camera(s) found")
            self.easyip_status_label.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
        else:
            self.easyip_status_label.setText("Ready to search for cameras")
            self.easyip_status_label.setStyleSheet("color: #888898; font-size: 12px; padding: 4px;")
    
    def _filter_easyip_cameras(self, search_text: str):
        """Filter EasyIP camera list by search text"""
        search_lower = search_text.lower()
        visible_count = 0
        
        for ip, card in self._easyip_camera_cards.items():
            camera = None
            for cam in self._easyip_discovered_cameras:
                if cam.ip_address == ip:
                    camera = cam
                    break
            
            if not camera:
                continue
            
            # Check if matches search
            matches = (
                search_lower in camera.ip_address.lower() or
                search_lower in (camera.name or "").lower() or
                search_lower in (camera.model or "").lower() or
                search_lower in (camera.mac_address or "").lower()
            )
            
            card.setVisible(matches)
            if matches:
                visible_count += 1
        
        # Show/hide empty state
        if visible_count == 0 and search_text:
            self.easyip_empty_label.setText(f"No cameras match '{search_text}'")
            self.easyip_empty_label.show()
        else:
            self.easyip_empty_label.hide()
    
    def _create_edit_form_panel(self) -> QWidget:
        """Create edit form panel for bottom sheet (2-column layout)."""
        panel = QFrame()
        # Panel itself is inside the bottom sheet; keep it transparent to avoid double borders.
        panel.setStyleSheet("QFrame { background: transparent; border: none; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        label_style = "color: #ffffff; font-size: 13px; font-weight: 500; border: none;"
        input_style = """
            QLineEdit {
                background-color: #242430;
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
        """
        spin_style = """
            QSpinBox {
                background-color: #242430;
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
        """
        combo_style = """
            QComboBox {
                background-color: #242430;
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
        """

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        # Row 0: Name
        name_label = QLabel("Name")
        name_label.setStyleSheet(label_style)
        self.edit_name_input = QLineEdit()
        self.edit_name_input.setStyleSheet(input_style)
        grid.addWidget(name_label, 0, 0)
        grid.addWidget(self.edit_name_input, 0, 1)

        # Row 1: IP
        ip_label = QLabel("IP")
        ip_label.setStyleSheet(label_style)
        self.edit_ip_input = QLineEdit()
        self.edit_ip_input.setStyleSheet(input_style)
        grid.addWidget(ip_label, 1, 0)
        grid.addWidget(self.edit_ip_input, 1, 1)

        # Row 2: Port
        port_label = QLabel("Port")
        port_label.setStyleSheet(label_style)
        self.edit_port_input = QSpinBox()
        self.edit_port_input.setRange(1, 65535)
        self.edit_port_input.setValue(80)
        self.edit_port_input.setStyleSheet(spin_style)
        grid.addWidget(port_label, 2, 0)
        grid.addWidget(self.edit_port_input, 2, 1)

        # Row 3: Username
        user_label = QLabel("User")
        user_label.setStyleSheet(label_style)
        self.edit_user_input = QLineEdit()
        self.edit_user_input.setStyleSheet(input_style)
        self.edit_user_input.setText("admin")
        grid.addWidget(user_label, 3, 0)
        grid.addWidget(self.edit_user_input, 3, 1)

        # Row 4: Password
        pass_label = QLabel("Pass")
        pass_label.setStyleSheet(label_style)
        self.edit_pass_input = QLineEdit()
        self.edit_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass_input.setStyleSheet(input_style)
        self.edit_pass_input.setText("12345")
        grid.addWidget(pass_label, 4, 0)
        grid.addWidget(self.edit_pass_input, 4, 1)

        # Row 5: ATEM
        atem_label = QLabel("ATEM")
        atem_label.setStyleSheet(label_style)
        self.edit_atem_combo = QComboBox()
        self.edit_atem_combo.addItem("No ATEM mapping", 0)
        for i in range(1, 21):
            self.edit_atem_combo.addItem(f"Input {i}", i)
        self.edit_atem_combo.setStyleSheet(combo_style)
        grid.addWidget(atem_label, 5, 0)
        grid.addWidget(self.edit_atem_combo, 5, 1)

        layout.addLayout(grid)
        layout.addStretch(1)
        
        # Buttons + save progress
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
                color: #121218;
            }
        """)
        cancel_btn.clicked.connect(self._cancel_inline_edit)
        btn_layout.addWidget(cancel_btn)
        
        self.edit_save_btn = QPushButton("Save Changes")
        self.edit_save_btn.setFixedHeight(48)
        self.edit_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9500;
                border: none;
                border-radius: 8px;
                color: #121218;
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
        self.edit_save_btn.clicked.connect(self._save_inline_edit)

        # Small indeterminate progress bar shown while saving (keeps UI clean).
        self.edit_save_progress = QProgressBar()
        self.edit_save_progress.setRange(0, 0)
        self.edit_save_progress.setFixedHeight(6)
        self.edit_save_progress.setTextVisible(False)
        self.edit_save_progress.setVisible(False)
        self.edit_save_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #2a2a38;
            }
            QProgressBar::chunk {
                background-color: #FF9500;
                border-radius: 3px;
            }
        """)

        save_container = QWidget()
        save_container.setStyleSheet("background: transparent;")
        save_container_layout = QVBoxLayout(save_container)
        save_container_layout.setContentsMargins(0, 0, 0, 0)
        save_container_layout.setSpacing(6)
        save_container_layout.addWidget(self.edit_save_btn)
        save_container_layout.addWidget(self.edit_save_progress)
        btn_layout.addWidget(save_container)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _cancel_inline_edit(self):
        """Cancel inline editing"""
        self._editing_camera_id = None
        self._close_bottom_sheet()

    def _show_toast(self, message: str, duration: int = 1800, error: bool = False):
        """Show an in-app toast via MainWindow if available (non-blocking)."""
        try:
            w = self
            while w is not None:
                toast = getattr(w, "toast", None)
                if toast is not None and hasattr(toast, "show_message"):
                    toast.show_message(message, duration=duration, error=error)
                    return
                w = w.parent()
        except Exception:
            pass
    
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
            self._show_toast("Name and IP address are required", duration=2200, error=True)
            return

        # Begin saving UI (button progress) and defer the blocking save to next tick
        # so Qt can repaint.
        self._set_inline_save_in_progress(True)
        atem_input = self.edit_atem_combo.currentData()
        QTimer.singleShot(0, lambda: self._do_save_inline_edit(
            name=name,
            ip=ip,
            port=port,
            username=username,
            password=password,
            atem_input=atem_input,
        ))
        return

    def _set_inline_save_in_progress(self, in_progress: bool):
        try:
            btn = getattr(self, "edit_save_btn", None)
            pb = getattr(self, "edit_save_progress", None)
            if btn is not None:
                btn.setEnabled(not in_progress)
                btn.setText("Saving..." if in_progress else "Save Changes")
            if pb is not None:
                pb.setVisible(bool(in_progress))
        except Exception:
            pass

    def _do_save_inline_edit(self, *, name: str, ip: str, port: int, username: str, password: str, atem_input: int):
        """Perform the actual save (may be slow), with error handling."""
        try:
            camera = self.settings.get_camera(self._editing_camera_id)
            if not camera:
                raise RuntimeError("Camera not found")

            # Update camera
            camera.name = name
            camera.ip_address = ip
            camera.port = port
            camera.username = username
            camera.password = password

            self.settings.update_camera(camera)

            # Update ATEM mapping
            if atem_input and atem_input > 0:
                self.settings.atem.input_mapping[str(camera.id)] = atem_input
            elif str(camera.id) in self.settings.atem.input_mapping:
                del self.settings.atem.input_mapping[str(camera.id)]

            self.settings.save()

            # Close panel immediately after success
            self._editing_camera_id = None
            self.settings_changed.emit()
            self._close_bottom_sheet()
            QTimer.singleShot(0, self._refresh_camera_list)
            self._show_toast(f"Saved: {name}", duration=1800, error=False)
        except Exception as e:
            self._show_toast(f"Save failed: {e}", duration=2600, error=True)
        finally:
            self._set_inline_save_in_progress(False)
    
    def _create_camera_list_panel(self, compact: bool = False) -> QWidget:
        """Create camera list panel with search and bulk operations.
        
        Args:
            compact: when True, show a simple edit column header (configured page).
        """
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
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
                background-color: #242430;
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
                background-color: #242430;
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
    
    def _edit_camera(self, camera_id: int):
        """Edit existing camera - show inline edit form"""
        camera = self.settings.get_camera(camera_id)
        if not camera:
            return
        
        self._editing_camera_id = camera_id
        
        # Switch to Configured page if not already there
        if self.content_stack.currentIndex() != 0:
            self._on_section_clicked(0)
        
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
            
            # Show bottom sheet
            self._open_bottom_sheet("Edit Camera", panel_index=0)

    def _delete_camera(self, camera_id: int):
        """Delete a camera from the configured list"""
        camera = self.settings.get_camera(camera_id)
        if not camera:
            return

        # Remove from settings
        self.settings.cameras = [c for c in self.settings.cameras if c.id != camera_id]

        # Remove from ATEM mapping if exists
        if str(camera_id) in self.settings.atem.input_mapping:
            del self.settings.atem.input_mapping[str(camera_id)]

        # Save settings
        self.settings.save()

        # Refresh camera list
        self._refresh_camera_list()

        # Refresh camera buttons in main window for instant feedback
        main_window = self.window()
        if main_window and hasattr(main_window, '_update_camera_buttons'):
            main_window._update_camera_buttons()

        # Show success message
        if hasattr(self, 'toast') and self.toast:
            self.toast.show_message(f"Deleted camera: {camera.name}", duration=2000)

    def _move_camera_up(self, camera_id: int):
        """Move camera up in the list"""
        camera_index = None
        for i, cam in enumerate(self.settings.cameras):
            if cam.id == camera_id:
                camera_index = i
                break

        if camera_index is not None and camera_index > 0:
            # Swap with previous camera
            self.settings.cameras[camera_index], self.settings.cameras[camera_index - 1] = \
                self.settings.cameras[camera_index - 1], self.settings.cameras[camera_index]

            # Save and refresh
            self.settings.save()
            self._refresh_camera_list()

            # Refresh camera buttons in main window for instant feedback
            main_window = self.window()
            if main_window and hasattr(main_window, '_update_camera_buttons'):
                main_window._update_camera_buttons()

    def _move_camera_down(self, camera_id: int):
        """Move camera down in the list"""
        camera_index = None
        for i, cam in enumerate(self.settings.cameras):
            if cam.id == camera_id:
                camera_index = i
                break

        if camera_index is not None and camera_index < len(self.settings.cameras) - 1:
            # Swap with next camera
            self.settings.cameras[camera_index], self.settings.cameras[camera_index + 1] = \
                self.settings.cameras[camera_index + 1], self.settings.cameras[camera_index]

            # Save and refresh
            self.settings.save()
            self._refresh_camera_list()

            # Refresh camera buttons in main window for instant feedback
            main_window = self.window()
            if main_window and hasattr(main_window, '_update_camera_buttons'):
                main_window._update_camera_buttons()

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
    
