"""
Settings Page

Configuration for ATEM and other system settings.
"""
import re
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGroupBox, QFrame, QMessageBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal

from ..config.settings import Settings


class SettingsPage(QWidget):
    """
    Settings page for ATEM and system configuration.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup the settings page UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Content - horizontal layout for panels
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # ATEM panel
        atem_panel = self._create_atem_panel()
        content_layout.addWidget(atem_panel)
        
        # Network configuration panel
        network_panel = self._create_network_panel()
        content_layout.addWidget(network_panel)
        
        content_layout.addStretch()
        
        main_layout.addLayout(content_layout)
        main_layout.addStretch()
    
    def _create_atem_panel(self) -> QWidget:
        """Create ATEM configuration panel"""
        panel = QFrame()
        panel.setFixedWidth(400)
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
        header.setStyleSheet("font-size: 18px; font-weight: 600; border: none;")
        layout.addWidget(header)
        
        # Connection info
        info_label = QLabel("Connect to a Blackmagic ATEM switcher\nfor tally (red/green) indication.")
        info_label.setStyleSheet("color: #888898; border: none;")
        layout.addWidget(info_label)
        
        # IP Address
        ip_layout = QVBoxLayout()
        ip_label = QLabel("ATEM IP Address:")
        ip_label.setStyleSheet("border: none;")
        ip_layout.addWidget(ip_label)
        self.atem_ip_input = QLineEdit()
        self.atem_ip_input.setPlaceholderText("192.168.1.240")
        ip_layout.addWidget(self.atem_ip_input)
        layout.addLayout(ip_layout)
        
        # Status
        self.atem_status_label = QLabel("Not Connected")
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
            "Each camera can be mapped to an ATEM input\n"
            "in the Camera configuration page.\n\n"
            "When that input is on Program (live),\n"
            "the camera button will show RED.\n"
            "When on Preview, it will show GREEN."
        )
        mapping_info.setStyleSheet("color: #888898; font-size: 12px;")
        mapping_layout.addWidget(mapping_info)
        
        layout.addWidget(mapping_group)
        layout.addStretch()
        
        return panel
    
    def _create_network_panel(self) -> QWidget:
        """Create network configuration panel"""
        panel = QFrame()
        panel.setFixedWidth(400)
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
        header = QLabel("Network Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: 600; border: none;")
        layout.addWidget(header)
        
        # Connection info
        info_label = QLabel("Configure network settings for the Raspberry Pi.\nChanges require administrator privileges.")
        info_label.setStyleSheet("color: #888898; border: none; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Interface selection (WiFi or LAN)
        interface_layout = QVBoxLayout()
        interface_label = QLabel("Network Interface:")
        interface_label.setStyleSheet("border: none;")
        interface_layout.addWidget(interface_label)
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["WiFi", "Ethernet (LAN)"])
        interface_layout.addWidget(self.interface_combo)
        self.interface_combo.currentIndexChanged.connect(self._on_interface_changed)
        layout.addLayout(interface_layout)
        
        # IP Address
        ip_layout = QVBoxLayout()
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("border: none;")
        ip_layout.addWidget(ip_label)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)
        
        # Subnet Mask
        subnet_layout = QVBoxLayout()
        subnet_label = QLabel("Subnet Mask:")
        subnet_label.setStyleSheet("border: none;")
        subnet_layout.addWidget(subnet_label)
        self.subnet_input = QLineEdit()
        self.subnet_input.setPlaceholderText("255.255.255.0")
        subnet_layout.addWidget(self.subnet_input)
        layout.addLayout(subnet_layout)
        
        # Gateway
        gateway_layout = QVBoxLayout()
        gateway_label = QLabel("Gateway:")
        gateway_label.setStyleSheet("border: none;")
        gateway_layout.addWidget(gateway_label)
        self.gateway_input = QLineEdit()
        self.gateway_input.setPlaceholderText("192.168.1.1")
        gateway_layout.addWidget(self.gateway_input)
        layout.addLayout(gateway_layout)
        
        # Status
        self.network_status_label = QLabel("Ready")
        self.network_status_label.setStyleSheet("""
            QLabel {
                padding: 8px 16px;
                border-radius: 6px;
                background-color: rgba(34, 197, 94, 0.2);
                color: #22c55e;
                border: none;
            }
        """)
        layout.addWidget(self.network_status_label)
        
        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(12)
        
        load_current_btn = QPushButton("Load Current Settings")
        load_current_btn.clicked.connect(self._load_current_network)
        btn_layout.addWidget(load_current_btn)
        
        apply_network_btn = QPushButton("Apply Network Settings")
        apply_network_btn.clicked.connect(self._apply_network_settings)
        apply_network_btn.setStyleSheet("QPushButton { background-color: #00b4d8; color: #0a0a0f; }")
        btn_layout.addWidget(apply_network_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return panel
    
    def _load_settings(self):
        """Load current settings into UI"""
        self.atem_ip_input.setText(self.settings.atem.ip_address)
        # Load current network settings on startup
        self._load_current_network()
    
    def _on_interface_changed(self, index):
        """Handle interface selection change"""
        # Reload network settings for selected interface
        self._load_current_network()
    
    def _load_current_network(self):
        """Load current network settings from system"""
        try:
            # Determine which interface to check
            interface_type = "wlan" if self.interface_combo.currentIndex() == 0 else "eth"
            
            # Find the actual interface name (e.g., wlan0, eth0)
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if f'{interface_type}' in line and 'state UP' in line:
                    # Extract interface name (e.g., "2: wlan0: ...")
                    match = re.search(rf'\d+:\s+({interface_type}\d+)', line)
                    if match:
                        interfaces.append(match.group(1))
            
            if not interfaces:
                self.network_status_label.setText("Interface not found")
                self.network_status_label.setStyleSheet("""
                    QLabel {
                        padding: 8px 16px;
                        border-radius: 6px;
                        background-color: rgba(239, 68, 68, 0.2);
                        color: #ef4444;
                        border: none;
                    }
                """)
                return
            
            interface = interfaces[0]  # Use first available interface
            
            # Get IP address
            result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/', result.stdout)
            if ip_match:
                self.ip_input.setText(ip_match.group(1))
            
            # Get subnet (from CIDR notation)
            subnet_match = re.search(r'inet\s+\d+\.\d+\.\d+\.\d+/(\d+)', result.stdout)
            if subnet_match:
                cidr = int(subnet_match.group(1))
                # Convert CIDR to subnet mask
                subnet = self._cidr_to_subnet(cidr)
                self.subnet_input.setText(subnet)
            
            # Get gateway
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            gateway_match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if gateway_match:
                self.gateway_input.setText(gateway_match.group(1))
            
            self.network_status_label.setText(f"Loaded: {interface}")
            self.network_status_label.setStyleSheet("""
                QLabel {
                    padding: 8px 16px;
                    border-radius: 6px;
                    background-color: rgba(34, 197, 94, 0.2);
                    color: #22c55e;
                    border: none;
                }
            """)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load network settings:\n{str(e)}")
            self.network_status_label.setText("Error loading settings")
            self.network_status_label.setStyleSheet("""
                QLabel {
                    padding: 8px 16px;
                    border-radius: 6px;
                    background-color: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                    border: none;
                }
            """)
    
    def _cidr_to_subnet(self, cidr):
        """Convert CIDR notation to subnet mask"""
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{mask >> 24}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    
    def _apply_network_settings(self):
        """Apply network configuration changes"""
        # Validate inputs
        ip = self.ip_input.text().strip()
        subnet = self.subnet_input.text().strip()
        gateway = self.gateway_input.text().strip()
        
        if not ip or not subnet or not gateway:
            QMessageBox.warning(self, "Error", "Please fill in all network fields")
            return
        
        # Validate IP format (basic)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip) or not re.match(ip_pattern, subnet) or not re.match(ip_pattern, gateway):
            QMessageBox.warning(self, "Error", "Please enter valid IP addresses")
            return
        
        # Confirm action
        reply = QMessageBox.question(
            self,
            "Apply Network Settings",
            f"This will change the network configuration for {'WiFi' if self.interface_combo.currentIndex() == 0 else 'Ethernet'}.\n\n"
            f"IP: {ip}\nSubnet: {subnet}\nGateway: {gateway}\n\n"
            "This requires administrator privileges and may disconnect the network.\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Determine interface
            interface_type = "wlan" if self.interface_combo.currentIndex() == 0 else "eth"
            
            # Find the actual interface name
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
            
            # Try using nmcli (NetworkManager) first
            try:
                # Convert subnet mask to CIDR
                cidr = self._subnet_to_cidr(subnet)
                
                # Configure using nmcli
                subprocess.run(['sudo', 'nmcli', 'connection', 'modify', interface, 
                               f'ipv4.addresses', f'{ip}/{cidr}'], check=True)
                subprocess.run(['sudo', 'nmcli', 'connection', 'modify', interface,
                               'ipv4.gateway', gateway], check=True)
                subprocess.run(['sudo', 'nmcli', 'connection', 'modify', interface,
                               'ipv4.method', 'manual'], check=True)
                subprocess.run(['sudo', 'nmcli', 'connection', 'down', interface], check=False)
                subprocess.run(['sudo', 'nmcli', 'connection', 'up', interface], check=True)
                
                QMessageBox.information(self, "Success", 
                    f"Network settings applied successfully to {interface}.\n"
                    "The connection may be temporarily interrupted.")
                self.network_status_label.setText(f"Applied to {interface}")
                self.network_status_label.setStyleSheet("""
                    QLabel {
                        padding: 8px 16px;
                        border-radius: 6px;
                        background-color: rgba(34, 197, 94, 0.2);
                        color: #22c55e;
                        border: none;
                    }
                """)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to dhcpcd method
                QMessageBox.warning(self, "NetworkManager Not Available",
                    "NetworkManager (nmcli) not found. Please configure network manually\n"
                    "or install NetworkManager for automatic configuration.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply network settings:\n{str(e)}")
            self.network_status_label.setText("Failed to apply")
            self.network_status_label.setStyleSheet("""
                QLabel {
                    padding: 8px 16px;
                    border-radius: 6px;
                    background-color: rgba(239, 68, 68, 0.2);
                    color: #ef4444;
                    border: none;
                }
            """)
    
    def _subnet_to_cidr(self, subnet):
        """Convert subnet mask to CIDR notation"""
        parts = subnet.split('.')
        binary_str = ''
        for part in parts:
            binary_str += format(int(part), '08b')
        return str(binary_str.count('1'))
    
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
