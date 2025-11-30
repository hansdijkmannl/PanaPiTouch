"""
Grid Overlay

Provides rule of thirds, center cross, and level lines for camera framing.
"""
import cv2
import numpy as np
from typing import Tuple


class GridOverlay:
    """
    Grid overlay for camera framing assistance.
    
    Features:
    - Rule of thirds (2 horizontal + 2 vertical lines)
    - Center crosshair
    - Level lines (single horizontal + vertical through center)
    """
    
    def __init__(self):
        self.enabled = False
        self.rule_of_thirds = True
        self.center_cross = False
        self.level_lines = False
        
        # Styling
        self.color = (255, 255, 255)  # White (BGR)
        self.line_thickness = 1
        self.line_opacity = 0.6
        self.center_cross_size = 40  # pixels from center
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply grid overlay to frame.
        
        Args:
            frame: BGR image
            
        Returns:
            Frame with grid overlay
        """
        if not self.enabled:
            return frame
        
        # Check if any grid type is enabled
        if not (self.rule_of_thirds or self.center_cross or self.level_lines):
            return frame
        
        h, w = frame.shape[:2]
        
        # Create overlay
        overlay = frame.copy()
        
        # Rule of thirds
        if self.rule_of_thirds:
            # Vertical lines at 1/3 and 2/3
            x1 = w // 3
            x2 = 2 * w // 3
            cv2.line(overlay, (x1, 0), (x1, h), self.color, self.line_thickness)
            cv2.line(overlay, (x2, 0), (x2, h), self.color, self.line_thickness)
            
            # Horizontal lines at 1/3 and 2/3
            y1 = h // 3
            y2 = 2 * h // 3
            cv2.line(overlay, (0, y1), (w, y1), self.color, self.line_thickness)
            cv2.line(overlay, (0, y2), (w, y2), self.color, self.line_thickness)
        
        # Level lines (center cross through entire frame)
        if self.level_lines:
            cx, cy = w // 2, h // 2
            # Full width horizontal line
            cv2.line(overlay, (0, cy), (w, cy), self.color, self.line_thickness)
            # Full height vertical line
            cv2.line(overlay, (cx, 0), (cx, h), self.color, self.line_thickness)
        
        # Center crosshair (small cross in center)
        if self.center_cross:
            cx, cy = w // 2, h // 2
            size = self.center_cross_size
            # Horizontal part
            cv2.line(overlay, (cx - size, cy), (cx + size, cy), self.color, self.line_thickness + 1)
            # Vertical part
            cv2.line(overlay, (cx, cy - size), (cx, cy + size), self.color, self.line_thickness + 1)
            # Center dot
            cv2.circle(overlay, (cx, cy), 3, self.color, -1)
        
        # Blend overlay with original
        result = cv2.addWeighted(overlay, self.line_opacity, frame, 1 - self.line_opacity, 0)
        
        return result
    
    def toggle(self):
        """Toggle grid overlay"""
        self.enabled = not self.enabled
    
    def toggle_rule_of_thirds(self) -> bool:
        """Toggle rule of thirds"""
        self.rule_of_thirds = not self.rule_of_thirds
        return self.rule_of_thirds
    
    def toggle_center_cross(self) -> bool:
        """Toggle center crosshair"""
        self.center_cross = not self.center_cross
        return self.center_cross
    
    def toggle_level_lines(self) -> bool:
        """Toggle level lines"""
        self.level_lines = not self.level_lines
        return self.level_lines
    
    def set_color(self, color: Tuple[int, int, int]):
        """Set grid color (BGR)"""
        self.color = color
    
    def set_opacity(self, opacity: float):
        """Set line opacity (0.0 - 1.0)"""
        self.opacity = max(0.0, min(1.0, opacity))

