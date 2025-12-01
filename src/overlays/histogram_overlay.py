"""
Histogram Overlay

Displays RGB histogram showing exposure distribution.
"""
import cv2
import numpy as np


class HistogramOverlay:
    """
    Displays RGB histogram in corner of frame.
    
    Shows distribution of brightness values for Red, Green, and Blue channels.
    Useful for checking exposure and color balance.
    """
    
    def __init__(self):
        self.enabled = False
        self.position = 'bottom-right'  # 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        self.size = (200, 100)  # Width x Height of histogram display
        self.opacity = 0.8
        self.show_rgb = True  # Show separate RGB channels
        
    def toggle(self) -> bool:
        """Toggle histogram on/off"""
        self.enabled = not self.enabled
        return self.enabled
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """Apply histogram overlay to frame"""
        if not self.enabled or frame is None:
            return frame
        
        h, w = frame.shape[:2]
        hist_w, hist_h = self.size
        margin = 10
        
        # Calculate position
        if self.position == 'top-left':
            x, y = margin, margin
        elif self.position == 'top-right':
            x, y = w - hist_w - margin, margin
        elif self.position == 'bottom-left':
            x, y = margin, h - hist_h - margin
        else:  # bottom-right
            x, y = w - hist_w - margin, h - hist_h - margin
        
        # Create histogram image
        hist_img = self._create_histogram(frame, hist_w, hist_h)
        
        # Blend histogram onto frame
        if hist_img is not None:
            # Create semi-transparent background
            overlay = frame.copy()
            cv2.rectangle(overlay, (x - 2, y - 2), (x + hist_w + 2, y + hist_h + 2), 
                         (20, 20, 25), -1)
            cv2.rectangle(overlay, (x - 2, y - 2), (x + hist_w + 2, y + hist_h + 2), 
                         (60, 60, 70), 1)
            
            # Blend background
            frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
            
            # Draw histogram
            frame[y:y+hist_h, x:x+hist_w] = cv2.addWeighted(
                frame[y:y+hist_h, x:x+hist_w], 1 - self.opacity,
                hist_img, self.opacity, 0
            )
        
        return frame
    
    def _create_histogram(self, frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """Create histogram visualization"""
        # Create black background
        hist_img = np.zeros((height, width, 3), dtype=np.uint8)
        hist_img[:] = (20, 20, 25)
        
        if self.show_rgb:
            # Calculate histograms for each channel
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # BGR
            
            for i, color in enumerate(colors):
                hist = cv2.calcHist([frame], [i], None, [256], [0, 256])
                cv2.normalize(hist, hist, 0, height - 4, cv2.NORM_MINMAX)
                
                # Draw histogram line
                pts = []
                for j, val in enumerate(hist):
                    x_pos = int(j * (width - 1) / 255)
                    y_pos = height - 2 - int(val[0])
                    pts.append((x_pos, y_pos))
                
                if len(pts) > 1:
                    pts = np.array(pts, dtype=np.int32)
                    cv2.polylines(hist_img, [pts], False, color, 1, cv2.LINE_AA)
        else:
            # Grayscale histogram
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, height - 4, cv2.NORM_MINMAX)
            
            pts = []
            for j, val in enumerate(hist):
                x_pos = int(j * (width - 1) / 255)
                y_pos = height - 2 - int(val[0])
                pts.append((x_pos, y_pos))
            
            if len(pts) > 1:
                pts = np.array(pts, dtype=np.int32)
                cv2.polylines(hist_img, [pts], False, (200, 200, 200), 1, cv2.LINE_AA)
        
        return hist_img

