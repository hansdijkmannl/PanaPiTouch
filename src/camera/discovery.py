"""
Panasonic PTZ Camera Discovery

Implements network discovery using Panasonic UDP Broadcast protocol,
similar to Panasonic Easy IP Setup tool.

Based on the discovery mechanism from:
https://github.com/dPro-Software/Panasonic-IP-setup
"""
import socket
import struct
import threading
import time
import re
import concurrent.futures
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
import requests


@dataclass
class DiscoveredCamera:
    """Represents a discovered Panasonic camera"""
    ip_address: str
    mac_address: str = ""
    model: str = ""
    name: str = ""
    firmware: str = ""
    serial: str = ""
    subnet_mask: str = ""
    gateway: str = ""
    dhcp_enabled: bool = False


class CameraDiscovery:
    """
    Discover Panasonic PTZ cameras on the network.
    
    Uses Panasonic proprietary UDP broadcast protocol,
    similar to the Easy IP Setup tool.
    """
    
    # Panasonic PTZ model prefixes
    PANASONIC_MODELS = ['AW-', 'AG-', 'UE', 'HE', 'PTZ']
    
    # Panasonic discovery ports (used by Easy IP Setup)
    PANASONIC_DISCOVERY_PORTS = [10669, 10670, 10671]
    
    def __init__(self):
        self.discovered_cameras: Dict[str, DiscoveredCamera] = {}
        self._running = False
        self._lock = threading.Lock()
        self._progress_callback: Optional[Callable[[str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    def _report_progress(self, message: str):
        """Report progress to callback"""
        if self._progress_callback:
            try:
                self._progress_callback(message)
            except:
                pass
        print(f"[Discovery] {message}")
    
    def _on_camera_found(self, camera: DiscoveredCamera) -> bool:
        """Callback when a camera is discovered. Returns True if new camera."""
        with self._lock:
            if camera.ip_address not in self.discovered_cameras:
                self.discovered_cameras[camera.ip_address] = camera
                self._report_progress(f"Found: {camera.name or camera.ip_address} ({camera.model or 'Unknown'})")
                return True
            else:
                # Update existing camera with new info if available
                existing = self.discovered_cameras[camera.ip_address]
                if camera.model and not existing.model:
                    existing.model = camera.model
                if camera.mac_address and not existing.mac_address:
                    existing.mac_address = camera.mac_address
                if camera.serial and not existing.serial:
                    existing.serial = camera.serial
                if camera.firmware and not existing.firmware:
                    existing.firmware = camera.firmware
                if camera.name and not existing.name:
                    existing.name = camera.name
                return False
    
    def _get_camera_info_http(self, camera: DiscoveredCamera):
        """Get additional camera info via Panasonic HTTP API"""
        try:
            base_url = f"http://{camera.ip_address}"
            auth = ('admin', 'admin')
            timeout = 2
            
            # Try to get model/OID
            try:
                url = f"{base_url}/cgi-bin/aw_cam?cmd=QID&res=1"
                response = requests.get(url, timeout=timeout, auth=auth)
                if response.status_code == 200:
                    text = response.text.strip()
                    if 'OID:' in text:
                        camera.model = text.split('OID:')[1].strip()[:30]
            except:
                pass
            
            # Try to get serial number
            try:
                url = f"{base_url}/cgi-bin/aw_cam?cmd=QSN&res=1"
                response = requests.get(url, timeout=timeout, auth=auth)
                if response.status_code == 200:
                    text = response.text.strip()
                    if 'SN:' in text:
                        camera.serial = text.split('SN:')[1].strip()
            except:
                pass
            
            # Try to get firmware version
            try:
                url = f"{base_url}/cgi-bin/aw_cam?cmd=QSV&res=1"
                response = requests.get(url, timeout=timeout, auth=auth)
                if response.status_code == 200:
                    text = response.text.strip()
                    if 'SV:' in text:
                        camera.firmware = text.split('SV:')[1].strip()
            except:
                pass
            
            # Try to get camera title/name
            try:
                url = f"{base_url}/cgi-bin/aw_cam?cmd=QCT&res=1"
                response = requests.get(url, timeout=timeout, auth=auth)
                if response.status_code == 200:
                    text = response.text.strip()
                    if 'CT:' in text:
                        title = text.split('CT:')[1].strip()
                        if title:
                            camera.name = title
            except:
                pass
            
            # Set default name if not set
            if not camera.name:
                camera.name = camera.model or f"Camera ({camera.ip_address})"
                
        except Exception as e:
            if not camera.name:
                camera.name = f"Camera ({camera.ip_address})"
    
    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return None
    
    def _parse_panasonic_response(self, data: bytes, camera: DiscoveredCamera):
        """Parse Panasonic UDP discovery response"""
        try:
            # Try to decode as text
            text = data.decode('utf-8', errors='ignore')
            
            # Look for model patterns in response
            if 'AW-' in text or 'UE' in text or 'HE' in text:
                match = re.search(r'(AW-[A-Z0-9]+|UE[0-9]+|HE[0-9]+)', text)
                if match:
                    camera.model = match.group(1)
            
            # Look for MAC address pattern in text
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', text)
            if mac_match:
                camera.mac_address = mac_match.group(0).upper()
            
            # Parse binary response format
            # Panasonic cameras typically respond with structured data
            if len(data) >= 6:
                # Try to extract MAC from binary data at common offsets
                for offset in [0, 4, 6, 8]:
                    if offset + 6 <= len(data):
                        mac_bytes = data[offset:offset + 6]
                        # Check if it looks like a valid MAC (not all zeros or all ones)
                        if (mac_bytes != b'\x00\x00\x00\x00\x00\x00' and 
                            mac_bytes != b'\xff\xff\xff\xff\xff\xff' and
                            any(b != 0 for b in mac_bytes[:3])):
                            # Check for Panasonic OUI prefixes
                            # Panasonic uses several OUIs including 00:80:45, 00:1B:E3, etc.
                            potential_mac = ':'.join(f'{b:02X}' for b in mac_bytes)
                            if not camera.mac_address:
                                camera.mac_address = potential_mac
                            break
                        
        except Exception as e:
            pass
    
    def _panasonic_udp_discover(self) -> List[DiscoveredCamera]:
        """
        Discover cameras via Panasonic proprietary UDP protocol.
        This is the same method used by Easy IP Setup tool.
        """
        cameras = []
        found_ips = set()
        
        # Get local network info
        local_ip = self._get_local_ip()
        if not local_ip:
            self._report_progress("Could not determine local IP address")
            return cameras
        
        base_ip = '.'.join(local_ip.split('.')[:-1])
        self._report_progress(f"Scanning network {base_ip}.x ...")
        
        # Panasonic discovery packets - various formats
        discovery_packets = [
            # Simple discovery probe (most common)
            b'\x00\x00\x00\x01',
            # Alternative formats used by Easy IP Setup
            b'\x00\x00\x00\x00',
            bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01]),
            # PTCP search command
            b'SEARCH * PTCP/1.0\r\n\r\n',
        ]
        
        # Try each Panasonic discovery port
        for port in self.PANASONIC_DISCOVERY_PORTS:
            self._report_progress(f"Scanning UDP port {port}...")
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.5)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Bind to receive responses
                try:
                    sock.bind(('', port))
                except:
                    sock.bind(('', 0))
                
                # Send discovery packets
                for packet in discovery_packets:
                    try:
                        # Broadcast to 255.255.255.255
                        sock.sendto(packet, ('255.255.255.255', port))
                        # Broadcast to subnet broadcast address
                        sock.sendto(packet, (f'{base_ip}.255', port))
                        # Also try <broadcast>
                        sock.sendto(packet, ('<broadcast>', port))
                    except Exception as e:
                        pass
                
                # Small delay to allow responses
                time.sleep(0.1)
                
                # Receive responses
                end_time = time.time() + 3
                while time.time() < end_time:
                    try:
                        data, addr = sock.recvfrom(4096)
                        
                        # Skip if already found or if it's our own broadcast
                        if addr[0] in found_ips or addr[0] == local_ip:
                            continue
                        
                        if len(data) > 0:
                            camera = DiscoveredCamera(ip_address=addr[0])
                            
                            # Parse response for camera info
                            self._parse_panasonic_response(data, camera)
                            
                            found_ips.add(addr[0])
                            cameras.append(camera)
                            self._report_progress(f"Found device at {addr[0]}")
                                
                    except socket.timeout:
                        continue
                    except Exception as e:
                        continue
                
                sock.close()
                
            except Exception as e:
                self._report_progress(f"Error on port {port}: {e}")
                continue
        
        return cameras
    
    def discover(self, timeout: float = 10.0, use_http_probe: bool = False) -> List[DiscoveredCamera]:
        """
        Discover Panasonic PTZ cameras on the network.
        Uses Panasonic UDP broadcast protocol like Easy IP Setup.
        
        Args:
            timeout: Discovery timeout in seconds (not currently used, kept for compatibility)
            use_http_probe: Ignored (kept for compatibility)
            
        Returns:
            List of discovered cameras with full information
        """
        self.discovered_cameras.clear()
        self._report_progress("Starting Panasonic camera discovery...")
        
        # Run Panasonic UDP broadcast discovery
        try:
            cameras = self._panasonic_udp_discover()
            
            # Register found cameras
            for camera in cameras:
                self._on_camera_found(camera)
                
        except Exception as e:
            self._report_progress(f"Discovery error: {e}")
        
        # Get detailed info for each camera via HTTP API
        if self.discovered_cameras:
            self._report_progress("Fetching camera details...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(self._get_camera_info_http, self.discovered_cameras.values()))
        
        result = list(self.discovered_cameras.values())
        self._report_progress(f"Discovery complete: {len(result)} camera(s) found")
        
        return result
    
    def discover_async(self, callback: Callable[[DiscoveredCamera], None], 
                       use_http_probe: bool = False) -> threading.Thread:
        """
        Discover cameras asynchronously, calling callback for each found camera.
        
        Args:
            callback: Function to call for each discovered camera
            use_http_probe: Ignored (kept for compatibility)
            
        Returns:
            The discovery thread
        """
        def _discover_thread():
            cameras = self.discover()
            for camera in cameras:
                try:
                    callback(camera)
                except:
                    pass
        
        thread = threading.Thread(target=_discover_thread, daemon=True)
        thread.start()
        return thread
    
    # Legacy methods for compatibility
    def start_continuous_discovery(self, callback: Callable[[DiscoveredCamera], None]):
        """Start continuous background discovery (legacy compatibility)"""
        self.discover_async(callback)
    
    def stop_continuous_discovery(self):
        """Stop continuous discovery (legacy compatibility)"""
        self._running = False
