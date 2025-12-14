"""
Configuration management for PanaPiTouch
"""
import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class CameraConfig:
    """Configuration for a single camera"""
    id: int
    name: str
    ip_address: str
    port: int = 80
    username: str = "admin"
    password: str = "admin"
    enabled: bool = True
    
    def get_stream_url(self) -> str:
        """Get MJPEG stream URL for Panasonic PTZ cameras"""
        # Panasonic PTZ cameras typically use this endpoint for live preview
        return f"http://{self.ip_address}:{self.port}/cgi-bin/mjpeg"
    
    def get_snapshot_url(self) -> str:
        """Get snapshot URL"""
        return f"http://{self.ip_address}:{self.port}/cgi-bin/camera?resolution=1920x1080"
    
    def get_web_interface_url(self) -> str:
        """Get web interface URL"""
        return f"http://{self.ip_address}:{self.port}/"


@dataclass
class ATEMConfig:
    """Configuration for Blackmagic ATEM switcher"""
    ip_address: str = ""
    enabled: bool = False
    # Camera to ATEM input mapping (camera_id -> atem_input)
    input_mapping: dict = field(default_factory=dict)


@dataclass
class Settings:
    """Main application settings"""
    cameras: List[CameraConfig] = field(default_factory=list)
    atem: ATEMConfig = field(default_factory=ATEMConfig)
    selected_camera: int = 0
    companion_url: str = "http://localhost:8000"
    # Orientation mode
    portrait_mode: bool = False  # False = landscape, True = portrait
    # Target display: Wisecoco 10.5" 2560x1600 (16:10)
    fullscreen: bool = False  # False for development
    display_width: int = 1600  # Dev window (16:10 aspect)
    display_height: int = 1000
    # Native resolution for fullscreen
    native_width: int = 2560
    native_height: int = 1600
    preview_width: int = 1920
    preview_height: int = 1080
    # OSK preset texts (6 customizable preset buttons)
    osk_presets: List[str] = field(default_factory=lambda: ["", "", "", "", "", ""])
    
    _config_path: str = field(default="", repr=False)
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Get the configuration file path"""
        config_dir = Path.home() / ".config" / "panapitouch"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.yaml"
    
    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from file"""
        config_path = cls.get_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                
                cameras = []
                for cam_data in data.get('cameras', []):
                    cameras.append(CameraConfig(**cam_data))
                
                atem_data = data.get('atem', {})
                atem = ATEMConfig(
                    ip_address=atem_data.get('ip_address', ''),
                    enabled=atem_data.get('enabled', False),
                    input_mapping=atem_data.get('input_mapping', {})
                )
                
                settings = cls(
                    cameras=cameras,
                    atem=atem,
                    selected_camera=data.get('selected_camera', 0),
                    companion_url=data.get('companion_url', 'http://localhost:8000'),
                    portrait_mode=data.get('portrait_mode', False),
                    fullscreen=data.get('fullscreen', False),
                    display_width=data.get('display_width', 1600),
                    display_height=data.get('display_height', 1000),
                    native_width=data.get('native_width', 2560),
                    native_height=data.get('native_height', 1600),
                    preview_width=data.get('preview_width', 1920),
                    preview_height=data.get('preview_height', 1080),
                    osk_presets=data.get('osk_presets', ["", "", "", "", "", ""]),
                )
                settings._config_path = str(config_path)
                return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Return default settings
        settings = cls()
        settings._config_path = str(config_path)
        return settings
    
    def save(self):
        """Save settings to file"""
        config_path = self.get_config_path()
        
        data = {
            'cameras': [
                {
                    'id': cam.id,
                    'name': cam.name,
                    'ip_address': cam.ip_address,
                    'port': cam.port,
                    'username': cam.username,
                    'password': cam.password,
                    'enabled': cam.enabled,
                }
                for cam in self.cameras
            ],
            'atem': {
                'ip_address': self.atem.ip_address,
                'enabled': self.atem.enabled,
                'input_mapping': self.atem.input_mapping,
            },
            'selected_camera': self.selected_camera,
            'companion_url': self.companion_url,
            'portrait_mode': self.portrait_mode,
            'fullscreen': self.fullscreen,
            'display_width': self.display_width,
            'display_height': self.display_height,
            'native_width': self.native_width,
            'native_height': self.native_height,
            'preview_width': self.preview_width,
            'preview_height': self.preview_height,
            'osk_presets': self.osk_presets,
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def get_camera(self, camera_id: int) -> Optional[CameraConfig]:
        """Get camera by ID"""
        for cam in self.cameras:
            if cam.id == camera_id:
                return cam
        return None
    
    def add_camera(self, camera: CameraConfig):
        """Add a camera"""
        if len(self.cameras) < 30:
            self.cameras.append(camera)
            self.save()
    
    def remove_camera(self, camera_id: int):
        """Remove a camera"""
        self.cameras = [c for c in self.cameras if c.id != camera_id]
        self.save()
    
    def update_camera(self, camera: CameraConfig):
        """Update a camera"""
        for i, cam in enumerate(self.cameras):
            if cam.id == camera.id:
                self.cameras[i] = camera
                self.save()
                return
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary for backup"""
        return {
            'cameras': [
                {
                    'id': cam.id,
                    'name': cam.name,
                    'ip_address': cam.ip_address,
                    'port': cam.port,
                    'username': cam.username,
                    'password': cam.password,
                    'enabled': cam.enabled,
                }
                for cam in self.cameras
            ],
            'atem': {
                'ip_address': self.atem.ip_address,
                'enabled': self.atem.enabled,
                'input_mapping': self.atem.input_mapping,
            },
            'selected_camera': self.selected_camera,
            'companion_url': self.companion_url,
            'fullscreen': self.fullscreen,
            'display_width': self.display_width,
            'display_height': self.display_height,
            'native_width': self.native_width,
            'native_height': self.native_height,
            'preview_width': self.preview_width,
            'preview_height': self.preview_height,
        }
    
    def load_from_dict(self, data: dict):
        """Load settings from dictionary (for restore from backup)"""
        # Load cameras
        self.cameras = []
        for cam_data in data.get('cameras', []):
            self.cameras.append(CameraConfig(**cam_data))
        
        # Load ATEM settings
        atem_data = data.get('atem', {})
        self.atem = ATEMConfig(
            ip_address=atem_data.get('ip_address', ''),
            enabled=atem_data.get('enabled', False),
            input_mapping=atem_data.get('input_mapping', {})
        )
        
        # Load other settings
        self.selected_camera = data.get('selected_camera', 0)
        self.companion_url = data.get('companion_url', 'http://localhost:8000')
        self.fullscreen = data.get('fullscreen', False)
        self.display_width = data.get('display_width', 1600)
        self.display_height = data.get('display_height', 1000)
        self.native_width = data.get('native_width', 2560)
        self.native_height = data.get('native_height', 1600)
        self.preview_width = data.get('preview_width', 1920)
        self.preview_height = data.get('preview_height', 1080)
