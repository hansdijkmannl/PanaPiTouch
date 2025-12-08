#!/usr/bin/env python3
"""
PanaPiTouch - Panasonic PTZ Camera Touchscreen Monitor

A touchscreen application for monitoring Panasonic PTZ cameras
with video analysis overlays and Blackmagic ATEM tally integration.

Designed for use with Wisecoco 8" 2480x1860 AMOLED display.
"""
import sys
import os
import logging

# Set up logging first
from src.core.logging_config import setup_logging
setup_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

# Select platform dynamically: prefer Wayland if available; otherwise X11.
# Avoid forcing xcb when DISPLAY is missing (prevents "could not connect to display").
if 'QT_QPA_PLATFORM' not in os.environ:
    if os.environ.get('WAYLAND_DISPLAY'):
        os.environ['QT_QPA_PLATFORM'] = 'wayland'
    elif os.environ.get('DISPLAY'):
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    else:
        # Fallback: try Wayland first; if not present, Qt will still error visibly.
        os.environ['QT_QPA_PLATFORM'] = 'wayland'

# Disable all scaling - run at native resolution
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '0')
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '0')
os.environ.pop('QT_SCALE_FACTOR', None)  # clear any forced scale

# Enable system OSK (squeekboard) via Qt input method
# On Wayland, Qt will automatically use the system input method when text fields get focus
# This allows the Pi OS on-screen keyboard to appear automatically
if os.environ.get('WAYLAND_DISPLAY'):
    # On Wayland, let Qt use the default input method (squeekboard)
    # Don't set QT_IM_MODULE - let Qt auto-detect
    pass
elif os.environ.get('DISPLAY'):
    # On X11, we might need matchbox-keyboard
    # But let's try to use the system default first
    pass

# IMPORTANT: QtWebEngineWidgets must be imported before QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui import MainWindow


def main():
    """Main entry point"""
    try:
        logger.info("Starting PanaPiTouch application")
        
        # Create application
        app = QApplication(sys.argv)
        
        # Set application info
        app.setApplicationName("PanaPiTouch")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("PanaPiTouch")
        
        # Set default font
        font = QFont("Segoe UI", 11)
        if not font.exactMatch():
            font = QFont("SF Pro Display", 11)
            if not font.exactMatch():
                font = QFont("DejaVu Sans", 11)
        app.setFont(font)
        
        # Enable touch events
        app.setAttribute(Qt.ApplicationAttribute.AA_SynthesizeTouchForUnhandledMouseEvents, True)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # Run application
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("Fatal error starting application")
        raise


if __name__ == "__main__":
    main()

