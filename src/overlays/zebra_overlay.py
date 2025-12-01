"""
Zebra Pattern Overlay

Highlights overexposed areas with diagonal stripes.
"""
import cv2
import numpy as np


class ZebraOverlay:
    """
    Displays zebra pattern on overexposed areas.
    
    Shows diagonal stripes on areas exceeding the threshold IRE level.
    Standard broadcast thresholds are 70% and 100% IRE.
    """
    
    def __init__(self):
        self.enabled = False
        self.threshold = 90  # Percentage (0-100), 90% = ~230 in 8-bit
        self.stripe_width = 4
        self.stripe_spacing = 8
        self.color = (0, 0, 0)  # Black stripes
        self.show_100_ire = True  # Also highlight 100% areas in different color
        
    def toggle(self) -> bool:
        """Toggle zebra on/off"""
        self.enabled = not self.enabled
        return self.enabled
    
    def set_threshold(self, percent: int):
        """Set zebra threshold (0-100)"""
        self.threshold = max(0, min(100, percent))
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """Apply zebra pattern overlay to frame"""
        if not self.enabled or frame is None:
            return frame
        
        h, w = frame.shape[:2]
        
        # Convert threshold percentage to 8-bit value
        threshold_value = int(self.threshold * 255 / 100)
        
        # Convert to grayscale for luminance check
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Create mask for overexposed areas
        _, mask = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Create zebra pattern
        zebra_pattern = self._create_zebra_pattern(w, h)
        
        # Apply zebra only to overexposed areas
        zebra_mask = cv2.bitwise_and(zebra_pattern, mask)
        
        # Create output frame
        result = frame.copy()
        
        # Apply primary zebra (threshold level)
        result[zebra_mask > 0] = self.color
        
        # Optionally highlight 100% IRE (clipped) areas
        if self.show_100_ire:
            _, clip_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)
            # Use red for clipped areas
            red_zebra = cv2.bitwise_and(zebra_pattern, clip_mask)
            result[red_zebra > 0] = (0, 0, 255)  # Red in BGR
        
        return result
    
    def _create_zebra_pattern(self, width: int, height: int) -> np.ndarray:
        """Create diagonal stripe pattern"""
        pattern = np.zeros((height, width), dtype=np.uint8)
        
        total_width = self.stripe_width + self.stripe_spacing
        
        # Create diagonal stripes
        for y in range(height):
            for x in range(width):
                # Diagonal stripe calculation
                if ((x + y) % total_width) < self.stripe_width:
                    pattern[y, x] = 255
        
        return pattern

