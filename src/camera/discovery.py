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
    # New fields from EasyIPSetupToolPlus research
    status: str = "Unknown"  # "Power ON", "Standby", "Offline", "Auth Required"
    auth_required: bool = False
    reachable: bool = False


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
        self._selected_adapter: Optional[str] = None  # Network adapter IP to use
    
    @staticmethod
    def get_network_adapters() -> List[Dict[str, str]]:
        """
        Get list of available network adapters with their IP addresses.
        Similar to EasyIPSetupToolPlus network pulldown.
        
        Returns:
            List of dicts with 'name', 'ip', 'netmask' keys
        """
        adapters = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get('addr', '')
                        netmask = addr.get('netmask', '')
                        if ip and not ip.startswith('127.'):
                            adapters.append({
                                'name': iface,
                                'ip': ip,
                                'netmask': netmask
                            })
        except ImportError:
            # Fallback if netifaces not available
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip and not local_ip.startswith('127.'):
                    adapters.append({
                        'name': 'default',
                        'ip': local_ip,
                        'netmask': '255.255.255.0'
                    })
            except:
                pass
            # Also try socket method
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                if local_ip and not any(a['ip'] == local_ip for a in adapters):
                    adapters.append({
                        'name': 'default',
                        'ip': local_ip,
                        'netmask': '255.255.255.0'
                    })
            except:
                pass
        return adapters
    
    def set_network_adapter(self, adapter_ip: Optional[str]):
        """Set which network adapter to use for discovery"""
        self._selected_adapter = adapter_ip
    
    @staticmethod
    def identify_camera(ip_address: str, username: str = "admin", password: str = "12345", duration: int = 5) -> bool:
        """
        Make camera LED blink rapidly to identify it physically.
        Similar to EasyIPSetupToolPlus Identify feature.
        
        Args:
            ip_address: Camera IP address
            username: Camera username
            password: Camera password  
            duration: How long to blink in seconds (default 5)
            
        Returns:
            True if command was sent successfully
        """
        try:
            auth = (username, password) if username else None
            base_url = f"http://{ip_address}"
            
            # Panasonic identify commands - try multiple formats
            identify_commands = [
                # XSF command for LED control (common on newer models)
                f"{base_url}/cgi-bin/aw_cam?cmd=XSF:01&res=1",
                # Alternative LED blink command
                f"{base_url}/cgi-bin/aw_cam?cmd=%23LED1&res=1",
                # Power indicator high-speed blink
                f"{base_url}/cgi-bin/aw_cam?cmd=%23D11&res=1",
            ]
            
            for cmd_url in identify_commands:
                try:
                    response = requests.get(cmd_url, auth=auth, timeout=2)
                    if response.status_code == 200:
                        # Success - LED should be blinking
                        # Schedule turning it off after duration
                        def stop_identify():
                            time.sleep(duration)
                            try:
                                # Turn off identify
                                requests.get(f"{base_url}/cgi-bin/aw_cam?cmd=XSF:00&res=1", 
                                           auth=auth, timeout=2)
                                requests.get(f"{base_url}/cgi-bin/aw_cam?cmd=%23LED0&res=1",
                                           auth=auth, timeout=2)
                                requests.get(f"{base_url}/cgi-bin/aw_cam?cmd=%23D10&res=1",
                                           auth=auth, timeout=2)
                            except:
                                pass
                        
                        threading.Thread(target=stop_identify, daemon=True).start()
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            print(f"[Discovery] Identify error: {e}")
            return False
    
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
        """Get additional camera info via Panasonic HTTP API with auth detection"""
        try:
            base_url = f"http://{camera.ip_address}"
            # Try both common default credentials
            credentials_to_try = [
                ('admin', '12345'),  # Newer Panasonic default
                ('admin', 'admin'),  # Older default
                (None, None),        # No auth
            ]
            timeout = 2
            working_auth = None
            
            # First, test connectivity and auth
            for auth_pair in credentials_to_try:
                try:
                    auth = auth_pair if auth_pair[0] else None
                    url = f"{base_url}/cgi-bin/aw_cam?cmd=QID&res=1"
                    response = requests.get(url, timeout=timeout, auth=auth)
                    
                    if response.status_code == 200:
                        camera.reachable = True
                        camera.auth_required = (auth is not None)
                        working_auth = auth
                        text = response.text.strip()
                        if 'OID:' in text:
                            camera.model = text.split('OID:')[1].strip()[:30]
                        break
                    elif response.status_code == 401:
                        camera.reachable = True
                        camera.auth_required = True
                        camera.status = "Auth Required"
                        # Continue trying other credentials
                        continue
                    elif response.status_code == 403:
                        camera.reachable = True
                        camera.auth_required = True
                        camera.status = "Auth Required"
                        continue
                except requests.exceptions.ConnectTimeout:
                    camera.status = "Offline"
                    camera.reachable = False
                    return
                except requests.exceptions.ConnectionError:
                    camera.status = "Offline"
                    camera.reachable = False
                    return
                except:
                    continue
            
            # If no working auth found but camera responded with 401, mark as auth required
            if not working_auth and camera.auth_required:
                camera.status = "Auth Required"
                if not camera.name:
                    camera.name = f"Camera ({camera.ip_address})"
                return
            
            # Continue fetching info with working credentials
            auth = working_auth
            
            # Try to get power status (similar to EasyIPSetupToolPlus)
            try:
                url = f"{base_url}/cgi-bin/aw_cam?cmd=O&res=1"
                response = requests.get(url, timeout=timeout, auth=auth)
                if response.status_code == 200:
                    text = response.text.strip().upper()
                    if 'P1' in text or 'O1' in text:
                        camera.status = "Power ON"
                    elif 'P0' in text or 'O0' in text:
                        camera.status = "Standby"
                    else:
                        camera.status = "Power ON"  # Assume on if responding
            except:
                if camera.reachable:
                    camera.status = "Power ON"
            
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
            camera.status = "Offline"
            if not camera.name:
                camera.name = f"Camera ({camera.ip_address})"
    
    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address, using selected adapter if set"""
        # If a specific adapter is selected, use its IP
        if self._selected_adapter:
            return self._selected_adapter
        
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
    
    @staticmethod
    def get_camera_thumbnail(ip_address: str, username: str = "admin", password: str = "12345", 
                             size: tuple = (160, 90)) -> Optional[bytes]:
        """
        Get a thumbnail image from a camera for preview.
        
        Args:
            ip_address: Camera IP address
            username: Camera username
            password: Camera password
            size: Desired thumbnail size (width, height)
            
        Returns:
            JPEG image bytes or None if failed
        """
        try:
            import cv2
            import numpy as np
            
            auth = (username, password) if username else None
            
            # Try snapshot endpoint first (faster)
            snapshot_urls = [
                f"http://{ip_address}/cgi-bin/mjpeg?resolution={size[0]}x{size[1]}",
                f"http://{ip_address}/cgi-bin/camera?resolution={size[0]}x{size[1]}",
                f"http://{ip_address}/snapshot.jpg",
            ]
            
            for url in snapshot_urls:
                try:
                    response = requests.get(url, auth=auth, timeout=3, stream=True)
                    if response.status_code == 200:
                        img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        if img is not None:
                            # Resize if needed
                            if img.shape[1] != size[0] or img.shape[0] != size[1]:
                                img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
                            _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            return jpeg.tobytes()
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"[Discovery] Thumbnail error for {ip_address}: {e}")
            return None
    
    @staticmethod
    def check_camera_status(ip_address: str, username: str = "admin", password: str = "12345") -> str:
        """
        Quick check of camera status without full discovery.
        
        Args:
            ip_address: Camera IP address
            username: Camera username
            password: Camera password
            
        Returns:
            Status string: "Power ON", "Standby", "Auth Required", "Offline"
        """
        try:
            auth = (username, password) if username else None
            
            # Try power status command
            url = f"http://{ip_address}/cgi-bin/aw_cam?cmd=O&res=1"
            response = requests.get(url, auth=auth, timeout=2)
            
            if response.status_code == 200:
                text = response.text.strip().upper()
                if 'P1' in text or 'O1' in text:
                    return "Power ON"
                elif 'P0' in text or 'O0' in text:
                    return "Standby"
                else:
                    return "Power ON"  # Responding = online
            elif response.status_code in (401, 403):
                return "Auth Required"
            else:
                return "Offline"
                
        except requests.exceptions.ConnectTimeout:
            return "Offline"
        except requests.exceptions.ConnectionError:
            return "Offline"
        except:
            return "Unknown"
    
    # Legacy methods for compatibility
    def start_continuous_discovery(self, callback: Callable[[DiscoveredCamera], None]):
        """Start continuous background discovery (legacy compatibility)"""
        self.discover_async(callback)
    
    def stop_continuous_discovery(self):
        """Stop continuous discovery (legacy compatibility)"""
        self._running = False
