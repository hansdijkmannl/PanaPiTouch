"""
Grid Overlay

Provides rule of thirds and full grid for camera framing.
"""
import cv2
import numpy as np
from typing import Tuple
from .base import Overlay


class GridOverlay(Overlay):
    """
    Grid overlay for camera framing assistance.
    
    Features:
    - Rule of thirds (2 horizontal + 2 vertical lines)
    - Full grid (multiple horizontal + vertical lines for leveling)
    """
    
    def __init__(self):
        super().__init__()
        self.rule_of_thirds = True
        self.full_grid = False
        
        # Styling - thicker lines for visibility
        self.color = (255, 255, 255)  # White (BGR)
        self.line_thickness = 2  # Doubled from 1
        self.line_opacity = 0.6
        self.grid_divisions = 6  # Number of divisions for full grid
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply grid overlay to frame.

        Args:
            frame: BGR image (may be read-only)

        Returns:
            Frame with grid overlay (always a new writable array)
        """
        if not self._enabled:
            return frame

        # Check if any grid type is enabled
        if not (self.rule_of_thirds or self.full_grid):
            return frame

        h, w = frame.shape[:2]

        # Create writable overlay copy
        overlay = np.array(frame, copy=True)

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

        # Full grid for leveling
        if self.full_grid:
            # Draw vertical lines
            for i in range(1, self.grid_divisions):
                x = (w * i) // self.grid_divisions
                cv2.line(overlay, (x, 0), (x, h), self.color, self.line_thickness)

            # Draw horizontal lines
            for i in range(1, self.grid_divisions):
                y = (h * i) // self.grid_divisions
                cv2.line(overlay, (0, y), (w, y), self.color, self.line_thickness)

        # Blend overlay with original
        result = cv2.addWeighted(overlay, self.line_opacity, frame, 1 - self.line_opacity, 0)

        return result
    
    def toggle(self):
        """Toggle grid overlay"""
        super().toggle()
    
    def toggle_rule_of_thirds(self) -> bool:
        """Toggle rule of thirds"""
        self.rule_of_thirds = not self.rule_of_thirds
        return self.rule_of_thirds
    
    def toggle_full_grid(self) -> bool:
        """Toggle full grid"""
        self.full_grid = not self.full_grid
        return self.full_grid
    
    def set_color(self, color: Tuple[int, int, int]):
        """Set grid color (BGR)"""
        self.color = color
    
    def set_opacity(self, opacity: float):
        """Set line opacity (0.0 - 1.0)"""
        self.line_opacity = max(0.0, min(1.0, opacity))
    
    def set_grid_divisions(self, divisions: int):
        """Set number of grid divisions"""
        self.grid_divisions = max(2, min(12, divisions))

