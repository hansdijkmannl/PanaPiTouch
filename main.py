#!/usr/bin/env python3
"""
PanaPiTouch - Panasonic PTZ Camera Touchscreen Monitor

A touchscreen application for monitoring Panasonic PTZ cameras
with video analysis overlays and Blackmagic ATEM tally integration.

Designed for use with Wisecoco 8" 2480x1860 AMOLED display.
"""
import sys
import os

# Set environment variables for Qt on Raspberry Pi
if 'QT_QPA_PLATFORM' not in os.environ:
    os.environ['QT_QPA_PLATFORM'] = 'xcb'  # or 'eglfs' for fullscreen
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# IMPORTANT: QtWebEngineWidgets must be imported before QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui import MainWindow


def main():
    """Main entry point"""
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
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

