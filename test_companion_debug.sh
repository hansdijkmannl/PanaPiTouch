#!/bin/bash
cd /home/admin/PanaPiTouch
python3 -c "
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()

# Add debug output
print(f'Window fullscreen: {window.isFullScreen()}')
print(f'Window size: {window.size()}')
print(f'Has OSK: {window.osk is not None}')
if window.osk:
    print(f'OSK visible: {window.osk.isVisible()}')

# Navigate to companion page
window.page_stack.setCurrentIndex(2)
print('Switched to Companion page')

# Check companion page
print(f'Companion page web_view: {window.companion_page.web_view}')
print(f'Window fullscreen after switch: {window.isFullScreen()}')
print(f'Window size after switch: {window.size()}')

sys.exit(app.exec())
"
