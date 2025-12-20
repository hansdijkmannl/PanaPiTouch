"""
Multiview Manager for PanaPiTouch

Composites multiple camera streams into a single grid view.
Optimized for Raspberry Pi 5 with 8GB RAM.
"""
import cv2
import numpy as np
import threading
import time
import requests
from typing import Dict, List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class CameraInfo:
    """Camera info for multiview"""
    id: int
    name: str
    ip_address: str
    username: str = "admin"
    password: str = "admin"


class MultiviewStream:
    """Handles a single camera stream for multiview (lower resolution)"""
    
    def __init__(self, camera: CameraInfo, resolution: Tuple[int, int] = (640, 360)):
        self.camera = camera
        self.resolution = resolution
        self._running = False
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._last_frame_time = 0
        # Exponential backoff for failed connections
        self._connection_failures = 0
        self._max_backoff = 30  # Maximum 30 seconds
    
    @property
    def frame(self) -> Optional[np.ndarray]:
        """Get current frame (thread-safe)"""
        with self._frame_lock:
            return self._current_frame
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def get_stream_url(self) -> str:
        """Get MJPEG stream URL with lower resolution"""
        w, h = self.resolution
        # Panasonic MJPEG URL with resolution parameter
        return f"http://{self.camera.ip_address}/cgi-bin/mjpeg?resolution={w}x{h}"

    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        if self._connection_failures == 0:
            return 0
        # Exponential: 2, 4, 8, 16, 30, 30...
        return min(2 ** self._connection_failures, self._max_backoff)

    def _wait_with_backoff(self):
        """Wait with exponential backoff, checking _running to allow early exit"""
        delay = self._calculate_backoff_delay()
        if delay == 0:
            return
        end_time = time.time() + delay
        while self._running and time.time() < end_time:
            time.sleep(0.5)
    
    def _capture_loop(self):
        """Capture frames in background thread"""
        stream_url = self.get_stream_url()
        auth = (self.camera.username, self.camera.password)

        while self._running:
            # Wait with exponential backoff before retry
            self._wait_with_backoff()
            if not self._running:
                break

            try:
                # Try to open stream with timeout
                cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)

                if not cap.isOpened():
                    self._connected = False
                    self._connection_failures += 1
                    cap.release()
                    # Fallback: try snapshot mode
                    self._capture_snapshot_loop(auth)
                    continue

                # Successfully connected
                self._connected = True
                self._connection_failures = 0

                while self._running:
                    ret, frame = cap.read()
                    if not ret:
                        self._connected = False
                        self._connection_failures += 1
                        break

                    # Resize if needed
                    if frame.shape[:2] != (self.resolution[1], self.resolution[0]):
                        frame = cv2.resize(frame, self.resolution, interpolation=cv2.INTER_LINEAR)

                    with self._frame_lock:
                        self._current_frame = frame
                    self._last_frame_time = time.time()

                cap.release()

            except Exception as e:
                self._connected = False
                self._connection_failures += 1
                print(f"Multiview stream error ({self.camera.name}): {e}")
    
    def _capture_snapshot_loop(self, auth):
        """Fallback to snapshot capture"""
        w, h = self.resolution
        snapshot_url = f"http://{self.camera.ip_address}/cgi-bin/camera?resolution={w}x{h}"

        # Snapshot mode often means camera is unreachable - use longer backoff
        consecutive_failures = 0

        while self._running:
            try:
                response = requests.get(snapshot_url, auth=auth, timeout=2)
                if response.status_code == 200:
                    self._connected = True
                    self._connection_failures = 0  # Reset on success
                    consecutive_failures = 0
                    img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    if frame is not None:
                        if frame.shape[:2] != (h, w):
                            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)

                        with self._frame_lock:
                            self._current_frame = frame
                        self._last_frame_time = time.time()
                    time.sleep(0.05)  # 20fps for snapshots
                else:
                    self._connected = False
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        # After 3 snapshot failures, use exponential backoff
                        self._connection_failures += 1
                        return  # Exit snapshot loop to retry main stream
                    time.sleep(0.2)
            except Exception:
                self._connected = False
                consecutive_failures += 1
                if consecutive_failures > 3:
                    self._connection_failures += 1
                    return
                time.sleep(0.2)
    
    def start(self):
        """Start streaming"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop streaming"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self._connected = False


class MultiviewManager:
    """
    Manages multiple camera streams and composites them into a grid.
    
    Optimized for Pi 5:
    - Uses ThreadPoolExecutor for parallel operations
    - Lower resolution per tile (640x360 or 480x270)
    - Frame skipping if falling behind
    - Efficient numpy compositing
    """
    
    def __init__(self, output_size: Tuple[int, int] = (1920, 1080)):
        self.output_size = output_size
        self._streams: Dict[int, MultiviewStream] = {}
        self._cameras: List[CameraInfo] = []
        self._running = False
        self._grid_cols = 2
        self._grid_rows = 2
        self._composite_thread: Optional[threading.Thread] = None
        self._frame_callback: Optional[Callable[[np.ndarray], None]] = None
        self._fps = 0
        self._last_frame_time = 0
    
    @property
    def fps(self) -> float:
        return self._fps
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback for composite frames"""
        self._frame_callback = callback
    
    def _calculate_tile_size(self) -> Tuple[int, int]:
        """Calculate tile size based on grid and output"""
        tile_w = self.output_size[0] // self._grid_cols
        tile_h = self.output_size[1] // self._grid_rows
        return (tile_w, tile_h)
    
    def _calculate_stream_resolution(self) -> Tuple[int, int]:
        """Calculate optimal stream resolution per tile"""
        tile_w, tile_h = self._calculate_tile_size()
        
        # Request slightly higher resolution for better quality
        # but cap at reasonable values for Pi 5 performance
        stream_w = min(tile_w, 640)
        stream_h = min(tile_h, 360)
        
        # Maintain 16:9 aspect ratio
        if stream_w / stream_h > 16/9:
            stream_w = int(stream_h * 16 / 9)
        else:
            stream_h = int(stream_w * 9 / 16)
        
        return (stream_w, stream_h)
    
    def start(self, cameras: List[CameraInfo], cols: int, rows: int):
        """Start multiview with given cameras and grid layout"""
        if self._running:
            self.stop()
        
        self._cameras = cameras[:cols * rows]  # Limit to grid size
        self._grid_cols = cols
        self._grid_rows = rows
        
        # Calculate stream resolution
        stream_res = self._calculate_stream_resolution()
        print(f"Multiview: {cols}x{rows} grid, stream res: {stream_res}")
        
        # Create and start streams
        self._streams.clear()
        for camera in self._cameras:
            stream = MultiviewStream(camera, resolution=stream_res)
            stream.start()
            self._streams[camera.id] = stream
        
        # Start composite thread
        self._running = True
        self._composite_thread = threading.Thread(target=self._composite_loop, daemon=True)
        self._composite_thread.start()
    
    def stop(self):
        """Stop all streams and compositing"""
        self._running = False
        
        # Wait for composite thread
        if self._composite_thread:
            self._composite_thread.join(timeout=1)
        
        # Stop all streams
        for stream in self._streams.values():
            stream.stop()
        self._streams.clear()
    
    def _create_no_signal_tile(self, size: Tuple[int, int], text: str = "NO SIGNAL") -> np.ndarray:
        """Create a 'no signal' tile"""
        tile = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        tile[:] = (20, 20, 25)  # Dark gray
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (size[0] - text_size[0]) // 2
        text_y = (size[1] + text_size[1]) // 2
        cv2.putText(tile, text, (text_x, text_y), font, font_scale, (80, 80, 90), thickness)
        
        return tile
    
    def _create_camera_label(self, tile: np.ndarray, name: str, connected: bool) -> np.ndarray:
        """Add camera label to tile"""
        h, w = tile.shape[:2]
        
        # Label background
        label_h = 24
        cv2.rectangle(tile, (0, 0), (w, label_h), (0, 0, 0), -1)
        
        # Camera name
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        # Truncate name if too long
        display_name = name[:12] if len(name) > 12 else name
        
        # Connection indicator
        indicator_color = (0, 200, 0) if connected else (0, 0, 200)  # BGR: green/red
        cv2.circle(tile, (12, label_h // 2), 5, indicator_color, -1)
        
        # Name text
        cv2.putText(tile, display_name, (24, label_h - 6), font, font_scale, (255, 255, 255), thickness)
        
        return tile
    
    def _resize_and_crop_to_tile(self, frame: np.ndarray, tile_size: Tuple[int, int]) -> np.ndarray:
        """
        Resize and center-crop frame to fill tile while maintaining 16:9 aspect ratio.
        
        This crops the sides of the image rather than letterboxing.
        """
        tile_w, tile_h = tile_size
        src_h, src_w = frame.shape[:2]
        
        # Calculate scaling to fill tile (crop-to-fill strategy)
        # Scale so the smaller dimension fills the tile
        scale_w = tile_w / src_w
        scale_h = tile_h / src_h
        scale = max(scale_w, scale_h)  # Use max to ensure we fill (not fit)
        
        # New size after scaling
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        
        # Resize frame
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Center crop to tile size
        x_offset = (new_w - tile_w) // 2
        y_offset = (new_h - tile_h) // 2
        
        cropped = resized[y_offset:y_offset + tile_h, x_offset:x_offset + tile_w]
        
        return cropped
    
    def _composite_loop(self):
        """Main compositing loop"""
        frame_count = 0
        start_time = time.time()
        target_fps = 20  # Target 20fps for multiview
        frame_time = 1.0 / target_fps
        
        tile_size = self._calculate_tile_size()
        
        while self._running:
            loop_start = time.time()
            
            # Create composite frame
            composite = np.zeros((self.output_size[1], self.output_size[0], 3), dtype=np.uint8)
            composite[:] = (15, 15, 20)  # Dark background
            
            # Fill grid with camera tiles
            for idx, camera in enumerate(self._cameras):
                row = idx // self._grid_cols
                col = idx % self._grid_cols
                
                if idx >= self._grid_rows * self._grid_cols:
                    break
                
                # Get frame from stream
                stream = self._streams.get(camera.id)
                if stream:
                    frame = stream.frame
                    connected = stream.is_connected
                else:
                    frame = None
                    connected = False
                
                # Create tile
                if frame is not None:
                    # Resize and crop frame to tile size (maintains 16:9, crops edges)
                    tile = self._resize_and_crop_to_tile(frame, tile_size)
                else:
                    tile = self._create_no_signal_tile(tile_size, f"CAM {idx + 1}")
                
                # Add camera label
                tile = self._create_camera_label(tile, camera.name, connected)
                
                # Place tile in composite
                x = col * tile_size[0]
                y = row * tile_size[1]
                composite[y:y + tile_size[1], x:x + tile_size[0]] = tile
                
                # Add border between tiles
                border_color = (40, 40, 50)
                if col > 0:
                    cv2.line(composite, (x, y), (x, y + tile_size[1]), border_color, 2)
                if row > 0:
                    cv2.line(composite, (x, y), (x + tile_size[0], y), border_color, 2)
            
            # Fill empty slots
            total_slots = self._grid_cols * self._grid_rows
            num_cameras = len(self._cameras)
            
            for idx in range(num_cameras, total_slots):
                row = idx // self._grid_cols
                col = idx % self._grid_cols
                
                tile = self._create_no_signal_tile(tile_size, "EMPTY")
                
                x = col * tile_size[0]
                y = row * tile_size[1]
                composite[y:y + tile_size[1], x:x + tile_size[0]] = tile
                
                # Borders
                border_color = (40, 40, 50)
                if col > 0:
                    cv2.line(composite, (x, y), (x, y + tile_size[1]), border_color, 2)
                if row > 0:
                    cv2.line(composite, (x, y), (x + tile_size[0], y), border_color, 2)
            
            # Add multiview indicator
            cv2.putText(composite, f"MULTIVIEW {self._grid_cols}x{self._grid_rows}", 
                       (10, self.output_size[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (150, 150, 150), 1)
            
            # Send to callback
            if self._frame_callback:
                # Notify callback (error-handled)
                try:
                    self._frame_callback(composite)
                except Exception as e:
                    print(f"Multiview frame callback error: {e}")
            
            # Calculate FPS
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                self._fps = frame_count / elapsed
                frame_count = 0
                start_time = time.time()
            
            # Rate limiting
            loop_elapsed = time.time() - loop_start
            if loop_elapsed < frame_time:
                time.sleep(frame_time - loop_elapsed)
    
    def get_camera_count(self) -> int:
        """Get number of active cameras"""
        return len(self._cameras)
    
    def get_grid_size(self) -> Tuple[int, int]:
        """Get current grid size (cols, rows)"""
        return (self._grid_cols, self._grid_rows)

