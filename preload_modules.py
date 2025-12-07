#!/usr/bin/env python3
"""
Preload Modules Script

Preloads heavy Python modules and plugins at boot time to speed up app startup.
This script:
1. Compiles all Python modules to bytecode (.pyc files)
2. Imports all heavy dependencies to warm up OS file cache
3. Ensures modules are ready when the main app starts
"""
import sys
import os
import logging
import py_compile
import compileall

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compile_all_modules():
    """Compile all Python modules to bytecode for faster loading"""
    try:
        logger.info("Compiling Python modules to bytecode...")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Compile all .py files in src/ directory
        src_dir = os.path.join(base_dir, 'src')
        if os.path.exists(src_dir):
            compileall.compile_dir(src_dir, quiet=1, force=True)
            logger.info("Compiled application modules")
        
        # Compile main.py
        main_py = os.path.join(base_dir, 'main.py')
        if os.path.exists(main_py):
            py_compile.compile(main_py, doraise=True)
            logger.info("Compiled main.py")
        
        return True
    except Exception as e:
        logger.warning(f"Error compiling modules (non-fatal): {e}")
        return True  # Don't fail if compilation fails

def preload_modules():
    """Preload all heavy modules and plugins"""
    try:
        logger.info("Preloading Python modules...")
        
        # Set environment variables for Qt
        if 'QT_QPA_PLATFORM' not in os.environ:
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        
        # Preload PyQt6 modules (heavy)
        logger.info("Preloading PyQt6 modules...")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt, QTimer, pyqtSlot
        from PyQt6.QtGui import QFont, QImage, QPixmap
        
        # Preload QtWebEngineWidgets (very heavy - takes longest to load)
        logger.info("Preloading QtWebEngineWidgets...")
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        
        # Preload OpenCV (heavy)
        logger.info("Preloading OpenCV...")
        import cv2
        import numpy as np
        
        # Preload other common libraries
        logger.info("Preloading other libraries...")
        import requests
        import threading
        import queue
        import time
        import subprocess
        import json
        import re
        
        # Preload application modules (this will cache bytecode and warm OS cache)
        logger.info("Preloading application modules...")
        from src.core.logging_config import setup_logging
        from src.config.settings import Settings
        from src.camera.stream import CameraStream, StreamConfig
        from src.camera.discovery import CameraDiscovery
        from src.camera.multiview import MultiviewManager
        from src.atem.tally import ATEMTallyController
        from src.overlays import (
            FalseColorOverlay, WaveformOverlay, VectorscopeOverlay,
            FocusAssistOverlay, GridOverlay, FrameGuideOverlay
        )
        from src.core.video_pipeline import FrameWorker
        
        logger.info("All modules preloaded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error preloading modules: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # First compile all modules to bytecode
    compile_all_modules()
    
    # Then preload modules to warm up OS cache
    success = preload_modules()
    sys.exit(0 if success else 1)


