"""
Base Overlay Class

All overlays inherit from this base class to ensure consistent interface.
"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Optional


class Overlay(ABC):
    """
    Base class for all video overlays.
    
    All overlays must implement the apply() method which takes a frame
    and returns a processed frame.
    """
    
    def __init__(self):
        self._enabled = False
        self._opacity = 1.0
    
    @property
    def enabled(self) -> bool:
        """Check if overlay is enabled"""
        return self._enabled
    
    @property
    def opacity(self) -> float:
        """Get overlay opacity (0.0 - 1.0)"""
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: float):
        """Set overlay opacity (0.0 - 1.0)"""
        self._opacity = max(0.0, min(1.0, value))
    
    @abstractmethod
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply overlay to frame.
        
        Args:
            frame: Input frame (BGR format, numpy array)
            
        Returns:
            Processed frame (BGR format, numpy array)
        """
        pass
    
    def toggle(self):
        """Toggle overlay on/off"""
        self._enabled = not self._enabled
    
    def enable(self):
        """Enable overlay"""
        self._enabled = True
    
    def disable(self):
        """Disable overlay"""
        self._enabled = False
    
    def set_enabled(self, enabled: bool):
        """Set enabled state"""
        self._enabled = enabled




