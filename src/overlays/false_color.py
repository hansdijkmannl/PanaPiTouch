"""
False Color Overlay

Displays exposure information using IRE scale color-coded overlay.
Matches Atomos monitor false color display standards.

IRE (Institute of Radio Engineers) scale:
- 0 IRE = Black level (7.5 IRE for NTSC, 0 IRE for PAL)
- 100 IRE = White level
- Standard video levels mapped to IRE values
"""
import cv2
import numpy as np
from typing import Tuple


class FalseColorOverlay:
    """
    False color overlay for exposure analysis using IRE scale.
    
    Maps luminance values to IRE scale colors (Atomos-style):
    - 0-10 IRE: Purple/Black - Crushed blacks
    - 10-20 IRE: Blue - Underexposed shadows
    - 20-30 IRE: Cyan - Dark areas
    - 30-40 IRE: Green - Shadows
    - 40-50 IRE: Yellow-Green - Lower midtones
    - 50-60 IRE: Yellow - Midtones
    - 60-70 IRE: Orange - Upper midtones
    - 70-80 IRE: Red-Orange - Skin tones (typical)
    - 80-90 IRE: Red - Highlights
    - 90-100 IRE: Magenta/Pink - Overexposed
    - 100+ IRE: White - Clipped whites
    """
    
    def __init__(self):
        self.enabled = False
        self.opacity = 0.8
        self._lut = self._create_ire_false_color_lut()
    
    def _luma_to_ire(self, luma_value: int) -> float:
        """
        Convert luma value (0-255) to IRE scale (0-100).
        
        IRE scale assumes:
        - 0-16 = Black level (0 IRE for PAL, 7.5 IRE for NTSC)
        - 16-235 = Video range (7.5-100 IRE for NTSC, 0-100 IRE for PAL)
        - 235-255 = Above white (100+ IRE)
        
        Using standard PAL mapping (0 IRE = black):
        - 0-16: 0 IRE (black)
        - 16-235: 0-100 IRE (video range)
        - 235-255: 100+ IRE (above white)
        """
        if luma_value <= 16:
            return 0.0  # Black level
        elif luma_value >= 235:
            # Above white level - map to 100-120 IRE
            excess = luma_value - 235
            return 100.0 + (excess / 20.0) * 20.0  # Scale to 100-120 IRE
        else:
            # Video range: 16-235 maps to 0-100 IRE
            return ((luma_value - 16) / (235 - 16)) * 100.0
    
    def _create_ire_false_color_lut(self) -> np.ndarray:
        """Create lookup table for IRE-based false color mapping (Atomos-style)"""
        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        
        # Atomos-style IRE color mapping (BGR format)
        # Colors match professional monitor false color displays
        for luma in range(256):
            ire = self._luma_to_ire(luma)
            
            if ire < 10:
                # 0-10 IRE: Purple/Black - Crushed blacks
                lut[luma] = (128, 0, 128)
            elif ire < 20:
                # 10-20 IRE: Blue - Underexposed shadows
                lut[luma] = (255, 0, 0)
            elif ire < 30:
                # 20-30 IRE: Cyan - Dark areas
                lut[luma] = (255, 255, 0)
            elif ire < 40:
                # 30-40 IRE: Green - Shadows
                lut[luma] = (0, 255, 0)
            elif ire < 50:
                # 40-50 IRE: Yellow-Green - Lower midtones
                lut[luma] = (0, 255, 128)
            elif ire < 60:
                # 50-60 IRE: Yellow - Midtones
                lut[luma] = (0, 255, 255)
            elif ire < 70:
                # 60-70 IRE: Orange - Upper midtones
                lut[luma] = (0, 165, 255)
            elif ire < 80:
                # 70-80 IRE: Red-Orange - Skin tones (typical range)
                lut[luma] = (0, 100, 255)
            elif ire < 90:
                # 80-90 IRE: Red - Highlights
                lut[luma] = (0, 0, 255)
            elif ire < 100:
                # 90-100 IRE: Magenta/Pink - Overexposed
                lut[luma] = (255, 0, 255)
            else:
                # 100+ IRE: White - Clipped whites
                lut[luma] = (255, 255, 255)
        
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

