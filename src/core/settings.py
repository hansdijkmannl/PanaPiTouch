"""
Enhanced Settings with Pydantic validation

Migrated from dataclasses to Pydantic for better validation and type safety.

NOTE: This module requires pydantic>=2.0.0 to be installed.
It is optional - the app will continue to use config.settings (dataclass-based)
until pydantic is installed and migration is complete.
"""
try:
    from pathlib import Path
    from typing import List, Optional, Dict
    import yaml
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    # Pydantic not installed - this module is not available yet
    raise ImportError(
        "core.settings requires pydantic>=2.0.0. "
        "Install with: pip install pydantic>=2.0.0\n"
        "The app will continue to use config.settings until pydantic is installed."
    )


class CameraConfig(BaseModel):
    """Configuration for a single camera"""
    id: int
    name: str
    ip_address: str = Field(..., description="Camera IP address")
    port: int = Field(default=80, ge=1, le=65535)
    username: str = Field(default="admin")
    password: str = Field(default="admin")
    enabled: bool = Field(default=True)
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Basic IP address validation"""
        parts = v.split('.')
        if len(parts) != 4:
            raise ValueError("Invalid IP address format")
        for part in parts:
            if not part.isdigit() or not (0 <= int(part) <= 255):
                raise ValueError("Invalid IP address format")
        return v
    
    def get_stream_url(self) -> str:
        """Get MJPEG stream URL for Panasonic PTZ cameras"""
        return f"http://{self.ip_address}:{self.port}/cgi-bin/mjpeg"
    
    def get_snapshot_url(self) -> str:
        """Get snapshot URL"""
        return f"http://{self.ip_address}:{self.port}/cgi-bin/camera?resolution=1920x1080"
    
    def get_web_interface_url(self) -> str:
        """Get web interface URL"""
        return f"http://{self.ip_address}:{self.port}/"


class ATEMConfig(BaseModel):
    """Configuration for Blackmagic ATEM switcher"""
    ip_address: str = Field(default="")
    enabled: bool = Field(default=False)
    input_mapping: Dict[int, int] = Field(default_factory=dict)  # camera_id -> atem_input


class Settings(BaseModel):
    """Main application settings with Pydantic validation and dirty flag optimization"""
    cameras: List[CameraConfig] = Field(default_factory=list)
    atem: ATEMConfig = Field(default_factory=ATEMConfig)
    selected_camera: int = Field(default=0, ge=0)
    companion_url: str = Field(default="http://localhost:8000")

    # Companion integration settings
    companion_enabled: bool = Field(default=False)
    companion_control_mode: str = Field(default="hybrid")  # "direct", "companion", or "hybrid"
    companion_page: int = Field(default=1, ge=1, le=99)  # Companion page for camera controls

    # Display settings
    fullscreen: bool = Field(default=False)
    display_width: int = Field(default=1600, ge=640)
    display_height: int = Field(default=1000, ge=480)
    native_width: int = Field(default=2560, ge=640)
    native_height: int = Field(default=1600, ge=480)
    preview_width: int = Field(default=1920, ge=640)
    preview_height: int = Field(default=1080, ge=480)

    # Dirty flag tracking (not serialized)
    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self._dirty = False  # Track if settings changed since last save

    def mark_dirty(self):
        """Mark settings as modified (need to save)"""
        self._dirty = True

    def is_dirty(self) -> bool:
        """Check if settings have unsaved changes"""
        return getattr(self, '_dirty', False)
    
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
                
                # Convert to Pydantic models
                cameras = [CameraConfig(**cam_data) for cam_data in data.get('cameras', [])]
                atem = ATEMConfig(**data.get('atem', {}))
                
                return cls(
                    cameras=cameras,
                    atem=atem,
                    selected_camera=data.get('selected_camera', 0),
                    companion_url=data.get('companion_url', 'http://localhost:8000'),
                    companion_enabled=data.get('companion_enabled', False),
                    companion_control_mode=data.get('companion_control_mode', 'hybrid'),
                    companion_page=data.get('companion_page', 1),
                    fullscreen=data.get('fullscreen', False),
                    display_width=data.get('display_width', 1600),
                    display_height=data.get('display_height', 1000),
                    native_width=data.get('native_width', 2560),
                    native_height=data.get('native_height', 1600),
                    preview_width=data.get('preview_width', 1920),
                    preview_height=data.get('preview_height', 1080),
                )
            except Exception as e:
                print(f"Error loading settings: {e}")
                import traceback
                traceback.print_exc()
        
        # Return default settings
        return cls()
    
    def save(self, force: bool = False):
        """
        Save settings to file (only if dirty or forced).

        Args:
            force: Force save even if not dirty
        """
        # Skip save if not dirty (optimization)
        if not force and not self.is_dirty():
            return

        config_path = self.get_config_path()

        data = {
            'cameras': [cam.model_dump() for cam in self.cameras],
            'atem': self.atem.model_dump(),
            'selected_camera': self.selected_camera,
            'companion_url': self.companion_url,
            'companion_enabled': self.companion_enabled,
            'companion_control_mode': self.companion_control_mode,
            'companion_page': self.companion_page,
            'fullscreen': self.fullscreen,
            'display_width': self.display_width,
            'display_height': self.display_height,
            'native_width': self.native_width,
            'native_height': self.native_height,
            'preview_width': self.preview_width,
            'preview_height': self.preview_height,
        }

        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        self._dirty = False  # Clear dirty flag after successful save
    
    def get_camera(self, camera_id: int) -> Optional[CameraConfig]:
        """Get camera by ID"""
        for cam in self.cameras:
            if cam.id == camera_id:
                return cam
        return None
    
    def add_camera(self, camera: CameraConfig):
        """Add a camera and mark dirty"""
        if len(self.cameras) < 30:
            self.cameras.append(camera)
            self.mark_dirty()
            self.save()

    def remove_camera(self, camera_id: int):
        """Remove a camera and mark dirty"""
        self.cameras = [c for c in self.cameras if c.id != camera_id]
        self.mark_dirty()
        self.save()

    def update_camera(self, camera: CameraConfig):
        """Update a camera and mark dirty"""
        for i, cam in enumerate(self.cameras):
            if cam.id == camera.id:
                self.cameras[i] = camera
                self.mark_dirty()
                self.save()
                return
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary for backup"""
        return {
            'cameras': [cam.model_dump() for cam in self.cameras],
            'atem': self.atem.model_dump(),
            'selected_camera': self.selected_camera,
            'companion_url': self.companion_url,
            'companion_enabled': self.companion_enabled,
            'companion_control_mode': self.companion_control_mode,
            'companion_page': self.companion_page,
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
        cameras = [CameraConfig(**cam_data) for cam_data in data.get('cameras', [])]
        atem = ATEMConfig(**data.get('atem', {}))
        
        self.cameras = cameras
        self.atem = atem
        self.selected_camera = data.get('selected_camera', 0)
        self.companion_url = data.get('companion_url', 'http://localhost:8000')
        self.companion_enabled = data.get('companion_enabled', False)
        self.companion_control_mode = data.get('companion_control_mode', 'hybrid')
        self.companion_page = data.get('companion_page', 1)
        self.fullscreen = data.get('fullscreen', False)
        self.display_width = data.get('display_width', 1600)
        self.display_height = data.get('display_height', 1000)
        self.native_width = data.get('native_width', 2560)
        self.native_height = data.get('native_height', 1600)
        self.preview_width = data.get('preview_width', 1920)
        self.preview_height = data.get('preview_height', 1080)
