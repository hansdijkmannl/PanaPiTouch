"""
False Color Overlay

Displays exposure information using a color-coded overlay.
Similar to professional broadcast monitors.
"""
import cv2
import numpy as np
from typing import Tuple


class FalseColorOverlay:
    """
    False color overlay for exposure analysis.
    
    Maps luminance values to colors:
    - Purple/Blue: Underexposed (<5%)
    - Blue: Very dark (5-10%)
    - Cyan: Dark (10-20%)
    - Green: Shadows (20-40%)
    - Yellow-Green: Midtones (40-50%)
    - Yellow: Skin tones (50-70%)
    - Orange: Highlights (70-85%)
    - Red: Overexposed (85-95%)
    - White/Pink: Clipped (>95%)
    """
    
    def __init__(self):
        self.enabled = False
        self.opacity = 0.8
        self._lut = self._create_false_color_lut()
    
    def _create_false_color_lut(self) -> np.ndarray:
        """Create lookup table for false color mapping"""
        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        
        # Define color ranges (BGR format)
        ranges = [
            (0, 13, (128, 0, 128)),      # Purple - crushed blacks
            (13, 26, (255, 0, 0)),        # Blue - underexposed
            (26, 51, (255, 255, 0)),      # Cyan - dark
            (51, 102, (0, 255, 0)),       # Green - shadows/dark mid
            (102, 128, (0, 255, 128)),    # Yellow-green - midtones
            (128, 179, (0, 255, 255)),    # Yellow - skin tones
            (179, 217, (0, 165, 255)),    # Orange - highlights
            (217, 243, (0, 0, 255)),      # Red - overexposed
            (243, 256, (255, 200, 255)),  # Pink/white - clipped
        ]
        
        for start, end, color in ranges:
            lut[start:end] = color
        
        return lut
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply false color overlay to frame.
        
        Args:
            frame: BGR image (numpy array)
            
        Returns:
            Frame with false color overlay
        """
        if not self.enabled:
            return frame
        
        # Convert to grayscale for luminance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply LUT
        false_color = cv2.LUT(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), self._lut)
        
        # Blend with original
        if self.opacity < 1.0:
            result = cv2.addWeighted(frame, 1 - self.opacity, false_color, self.opacity, 0)
        else:
            result = false_color
        
        return result
    
    def toggle(self):
        """Toggle false color overlay"""
        self.enabled = not self.enabled
    
    def set_opacity(self, opacity: float):
        """Set overlay opacity (0.0 - 1.0)"""
        self.opacity = max(0.0, min(1.0, opacity))


def create_false_color_legend(height: int = 200, width: int = 40) -> np.ndarray:
    """Create a legend image showing the false color scale"""
    legend = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Fill with gradient
    for y in range(height):
        value = int(255 * (1 - y / height))
        legend[y, :] = [value, value, value]
    
    # Apply LUT
    overlay = FalseColorOverlay()
    overlay.enabled = True
    overlay.opacity = 1.0
    
    return overlay.apply(legend)

