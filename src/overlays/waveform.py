"""
Waveform Monitor Overlay

Displays luminance waveform like professional broadcast monitors.
"""
import cv2
import numpy as np
from typing import Tuple, Optional
from .base import Overlay


class WaveformOverlay(Overlay):
    """
    Waveform monitor overlay for exposure analysis.
    
    Displays vertical luminance distribution for each horizontal position.
    Can show RGB parade or combined luma waveform.
    """
    
    def __init__(self):
        super().__init__()
        self.mode = 'luma'  # 'luma', 'rgb', 'parade'
        self.position = 'bottom-right'  # 'bottom-right', 'overlay', 'side'
        self.size = (320, 200)  # (width, height)
        self._opacity = 0.85
        self._waveform_cache: Optional[np.ndarray] = None
    
    def _generate_waveform(self, frame: np.ndarray) -> np.ndarray:
        """Generate waveform display - optimized for performance"""
        h, w = frame.shape[:2]
        wf_w, wf_h = self.size
        
        # Create waveform image
        waveform = np.zeros((wf_h, wf_w, 3), dtype=np.uint8)
        
        # Background with grid lines
        waveform[:] = (20, 20, 20)
        
        # Draw horizontal grid lines at 0%, 25%, 50%, 75%, 100%
        for pct in [0, 25, 50, 75, 100]:
            y = int(wf_h * (1 - pct / 100))
            cv2.line(waveform, (0, y), (wf_w, y), (60, 60, 60), 1)
        
        if self.mode == 'luma':
            # Luminance waveform - fully vectorized version
            # Downsample frame first for faster processing
            scale_factor = max(2, w // wf_w)  # More aggressive downsampling
            gray = cv2.cvtColor(frame[::scale_factor, ::scale_factor], cv2.COLOR_BGR2GRAY)

            # Resize to waveform width (much faster than column-by-column)
            gray_resized = cv2.resize(gray, (wf_w, h // scale_factor))

            # Fully vectorized histogram computation using bincount
            # Map pixel values to waveform Y positions
            y_indices = (gray_resized.astype(np.float32) * (wf_h - 1) / 255).astype(np.int32)
            y_indices = np.clip(y_indices, 0, wf_h - 1)

            # For each column, accumulate pixel counts at each Y position
            for x in range(wf_w):
                # Use bincount for fast histogram (much faster than np.histogram)
                counts = np.bincount(y_indices[:, x], minlength=wf_h)
                # Limit max brightness and convert to intensity
                counts = np.clip(counts, 0, 10)
                intensities = np.clip(counts * 30, 0, 255).astype(np.uint8)

                # Invert Y axis and assign to waveform (vectorized)
                waveform[:, x, 0] = intensities[::-1]
                waveform[:, x, 1] = intensities[::-1]
                waveform[:, x, 2] = intensities[::-1]
        
        elif self.mode == 'rgb' or self.mode == 'parade':
            # RGB parade - vectorized version
            colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]  # BGR order: Blue, Green, Red display
            channels = cv2.split(frame)  # B, G, R

            section_width = wf_w // 3
            scale_factor = max(2, h // 200)  # Downsample height

            for i, (channel, color) in enumerate(zip(channels, colors)):
                # Downsample and resize channel
                ch_small = channel[::scale_factor, ::scale_factor]
                ch_resized = cv2.resize(ch_small, (section_width, ch_small.shape[0]))

                # Vectorized histogram computation
                y_indices = (ch_resized.astype(np.float32) * (wf_h - 1) / 255).astype(np.int32)
                y_indices = np.clip(y_indices, 0, wf_h - 1)

                x_offset = i * section_width
                color_array = np.array(color, dtype=np.float32)

                for x in range(section_width):
                    counts = np.bincount(y_indices[:, x], minlength=wf_h)
                    counts = np.clip(counts, 0, 10)
                    intensities = np.clip(counts / 5.0, 0, 1.0)

                    # Apply color with intensity (vectorized)
                    colored = (color_array[np.newaxis, :] * intensities[:, np.newaxis]).astype(np.uint8)
                    waveform[:, x + x_offset] = colored[::-1]
        
        # Draw border
        cv2.rectangle(waveform, (0, 0), (wf_w - 1, wf_h - 1), (100, 100, 100), 1)
        
        # Add labels
        cv2.putText(waveform, "100", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
        cv2.putText(waveform, "0", (5, wf_h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
        
        return waveform
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply waveform overlay to frame.

        Args:
            frame: BGR image (may be read-only)

        Returns:
            Frame with waveform overlay (always a new writable array)
        """
        if not self._enabled:
            return frame

        # Create writable copy only when we need to modify it
        # Input frame may be read-only for zero-copy optimization
        result = np.array(frame, copy=True)
        waveform = self._generate_waveform(frame)
        wf_h, wf_w = waveform.shape[:2]

        if self.position == 'bottom-right':
            # Position in bottom-right corner with padding
            x = frame.shape[1] - wf_w - 20
            y = frame.shape[0] - wf_h - 20

            # Create ROI
            roi = result[y:y+wf_h, x:x+wf_w]

            # Blend
            blended = cv2.addWeighted(roi, 1 - self._opacity, waveform, self._opacity, 0)
            result[y:y+wf_h, x:x+wf_w] = blended

        elif self.position == 'overlay':
            # Semi-transparent overlay at bottom
            x = (frame.shape[1] - wf_w) // 2
            y = frame.shape[0] - wf_h - 20

            roi = result[y:y+wf_h, x:x+wf_w]
            blended = cv2.addWeighted(roi, 1 - self._opacity, waveform, self._opacity, 0)
            result[y:y+wf_h, x:x+wf_w] = blended

        return result
    
    def cycle_mode(self):
        """Cycle through waveform modes"""
        modes = ['luma', 'rgb', 'parade']
        current_idx = modes.index(self.mode)
        self.mode = modes[(current_idx + 1) % len(modes)]
    
    def set_size(self, width: int, height: int):
        """Set waveform display size"""
        self.size = (width, height)

