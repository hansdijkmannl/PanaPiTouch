"""
Settings Page

Configuration for cameras and ATEM connection.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox,
    QGroupBox, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QIntValidator

from ..config.settings import Settings, CameraConfig, ATEMConfig
from ..camera.discovery import CameraDiscovery, DiscoveredCamera


class DiscoveryWorker(QThread):
    """Worker thread for Panasonic camera discovery"""
    camera_found = pyqtSignal(object)  # DiscoveredCamera
    progress = pyqtSignal(str)
    finished_signal = pyqtSignal(int)  # Total count
    
    def __init__(self):
        super().__init__()
        self.discovery = CameraDiscovery()
    
    def run(self):
        """Run Panasonic UDP discovery in background thread"""
        self.discovery.set_progress_callback(self._on_progress)
        cameras = self.discovery.discover()
        
        for cam in cameras:
            self.camera_found.emit(cam)
        
        self.finished_signal.emit(len(cameras))
    
    def _on_progress(self, message: str):
        """Handle progress updates"""
        self.progress.emit(message)


class CameraListItem(QFrame):
    """Custom widget for camera list items"""
    
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    
    def __init__(self, camera: CameraConfig, parent=None):
        super().__init__(parent)
        self.camera = camera
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Camera info
        info_layout = QVBoxLayout()
        
        name_label = QLabel(f"<b>{self.camera.name}</b>")
        name_label.setStyleSheet("font-size: 15px;")
        
        ip_label = QLabel(f"{self.camera.ip_address}:{self.camera.port}")
        ip_label.setStyleSheet("color: #888898; font-size: 13px;")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(ip_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(80, 40)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.camera.id))
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(80, 40)
        delete_btn.setStyleSheet("QPushButton { color: #ef4444; }")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.camera.id))
        
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        self.setStyleSheet("""
            CameraListItem {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
            CameraListItem:hover {
                background-color: #22222e;
            }
        """)


class SettingsPage(QWidget):
    """
    Settings page for camera and ATEM configuration.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._editing_camera_id = None
        self._discovery_worker = None
        self._discovered_cameras = []
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup the settings page UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Left panel - Camera settings
        left_panel = self._create_camera_panel()
        main_layout.addWidget(left_panel, stretch=2)
        
        # Right panel - ATEM settings
        right_panel = self._create_atem_panel()
        main_layout.addWidget(right_panel, stretch=1)
    
    def _create_camera_panel(self) -> QWidget:
        """Create camera configuration panel"""
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
        
        # Header
        header = QLabel("Camera Configuration")
        header.setStyleSheet("font-size: 20px; font-weight: 700; border: none;")
        layout.addWidget(header)
        
        # Discovery section
        discovery_group = QGroupBox("Discover Cameras (Panasonic Easy IP)")
        discovery_layout = QVBoxLayout(discovery_group)
        
        # Scan button
        self.discover_btn = QPushButton("🔍  Scan Network for Panasonic PTZ Cameras")
        self.discover_btn.setFixedHeight(50)
        self.discover_btn.clicked.connect(self._discover_cameras)
        discovery_layout.addWidget(self.discover_btn)
        
        # Status label
        self.discovery_status = QLabel("Ready to scan")
        self.discovery_status.setStyleSheet("color: #888898; font-size: 12px; padding: 4px;")
        discovery_layout.addWidget(self.discovery_status)
        
        self.discovered_list = QListWidget()
        self.discovered_list.setFixedHeight(120)
        self.discovered_list.itemDoubleClicked.connect(self._add_discovered_camera)
        discovery_layout.addWidget(self.discovered_list)
        
        add_discovered_btn = QPushButton("Add Selected Camera")
        add_discovered_btn.clicked.connect(self._add_selected_discovered)
        discovery_layout.addWidget(add_discovered_btn)
        
        layout.addWidget(discovery_group)
        
        # Horizontal layout for Manual add + Camera list side by side
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        
        # Manual add section (left side)
        manual_group = QGroupBox("Add Camera Manually")
        manual_layout = QGridLayout(manual_group)
        manual_layout.setSpacing(10)
        
        # Name
        manual_layout.addWidget(QLabel("Name:"), 0, 0)
        self.camera_name_input = QLineEdit()
        self.camera_name_input.setPlaceholderText("Camera 1")
        manual_layout.addWidget(self.camera_name_input, 0, 1)
        
        # IP Address
        manual_layout.addWidget(QLabel("IP Address:"), 1, 0)
        self.camera_ip_input = QLineEdit()
        self.camera_ip_input.setPlaceholderText("192.168.1.100")
        manual_layout.addWidget(self.camera_ip_input, 1, 1)
        
        # Username
        manual_layout.addWidget(QLabel("Username:"), 2, 0)
        self.camera_user_input = QLineEdit()
        self.camera_user_input.setPlaceholderText("admin")
        manual_layout.addWidget(self.camera_user_input, 2, 1)
        
        # Password
        manual_layout.addWidget(QLabel("Password:"), 3, 0)
        self.camera_pass_input = QLineEdit()
        self.camera_pass_input.setPlaceholderText("admin")
        self.camera_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        manual_layout.addWidget(self.camera_pass_input, 3, 1)
        
        # ATEM Input mapping
        manual_layout.addWidget(QLabel("ATEM Input:"), 4, 0)
        self.camera_atem_input = QSpinBox()
        self.camera_atem_input.setRange(0, 20)
        self.camera_atem_input.setValue(0)
        self.camera_atem_input.setSpecialValueText("None")
        manual_layout.addWidget(self.camera_atem_input, 4, 1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.test_camera_btn = QPushButton("Test")
        self.test_camera_btn.clicked.connect(self._test_camera)
        btn_layout.addWidget(self.test_camera_btn)
        
        self.save_camera_btn = QPushButton("Save")
        self.save_camera_btn.clicked.connect(self._save_camera)
        self.save_camera_btn.setStyleSheet("QPushButton { background-color: #00b4d8; color: #0a0a0f; }")
        btn_layout.addWidget(self.save_camera_btn)
        
        self.cancel_edit_btn = QPushButton("Cancel")
        self.cancel_edit_btn.clicked.connect(self._cancel_edit)
        self.cancel_edit_btn.hide()
        btn_layout.addWidget(self.cancel_edit_btn)
        
        manual_layout.addLayout(btn_layout, 5, 0, 1, 2)
        
        bottom_row.addWidget(manual_group, stretch=1)
        
        # Camera list (right side)
        list_group = QGroupBox(f"Configured Cameras (0/10)")
        self.camera_list_group = list_group
        list_layout = QVBoxLayout(list_group)
        
        self.camera_scroll = QScrollArea()
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.camera_list_widget = QWidget()
        self.camera_list_layout = QVBoxLayout(self.camera_list_widget)
        self.camera_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.camera_list_layout.setSpacing(8)
        
        self.camera_scroll.setWidget(self.camera_list_widget)
        list_layout.addWidget(self.camera_scroll)
        
        bottom_row.addWidget(list_group, stretch=1)
        
        layout.addLayout(bottom_row, stretch=1)
        
        return panel
    
    def _create_atem_panel(self) -> QWidget:
        """Create ATEM configuration panel"""
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
        
        # Header
        header = QLabel("ATEM Switcher")
        header.setStyleSheet("font-size: 20px; font-weight: 700; border: none;")
        layout.addWidget(header)
        
        # Connection info
        info_label = QLabel("Connect to a Blackmagic ATEM switcher\nfor tally (red/green) indication.")
        info_label.setStyleSheet("color: #888898; border: none;")
        layout.addWidget(info_label)
        
        # IP Address
        ip_layout = QVBoxLayout()
        ip_layout.addWidget(QLabel("ATEM IP Address:"))
        self.atem_ip_input = QLineEdit()
        self.atem_ip_input.setPlaceholderText("192.168.1.240")
        ip_layout.addWidget(self.atem_ip_input)
        layout.addLayout(ip_layout)
        
        # Status
        self.atem_status_label = QLabel("Not Connected")
        self.atem_status_label.setObjectName("statusLabel")
        self.atem_status_label.setProperty("status", "disconnected")
        self.atem_status_label.setStyleSheet("""
            QLabel {
                padding: 8px 16px;
                border-radius: 6px;
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
                border: none;
            }
        """)
        layout.addWidget(self.atem_status_label)
        
        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(12)
        
        test_atem_btn = QPushButton("Test Connection")
        test_atem_btn.clicked.connect(self._test_atem)
        btn_layout.addWidget(test_atem_btn)
        
        save_atem_btn = QPushButton("Save ATEM Settings")
        save_atem_btn.clicked.connect(self._save_atem)
        save_atem_btn.setStyleSheet("QPushButton { background-color: #00b4d8; color: #0a0a0f; }")
        btn_layout.addWidget(save_atem_btn)
        
        layout.addLayout(btn_layout)
        
        # Tally mapping info
        mapping_group = QGroupBox("Tally Mapping")
        mapping_layout = QVBoxLayout(mapping_group)
        
        mapping_info = QLabel(
            "Each camera can be mapped to an ATEM input.\n"
            "When that input is on Program (live), the\n"
            "camera button will show RED.\n"
            "When on Preview, it will show GREEN."
        )
        mapping_info.setStyleSheet("color: #888898; font-size: 12px;")
        mapping_layout.addWidget(mapping_info)
        
        layout.addWidget(mapping_group)
        
        layout.addStretch()
        
        return panel
    
    def _load_settings(self):
        """Load current settings into UI"""
        # Load ATEM settings
        self.atem_ip_input.setText(self.settings.atem.ip_address)
        
        # Load camera list
        self._refresh_camera_list()
    
    def _refresh_camera_list(self):
        """Refresh the camera list display"""
        # Clear existing items
        while self.camera_list_layout.count():
            item = self.camera_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add cameras
        for camera in self.settings.cameras:
            item = CameraListItem(camera)
            item.edit_clicked.connect(self._edit_camera)
            item.delete_clicked.connect(self._delete_camera)
            self.camera_list_layout.addWidget(item)
        
        # Update count
        self.camera_list_group.setTitle(f"Configured Cameras ({len(self.settings.cameras)}/10)")
    
    def _discover_cameras(self):
        """Discover cameras on the network using background thread"""
        # Stop any running discovery
        if self._discovery_worker and self._discovery_worker.isRunning():
            return
        
        # Clear UI
        self.discovered_list.clear()
        self._discovered_cameras = []
        
        # Update UI state
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("⏳ Scanning...")
        self.discovery_status.setText("Starting network discovery...")
        self.discovery_status.setStyleSheet("color: #00b4d8; font-size: 12px; padding: 4px;")
        
        # Create and start worker thread
        self._discovery_worker = DiscoveryWorker()
        self._discovery_worker.camera_found.connect(self._on_camera_discovered)
        self._discovery_worker.progress.connect(self._on_discovery_progress)
        self._discovery_worker.finished_signal.connect(self._on_discovery_finished)
        self._discovery_worker.start()
    
    @pyqtSlot(object)
    def _on_camera_discovered(self, camera: DiscoveredCamera):
        """Handle discovered camera from worker thread"""
        # Check if already in list
        for existing in self._discovered_cameras:
            if existing.ip_address == camera.ip_address:
                return
            
        self._discovered_cameras.append(camera)
        
        # Add to list widget
        display_name = camera.name or camera.model or "Unknown"
        display_text = f"{display_name} - {camera.ip_address}"
        if camera.mac_address:
            display_text += f" [{camera.mac_address}]"
        
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, camera)
        self.discovered_list.addItem(item)
                
    @pyqtSlot(str)
    def _on_discovery_progress(self, message: str):
        """Handle progress update from worker thread"""
        self.discovery_status.setText(message)
        QApplication.processEvents()  # Keep UI responsive
    
    @pyqtSlot(int)
    def _on_discovery_finished(self, count: int):
        """Handle discovery completion"""
        self.discover_btn.setEnabled(True)
        self.discover_btn.setText("🔍  Scan Network")
        
        if count == 0:
            self.discovery_status.setText("No cameras found")
            self.discovery_status.setStyleSheet("color: #ef4444; font-size: 12px; padding: 4px;")
            self.discovered_list.addItem("No Panasonic cameras found on network")
        else:
            self.discovery_status.setText(f"Found {count} camera(s)")
            self.discovery_status.setStyleSheet("color: #22c55e; font-size: 12px; padding: 4px;")
    
    def _add_discovered_camera(self, item: QListWidgetItem):
        """Add discovered camera to config"""
        cam: DiscoveredCamera = item.data(Qt.ItemDataRole.UserRole)
        if cam:
            self.camera_name_input.setText(cam.name or cam.model or f"Camera")
            self.camera_ip_input.setText(cam.ip_address)
            self.camera_user_input.setText("admin")
            self.camera_pass_input.setText("admin")
    
    def _add_selected_discovered(self):
        """Add selected discovered camera"""
        item = self.discovered_list.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole):
            self._add_discovered_camera(item)
    
    def _test_camera(self):
        """Test camera connection"""
        from ..camera.stream import CameraStream, StreamConfig
        
        ip = self.camera_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an IP address")
            return
        
        config = StreamConfig(
            ip_address=ip,
            port=80,
            username=self.camera_user_input.text() or "admin",
            password=self.camera_pass_input.text() or "admin"
        )
        
        stream = CameraStream(config)
        success, message = stream.test_connection()
        
        if success:
            QMessageBox.information(self, "Success", f"Connection successful!\n{message}")
        else:
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to camera:\n{message}")
    
    def _save_camera(self):
        """Save camera configuration"""
        name = self.camera_name_input.text().strip()
        ip = self.camera_ip_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a camera name")
            return
        
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an IP address")
            return
        
        if self._editing_camera_id is not None:
            # Update existing camera
            camera = CameraConfig(
                id=self._editing_camera_id,
                name=name,
                ip_address=ip,
                port=80,
                username=self.camera_user_input.text() or "admin",
                password=self.camera_pass_input.text() or "admin"
            )
            self.settings.update_camera(camera)
            
            # Update ATEM mapping
            atem_input = self.camera_atem_input.value()
            if atem_input > 0:
                self.settings.atem.input_mapping[str(camera.id)] = atem_input
            elif str(camera.id) in self.settings.atem.input_mapping:
                del self.settings.atem.input_mapping[str(camera.id)]
            
            self._editing_camera_id = None
            self.cancel_edit_btn.hide()
            self.save_camera_btn.setText("Save Camera")
        else:
            # Add new camera
            if len(self.settings.cameras) >= 10:
                QMessageBox.warning(self, "Error", "Maximum 10 cameras allowed")
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
                port=80,
                username=self.camera_user_input.text() or "admin",
                password=self.camera_pass_input.text() or "admin"
            )
            self.settings.add_camera(camera)
            
            # Update ATEM mapping
            atem_input = self.camera_atem_input.value()
            if atem_input > 0:
                self.settings.atem.input_mapping[str(camera.id)] = atem_input
        
        self.settings.save()
        self._refresh_camera_list()
        self._clear_camera_form()
        self.settings_changed.emit()
    
    def _edit_camera(self, camera_id: int):
        """Edit existing camera"""
        camera = self.settings.get_camera(camera_id)
        if not camera:
            return
        
        self._editing_camera_id = camera_id
        
        self.camera_name_input.setText(camera.name)
        self.camera_ip_input.setText(camera.ip_address)
        self.camera_user_input.setText(camera.username)
        self.camera_pass_input.setText(camera.password)
        
        # Load ATEM mapping
        atem_input = self.settings.atem.input_mapping.get(str(camera_id), 0)
        self.camera_atem_input.setValue(atem_input)
        
        self.save_camera_btn.setText("Update Camera")
        self.cancel_edit_btn.show()
    
    def _cancel_edit(self):
        """Cancel camera edit"""
        self._editing_camera_id = None
        self._clear_camera_form()
        self.cancel_edit_btn.hide()
        self.save_camera_btn.setText("Save Camera")
    
    def _delete_camera(self, camera_id: int):
        """Delete camera"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this camera?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.remove_camera(camera_id)
            
            # Remove ATEM mapping
            if str(camera_id) in self.settings.atem.input_mapping:
                del self.settings.atem.input_mapping[str(camera_id)]
            
            self.settings.save()
            self._refresh_camera_list()
            self.settings_changed.emit()
    
    def _clear_camera_form(self):
        """Clear camera form inputs"""
        self.camera_name_input.clear()
        self.camera_ip_input.clear()
        self.camera_user_input.clear()
        self.camera_pass_input.clear()
        self.camera_atem_input.setValue(0)
    
    def _test_atem(self):
        """Test ATEM connection"""
        from ..atem.tally import ATEMTallyController
        
        ip = self.atem_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an ATEM IP address")
            return
        
        controller = ATEMTallyController()
        success, message = controller.test_connection(ip)
        
        if success:
            QMessageBox.information(self, "Success", f"Connection successful!\n{message}")
            self.atem_status_label.setText("Connected")
            self.atem_status_label.setStyleSheet("""
                QLabel {
                    padding: 8px 16px;
                    border-radius: 6px;
                    background-color: rgba(34, 197, 94, 0.2);
                    color: #22c55e;
                    border: none;
                }
            """)
        else:
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to ATEM:\n{message}")
            self.atem_status_label.setText("Connection Failed")
    
    def _save_atem(self):
        """Save ATEM settings"""
        ip = self.atem_ip_input.text().strip()
        
        self.settings.atem.ip_address = ip
        self.settings.atem.enabled = bool(ip)
        self.settings.save()
        
        QMessageBox.information(self, "Saved", "ATEM settings saved successfully")
        self.settings_changed.emit()

