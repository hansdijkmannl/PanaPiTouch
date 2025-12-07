"""
Preview Widget for camera display

Displays the live camera feed with optional overlays.
Uses background thread for overlay processing to keep UI responsive.
"""
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from ..overlays import (
    FalseColorOverlay, WaveformOverlay, VectorscopeOverlay, FocusAssistOverlay,
    GridOverlay, FrameGuideOverlay, OverlayPipeline
)
from ..core.video_pipeline import FrameWorker
from ..atem.tally import TallyState


class PreviewWidget(QWidget):
    """
    Widget for displaying camera preview with overlays.
    
    Displays 1920x1080 preview with optional analysis overlays
    and tally border indication.
    
    Optimized for Raspberry Pi:
    - Uses fast scaling instead of smooth
    - Minimizes frame copies
    - Background thread for overlay processing
    """
    
    frame_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.preview_width = 1920
        self.preview_height = 1080
        
        # Overlays
        self.false_color = FalseColorOverlay()
        self.waveform = WaveformOverlay()
        self.vectorscope = VectorscopeOverlay()
        self.focus_assist = FocusAssistOverlay()
        self.grid_overlay = GridOverlay()
        self.frame_guide = FrameGuideOverlay()
        
        # Overlay Pipeline - chains overlays together for efficient processing
        self.overlay_pipeline = OverlayPipeline()
        # Add overlays to pipeline in processing order (analysis first, then guides on top)
        self.overlay_pipeline.add(self.false_color)
        self.overlay_pipeline.add(self.focus_assist)
        self.overlay_pipeline.add(self.waveform)
        self.overlay_pipeline.add(self.vectorscope)
        self.overlay_pipeline.add(self.grid_overlay)
        self.overlay_pipeline.add(self.frame_guide)
        
        # Video Pipeline Worker - processes frames in background thread
        # Worker runs continuously and handles both overlay and pass-through cases
        self.frame_worker = FrameWorker(self.overlay_pipeline, parent=self)
        self.frame_worker.frame_processed.connect(self._on_frame_processed, Qt.ConnectionType.QueuedConnection)
        self._worker_started = False
        
        # Tally state
        self._tally_state = TallyState.OFF
        
        # Current frame (avoid copies where possible)
        self._current_frame: np.ndarray = None
        self._display_frame: np.ndarray = None
        self._frame_dirty = False
        
        self._setup_ui()
        
        # Update timer for display - 40ms = ~25fps target (optimized for Pi)
        # Lower frequency reduces CPU load while maintaining smooth playback
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(40)  # 25fps - good balance for Pi
        
        # Frame rate limiting - track last update time
        self._last_update_time = 0
        self._min_update_interval = 0.04  # 25fps max
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #0a0a0f;
                border: 4px solid #2a2a38;
                border-radius: 4px;
            }
        """)
        
        # No signal text
        self._set_no_signal()
        
        layout.addWidget(self.preview_label)
        
        # Set object name for styling
        self.setObjectName("previewFrame")
    
    
    def _set_no_signal(self):
        """Display no signal message"""
        # Create a black frame with "No Signal" text
        frame = np.zeros((self.preview_height, self.preview_width, 3), dtype=np.uint8)
        frame[:] = (15, 15, 20)  # Dark background
        
        # Add text
        text = "NO SIGNAL"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 3
        thickness = 4
        
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (self.preview_width - text_size[0]) // 2
        text_y = (self.preview_height + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (60, 60, 70), thickness)
        
        self._display_frame = frame
        self._update_pixmap(frame)
    
    def _update_pixmap(self, frame: np.ndarray):
        """Update the displayed pixmap - optimized for performance"""
        if frame is None:
            return
        
        try:
            h, w = frame.shape[:2]
            
            # Get target size
            label_size = self.preview_label.size()
            target_w = label_size.width()
            target_h = label_size.height()
            
            if target_w <= 0 or target_h <= 0:
                return
            
            # Calculate scaled size maintaining aspect ratio
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Resize frame using OpenCV (faster than Qt scaling on Pi)
            if new_w != w or new_h != h:
                # Use INTER_AREA for downscaling (faster and better quality), INTER_LINEAR for upscaling
                if new_w < w or new_h < h:
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                else:
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                h, w = frame.shape[:2]
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create QImage directly from buffer (QImage will make a copy internally)
            bytes_per_line = 3 * w
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Create pixmap (this makes a copy, but necessary for display)
            pixmap = QPixmap.fromImage(q_img)
            
            self.preview_label.setPixmap(pixmap)
        except Exception:
            # Ignore errors during display update (widget might be destroyed)
            pass
    
    def update_frame(self, frame: np.ndarray):
        """Update the current frame from camera (error-handled)"""
        try:
            if frame is None:
                return
            
            # Store reference
            self._current_frame = frame
            
            # Start worker if not already started (runs continuously)
            if not self._worker_started:
                try:
                    self.frame_worker.start_processing()
                    self._worker_started = True
                except Exception as e:
                    # Worker might already be running or destroyed
                    pass
            
            # Send frame to worker (worker handles overlay vs pass-through internally)
            if hasattr(self, 'frame_worker') and self.frame_worker is not None:
                self.frame_worker.update_frame(frame)
        except Exception as e:
            # Don't crash on frame update errors
            pass
    
    def _on_frame_processed(self, processed_frame: np.ndarray):
        """Handle processed frame from worker thread (error-handled)"""
        try:
            if processed_frame is None:
                return
            
            # Check if widget still exists
            if not hasattr(self, 'preview_label') or self.preview_label is None:
                return
            
            self._display_frame = processed_frame
            self._frame_dirty = True
        except Exception:
            # Ignore errors (widget might be destroyed)
            pass
    
    def _update_display(self):
        """Update the display with current frame (rate-limited)"""
        import time
        
        # Rate limiting - don't update more than 25fps
        current_time = time.time()
        if current_time - self._last_update_time < self._min_update_interval:
            return  # Skip this update
        
        if self._display_frame is not None and self._frame_dirty:
            try:
                self._frame_dirty = False
                self._update_pixmap(self._display_frame)
                self.frame_updated.emit()
                self._last_update_time = current_time
            except Exception as e:
                # Widget might be destroyed - ignore errors
                pass
    
    def set_tally_state(self, state: TallyState):
        """Set tally state (affects border color) (error-handled)"""
        try:
            if not hasattr(self, 'preview_label') or self.preview_label is None:
                return
            
            self._tally_state = state
            
            # Update border style based on tally
            if state == TallyState.PROGRAM:
                self.preview_label.setStyleSheet("""
                    QLabel {
                        background-color: #0a0a0f;
                        border: 4px solid #ff3333;
                        border-radius: 4px;
                    }
                """)
            elif state == TallyState.PREVIEW:
                self.preview_label.setStyleSheet("""
                    QLabel {
                        background-color: #0a0a0f;
                        border: 4px solid #33cc33;
                        border-radius: 4px;
                    }
                """)
            else:
                self.preview_label.setStyleSheet("""
                    QLabel {
                        background-color: #0a0a0f;
                        border: 4px solid #2a2a38;
                        border-radius: 4px;
                    }
                """)
        except Exception:
            # Ignore errors during tally state update
            pass
    
    def toggle_false_color(self):
        """Toggle false color overlay"""
        self.false_color.toggle()
        return self.false_color.enabled
    
    def toggle_waveform(self):
        """Toggle waveform overlay"""
        self.waveform.toggle()
        return self.waveform.enabled
    
    def toggle_vectorscope(self):
        """Toggle vectorscope overlay"""
        self.vectorscope.toggle()
        return self.vectorscope.enabled
    
    def toggle_focus_assist(self):
        """Toggle focus assist overlay"""
        self.focus_assist.toggle()
        return self.focus_assist.enabled
    
    def toggle_grid(self):
        """Toggle grid overlay"""
        self.grid_overlay.toggle()
        return self.grid_overlay.enabled
    
    def toggle_rule_of_thirds(self):
        """Toggle rule of thirds in grid overlay"""
        if not self.grid_overlay.enabled:
            self.grid_overlay.set_enabled(True)
        return self.grid_overlay.toggle_rule_of_thirds()
    
    def toggle_full_grid(self):
        """Toggle full grid in grid overlay"""
        if not self.grid_overlay.enabled:
            self.grid_overlay.set_enabled(True)
        return self.grid_overlay.toggle_full_grid()
    
    def toggle_frame_guide(self):
        """Toggle frame guide overlay"""
        self.frame_guide.toggle()
        return self.frame_guide.enabled
    
    def clear_frame(self):
        """Clear the current frame and show no signal (error-handled)"""
        try:
            self._current_frame = None
            self._display_frame = None
            self._frame_dirty = False
            
            # Stop worker when clearing frame
            if self._worker_started and hasattr(self, 'frame_worker') and self.frame_worker is not None:
                try:
                    self.frame_worker.stop_processing()
                except Exception:
                    pass
                finally:
                    self._worker_started = False
            
            self._set_no_signal()
        except Exception:
            # Ignore errors during cleanup
            pass
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Mark frame dirty to trigger redraw at new size
        if self._display_frame is not None:
            self._frame_dirty = True
    
    def closeEvent(self, event):
        """Clean up worker thread on close (error-handled)"""
        try:
            if self._worker_started and hasattr(self, 'frame_worker') and self.frame_worker is not None:
                self.frame_worker.stop_processing()
        except Exception:
            pass
        finally:
            super().closeEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for frame guide drag/resize"""
        if self.frame_guide.drag_mode:
            # Get position relative to preview label
            pos = self.preview_label.mapFrom(self, event.pos())
            label_size = self.preview_label.size()
            
            # Check if click is within the preview area
            if 0 <= pos.x() <= label_size.width() and 0 <= pos.y() <= label_size.height():
                # Get current frame dimensions
                if self._current_frame is not None:
                    frame_h, frame_w = self._current_frame.shape[:2]
                    
                    # Scale click position to frame coordinates
                    scale = min(label_size.width() / frame_w, label_size.height() / frame_h)
                    offset_x = (label_size.width() - frame_w * scale) / 2
                    offset_y = (label_size.height() - frame_h * scale) / 2
                    
                    frame_x = int((pos.x() - offset_x) / scale)
                    frame_y = int((pos.y() - offset_y) / scale)
                    
                    self.frame_guide.handle_touch_start(frame_x, frame_y, frame_w, frame_h)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for frame guide drag/resize"""
        if self.frame_guide.drag_mode and self.frame_guide._drag_start is not None:
            pos = self.preview_label.mapFrom(self, event.pos())
            label_size = self.preview_label.size()
            
            if self._current_frame is not None:
                frame_h, frame_w = self._current_frame.shape[:2]
                
                scale = min(label_size.width() / frame_w, label_size.height() / frame_h)
                offset_x = (label_size.width() - frame_w * scale) / 2
                offset_y = (label_size.height() - frame_h * scale) / 2
                
                frame_x = int((pos.x() - offset_x) / scale)
                frame_y = int((pos.y() - offset_y) / scale)
                
                self.frame_guide.handle_touch_move(frame_x, frame_y, frame_w, frame_h)
                self._frame_dirty = True
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for frame guide drag/resize"""
        if self.frame_guide.drag_mode:
            self.frame_guide.handle_touch_end()
        
        super().mouseReleaseEvent(event)
