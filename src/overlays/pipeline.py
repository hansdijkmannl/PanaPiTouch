"""
Overlay Pipeline

Chains multiple overlays together for efficient frame processing.
"""
from typing import List, Optional
import numpy as np
from .base import Overlay


class OverlayPipeline:
    """
    Pipeline for chaining multiple overlays together.
    
    Overlays are processed in the order they are added.
    Only enabled overlays are processed.
    """
    
    def __init__(self):
        self._overlays: List[Overlay] = []
    
    def add(self, overlay: Overlay) -> 'OverlayPipeline':
        """
        Add an overlay to the pipeline.
        
        Args:
            overlay: Overlay instance to add
            
        Returns:
            Self for method chaining
        """
        if overlay not in self._overlays:
            self._overlays.append(overlay)
        return self
    
    def remove(self, overlay: Overlay) -> 'OverlayPipeline':
        """
        Remove an overlay from the pipeline.
        
        Args:
            overlay: Overlay instance to remove
            
        Returns:
            Self for method chaining
        """
        if overlay in self._overlays:
            self._overlays.remove(overlay)
        return self
    
    def clear(self):
        """Clear all overlays from pipeline"""
        self._overlays.clear()
    
    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process frame through all enabled overlays in order.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Processed frame (BGR format)
        """
        result = frame
        
        for overlay in self._overlays:
            if overlay.enabled:
                result = overlay.apply(result)
        
        return result
    
    def get_enabled_overlays(self) -> List[Overlay]:
        """Get list of currently enabled overlays"""
        return [overlay for overlay in self._overlays if overlay.enabled]
    
    def has_enabled_overlays(self) -> bool:
        """Check if any overlays are enabled"""
        return any(overlay.enabled for overlay in self._overlays)
    
    def __len__(self) -> int:
        """Get number of overlays in pipeline"""
        return len(self._overlays)
    
    def __iter__(self):
        """Iterate over overlays"""
        return iter(self._overlays)




