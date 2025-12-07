"""
Panasonic PTZ Camera Implementation

Implements the Camera interface for Panasonic PTZ cameras.
Handles camera control via HTTP/CGI API.
"""
import requests
import numpy as np
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import yaml

from .base import Camera
from .stream import CameraStream, StreamConfig


class PanasonicCamera(Camera):
    """
    Panasonic PTZ camera implementation.
    
    Supports camera control via HTTP/CGI API:
    - /cgi-bin/aw_cam?cmd=... (camera settings)
    - /cgi-bin/aw_ptz?cmd=... (PTZ control)
    """
    
    def __init__(self, camera_id: int, name: str, ip_address: str, 
                 port: int = 80, username: str = "admin", password: str = "admin",
                 model: str = "UE150"):
        """
        Initialize Panasonic camera.
        
        Args:
            camera_id: Unique camera identifier
            name: Camera name/label
            ip_address: Camera IP address
            port: HTTP port (default 80)
            username: HTTP auth username
            password: HTTP auth password
            model: Camera model (UE150, HE40, etc.) - used for command mapping
        """
        super().__init__(camera_id, name, ip_address)
        self.port = port
        self.username = username
        self.password = password
        self.model = model
        
        # Stream handler
        stream_config = StreamConfig(
            ip_address=ip_address,
            port=port,
            username=username,
            password=password
        )
        self._stream = CameraStream(stream_config)
        
        # Load command mappings from YAML
        self._command_map: Dict[str, Any] = {}
        self._load_command_map()
        
        # State tracking
        self._streaming = False
        self._current_fps = 0.0
    
    def _load_command_map(self):
        """Load camera command mappings from YAML file"""
        config_path = Path(__file__).parent.parent.parent / "config" / "cameras" / f"{self.model.lower()}.yaml"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self._command_map = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading command map for {self.model}: {e}")
        else:
            # Use default/fallback commands
            self._command_map = self._get_default_commands()
    
    def _get_default_commands(self) -> Dict[str, Any]:
        """Get default command mappings (fallback)"""
        return {
            'exposure': {
                'iris_mode': {'command': 'OSD:48:{data}', 'options': {'Manual': '0', 'Auto': '1'}},
                'iris_value': {'command': 'OSD:49:{data}'},
                'gain_mode': {'command': 'OSD:50:{data}', 'options': {'Manual': '0', 'Auto': '1'}},
                'gain_value': {'command': 'OSD:51:{data}'},
                'shutter_mode': {'command': 'OSD:52:{data}', 'options': {'Manual': '0', 'Auto': '1'}},
                'shutter_value': {'command': 'OSD:53:{data}'},
            },
            'color': {
                'white_balance': {'command': 'OSD:54:{data}', 'options': {'Auto': '0', 'Indoor': '1', 'Outdoor': '2', 'Manual': '3'}},
                'color_temperature': {'command': 'OSD:55:{data}'},
                'gamma': {'command': 'OSD:56:{data}', 'options': {'Standard': '0', 'Cinema': '1', 'Wide': '2'}},
            },
            'ptz': {
                'preset_recall': {'command': 'R{data:02d}'},
                'preset_save': {'command': 'M{data:02d}'},
            }
        }
    
    def _send_command(self, command: str, endpoint: str = "aw_cam") -> bool:
        """
        Send HTTP command to camera.
        
        Args:
            command: Command string (e.g., "OSD:48:0" or "R01")
            endpoint: CGI endpoint ("aw_cam" or "aw_ptz")
            
        Returns:
            True if command sent successfully
        """
        try:
            url = f"http://{self.ip_address}:{self.port}/cgi-bin/{endpoint}?cmd={command}&res=1"
            response = requests.get(url, auth=(self.username, self.password), timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            print(f"Camera command error: {e}")
            return False
    
    def start_stream(self) -> bool:
        """Start video stream"""
        if not self._streaming:
            self._stream.start(use_rtsp=True)
            self._streaming = True
        return True
    
    def stop_stream(self):
        """Stop video stream"""
        if self._streaming:
            self._stream.stop()
            self._streaming = False
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current frame from stream"""
        return self._stream.current_frame
    
    def is_streaming(self) -> bool:
        """Check if stream is active"""
        return self._streaming and self._stream.is_connected
    
    @property
    def fps(self) -> float:
        """Get current frames per second"""
        return self._stream.fps if self._streaming else 0.0
    
    def set_exposure_setting(self, setting: str, value: Any) -> bool:
        """
        Set exposure setting (iris, gain, shutter, ND).
        
        Args:
            setting: Setting name (e.g., 'iris_mode', 'iris_value', 'gain_mode')
            value: Setting value
            
        Returns:
            True if command sent successfully
        """
        if 'exposure' not in self._command_map:
            return False
        
        exp_map = self._command_map.get('exposure', {})
        if setting not in exp_map:
            return False
        
        cmd_def = exp_map[setting]
        cmd_template = cmd_def.get('command', '')
        
        # Format command with value
        if '{data}' in cmd_template:
            cmd = cmd_template.format(data=str(value))
        else:
            cmd = cmd_template
        
        return self._send_command(cmd)
    
    def set_color_setting(self, setting: str, value: Any) -> bool:
        """
        Set color setting (WB, temperature, gamma, matrix).
        
        Args:
            setting: Setting name (e.g., 'white_balance', 'color_temperature')
            value: Setting value
            
        Returns:
            True if command sent successfully
        """
        if 'color' not in self._command_map:
            return False
        
        color_map = self._command_map.get('color', {})
        if setting not in color_map:
            return False
        
        cmd_def = color_map[setting]
        cmd_template = cmd_def.get('command', '')
        
        # Format command with value
        if '{data}' in cmd_template:
            cmd = cmd_template.format(data=str(value))
        else:
            cmd = cmd_template
        
        return self._send_command(cmd)
    
    def recall_preset(self, preset_number: int) -> bool:
        """
        Recall PTZ preset.
        
        Args:
            preset_number: Preset number (1-100)
            
        Returns:
            True if command sent successfully
        """
        if 'ptz' not in self._command_map:
            return False
        
        ptz_map = self._command_map.get('ptz', {})
        preset_cmd = ptz_map.get('preset_recall', {}).get('command', 'R{data:02d}')
        
        cmd = preset_cmd.format(data=preset_number)
        return self._send_command(cmd, endpoint="aw_ptz")
    
    def save_preset(self, preset_number: int) -> bool:
        """
        Save current PTZ position as preset.
        
        Args:
            preset_number: Preset number (1-100)
            
        Returns:
            True if command sent successfully
        """
        if 'ptz' not in self._command_map:
            return False
        
        ptz_map = self._command_map.get('ptz', {})
        preset_cmd = ptz_map.get('preset_save', {}).get('command', 'M{data:02d}')
        
        cmd = preset_cmd.format(data=preset_number)
        return self._send_command(cmd, endpoint="aw_ptz")




