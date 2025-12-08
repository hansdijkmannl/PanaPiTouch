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

# Default to X11/XWayland
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

# Disable all scaling - run at native resolution
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '0')
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '0')
os.environ.pop('QT_SCALE_FACTOR', None)  # clear any forced scale

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

