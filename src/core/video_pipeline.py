"""
Video Processing Pipeline

Handles frame processing through overlay pipeline in a separate thread.
Worker runs continuously and handles both overlay and pass-through cases.
"""
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import numpy as np
from collections import deque
from ..overlays.pipeline import OverlayPipeline


class FrameWorker(QThread):
    """
    Worker thread for processing video frames through overlay pipeline.
    
    Runs continuously - checks if overlays are enabled and either processes
    through pipeline or passes frame through unchanged. This eliminates
    start/stop race conditions.
    """
    frame_processed = pyqtSignal(np.ndarray)  # Signal emitted when frame is processed
    
    def __init__(self, overlay_pipeline: OverlayPipeline, parent=None):
        super().__init__(parent)
        self.overlay_pipeline = overlay_pipeline
        self._running = False
        self._frame_queue = deque(maxlen=2)  # Keep only latest 2 frames
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._shutdown = False
    
    def update_frame(self, frame: np.ndarray):
        """Update the current frame to process (thread-safe)"""
        if frame is None:
            return
        
        self._mutex.lock()
        try:
            if self._shutdown:
                return
            
            # Keep only the latest frame (drop old ones)
            # Only copy if we need to (when queue is not empty, we'll process it)
            self._frame_queue.clear()
            # Copy frame to avoid modification during processing
            # This is necessary for thread safety
            self._frame_queue.append(frame.copy())
            self._condition.wakeOne()  # Wake up the processing loop
        except Exception as e:
            # Prevent crashes from mutex errors
            pass
        finally:
            self._mutex.unlock()
    
    def start_processing(self):
        """Start frame processing"""
        if self._running:
            return  # Already running
        
        self._mutex.lock()
        try:
            self._running = True
            self._shutdown = False
            self._frame_queue.clear()
        finally:
            self._mutex.unlock()
        
        if not self.isRunning():
            self.start()
    
    def stop_processing(self):
        """Stop frame processing (thread-safe)"""
        if not self._running:
            return
        
        self._mutex.lock()
        try:
            self._shutdown = True
            self._running = False
            self._frame_queue.clear()
            self._condition.wakeAll()  # Wake up the processing loop to exit
        finally:
            self._mutex.unlock()
        
        # Wait for thread to finish (with timeout)
        if self.isRunning():
            if not self.wait(timeout=500):
                self.terminate()
                self.wait(timeout=200)
    
    def run(self):
        """Main processing loop - runs continuously"""
        while True:
            frame = None
            
            self._mutex.lock()
            try:
                # Wait for a frame or shutdown signal
                while len(self._frame_queue) == 0 and not self._shutdown:
                    self._condition.wait(self._mutex, 100)  # Wait up to 100ms
                
                # Check if we should exit
                if self._shutdown:
                    break
                
                # Get frame to process
                if len(self._frame_queue) > 0:
                    frame = self._frame_queue.popleft()
            except Exception:
                break
            finally:
                self._mutex.unlock()
            
            # Process frame outside the lock
            if frame is not None:
                try:
                    # Check if we should still process (shutdown might have happened)
                    self._mutex.lock()
                    try:
                        should_process = self._running and not self._shutdown
                    finally:
                        self._mutex.unlock()
                    
                    if not should_process:
                        continue
                    
                    # Check if overlays are enabled
                    has_overlays = self.overlay_pipeline.has_enabled_overlays()
                    
                    if has_overlays:
                        # Process frame through overlay pipeline
                        processed_frame = self.overlay_pipeline.process(frame)
                    else:
                        # No overlays - pass frame through unchanged
                        processed_frame = frame
                    
                    # Final check before emitting
                    self._mutex.lock()
                    try:
                        if self._running and not self._shutdown:
                            self.frame_processed.emit(processed_frame)
                    finally:
                        self._mutex.unlock()
                except Exception:
                    # Ignore processing errors
                    pass
