"""
Camera Stream Handler for Panasonic PTZ cameras

Handles MJPEG and RTSP (H.264/H.265) stream capture and frame processing.
Uses standard RTSP → RTP protocol as documented by Panasonic PTZ Control Center.
"""
import cv2
import numpy as np
import threading
import queue
import time
import requests
import re
from typing import Optional, Callable, Tuple, List, Dict
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass
class StreamConfig:
    """Stream configuration"""
    ip_address: str
    port: int = 80
    username: str = "admin"
    password: str = "admin"
    resolution: Tuple[int, int] = (1920, 1080)
    rtsp_port: int = 554  # Standard RTSP port
    rtsp_stream: int = 1  # Stream number (1-4 typically)


class CameraStream:
    """
    Handles video streaming from Panasonic PTZ cameras.
    
    Panasonic PTZ cameras (UE150, HE40, UE100, UE160, etc.) support:
    - MJPEG streaming via /cgi-bin/mjpeg
    - RTSP streaming (H.264/H.265) via standard RTSP → RTP protocol
      Format: rtsp://<ip>:554/mediainput/h264/stream_1
    - Single frame capture via /cgi-bin/camera
    
    Uses the same protocol as Panasonic PTZ Control Center:
    - HTTP/CGI API for discovery and control (port 80)
    - RTSP/RTP for video preview (port 554)
    """
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._callbacks: list = []
        self._last_frame_time = 0
        self._fps = 0
        self._connected = False
        self._error_message = ""
        self._stream_type: Optional[str] = None  # 'rtsp', 'mjpeg', or 'snapshot'
        self._rtsp_attempts = 0
        self._max_rtsp_attempts = 3  # Try RTSP 3 times before falling back
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def current_frame(self) -> Optional[np.ndarray]:
        """Get current frame (returns copy for thread safety)"""
        try:
            with self._frame_lock:
                # Return a copy to prevent external modification
                if self._current_frame is not None:
                    return self._current_frame.copy()
                return None
        except Exception:
            # Lock might fail if stream is being destroyed
            return None
    
    @property
    def fps(self) -> float:
        return self._fps
    
    @property
    def error_message(self) -> str:
        return self._error_message
    
    def pause(self):
        """Pause the stream to save CPU (stops processing frames but keeps connection)"""
        self._paused = True
    
    def resume(self):
        """Resume the stream after pausing"""
        self._paused = False
    
    @property
    def is_paused(self) -> bool:
        return getattr(self, '_paused', False)
    
    def get_rtsp_url(self, stream_number: Optional[int] = None) -> str:
        """
        Get RTSP stream URL for H.264/H.265 streaming.
        
        Format matches Panasonic PTZ Control Center:
        rtsp://<ip>:554/mediainput/h264/stream_1
        
        Args:
            stream_number: Stream number (1-4). Defaults to config.rtsp_stream.
        
        Returns:
            RTSP URL string
        """
        stream_num = stream_number or self.config.rtsp_stream
        auth = f"{self.config.username}:{self.config.password}@" if self.config.username else ""
        # Standard Panasonic RTSP URL format (lowercase "mediainput")
        return f"rtsp://{auth}{self.config.ip_address}:{self.config.rtsp_port}/mediainput/h264/stream_{stream_num}"
    
    def query_rtsp_streams(self) -> List[Dict[str, any]]:
        """
        Query camera for available RTSP streams using CGI API.
        
        Uses Panasonic's Integrated Camera Interface:
        http://<cam_ip>/cgi-bin/getuid?FILE=2&vcodec=h264
        
        Returns:
            List of stream info dicts with keys: stream_number, resolution, bitrate, etc.
        """
        streams = []
        auth = (self.config.username, self.config.password) if self.config.username else None
        
        try:
            # Query for H.264 streams (FILE=2 typically refers to H.264)
            url = f"http://{self.config.ip_address}:{self.config.port}/cgi-bin/getuid?FILE=2&vcodec=h264"
            response = requests.get(url, timeout=3, auth=auth)
            
            if response.status_code == 200:
                # Parse response (format varies by camera model)
                # Example response might contain stream info
                content = response.text
                
                # Try to extract stream information
                # This is model-dependent, so we'll return basic info
                for stream_num in range(1, 5):  # Typically 1-4 streams
                    streams.append({
                        'stream_number': stream_num,
                        'url': self.get_rtsp_url(stream_num),
                        'codec': 'h264',
                        'available': True  # Assume available, actual check would require RTSP connection test
                    })
        except Exception as e:
            print(f"Error querying RTSP streams: {e}")
        
        return streams
    
    def get_stream_url(self) -> str:
        """Get MJPEG stream URL with resolution parameter for better performance"""
        auth = f"{self.config.username}:{self.config.password}@" if self.config.username else ""
        # Request specific resolution from camera to reduce bandwidth and processing
        w, h = self.config.resolution
        return f"http://{auth}{self.config.ip_address}:{self.config.port}/cgi-bin/mjpeg?resolution={w}x{h}"
    
    def get_snapshot_url(self) -> str:
        """Get single frame URL"""
        return f"http://{self.config.ip_address}:{self.config.port}/cgi-bin/camera?resolution={self.config.resolution[0]}x{self.config.resolution[1]}"
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Add callback for new frames"""
        self._callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Remove frame callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, frame: np.ndarray):
        """Notify all callbacks of new frame (thread-safe, error-handled)"""
        # Create a copy of callbacks list to avoid modification during iteration
        callbacks_to_call = list(self._callbacks)
        
        for callback in callbacks_to_call:
            try:
                callback(frame)
            except Exception as e:
                # Log error but don't crash - remove problematic callback
                print(f"Frame callback error (removing callback): {e}")
                try:
                    if callback in self._callbacks:
                        self._callbacks.remove(callback)
                except:
                    pass  # Ignore errors during cleanup
    
    def _capture_mjpeg(self):
        """Capture frames from MJPEG stream - optimized for Raspberry Pi"""
        if self._stream_type != 'mjpeg':
            self._stream_type = 'mjpeg'
        
        stream_url = self.get_stream_url()
        print(f"Using MJPEG stream: {stream_url}")
        
        while self._running:
            try:
                # Create video capture with MJPEG stream
                cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                
                # Optimize capture settings for performance
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
                cap.set(cv2.CAP_PROP_FPS, 25)  # Request 25fps (common camera frame rate)
                # Try to use hardware acceleration if available
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                except:
                    pass
                
                if not cap.isOpened():
                    self._connected = False
                    self._error_message = "Failed to open stream"
                    time.sleep(2)
                    continue
                
                self._connected = True
                self._error_message = ""
                frame_count = 0
                start_time = time.time()
                
                # Pre-allocate frame buffer to avoid repeated allocations
                target_w, target_h = self.config.resolution
                
                while self._running:
                    # Skip frame processing when paused to save CPU
                    if getattr(self, '_paused', False):
                        time.sleep(0.1)
                        continue
                    
                    ret, frame = cap.read()
                    
                    if not ret:
                        self._connected = False
                        self._error_message = "Stream disconnected"
                        break
                    
                    # Early downscaling for performance - resize immediately if frame is larger than target
                    # This reduces processing overhead for subsequent operations
                    frame_h, frame_w = frame.shape[:2]
                    if frame_w > target_w or frame_h > target_h:
                        # Use INTER_AREA for downscaling (faster and better quality for downscaling)
                        frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    elif frame_w != target_w or frame_h != target_h:
                        # Upscaling - use INTER_LINEAR
                        frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                    
                    # Update current frame (direct assignment, no lock overhead for simple reference)
                    with self._frame_lock:
                        self._current_frame = frame
                    
                    # Calculate FPS
                    frame_count += 1
                    elapsed = time.time() - start_time
                    if elapsed >= 1.0:
                        self._fps = frame_count / elapsed
                        frame_count = 0
                        start_time = time.time()
                    
                    # Notify callbacks directly (no copy needed, callbacks should not modify)
                    self._notify_callbacks(frame)
                
                cap.release()
                
            except Exception as e:
                self._connected = False
                self._error_message = str(e)
                print(f"Stream error: {e}")
                time.sleep(2)
    
    def _capture_rtsp(self):
        """
        Capture frames from RTSP stream (H.264/H.265).
        
        Uses standard RTSP → RTP protocol as used by Panasonic PTZ Control Center.
        OpenCV's VideoCapture handles RTSP negotiation and RTP packet reception.
        
        Falls back to MJPEG if RTSP fails after multiple attempts.
        """
        rtsp_url = self.get_rtsp_url()
        self._stream_type = 'rtsp'
        self._rtsp_attempts = 0
        
        print(f"Attempting RTSP stream: {rtsp_url}")
        
        while self._running:
            try:
                self._rtsp_attempts += 1
                
                # Open RTSP stream using OpenCV (which handles RTSP/RTP internally)
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                
                # Optimize capture settings
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
                cap.set(cv2.CAP_PROP_FPS, 25)  # Request 25fps (common camera frame rate)
                
                if not cap.isOpened():
                    self._connected = False
                    self._error_message = "Failed to open RTSP stream"
                    
                    if self._rtsp_attempts >= self._max_rtsp_attempts:
                        print(f"RTSP failed after {self._max_rtsp_attempts} attempts, falling back to MJPEG...")
                        self._fallback_to_mjpeg()
                        return
                    
                    print(f"RTSP connection attempt {self._rtsp_attempts}/{self._max_rtsp_attempts} failed, retrying...")
                    time.sleep(2)
                    continue
                
                # Successfully opened RTSP stream
                self._connected = True
                self._error_message = ""
                self._rtsp_attempts = 0  # Reset counter on success
                print(f"RTSP stream connected successfully")
                
                frame_count = 0
                start_time = time.time()
                target_w, target_h = self.config.resolution
                consecutive_failures = 0
                max_consecutive_failures = 30  # ~1 second at 30fps
                
                while self._running:
                    # Skip frame processing when paused to save CPU
                    if getattr(self, '_paused', False):
                        time.sleep(0.1)
                        continue
                    
                    ret, frame = cap.read()
                    
                    if not ret:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            self._connected = False
                            self._error_message = "RTSP stream disconnected"
                            print("RTSP stream disconnected, falling back to MJPEG...")
                            cap.release()
                            self._fallback_to_mjpeg()
                            return
                        continue
                    
                    # Reset failure counter on successful frame
                    consecutive_failures = 0
                    
                    # Resize if needed
                    frame_h, frame_w = frame.shape[:2]
                    if frame_w > target_w or frame_h > target_h:
                        frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    elif frame_w != target_w or frame_h != target_h:
                        frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                    
                    # Update current frame
                    with self._frame_lock:
                        self._current_frame = frame
                    
                    # Calculate FPS
                    frame_count += 1
                    elapsed = time.time() - start_time
                    if elapsed >= 1.0:
                        self._fps = frame_count / elapsed
                        frame_count = 0
                        start_time = time.time()
                    
                    # Notify callbacks
                    self._notify_callbacks(frame)
                
                cap.release()
                
            except Exception as e:
                self._connected = False
                self._error_message = str(e)
                print(f"RTSP stream error: {e}")
                
                if self._rtsp_attempts >= self._max_rtsp_attempts:
                    print(f"RTSP failed after {self._max_rtsp_attempts} attempts, falling back to MJPEG...")
                    self._fallback_to_mjpeg()
                    return
                
                time.sleep(2)
    
    def _fallback_to_mjpeg(self):
        """Fallback to MJPEG streaming when RTSP fails"""
        if not self._running:
            return
        
        print("Switching to MJPEG stream as fallback...")
        self._stream_type = 'mjpeg'
        
        # Stop current thread and start MJPEG capture
        # Note: We're already in a thread, so we'll start MJPEG in a new thread
        mjpeg_thread = threading.Thread(target=self._capture_mjpeg, daemon=True)
        mjpeg_thread.start()
    
    def _capture_snapshot(self):
        """Capture frames via repeated snapshots (fallback)"""
        snapshot_url = self.get_snapshot_url()
        auth = (self.config.username, self.config.password) if self.config.username else None
        
        while self._running:
            # Skip frame processing when paused to save CPU
            if getattr(self, '_paused', False):
                time.sleep(0.1)
                continue
            
            try:
                request_start = time.time()
                response = requests.get(snapshot_url, timeout=1, auth=auth, stream=False)  # Reduced timeout and removed stream=True for faster response
                
                if response.status_code == 200:
                    self._connected = True
                    self._error_message = ""
                    
                    # Decode JPEG image
                    img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Resize to target resolution
                        if frame.shape[1] != self.config.resolution[0] or frame.shape[0] != self.config.resolution[1]:
                            frame = cv2.resize(frame, self.config.resolution)
                        
                        with self._frame_lock:
                            self._current_frame = frame
                        
                        self._notify_callbacks(frame)
                        
                        # Calculate actual frame time and adjust sleep to maintain ~25fps
                        request_time = time.time() - request_start
                        target_frame_time = 1.0 / 25.0  # 25fps = 40ms per frame
                        sleep_time = max(0.01, target_frame_time - request_time)  # Ensure at least 10ms sleep
                        time.sleep(sleep_time)
                    else:
                        time.sleep(0.04)  # Default 25fps if decode fails
                else:
                    self._connected = False
                    self._error_message = f"HTTP {response.status_code}"
                    time.sleep(0.2)  # Longer sleep on error
                    
            except Exception as e:
                self._connected = False
                self._error_message = str(e)
                time.sleep(0.2)  # Longer sleep on exception
    
    def start(self, use_rtsp: bool = True, use_snapshot: bool = False, force_mjpeg: bool = False):
        """
        Start capturing frames.
        
        By default, tries RTSP first (H.264/H.265) and automatically falls back to MJPEG if RTSP fails.
        This matches Panasonic PTZ Control Center behavior: RTSP as primary, MJPEG as fallback.
        
        Args:
            use_rtsp: If True (default), try RTSP first with automatic fallback to MJPEG.
            use_snapshot: If True, use snapshot method. Only used if use_rtsp is False.
            force_mjpeg: If True, skip RTSP and use MJPEG directly.
        """
        if self._running:
            return
        
        # Ensure any previous thread is fully stopped before starting a new one
        if self._thread is not None:
            self._running = False  # Signal thread to stop
            try:
                if self._thread.is_alive():
                    self._thread.join(timeout=1.0)  # Wait for cleanup
            except Exception:
                pass
            finally:
                self._thread = None
        
        self._running = True
        
        if force_mjpeg:
            # Skip RTSP, use MJPEG directly
            self._stream_type = 'mjpeg'
            self._thread = threading.Thread(target=self._capture_mjpeg, daemon=True)
        elif use_snapshot:
            # Use snapshot method
            self._stream_type = 'snapshot'
            self._thread = threading.Thread(target=self._capture_snapshot, daemon=True)
        elif use_rtsp:
            # Try RTSP first (will fallback to MJPEG automatically if it fails)
            self._thread = threading.Thread(target=self._capture_rtsp, daemon=True)
        else:
            # Use MJPEG directly
            self._stream_type = 'mjpeg'
            self._thread = threading.Thread(target=self._capture_mjpeg, daemon=True)
        
        self._thread.start()
    
    def stop(self):
        """Stop capturing frames (thread-safe)"""
        if not self._running:
            return  # Already stopped
        
        self._running = False
        
        # Clear callbacks to prevent memory leaks
        self._callbacks.clear()
        
        # Wait for thread to finish
        if self._thread:
            try:
                self._thread.join(timeout=3)  # Increased timeout for cleanup
            except Exception as e:
                print(f"Error joining stream thread: {e}")
            finally:
                self._thread = None
        
        # Clear frame data
        with self._frame_lock:
            self._current_frame = None
        
        self._connected = False
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame"""
        snapshot_url = self.get_snapshot_url()
        auth = (self.config.username, self.config.password) if self.config.username else None
        
        try:
            response = requests.get(snapshot_url, timeout=5, auth=auth)
            
            if response.status_code == 200:
                img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                return frame
        except Exception as e:
            print(f"Snapshot error: {e}")
        
        return None
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to camera"""
        try:
            url = f"http://{self.config.ip_address}:{self.config.port}/cgi-bin/aw_cam?cmd=QID&res=1"
            auth = (self.config.username, self.config.password) if self.config.username else None
            
            response = requests.get(url, timeout=3, auth=auth)
            
            if response.status_code == 200:
                return True, "Connected"
            elif response.status_code == 401:
                return False, "Authentication failed"
            else:
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection refused"
        except Exception as e:
            return False, str(e)

