"""
Base Camera Interface

Abstract interface for camera implementations.
Allows support for different camera brands/models in the future.
"""
from abc import ABC, abstractmethod
from typing import Optional, Callable, List
import numpy as np


class Camera(ABC):
    """
    Abstract base class for camera implementations.
    
    Provides a common interface for different camera types:
    - Panasonic PTZ cameras
    - Generic RTSP cameras
    - Future: Sony, Canon, etc.
    """
    
    def __init__(self, camera_id: int, name: str, ip_address: str):
        """
        Initialize camera.
        
        Args:
            camera_id: Unique camera identifier
            name: Camera name/label
            ip_address: Camera IP address
        """
        self.camera_id = camera_id
        self.name = name
        self.ip_address = ip_address
        self._frame_callbacks: List[Callable[[np.ndarray], None]] = []
    
    @abstractmethod
    def start_stream(self) -> bool:
        """
        Start video stream.
        
        Returns:
            True if stream started successfully
        """
        pass
    
    @abstractmethod
    def stop_stream(self):
        """Stop video stream"""
        pass
    
    @abstractmethod
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get current frame from stream.
        
        Returns:
            Current frame (BGR format) or None if not available
        """
        pass
    
    @abstractmethod
    def is_streaming(self) -> bool:
        """Check if stream is active"""
        pass
    
    @property
    @abstractmethod
    def fps(self) -> float:
        """Get current frames per second"""
        pass
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Add callback for new frames"""
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Remove frame callback"""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
    
    def _notify_frame_callbacks(self, frame: np.ndarray):
        """Notify all callbacks of new frame"""
        for callback in self._frame_callbacks:
            try:
                callback(frame)
            except Exception as e:
                print(f"Frame callback error: {e}")

