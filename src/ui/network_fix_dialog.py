"""
Network Fix Dialog

Dialog for fixing camera network settings (IP, subnet, gateway, DHCP).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
import requests
import socket

from ..camera.discovery import DiscoveredCamera


class NetworkFixDialog(QDialog):
    """Dialog for fixing camera network settings"""
    
    def __init__(self, camera: DiscoveredCamera, network_info: dict, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.network_info = network_info
        self.setWindowTitle("Fix Network Settings")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_fields()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("Fix Camera Network Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        layout.addWidget(title)
        
        # Info label
        info = QLabel(f"Camera: {self.camera.name or self.camera.model or 'Unknown'}\n"
                     f"Current IP: {self.camera.ip_address}")
        info.setStyleSheet("font-size: 12px; color: #888898; padding: 8px 0;")
        layout.addWidget(info)
        
        # Current settings (read-only)
        current_frame = QFrame()
        current_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a24;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(16, 12, 16, 12)
        current_layout.setSpacing(8)
        
        current_title = QLabel("Current Settings (Read-only)")
        current_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        current_layout.addWidget(current_title)
        
        self.current_ip_label = QLabel(f"IP: {self.camera.ip_address}")
        self.current_ip_label.setStyleSheet("font-size: 11px; color: #888898;")
        current_layout.addWidget(self.current_ip_label)
        
        subnet = getattr(self.camera, 'subnet_mask', 'Unknown')
        self.current_subnet_label = QLabel(f"Subnet: {subnet}")
        self.current_subnet_label.setStyleSheet("font-size: 11px; color: #888898;")
        current_layout.addWidget(self.current_subnet_label)
        
        gateway = getattr(self.camera, 'gateway', 'Unknown')
        self.current_gateway_label = QLabel(f"Gateway: {gateway}")
        self.current_gateway_label.setStyleSheet("font-size: 11px; color: #888898;")
        current_layout.addWidget(self.current_gateway_label)
        
        layout.addWidget(current_frame)
        
        # New settings
        new_frame = QFrame()
        new_frame.setStyleSheet("""
            QFrame {
                background-color: #12121a;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
        """)
        new_layout = QVBoxLayout(new_frame)
        new_layout.setContentsMargins(16, 16, 16, 16)
        new_layout.setSpacing(12)
        
        new_title = QLabel("New Settings")
        new_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        new_layout.addWidget(new_title)
        
        # IP Address
        ip_layout = QVBoxLayout()
        ip_layout.setSpacing(4)
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 500;")
        ip_layout.addWidget(ip_label)
        self.new_ip_input = QLineEdit()
        self.new_ip_input.setFixedHeight(40)
        self.new_ip_input.setStyleSheet("""
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
        ip_layout.addWidget(self.new_ip_input)
        new_layout.addLayout(ip_layout)
        
        # Subnet Mask
        subnet_layout = QVBoxLayout()
        subnet_layout.setSpacing(4)
        subnet_label = QLabel("Subnet Mask:")
        subnet_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 500;")
        subnet_layout.addWidget(subnet_label)
        self.new_subnet_input = QComboBox()
        self.new_subnet_input.setEditable(True)
        self.new_subnet_input.setFixedHeight(40)
        self.new_subnet_input.addItems([
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
        self.new_subnet_input.setStyleSheet("""
            QComboBox {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QComboBox:focus {
                border-color: #FF9500;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                border: 2px solid #2a2a38;
                selection-background-color: #FF9500;
                color: #FFFFFF;
            }
        """)
        subnet_layout.addWidget(self.new_subnet_input)
        new_layout.addLayout(subnet_layout)
        
        # Gateway
        gateway_layout = QVBoxLayout()
        gateway_layout.setSpacing(4)
        gateway_label = QLabel("Gateway (optional):")
        gateway_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 500;")
        gateway_layout.addWidget(gateway_label)
        self.new_gateway_input = QLineEdit()
        self.new_gateway_input.setFixedHeight(40)
        self.new_gateway_input.setStyleSheet(self.new_ip_input.styleSheet())
        gateway_layout.addWidget(self.new_gateway_input)
        new_layout.addLayout(gateway_layout)
        
        # DHCP Toggle
        dhcp_layout = QHBoxLayout()
        dhcp_layout.setSpacing(12)
        self.dhcp_checkbox = QCheckBox("Enable DHCP (auto-assign IP)")
        self.dhcp_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
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
        self.dhcp_checkbox.toggled.connect(self._on_dhcp_toggled)
        dhcp_layout.addWidget(self.dhcp_checkbox)
        dhcp_layout.addStretch()
        new_layout.addLayout(dhcp_layout)
        
        layout.addWidget(new_frame)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #ef4444; font-size: 11px; padding: 8px;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        layout.addWidget(self.warning_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
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
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.apply_btn = QPushButton("Apply Network Settings")
        self.apply_btn.setFixedHeight(44)
        self.apply_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #2a2a38;
                color: #888898;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_network_settings)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Connect validation
        self.new_ip_input.textChanged.connect(self._validate_settings)
        self.new_subnet_input.currentTextChanged.connect(self._validate_settings)
        self.new_gateway_input.textChanged.connect(self._validate_settings)
    
    def _populate_fields(self):
        """Populate fields with suggested values"""
        # Suggest IP in eth0 subnet
        suggested_ip = self._suggest_ip()
        if suggested_ip:
            self.new_ip_input.setText(suggested_ip)
        
        # Set subnet from eth0
        if self.network_info.get('subnet'):
            self.new_subnet_input.setCurrentText(self.network_info['subnet'])
        
        # Set gateway from eth0
        if self.network_info.get('gateway'):
            self.new_gateway_input.setText(self.network_info['gateway'])
        
        self._validate_settings()
    
    def _suggest_ip(self) -> str:
        """Suggest an IP address in eth0 subnet"""
        try:
            eth0_ip = self.network_info.get('ip', '')
            eth0_subnet = self.network_info.get('subnet', '255.255.255.0')
            
            if not eth0_ip:
                return ""
            
            ip_parts = eth0_ip.split('.')
            if eth0_subnet == '255.255.255.0':
                base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                # Suggest .100-.200 range
                for i in range(100, 201):
                    suggested = f"{base}.{i}"
                    if suggested != eth0_ip:
                        return suggested
                return f"{base}.100"
        except:
            pass
        return ""
    
    def _on_dhcp_toggled(self, checked: bool):
        """Handle DHCP checkbox toggle"""
        self.new_ip_input.setEnabled(not checked)
        self.new_subnet_input.setEnabled(not checked)
        self.new_gateway_input.setEnabled(not checked)
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate network settings"""
        if self.dhcp_checkbox.isChecked():
            self.apply_btn.setEnabled(True)
            self.warning_label.hide()
            return
        
        ip = self.new_ip_input.text().strip()
        subnet = self.new_subnet_input.currentText().strip()
        gateway = self.new_gateway_input.text().strip()
        
        # Validate IP format
        if not self._is_valid_ip(ip):
            self.apply_btn.setEnabled(False)
            self.warning_label.setText("Invalid IP address format")
            self.warning_label.show()
            return
        
        # Validate subnet format
        if not self._is_valid_ip(subnet):
            self.apply_btn.setEnabled(False)
            self.warning_label.setText("Invalid subnet mask format")
            self.warning_label.show()
            return
        
        # Validate gateway if provided
        if gateway and not self._is_valid_ip(gateway):
            self.apply_btn.setEnabled(False)
            self.warning_label.setText("Invalid gateway format")
            self.warning_label.show()
            return
        
        # Check if IP is in same subnet as eth0
        eth0_ip = self.network_info.get('ip', '')
        eth0_subnet = self.network_info.get('subnet', '255.255.255.0')
        if eth0_ip and not self._same_subnet(ip, eth0_ip, eth0_subnet):
            self.warning_label.setText("⚠ Warning: IP is not in the same subnet as eth0. Camera may become unreachable.")
            self.warning_label.show()
        else:
            self.warning_label.hide()
        
        self.apply_btn.setEnabled(True)
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP address is valid"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
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
    
    def _apply_network_settings(self):
        """Apply network settings to camera via CGI commands"""
        if self.dhcp_checkbox.isChecked():
            # Enable DHCP
            reply = QMessageBox.question(
                self, "Confirm DHCP",
                "Enable DHCP? The camera will automatically get an IP address.\n"
                "You may need to rediscover the camera after it reboots.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self._send_network_command("DHCP:1")
        else:
            ip = self.new_ip_input.text().strip()
            subnet = self.new_subnet_input.currentText().strip()
            gateway = self.new_gateway_input.text().strip()
            
            if not ip or not subnet:
                QMessageBox.warning(self, "Error", "IP address and subnet mask are required")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Network Change",
                f"Change camera network settings to:\n\n"
                f"IP: {ip}\n"
                f"Subnet: {subnet}\n"
                f"Gateway: {gateway or 'None'}\n\n"
                f"The camera will reboot and may become unreachable at the old IP.\n"
                f"Make sure you can access it at the new IP.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Disable DHCP first
            self._send_network_command("DHCP:0")
            
            # Set IP, subnet, gateway
            self._send_network_command(f"IPADDR:{ip}")
            self._send_network_command(f"SUBNET:{subnet}")
            if gateway:
                self._send_network_command(f"GATEWAY:{gateway}")
        
        QMessageBox.information(
            self, "Settings Applied",
            "Network settings have been sent to the camera.\n"
            "The camera will reboot. You may need to rediscover it after a few seconds."
        )
        self.accept()
    
    def _send_network_command(self, command: str) -> bool:
        """Send network configuration command to camera"""
        try:
            base_url = f"http://{self.camera.ip_address}"
            url = f"{base_url}/cgi-bin/aw_cam?cmd={command}&res=1"
            
            # Try common credentials
            credentials = [
                ('admin', '12345'),
                ('admin', 'admin'),
                (None, None)
            ]
            
            for username, password in credentials:
                try:
                    auth = (username, password) if username else None
                    response = requests.get(url, auth=auth, timeout=3)
                    if response.status_code == 200:
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            print(f"[NetworkFix] Error sending command {command}: {e}")
            return False



