"""
Video Processing Pipeline

Handles frame processing through overlay pipeline in a separate thread.
Worker runs continuously and handles both overlay and pass-through cases.
"""
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import numpy as np
import cv2
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
            self._frame_queue.clear()
            # Store frame as read-only view to eliminate copy overhead
            # Overlays must not modify the frame in-place
            # Make the array read-only to prevent accidental modifications
            frame_view = frame.view()
            frame_view.flags.writeable = False
            self._frame_queue.append(frame_view)
            self._condition.wakeOne()  # Wake up the processing loop
        except (RuntimeError, ValueError) as e:
            # Specific exception handling for mutex and array errors
            import logging
            logging.getLogger(__name__).warning(f"Frame update error: {e}")
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
            except (RuntimeError, ValueError) as e:
                import logging
                logging.getLogger(__name__).error(f"Frame queue error: {e}")
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
                        # Process frame through overlay pipeline (will create new array)
                        processed_frame = self.overlay_pipeline.process(frame)
                    else:
                        # No overlays - pass read-only frame through unchanged
                        # This avoids unnecessary copies when no processing is needed
                        processed_frame = frame

                    # Final check before emitting
                    self._mutex.lock()
                    try:
                        if self._running and not self._shutdown:
                            self.frame_processed.emit(processed_frame)
                    finally:
                        self._mutex.unlock()
                except (cv2.error, ValueError, RuntimeError) as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Frame processing error: {e}")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Unexpected error in frame processing: {e}")
