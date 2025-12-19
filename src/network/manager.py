"""
Network Manager

Provides network diagnostics, port scanning, and configuration management
for Panasonic PTZ cameras.
"""
import socket
import time
import json
import os
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class NetworkDiagnostics:
    """Network diagnostics results"""
    ip_address: str
    ping_success: bool = False
    ping_time_ms: float = 0.0
    http_reachable: bool = False
    http_status_code: int = 0
    http_response_time_ms: float = 0.0
    port_80_open: bool = False
    port_554_open: bool = False  # RTSP
    port_10669_open: bool = False  # Panasonic discovery
    port_10670_open: bool = False  # Panasonic discovery
    error_message: str = ""


class NetworkManager:
    """Manages network operations for Panasonic cameras"""
    
    def __init__(self):
        pass
    
    def ping_camera(self, ip_address: str, timeout: float = 2.0) -> Tuple[bool, float]:
        """
        Ping a camera IP address using TCP port check (faster than subprocess ping).

        Tests connectivity by attempting to connect to HTTP port 80.
        This is much faster than subprocess ping and doesn't require privileges.

        Returns:
            Tuple of (success, time_ms)
        """
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, 80))
            sock.close()
            elapsed_ms = (time.time() - start_time) * 1000

            return (result == 0, elapsed_ms)
        except (socket.timeout, OSError):
            return (False, timeout * 1000)
        except Exception:
            return (False, 0.0)
    
    def check_http_connectivity(self, ip_address: str, port: int = 80, 
                                username: str = "", password: str = "",
                                timeout: float = 3.0) -> Tuple[bool, int, float]:
        """
        Check HTTP connectivity to camera.
        
        Returns:
            Tuple of (success, status_code, response_time_ms)
        """
        try:
            url = f"http://{ip_address}:{port}"
            auth = None
            if username and password:
                auth = (username, password)
            
            start_time = time.time()
            response = requests.get(
                url,
                auth=auth,
                timeout=timeout,
                allow_redirects=False
            )
            elapsed_ms = (time.time() - start_time) * 1000
            
            return True, response.status_code, elapsed_ms
        except requests.exceptions.Timeout:
            return False, 0, timeout * 1000
        except requests.exceptions.ConnectionError:
            return False, 0, 0.0
        except Exception as e:
            return False, 0, 0.0
    
    def check_port_open(self, ip_address: str, port: int, timeout: float = 2.0) -> bool:
        """Check if a TCP port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def scan_camera_ports(self, ip_address: str) -> Dict[str, bool]:
        """Scan common camera ports"""
        ports = {
            'port_80': 80,      # HTTP
            'port_554': 554,     # RTSP
            'port_10669': 10669, # Panasonic discovery
            'port_10670': 10670, # Panasonic discovery
        }
        
        results = {}
        for key, port in ports.items():
            results[key] = self.check_port_open(ip_address, port, timeout=1.0)
        
        return results
    
    def run_diagnostics(self, ip_address: str, username: str = "", 
                       password: str = "") -> NetworkDiagnostics:
        """Run full network diagnostics on a camera"""
        diagnostics = NetworkDiagnostics(ip_address=ip_address)
        
        # Ping test
        ping_success, ping_time = self.ping_camera(ip_address)
        diagnostics.ping_success = ping_success
        diagnostics.ping_time_ms = ping_time
        
        # HTTP connectivity
        http_success, http_status, http_time = self.check_http_connectivity(
            ip_address, username=username, password=password
        )
        diagnostics.http_reachable = http_success
        diagnostics.http_status_code = http_status
        diagnostics.http_response_time_ms = http_time
        
        # Port scanning
        port_results = self.scan_camera_ports(ip_address)
        diagnostics.port_80_open = port_results.get('port_80', False)
        diagnostics.port_554_open = port_results.get('port_554', False)
        diagnostics.port_10669_open = port_results.get('port_10669', False)
        diagnostics.port_10670_open = port_results.get('port_10670', False)
        
        return diagnostics
    
    def scan_network_range(self, base_ip: str, start: int = 1, end: int = 254,
                          ports: List[int] = None, max_workers: int = 50) -> List[Dict]:
        """
        Scan a network range for open ports using parallel execution.

        Optimized for speed using ThreadPoolExecutor with many concurrent connections.

        Args:
            base_ip: Base IP like "192.168.1" (without last octet)
            start: Start of range (default 1)
            end: End of range (default 254)
            ports: List of ports to scan (default [80, 554])
            max_workers: Max concurrent threads (default 50 for fast scanning)

        Returns:
            List of dicts with 'ip', 'ports_open' info
        """
        if ports is None:
            ports = [80, 554]  # HTTP and RTSP

        def scan_ip(i: int) -> Optional[Dict]:
            """Scan a single IP address"""
            ip = f"{base_ip}.{i}"

            # Quick ping first
            ping_success, _ = self.ping_camera(ip, timeout=0.5)
            if not ping_success:
                return None

            # Check ports
            open_ports = []
            for port in ports:
                if self.check_port_open(ip, port, timeout=0.5):
                    open_ports.append(port)

            if open_ports:
                return {
                    'ip': ip,
                    'ports_open': open_ports,
                    'ping_success': True
                }
            return None

        results = []

        # Parallel scanning for much better performance
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(scan_ip, i): i for i in range(start, end + 1)}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception:
                    pass  # Ignore individual scan failures

        return results
    
    @staticmethod
    def backup_network_configs(cameras: List, filepath: str) -> bool:
        """
        Backup camera network configurations to JSON file.
        
        Args:
            cameras: List of camera config objects
            filepath: Path to save backup file
        """
        try:
            backup_data = {
                'timestamp': time.time(),
                'cameras': []
            }
            
            for camera in cameras:
                camera_data = {
                    'id': getattr(camera, 'id', None),
                    'name': getattr(camera, 'name', ''),
                    'ip_address': getattr(camera, 'ip_address', ''),
                    'port': getattr(camera, 'port', 80),
                    'username': getattr(camera, 'username', ''),
                    'password': getattr(camera, 'password', ''),
                }
                backup_data['cameras'].append(camera_data)
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error backing up network configs: {e}")
            return False
    
    @staticmethod
    def restore_network_configs(filepath: str) -> Optional[Dict]:
        """
        Restore camera network configurations from JSON file.
        
        Returns:
            Dict with backup data or None if error
        """
        try:
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r') as f:
                backup_data = json.load(f)
            
            return backup_data
        except Exception as e:
            print(f"Error restoring network configs: {e}")
            return None

























