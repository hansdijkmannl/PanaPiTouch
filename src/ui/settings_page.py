"""
Settings Page

Configuration for ATEM, network, and system settings.
"""
import re
import subprocess
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGroupBox, QFrame, QMessageBox, QComboBox,
    QScrollArea, QGridLayout, QInputDialog
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt

from ..config.settings import Settings


class SettingsPage(QWidget):
    """
    Settings page for ATEM, network, and system configuration.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
        self._start_system_monitor()
    
    def _setup_ui(self):
        """Setup the settings page UI"""
        # Main scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
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
        
        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Top row - ATEM, Network, and Backup panels (equal stretch)
        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        
        atem_panel = self._create_atem_panel()
        top_row.addWidget(atem_panel, 1)  # stretch factor 1
        
        network_panel = self._create_network_panel()
        top_row.addWidget(network_panel, 1)  # stretch factor 1
        
        backup_panel = self._create_backup_panel()
        top_row.addWidget(backup_panel, 1)  # stretch factor 1
        
        main_layout.addLayout(top_row)
        
        # Bottom row - System Info panel
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)
        
        system_panel = self._create_system_panel()
        bottom_row.addWidget(system_panel)
        
        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)
        
        main_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        
        # Set scroll as main widget
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
    
    def _get_input_style(self):
        """Get consistent input field styling"""
        return """
            QLineEdit, QComboBox {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: #FFFFFF;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #FF9500;
            }
            QLineEdit::placeholder {
                color: #666676;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                selection-background-color: #FF9500;
                color: #FFFFFF;
            }
        """
    
    def _get_button_style(self, primary=False):
        """Get consistent button styling"""
        if primary:
            return """
                QPushButton {
                    background-color: #FF9500;
                    border: none;
                    border-radius: 8px;
                    color: #0a0a0f;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0px;
                    margin: 0px;
                    min-height: 44px;
                }
                QPushButton:hover {
                    background-color: #CC7700;
                }
                QPushButton:pressed {
                    background-color: #AA6600;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #2a2a38;
                    border: 2px solid #3a3a48;
                    border-radius: 8px;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0px;
                    margin: 0px;
                    min-height: 44px;
                }
                QPushButton:hover {
                    border-color: #FF9500;
                    background-color: #3a3a48;
                }
                QPushButton:pressed {
                    background-color: #4a4a58;
                }
            """
    
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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header with icon
        header_layout = QHBoxLayout()
        header_icon = QLabel("🎬")
        header_icon.setStyleSheet("font-size: 24px; border: none;")
        header_layout.addWidget(header_icon)
        header = QLabel("ATEM Switcher")
        header.setStyleSheet("font-size: 20px; font-weight: 600; border: none; color: #ffffff;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Connection info
        info_label = QLabel("Connect to a Blackmagic ATEM switcher for tally indication.")
        info_label.setStyleSheet("color: #888898; border: none; font-size: 13px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # IP Address
        ip_container = QVBoxLayout()
        ip_container.setSpacing(6)
        ip_label = QLabel("ATEM IP Address:")
        ip_label.setStyleSheet("border: none; color: #FFFFFF; font-size: 13px; font-weight: 500;")
        ip_container.addWidget(ip_label)
        self.atem_ip_input = QLineEdit()
        self.atem_ip_input.setPlaceholderText("192.168.1.240")
        self.atem_ip_input.setStyleSheet(self._get_input_style())
        ip_container.addWidget(self.atem_ip_input)
        layout.addLayout(ip_container)
        
        # ATEM Model display (shown after successful connection)
        self.atem_model_label = QLabel("")
        self.atem_model_label.setStyleSheet("""
            QLabel {
                padding: 10px 16px;
                border-radius: 8px;
                background-color: rgba(0, 180, 216, 0.15);
                color: #FF9500;
                border: 1px solid rgba(0, 180, 216, 0.3);
                font-size: 13px;
            }
        """)
        self.atem_model_label.hide()
        layout.addWidget(self.atem_model_label)
        
        # Status
        self.atem_status_label = QLabel("● Not Connected")
        self.atem_status_label.setStyleSheet("""
            QLabel {
                padding: 10px 16px;
                border-radius: 8px;
                background-color: rgba(239, 68, 68, 0.15);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                font-size: 13px;
            }
        """)
        layout.addWidget(self.atem_status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        test_atem_btn = QPushButton("Test Connection")
        test_atem_btn.setStyleSheet(self._get_button_style(primary=False))
        test_atem_btn.clicked.connect(self._test_atem)
        btn_layout.addWidget(test_atem_btn)
        
        save_atem_btn = QPushButton("Save")
        save_atem_btn.setStyleSheet(self._get_button_style(primary=True))
        save_atem_btn.clicked.connect(self._save_atem)
        btn_layout.addWidget(save_atem_btn)
        
        layout.addLayout(btn_layout)
        
        # Tally mapping info
        mapping_frame = QFrame()
        mapping_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        mapping_layout = QVBoxLayout(mapping_frame)
        mapping_layout.setContentsMargins(16, 12, 16, 12)
        
        mapping_header = QLabel("💡 Tally Mapping")
        mapping_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff; border: none;")
        mapping_layout.addWidget(mapping_header)
        
        mapping_info = QLabel(
            "Map cameras to ATEM inputs in the Camera page.\n"
            "🔴 RED = Program (Live)  •  🟢 GREEN = Preview"
        )
        mapping_info.setStyleSheet("color: #888898; font-size: 12px; border: none;")
        mapping_layout.addWidget(mapping_info)
        
        layout.addWidget(mapping_frame)
        layout.addStretch()
        
        return panel
    
    def _create_network_panel(self) -> QWidget:
        """Create network configuration panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header with icon
        header_layout = QHBoxLayout()
        header_icon = QLabel("🌐")
        header_icon.setStyleSheet("font-size: 24px; border: none;")
        header_layout.addWidget(header_icon)
        header = QLabel("Network Configuration")
        header.setStyleSheet("font-size: 20px; font-weight: 600; border: none; color: #ffffff;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Connection info
        info_label = QLabel("Configure network settings for the Raspberry Pi.")
        info_label.setStyleSheet("color: #888898; border: none; font-size: 13px;")
        layout.addWidget(info_label)
        
        # Interface selection
        interface_container = QVBoxLayout()
        interface_container.setSpacing(6)
        interface_label = QLabel("Network Interface:")
        interface_label.setStyleSheet("border: none; color: #FFFFFF; font-size: 13px; font-weight: 500;")
        interface_container.addWidget(interface_label)
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["WiFi (wlan0)", "Ethernet (eth0)"])
        self.interface_combo.setStyleSheet(self._get_input_style())
        self.interface_combo.currentIndexChanged.connect(self._on_interface_changed)
        interface_container.addWidget(self.interface_combo)
        layout.addLayout(interface_container)
        
        # IP Address
        ip_container = QVBoxLayout()
        ip_container.setSpacing(6)
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("border: none; color: #FFFFFF; font-size: 13px; font-weight: 500;")
        ip_container.addWidget(ip_label)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.ip_input.setStyleSheet(self._get_input_style())
        ip_container.addWidget(self.ip_input)
        layout.addLayout(ip_container)
        
        # Subnet and Gateway in a row
        subnet_gateway_row = QHBoxLayout()
        subnet_gateway_row.setSpacing(12)
        
        # Subnet Mask
        subnet_container = QVBoxLayout()
        subnet_container.setSpacing(6)
        subnet_label = QLabel("Subnet Mask:")
        subnet_label.setStyleSheet("border: none; color: #FFFFFF; font-size: 13px; font-weight: 500;")
        subnet_container.addWidget(subnet_label)
        self.subnet_input = QLineEdit()
        self.subnet_input.setPlaceholderText("255.255.255.0")
        self.subnet_input.setStyleSheet(self._get_input_style())
        subnet_container.addWidget(self.subnet_input)
        subnet_gateway_row.addLayout(subnet_container)
        
        # Gateway
        gateway_container = QVBoxLayout()
        gateway_container.setSpacing(6)
        gateway_label = QLabel("Gateway:")
        gateway_label.setStyleSheet("border: none; color: #FFFFFF; font-size: 13px; font-weight: 500;")
        gateway_container.addWidget(gateway_label)
        self.gateway_input = QLineEdit()
        self.gateway_input.setPlaceholderText("192.168.1.1")
        self.gateway_input.setStyleSheet(self._get_input_style())
        gateway_container.addWidget(self.gateway_input)
        subnet_gateway_row.addLayout(gateway_container)
        
        layout.addLayout(subnet_gateway_row)
        
        # Status
        self.network_status_label = QLabel("● Ready")
        self.network_status_label.setStyleSheet("""
            QLabel {
                padding: 10px 16px;
                border-radius: 8px;
                background-color: rgba(34, 197, 94, 0.15);
                color: #22c55e;
                border: 1px solid rgba(34, 197, 94, 0.3);
                font-size: 13px;
            }
        """)
        layout.addWidget(self.network_status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        load_current_btn = QPushButton("Load Current")
        load_current_btn.setStyleSheet(self._get_button_style(primary=False))
        load_current_btn.clicked.connect(self._load_current_network)
        btn_layout.addWidget(load_current_btn)
        
        apply_network_btn = QPushButton("Apply")
        apply_network_btn.setStyleSheet(self._get_button_style(primary=True))
        apply_network_btn.clicked.connect(self._apply_network_settings)
        btn_layout.addWidget(apply_network_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return panel
    
    def _create_system_panel(self) -> QWidget:
        """Create system information panel"""
        panel = QFrame()
        panel.setFixedWidth(820)  # Wider to show more info
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header with icon
        header_layout = QHBoxLayout()
        header_icon = QLabel("🖥️")
        header_icon.setStyleSheet("font-size: 24px; border: none;")
        header_layout.addWidget(header_icon)
        header = QLabel("System Information")
        header.setStyleSheet("font-size: 20px; font-weight: 600; border: none; color: #ffffff;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #3a3a48;
            }
        """)
        refresh_btn.clicked.connect(self._update_system_info)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # System info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(16)
        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)
        
        # Create info cards
        self.system_info_labels = {}
        
        info_items = [
            ("model", "🔧 Model", 0, 0),
            ("os", "💿 OS", 0, 2),
            ("cpu_temp", "🌡️ CPU Temp", 1, 0),
            ("cpu_usage", "⚡ CPU Usage", 1, 2),
            ("memory", "🧠 Memory", 2, 0),
            ("storage", "💾 Storage", 2, 2),
            ("uptime", "⏱️ Uptime", 3, 0),
            ("ip_address", "🌐 IP Address", 3, 2),
        ]
        
        for key, label_text, row, col in info_items:
            # Label
            label = QLabel(label_text)
            label.setStyleSheet("color: #888898; font-size: 12px; border: none;")
            info_grid.addWidget(label, row, col)
            
            # Value
            value_label = QLabel("Loading...")
            value_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500; border: none;")
            info_grid.addWidget(value_label, row, col + 1)
            self.system_info_labels[key] = value_label
        
        layout.addLayout(info_grid)
        
        # Temperature gauge (visual)
        temp_frame = QFrame()
        temp_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        temp_layout = QHBoxLayout(temp_frame)
        temp_layout.setContentsMargins(16, 12, 16, 12)
        
        temp_label = QLabel("CPU Temperature:")
        temp_label.setStyleSheet("color: #888898; font-size: 13px; border: none;")
        temp_layout.addWidget(temp_label)
        
        self.temp_bar = QFrame()
        self.temp_bar.setFixedHeight(20)
        self.temp_bar.setStyleSheet("""
            QFrame {
                background-color: #22c55e;
                border-radius: 4px;
                border: none;
            }
        """)
        self.temp_bar.setFixedWidth(100)
        temp_layout.addWidget(self.temp_bar)
        
        self.temp_value_label = QLabel("--°C")
        self.temp_value_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; border: none; min-width: 60px;")
        temp_layout.addWidget(self.temp_value_label)
        
        temp_layout.addStretch()
        
        # Throttling indicator
        self.throttle_label = QLabel("✓ No Throttling")
        self.throttle_label.setStyleSheet("color: #22c55e; font-size: 12px; border: none;")
        temp_layout.addWidget(self.throttle_label)
        
        layout.addWidget(temp_frame)
        
        return panel
    
    def _create_backup_panel(self) -> QWidget:
        """Create backup and restore panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header with icon
        header_layout = QHBoxLayout()
        header_icon = QLabel("💾")
        header_icon.setStyleSheet("font-size: 24px; border: none;")
        header_layout.addWidget(header_icon)
        header = QLabel("Backup & Restore")
        header.setStyleSheet("font-size: 20px; font-weight: 600; border: none; color: #ffffff;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Info
        info_label = QLabel("Save and restore your camera configurations and settings.")
        info_label.setStyleSheet("color: #888898; border: none; font-size: 13px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Create backup section
        create_frame = QFrame()
        create_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        create_layout = QVBoxLayout(create_frame)
        create_layout.setContentsMargins(16, 12, 16, 12)
        create_layout.setSpacing(10)
        
        create_header = QLabel("Create New Backup")
        create_header.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff; border: none;")
        create_layout.addWidget(create_header)
        
        self.backup_name_input = QLineEdit()
        self.backup_name_input.setObjectName("backup_name_input")
        self.backup_name_input.setPlaceholderText("Enter backup name")
        self.backup_name_input.setStyleSheet(self._get_input_style())
        create_layout.addWidget(self.backup_name_input)
        
        create_btn = QPushButton("Create Backup")
        create_btn.setStyleSheet(self._get_button_style(primary=True))
        create_btn.clicked.connect(self._create_backup)
        create_layout.addWidget(create_btn)
        layout.addWidget(create_frame)
        
        # Restore section
        restore_frame = QFrame()
        restore_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        restore_layout = QVBoxLayout(restore_frame)
        restore_layout.setContentsMargins(16, 12, 16, 12)
        restore_layout.setSpacing(10)
        
        restore_header = QLabel("Restore from Backup")
        restore_header.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff; border: none;")
        restore_layout.addWidget(restore_header)
        
        # Backup dropdown
        self.backup_combo = QComboBox()
        self.backup_combo.setStyleSheet(self._get_input_style())
        restore_layout.addWidget(self.backup_combo)
        
        # Action buttons row
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        
        restore_btn = QPushButton("Restore")
        restore_btn.setStyleSheet(self._get_button_style(primary=True))
        restore_btn.clicked.connect(self._restore_backup)
        action_row.addWidget(restore_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 2px solid #ef4444;
                border-radius: 8px;
                color: #ef4444;
                font-size: 14px;
                font-weight: 500;
                padding: 12px 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.3);
            }
        """)
        delete_btn.clicked.connect(self._delete_backup)
        action_row.addWidget(delete_btn)
        
        action_row.addStretch()
        restore_layout.addLayout(action_row)
        
        layout.addWidget(restore_frame)
        
        # Status
        self.backup_status_label = QLabel("● Ready")
        self.backup_status_label.setStyleSheet("""
            QLabel {
                padding: 10px 16px;
                border-radius: 8px;
                background-color: rgba(34, 197, 94, 0.15);
                color: #22c55e;
                border: 1px solid rgba(34, 197, 94, 0.3);
                font-size: 13px;
            }
        """)
        layout.addWidget(self.backup_status_label)
        
        layout.addStretch()
        
        # Initialize backup list
        self._refresh_backup_list()
        
        return panel
    
    def _get_backup_dir(self) -> Path:
        """Get backup directory, create if doesn't exist"""
        backup_dir = Path.home() / ".panapitouch" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def _refresh_backup_list(self):
        """Refresh the backup dropdown list"""
        self.backup_combo.clear()
        
        backup_dir = self._get_backup_dir()
        backups = list(backup_dir.glob("*.json"))
        
        if not backups:
            self.backup_combo.addItem("No backups found", None)
            return
        
        # Sort by modification time, newest first
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup_file in backups:
            # Get friendly name from filename
            name = backup_file.stem  # filename without .json
            
            # Get modification time
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            date_str = mtime.strftime("%b %d, %Y %H:%M")
            
            # Display as "Name (Date)"
            display_name = f"{name}  •  {date_str}"
            self.backup_combo.addItem(display_name, str(backup_file))
    
    def _create_backup(self):
        """Create a new backup with custom name"""
        name = self.backup_name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a backup name")
            return
        
        # Sanitize filename
        safe_name = re.sub(r'[^\w\s-]', '', name).strip()
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        
        if not safe_name:
            QMessageBox.warning(self, "Error", "Please enter a valid backup name")
            return
        
        backup_dir = self._get_backup_dir()
        backup_file = backup_dir / f"{safe_name}.json"
        
        # Check if exists
        if backup_file.exists():
            reply = QMessageBox.question(
                self,
                "Backup Exists",
                f"A backup named '{name}' already exists.\n\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            # Create backup data
            backup_data = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "name": name,
                "settings": self.settings.to_dict()
            }
            
            # Write backup file
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self._set_backup_status(f"Backup '{name}' created", "success")
            self.backup_name_input.clear()
            self._refresh_backup_list()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup:\n{str(e)}")
            self._set_backup_status("Backup failed", "error")
    
    def _restore_backup(self):
        """Restore selected backup"""
        backup_path = self.backup_combo.currentData()
        
        if not backup_path:
            QMessageBox.warning(self, "Error", "Please select a backup to restore")
            return
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            QMessageBox.warning(self, "Error", "Backup file not found")
            self._refresh_backup_list()
            return
        
        # Confirm restore
        reply = QMessageBox.question(
            self,
            "Restore Backup",
            f"This will replace your current settings with the backup.\n\n"
            "Your current settings will be lost.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Read backup
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Restore settings
            if "settings" in backup_data:
                self.settings.load_from_dict(backup_data["settings"])
                self.settings.save()
                
                # Reload UI
                self._load_settings()
                
                self._set_backup_status(f"Restored from backup", "success")
                self.settings_changed.emit()
                
                QMessageBox.information(
                    self, 
                    "Restore Complete", 
                    "Settings have been restored successfully.\n\n"
                    "Some changes may require restarting the app."
                )
            else:
                QMessageBox.warning(self, "Error", "Invalid backup file format")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup:\n{str(e)}")
            self._set_backup_status("Restore failed", "error")
    
    def _delete_backup(self):
        """Delete selected backup"""
        backup_path = self.backup_combo.currentData()
        
        if not backup_path:
            QMessageBox.warning(self, "Error", "Please select a backup to delete")
            return
        
        backup_file = Path(backup_path)
        backup_name = backup_file.stem
        
        reply = QMessageBox.question(
            self,
            "Delete Backup",
            f"Are you sure you want to delete '{backup_name}'?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            backup_file.unlink()
            self._set_backup_status(f"Deleted '{backup_name}'", "success")
            self._refresh_backup_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete backup:\n{str(e)}")
            self._set_backup_status("Delete failed", "error")
    
    def _set_backup_status(self, text, status_type="info"):
        """Set backup status label with appropriate styling"""
        colors = {
            "success": ("#22c55e", "rgba(34, 197, 94, 0.15)", "rgba(34, 197, 94, 0.3)"),
            "error": ("#ef4444", "rgba(239, 68, 68, 0.15)", "rgba(239, 68, 68, 0.3)"),
            "info": ("#FF9500", "rgba(0, 180, 216, 0.15)", "rgba(0, 180, 216, 0.3)"),
        }
        text_color, bg_color, border_color = colors.get(status_type, colors["info"])
        
        self.backup_status_label.setText(f"● {text}")
        self.backup_status_label.setStyleSheet(f"""
            QLabel {{
                padding: 10px 16px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                font-size: 13px;
            }}
        """)
    
    def _start_system_monitor(self):
        """Start periodic system info updates"""
        self._update_system_info()
        self._system_timer = QTimer(self)
        self._system_timer.timeout.connect(self._update_system_info)
        self._system_timer.start(5000)  # Update every 5 seconds
    
    def _update_system_info(self):
        """Update system information display"""
        try:
            # Model
            try:
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip().replace('\x00', '')
                    self.system_info_labels["model"].setText(model[:40])
            except:
                self.system_info_labels["model"].setText("Unknown")
            
            # OS
            try:
                result = subprocess.run(['lsb_release', '-d'], capture_output=True, text=True)
                os_info = result.stdout.split(':')[1].strip() if ':' in result.stdout else "Unknown"
                self.system_info_labels["os"].setText(os_info[:30])
            except:
                self.system_info_labels["os"].setText("Linux")
            
            # CPU Temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = int(f.read().strip()) / 1000
                    self.system_info_labels["cpu_temp"].setText(f"{temp:.1f}°C")
                    self.temp_value_label.setText(f"{temp:.1f}°C")
                    
                    # Update temperature bar color and width
                    if temp < 50:
                        color = "#22c55e"  # Green
                    elif temp < 70:
                        color = "#eab308"  # Yellow
                    else:
                        color = "#ef4444"  # Red
                    
                    # Width based on 0-85°C range
                    width = min(200, max(20, int((temp / 85) * 200)))
                    self.temp_bar.setFixedWidth(width)
                    self.temp_bar.setStyleSheet(f"""
                        QFrame {{
                            background-color: {color};
                            border-radius: 4px;
                            border: none;
                        }}
                    """)
            except:
                self.system_info_labels["cpu_temp"].setText("N/A")
                self.temp_value_label.setText("N/A")
            
            # CPU Usage
            try:
                result = subprocess.run(['grep', 'cpu ', '/proc/stat'], capture_output=True, text=True)
                values = result.stdout.split()[1:8]
                values = [int(v) for v in values]
                idle = values[3]
                total = sum(values)
                
                if hasattr(self, '_last_cpu_idle'):
                    idle_diff = idle - self._last_cpu_idle
                    total_diff = total - self._last_cpu_total
                    usage = 100 * (1 - idle_diff / total_diff) if total_diff > 0 else 0
                    self.system_info_labels["cpu_usage"].setText(f"{usage:.1f}%")
                else:
                    self.system_info_labels["cpu_usage"].setText("--")
                
                self._last_cpu_idle = idle
                self._last_cpu_total = total
            except:
                self.system_info_labels["cpu_usage"].setText("N/A")
            
            # Memory
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                total = int(re.search(r'MemTotal:\s+(\d+)', meminfo).group(1)) / 1024 / 1024
                available = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1)) / 1024 / 1024
                used = total - available
                self.system_info_labels["memory"].setText(f"{used:.1f} / {total:.1f} GB")
            except:
                self.system_info_labels["memory"].setText("N/A")
            
            # Storage
            try:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    used = parts[2]
                    total = parts[1]
                    self.system_info_labels["storage"].setText(f"{used} / {total}")
            except:
                self.system_info_labels["storage"].setText("N/A")
            
            # Uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                if days > 0:
                    self.system_info_labels["uptime"].setText(f"{days}d {hours}h {minutes}m")
                else:
                    self.system_info_labels["uptime"].setText(f"{hours}h {minutes}m")
            except:
                self.system_info_labels["uptime"].setText("N/A")
            
            # IP Address
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                self.system_info_labels["ip_address"].setText(ips[0] if ips else "No network")
            except:
                self.system_info_labels["ip_address"].setText("N/A")
            
            # Throttling check
            try:
                result = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True)
                throttled = result.stdout.strip()
                if 'throttled=0x0' in throttled:
                    self.throttle_label.setText("✓ No Throttling")
                    self.throttle_label.setStyleSheet("color: #22c55e; font-size: 12px; border: none;")
                else:
                    self.throttle_label.setText("⚠️ Throttling Detected")
                    self.throttle_label.setStyleSheet("color: #ef4444; font-size: 12px; border: none;")
            except:
                self.throttle_label.setText("")
                
        except Exception as e:
            print(f"Error updating system info: {e}")
    
    def _load_settings(self):
        """Load current settings into UI"""
        self.atem_ip_input.setText(self.settings.atem.ip_address)
        # Load current network settings on startup
        self._load_current_network()
    
    def _on_interface_changed(self, index):
        """Handle interface selection change"""
        self._load_current_network()
    
    def _load_current_network(self):
        """Load current network settings from system"""
        try:
            interface_type = "wlan" if self.interface_combo.currentIndex() == 0 else "eth"
            
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if f'{interface_type}' in line:
                    match = re.search(rf'\d+:\s+({interface_type}\d+)', line)
                    if match:
                        interfaces.append(match.group(1))
            
            if not interfaces:
                self._set_network_status("Interface not found", "error")
                return
            
            interface = interfaces[0]
            
            # Get IP address
            result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/', result.stdout)
            if ip_match:
                self.ip_input.setText(ip_match.group(1))
            
            # Get subnet
            subnet_match = re.search(r'inet\s+\d+\.\d+\.\d+\.\d+/(\d+)', result.stdout)
            if subnet_match:
                cidr = int(subnet_match.group(1))
                subnet = self._cidr_to_subnet(cidr)
                self.subnet_input.setText(subnet)
            
            # Get gateway
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            gateway_match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if gateway_match:
                self.gateway_input.setText(gateway_match.group(1))
            
            self._set_network_status(f"Loaded: {interface}", "success")
            
        except Exception as e:
            self._set_network_status("Error loading settings", "error")
    
    def _set_network_status(self, text, status_type="info"):
        """Set network status label with appropriate styling"""
        colors = {
            "success": ("#22c55e", "rgba(34, 197, 94, 0.15)", "rgba(34, 197, 94, 0.3)"),
            "error": ("#ef4444", "rgba(239, 68, 68, 0.15)", "rgba(239, 68, 68, 0.3)"),
            "info": ("#FF9500", "rgba(0, 180, 216, 0.15)", "rgba(0, 180, 216, 0.3)"),
        }
        text_color, bg_color, border_color = colors.get(status_type, colors["info"])
        
        self.network_status_label.setText(f"● {text}")
        self.network_status_label.setStyleSheet(f"""
            QLabel {{
                padding: 10px 16px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                font-size: 13px;
            }}
        """)
    
    def _set_atem_status(self, text, status_type="info", model=None):
        """Set ATEM status label with appropriate styling"""
        colors = {
            "success": ("#22c55e", "rgba(34, 197, 94, 0.15)", "rgba(34, 197, 94, 0.3)"),
            "error": ("#ef4444", "rgba(239, 68, 68, 0.15)", "rgba(239, 68, 68, 0.3)"),
            "info": ("#FF9500", "rgba(0, 180, 216, 0.15)", "rgba(0, 180, 216, 0.3)"),
        }
        text_color, bg_color, border_color = colors.get(status_type, colors["info"])
        
        self.atem_status_label.setText(f"● {text}")
        self.atem_status_label.setStyleSheet(f"""
            QLabel {{
                padding: 10px 16px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                font-size: 13px;
            }}
        """)
        
        # Show/hide model label
        if model:
            self.atem_model_label.setText(f"🎬 {model}")
            self.atem_model_label.show()
        else:
            self.atem_model_label.hide()
    
    def _cidr_to_subnet(self, cidr):
        """Convert CIDR notation to subnet mask"""
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{mask >> 24}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    
    def _subnet_to_cidr(self, subnet):
        """Convert subnet mask to CIDR notation"""
        parts = subnet.split('.')
        binary_str = ''
        for part in parts:
            binary_str += format(int(part), '08b')
        return str(binary_str.count('1'))
    
    def _apply_network_settings(self):
        """Apply network configuration changes"""
        ip = self.ip_input.text().strip()
        subnet = self.subnet_input.text().strip()
        gateway = self.gateway_input.text().strip()
        
        if not ip or not subnet or not gateway:
            QMessageBox.warning(self, "Error", "Please fill in all network fields")
            return
        
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip) or not re.match(ip_pattern, subnet) or not re.match(ip_pattern, gateway):
            QMessageBox.warning(self, "Error", "Please enter valid IP addresses")
            return
        
        interface_name = "WiFi" if self.interface_combo.currentIndex() == 0 else "Ethernet"
        reply = QMessageBox.question(
            self,
            "Apply Network Settings",
            f"Apply these settings to {interface_name}?\n\n"
            f"IP: {ip}\nSubnet: {subnet}\nGateway: {gateway}\n\n"
            "This may temporarily disconnect the network.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            interface_type = "wlan" if self.interface_combo.currentIndex() == 0 else "eth"
            
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if f'{interface_type}' in line:
                    match = re.search(rf'\d+:\s+({interface_type}\d+)', line)
                    if match:
                        interfaces.append(match.group(1))
            
            if not interfaces:
                QMessageBox.warning(self, "Error", f"No {interface_type} interface found")
                return
            
            interface = interfaces[0]
            
            # Try multiple network configuration methods
            success = False
            method_used = None
            cidr = self._subnet_to_cidr(subnet)
            
            # Method 1: NetworkManager (nmcli)
            try:
                # First, find the connection name for this interface
                result = subprocess.run(['nmcli', '-t', '-f', 'NAME,DEVICE', 'connection', 'show', '--active'],
                                       capture_output=True, text=True, check=True)
                connection_name = None
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        name, device = line.split(':', 1)
                        if device == interface:
                            connection_name = name
                            break
                
                if connection_name:
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name, 
                                   f'ipv4.addresses', f'{ip}/{cidr}'], check=True, 
                                   capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name,
                                   'ipv4.gateway', gateway], check=True, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name,
                                   'ipv4.method', 'manual'], check=True, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'down', connection_name], 
                                   check=False, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'up', connection_name], 
                                   check=True, capture_output=True)
                    success = True
                    method_used = "NetworkManager"
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"NetworkManager method failed: {e}")
            
            # Method 2: dhcpcd (common on Raspberry Pi)
            if not success:
                try:
                    dhcpcd_conf = Path(f"/etc/dhcpcd.conf")
                    if dhcpcd_conf.exists():
                        # Backup original config
                        backup_path = Path(f"/etc/dhcpcd.conf.backup.{int(datetime.now().timestamp())}")
                        shutil.copy(dhcpcd_conf, backup_path)
                        
                        # Read current config
                        with open(dhcpcd_conf, 'r') as f:
                            lines = f.readlines()
                        
                        # Remove old static IP config for this interface
                        new_lines = []
                        skip_until_blank = False
                        for i, line in enumerate(lines):
                            if f'interface {interface}' in line:
                                skip_until_blank = True
                            elif skip_until_blank and line.strip() == '':
                                skip_until_blank = False
                            
                            if not skip_until_blank:
                                new_lines.append(line)
                        
                        # Add new static IP config
                        new_lines.append(f'\n# Static IP configuration for {interface}\n')
                        new_lines.append(f'interface {interface}\n')
                        new_lines.append(f'static ip_address={ip}/{cidr}\n')
                        new_lines.append(f'static routers={gateway}\n')
                        new_lines.append(f'static domain_name_servers={gateway} 8.8.8.8\n')
                        
                        # Write new config
                        with open(dhcpcd_conf, 'w') as f:
                            f.writelines(new_lines)
                        
                        # Restart dhcpcd
                        subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], 
                                       check=True, capture_output=True)
                        success = True
                        method_used = "dhcpcd"
                except Exception as e:
                    print(f"dhcpcd method failed: {e}")
            
            # Method 3: systemd-networkd
            if not success:
                try:
                    netdev_file = Path(f"/etc/systemd/network/10-{interface}.network")
                    netdev_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    cidr = self._subnet_to_cidr(subnet)
                    config = f"""[Match]
Name={interface}

[Network]
Address={ip}/{cidr}
Gateway={gateway}
DNS={gateway} 8.8.8.8
"""
                    with open(netdev_file, 'w') as f:
                        f.write(config)
                    
                    subprocess.run(['sudo', 'systemctl', 'restart', 'systemd-networkd'], 
                                   check=True, capture_output=True)
                    success = True
                    method_used = "systemd-networkd"
                except Exception as e:
                    print(f"systemd-networkd method failed: {e}")
            
            if success:
                QMessageBox.information(self, "Success", 
                    f"Network settings applied to {interface} using {method_used}.\n\n"
                    "The connection may be temporarily interrupted.")
                self._set_network_status(f"Applied to {interface}", "success")
            else:
                QMessageBox.warning(self, "Network Configuration Failed",
                    "Could not configure network automatically.\n\n"
                    "Please configure manually via:\n"
                    "- NetworkManager: sudo nmcli\n"
                    "- dhcpcd: Edit /etc/dhcpcd.conf\n"
                    "- systemd-networkd: Edit /etc/systemd/network/\n\n"
                    "Or install NetworkManager:\n"
                    "  sudo apt install network-manager")
                self._set_network_status("Configuration failed", "error")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings:\n{str(e)}")
            self._set_network_status("Failed to apply", "error")
    
    def _test_atem(self):
        """Test ATEM connection and detect model"""
        from ..atem.tally import ATEMTallyController
        
        ip = self.atem_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an ATEM IP address")
            return
        
        self._set_atem_status("Connecting...", "info")
        
        controller = ATEMTallyController()
        success, message = controller.test_connection(ip)
        
        if success:
            # Try to get ATEM model info
            model = None
            try:
                if hasattr(controller, 'atem') and controller.atem:
                    model = getattr(controller.atem, 'atemModel', None)
                    if not model:
                        # Try alternate attribute names
                        model = getattr(controller.atem, 'productName', None)
            except:
                pass
            
            if not model:
                # Parse from message if available
                if 'ATEM' in message:
                    model = message
            
            self._set_atem_status("Connected", "success", model)
            QMessageBox.information(self, "Success", f"Connection successful!\n{message}")
        else:
            self._set_atem_status("Connection Failed", "error")
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to ATEM:\n{message}")
    
    def _save_atem(self):
        """Save ATEM settings"""
        ip = self.atem_ip_input.text().strip()
        
        self.settings.atem.ip_address = ip
        self.settings.atem.enabled = bool(ip)
        self.settings.save()
        
        QMessageBox.information(self, "Saved", "ATEM settings saved successfully")
        self.settings_changed.emit()
