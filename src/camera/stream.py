"""
Camera Stream Handler for Panasonic PTZ cameras

Handles MJPEG stream capture and frame processing.
"""
import cv2
import numpy as np
import threading
import queue
import time
import requests
from typing import Optional, Callable, Tuple
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


class CameraStream:
    """
    Handles video streaming from Panasonic PTZ cameras.
    
    Panasonic PTZ cameras (UE150, HE40, etc.) support:
    - MJPEG streaming via /cgi-bin/mjpeg
    - RTSP streaming (H.264/H.265)
    - Single frame capture via /cgi-bin/camera
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
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def current_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            # Return a copy to prevent external modification
            return self._current_frame.copy() if self._current_frame is not None else None
    
    @property
    def fps(self) -> float:
        return self._fps
    
    @property
    def error_message(self) -> str:
        return self._error_message
    
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
        """Notify all callbacks of new frame"""
        for callback in self._callbacks:
            try:
                callback(frame)
            except Exception as e:
                print(f"Frame callback error: {e}")
    
    def _capture_mjpeg(self):
        """Capture frames from MJPEG stream - optimized for Raspberry Pi"""
        stream_url = self.get_stream_url()
        
        while self._running:
            try:
                # Create video capture with MJPEG stream
                cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                
                # Optimize capture settings for performance
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
                cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30fps
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
    
    def _capture_snapshot(self):
        """Capture frames via repeated snapshots (fallback)"""
        snapshot_url = self.get_snapshot_url()
        auth = (self.config.username, self.config.password) if self.config.username else None
        
        while self._running:
            try:
                response = requests.get(snapshot_url, timeout=2, auth=auth, stream=True)
                
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
                else:
                    self._connected = False
                    self._error_message = f"HTTP {response.status_code}"
                    
            except Exception as e:
                self._connected = False
                self._error_message = str(e)
            
            # Limit snapshot rate
            time.sleep(0.033)  # ~30fps
    
    def start(self, use_mjpeg: bool = True):
        """Start capturing frames"""
        if self._running:
            return
        
        self._running = True
        
        if use_mjpeg:
            self._thread = threading.Thread(target=self._capture_mjpeg, daemon=True)
        else:
            self._thread = threading.Thread(target=self._capture_snapshot, daemon=True)
        
        self._thread.start()
    
    def stop(self):
        """Stop capturing frames"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
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

