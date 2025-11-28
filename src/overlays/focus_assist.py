"""
Focus Assist Overlay

Highlights in-focus areas using edge detection (focus peaking).
"""
import cv2
import numpy as np
from typing import Tuple


class FocusAssistOverlay:
    """
    Focus assist overlay (focus peaking).
    
    Highlights sharp edges to help with manual focus.
    Uses edge detection to find in-focus areas.
    """
    
    def __init__(self):
        self.enabled = False
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
        """Detect in-focus areas using edge detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Use Laplacian for edge detection (good for focus detection)
        laplacian = cv2.Laplacian(blurred, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        
        # Also use Sobel for directional edges
        sobel_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
        sobel = np.sqrt(sobel_x**2 + sobel_y**2)
        sobel = np.uint8(np.clip(sobel, 0, 255))
        
        # Combine edge maps
        edges = cv2.addWeighted(laplacian, 0.5, sobel, 0.5, 0)
        
        # Apply threshold
        threshold = self._get_threshold()
        _, mask = cv2.threshold(edges, threshold, 255, cv2.THRESH_BINARY)
        
        # Optional: dilate to make edges more visible
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply focus assist overlay to frame.
        
        Args:
            frame: BGR image
            
        Returns:
            Frame with focus peaking overlay
        """
        if not self.enabled:
            return frame
        
        # Detect focus areas
        mask = self._detect_focus(frame)
        
        if self.mode == 'edges_only':
            # Show only edges on black background
            result = np.zeros_like(frame)
            result[mask > 0] = self.color
        else:
            # Overlay edges on original frame
            result = frame.copy()
            
            # Create colored overlay
            overlay = np.zeros_like(frame)
            overlay[mask > 0] = self.color
            
            # Blend where mask is active
            alpha = 0.7
            result[mask > 0] = cv2.addWeighted(
                frame[mask > 0], 1 - alpha,
                overlay[mask > 0], alpha, 0
            )
        
        return result
    
    def toggle(self):
        """Toggle focus assist"""
        self.enabled = not self.enabled
    
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

