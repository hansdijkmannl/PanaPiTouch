"""
Focus Assist Overlay

Highlights in-focus areas using edge detection (focus peaking).
"""
import cv2
import numpy as np
from typing import Tuple
from .base import Overlay


class FocusAssistOverlay(Overlay):
    """
    Focus assist overlay (focus peaking).
    
    Highlights sharp edges to help with manual focus.
    Uses edge detection to find in-focus areas.
    """
    
    def __init__(self):
        super().__init__()
        self.color = (0, 0, 255)  # Red highlighting (BGR)
        self.threshold = 50
        self.sensitivity = 'medium'  # 'low', 'medium', 'high'
        self.mode = 'overlay'  # 'overlay', 'edges_only'
    
    def _get_threshold(self) -> int:
        """Get threshold based on sensitivity"""
        thresholds = {
            'low': 80,
            'medium': 50,
            'high': 30
        }
        return thresholds.get(self.sensitivity, 50)
    
    def _detect_focus(self, frame: np.ndarray) -> np.ndarray:
        """Detect in-focus areas using edge detection - optimized for performance"""
        # Downsample frame first for faster processing
        h, w = frame.shape[:2]
        scale = 2  # Process at half resolution
        small_frame = cv2.resize(frame, (w // scale, h // scale))
        
        # Convert to grayscale
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise (smaller kernel for speed)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Use only Laplacian for speed (skip Sobel - it's expensive)
        laplacian = cv2.Laplacian(blurred, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        
        # Apply threshold
        threshold = self._get_threshold()
        _, mask = cv2.threshold(laplacian, threshold, 255, cv2.THRESH_BINARY)
        
        # Optional: dilate to make edges more visible
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Resize mask back to original frame size
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        
        return mask
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply focus assist overlay to frame.

        Args:
            frame: BGR image (may be read-only)

        Returns:
            Frame with focus peaking overlay (always a new writable array)
        """
        if not self._enabled:
            return frame

        # Detect focus areas
        mask = self._detect_focus(frame)

        if self.mode == 'edges_only':
            # Show only edges on black background
            result = np.zeros_like(frame)
            result[mask > 0] = self.color
        else:
            # Overlay edges on original frame - vectorized blending
            result = np.array(frame, copy=True)

            # Vectorized alpha blending using numpy broadcasting
            # Much faster than per-pixel cv2.addWeighted in loop
            alpha = 0.7
            mask_bool = mask > 0

            # Create color array for broadcasting
            color_array = np.array(self.color, dtype=np.uint8)

            # Vectorized blend: result = (1-alpha)*frame + alpha*color
            result[mask_bool] = (
                (1 - alpha) * frame[mask_bool] + alpha * color_array
            ).astype(np.uint8)

        return result
    
    def toggle(self):
        """Toggle focus assist"""
        super().toggle()
    
    def set_color(self, color: Tuple[int, int, int]):
        """Set highlight color (BGR)"""
        self.color = color
    
    def set_color_preset(self, preset: str):
        """Set highlight color from preset"""
        presets = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'yellow': (0, 255, 255),
            'cyan': (255, 255, 0),
            'magenta': (255, 0, 255),
            'white': (255, 255, 255),
        }
        if preset in presets:
            self.color = presets[preset]
    
    def cycle_sensitivity(self):
        """Cycle through sensitivity levels"""
        sensitivities = ['low', 'medium', 'high']
        current_idx = sensitivities.index(self.sensitivity)
        self.sensitivity = sensitivities[(current_idx + 1) % len(sensitivities)]
    
    def cycle_color(self):
        """Cycle through color presets"""
        colors = ['red', 'green', 'blue', 'yellow', 'cyan']
        color_values = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0)]
        
        try:
            current_idx = color_values.index(self.color)
            self.color = color_values[(current_idx + 1) % len(color_values)]
        except ValueError:
            self.color = color_values[0]

