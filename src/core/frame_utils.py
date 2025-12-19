"""
Frame utility functions for optimization

Shared utility functions for frame processing, resizing, and manipulation.
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import hashlib


def compute_frame_hash(frame: np.ndarray) -> int:
    """
    Compute a fast hash of frame content for change detection.

    Uses downsampled frame to avoid hashing full 6MB of data.
    This is much faster than comparing full frames.

    Args:
        frame: Input frame (BGR)

    Returns:
        Hash value as integer
    """
    # Downsample heavily for fast hashing (use every 32nd pixel)
    downsampled = frame[::32, ::32].tobytes()
    # Use xxhash if available, otherwise fall back to built-in hash
    return hash(downsampled)


def resize_frame(frame: np.ndarray, target_size: Tuple[int, int],
                 cache: Optional[dict] = None) -> np.ndarray:
    """
    Resize frame with optional caching for common sizes.

    Uses appropriate interpolation based on up/downscaling.
    Caches resized frames to avoid repeated resizing at same size.

    Args:
        frame: Input frame
        target_size: (width, height) tuple
        cache: Optional dict for caching resized frames

    Returns:
        Resized frame
    """
    h, w = frame.shape[:2]
    target_w, target_h = target_size

    # Check cache if provided
    if cache is not None:
        cache_key = (id(frame), target_w, target_h)
        if cache_key in cache:
            return cache[cache_key]

    # No resize needed
    if w == target_w and h == target_h:
        return frame

    # Choose interpolation method based on scaling direction
    if target_w < w or target_h < h:
        # Downscaling - use INTER_AREA (faster and better quality)
        resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        # Upscaling - use INTER_LINEAR (good quality/speed balance)
        resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # Store in cache if provided (limit cache size to prevent memory leak)
    if cache is not None and len(cache) < 10:
        cache[cache_key] = resized

    return resized


def calculate_aspect_fit_size(source_size: Tuple[int, int],
                               target_size: Tuple[int, int]) -> Tuple[int, int]:
    """
    Calculate size to fit source into target while maintaining aspect ratio.

    Args:
        source_size: (width, height) of source
        target_size: (width, height) of target

    Returns:
        (width, height) tuple of fitted size
    """
    src_w, src_h = source_size
    tgt_w, tgt_h = target_size

    if tgt_w <= 0 or tgt_h <= 0 or src_w <= 0 or src_h <= 0:
        return source_size

    # Calculate scale to fit
    scale = min(tgt_w / src_w, tgt_h / src_h)

    return (int(src_w * scale), int(src_h * scale))


def get_stream_url(ip_address: str, port: int, username: str, password: str,
                   resolution: Tuple[int, int], stream_type: str = 'mjpeg') -> str:
    """
    Get camera stream URL (MJPEG or RTSP).

    Centralized URL construction for consistency.

    Args:
        ip_address: Camera IP
        port: HTTP port (80) or RTSP port (554)
        username: Username for auth
        password: Password for auth
        resolution: (width, height) tuple
        stream_type: 'mjpeg', 'rtsp', or 'snapshot'

    Returns:
        Stream URL string
    """
    auth = f"{username}:{password}@" if username else ""

    if stream_type == 'mjpeg':
        w, h = resolution
        return f"http://{auth}{ip_address}:{port}/cgi-bin/mjpeg?resolution={w}x{h}"
    elif stream_type == 'rtsp':
        # Default to stream 1, port 554
        return f"rtsp://{auth}{ip_address}:554/mediainput/h264/stream_1"
    elif stream_type == 'snapshot':
        w, h = resolution
        return f"http://{ip_address}:{port}/cgi-bin/camera?resolution={w}x{h}"
    else:
        raise ValueError(f"Unknown stream type: {stream_type}")
