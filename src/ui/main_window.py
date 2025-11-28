"""
Main Application Window

The main window with page navigation, camera preview, and controls.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizePolicy,
    QButtonGroup, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont

from ..config.settings import Settings
from ..camera.stream import CameraStream, StreamConfig
from ..atem.tally import ATEMTallyController, TallyState
from .preview_widget import PreviewWidget
from .settings_page import SettingsPage
from .companion_page import CompanionPage
from .styles import STYLESHEET, COLORS


class MainWindow(QMainWindow):
    """
    Main application window for PanaPiTouch.
    
    Layout:
    - Top: Page navigation buttons
    - Center: Page content (Preview, Companion, Settings)
    - Bottom: Camera selection buttons (on preview page)
    """
    
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = Settings.load()
        
        # Camera streams
        self.camera_streams: dict = {}
        self.current_camera_id = None
        
        # Demo mode state
        self._demo_running = False
        self._demo_thread = None
        
        # ATEM controller
        self.atem_controller = ATEMTallyController()
        
        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        
        # Initialize ATEM connection if configured
        if self.settings.atem.enabled and self.settings.atem.ip_address:
            self.atem_controller.connect(self.settings.atem.ip_address)
        
        # Select first camera if available
        if self.settings.cameras:
            self._select_camera(self.settings.cameras[0].id)
    
    def _setup_window(self):
        """Setup window properties"""
        self.setWindowTitle("PanaPiTouch - PTZ Camera Monitor")
        
        # Set window size based on display
        self.setMinimumSize(1280, 720)
        
        # Set stylesheet
        self.setStyleSheet(STYLESHEET)
        
        # Fullscreen if configured
        if self.settings.fullscreen:
            self.showFullScreen()
        else:
            self.resize(self.settings.display_width, self.settings.display_height)
    
    def _setup_ui(self):
        """Setup the main UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top navigation bar
        nav_bar = self._create_nav_bar()
        main_layout.addWidget(nav_bar)
        
        # Page stack
        self.page_stack = QStackedWidget()
        
        # Create pages
        self.preview_page = self._create_preview_page()
        self.companion_page = CompanionPage(self.settings.companion_url)
        self.settings_page = SettingsPage(self.settings)
        
        self.page_stack.addWidget(self.preview_page)
        self.page_stack.addWidget(self.companion_page)
        self.page_stack.addWidget(self.settings_page)
        
        main_layout.addWidget(self.page_stack, stretch=1)
    
    def _create_nav_bar(self) -> QWidget:
        """Create the top navigation bar"""
        nav_bar = QFrame()
        nav_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        nav_bar.setFixedHeight(70)
        
        layout = QHBoxLayout(nav_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)
        
        # App title/logo
        title = QLabel("PanaPiTouch")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {COLORS['primary']};
            padding-right: 30px;
        """)
        layout.addWidget(title)
        
        # Navigation buttons
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        
        nav_buttons = [
            ("📺  Preview", 0),
            ("🎛️  Companion", 1),
            ("⚙️  Settings", 2),
        ]
        
        for text, page_idx in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setFixedHeight(70)
            btn.setMinimumWidth(150)
            
            self.nav_button_group.addButton(btn, page_idx)
            layout.addWidget(btn)
            
            if page_idx == 0:
                btn.setChecked(True)
        
        self.nav_button_group.idClicked.connect(self._on_nav_clicked)
        
        layout.addStretch()
        
        # Status indicators - two rows, 10px font, no background
        status_container = QWidget()
        status_container.setStyleSheet("background: transparent; border: none;")
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)
        
        self.connection_status = QLabel("CAM: ● Disconnected")
        self.connection_status.setTextFormat(Qt.TextFormat.RichText)
        self.connection_status.setStyleSheet(f"""
            color: {COLORS['text_dim']}; 
            font-size: 10px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        self.connection_status.setToolTip("Camera disconnected")
        status_layout.addWidget(self.connection_status)
        
        self.atem_status = QLabel("ATEM: ● Not Configured")
        self.atem_status.setTextFormat(Qt.TextFormat.RichText)
        self.atem_status.setStyleSheet(f"""
            color: {COLORS['text_dim']}; 
            font-size: 10px;
            font-weight: 600;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        self.atem_status.setToolTip("ATEM not configured")
        status_layout.addWidget(self.atem_status)
        
        layout.addWidget(status_container)
        
        # Spacer before system buttons
        layout.addSpacing(20)
        
        # Reboot button
        reboot_btn = QPushButton("Reboot")
        reboot_btn.setFixedHeight(50)
        reboot_btn.setMinimumWidth(90)
        reboot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['warning']};
                border-radius: 8px;
                color: {COLORS['warning']};
                font-size: 14px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning']};
                color: {COLORS['background']};
            }}
        """)
        reboot_btn.clicked.connect(self._reboot_system)
        layout.addWidget(reboot_btn)
        
        # Shutdown button
        shutdown_btn = QPushButton("Shutdown")
        shutdown_btn.setFixedHeight(50)
        shutdown_btn.setMinimumWidth(100)
        shutdown_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['error']};
                border-radius: 8px;
                color: {COLORS['error']};
                font-size: 14px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['error']};
                color: white;
            }}
        """)
        shutdown_btn.clicked.connect(self._shutdown_system)
        layout.addWidget(shutdown_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(50)
        close_btn.setMinimumWidth(80)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['text_dim']};
                border-radius: 8px;
                color: {COLORS['text_dim']};
                font-size: 14px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['text_dim']};
                color: {COLORS['background']};
            }}
        """)
        close_btn.clicked.connect(self._confirm_close)
        layout.addWidget(close_btn)
        
        return nav_bar
    
    def _create_preview_page(self) -> QWidget:
        """Create the preview page with camera view and controls"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Top row with overlay buttons
        overlay_bar = self._create_overlay_bar()
        layout.addWidget(overlay_bar)
        
        # Preview widget
        self.preview_widget = PreviewWidget()
        layout.addWidget(self.preview_widget, stretch=1)
        
        # Bottom camera buttons
        camera_bar = self._create_camera_bar()
        layout.addWidget(camera_bar)
        
        return page
    
    def _create_overlay_bar(self) -> QWidget:
        """Create overlay toggle buttons - centered"""
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        bar.setFixedHeight(60)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        
        # Add stretch to center buttons
        layout.addStretch()
        
        # Overlay toggle buttons (no label, centered)
        self.overlay_buttons = {}
        
        overlays = [
            ("False Color", "false_color"),
            ("Waveform", "waveform"),
            ("Vectorscope", "vectorscope"),
            ("Focus Assist", "focus_assist"),
        ]
        
        for name, key in overlays:
            btn = QPushButton(name)
            btn.setObjectName("overlayButton")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda checked, k=key: self._toggle_overlay(k))
            
            self.overlay_buttons[key] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # FPS display
        self.fps_label = QLabel("-- fps")
        self.fps_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        layout.addWidget(self.fps_label)
        
        return bar
    
    def _create_camera_bar(self) -> QWidget:
        """Create camera selection buttons - fits 11 buttons (1 demo + 10 cameras)"""
        # Main container - transparent background
        self.camera_bar = QWidget()
        self.camera_bar.setFixedHeight(100)  # 80px buttons + 20px padding
        
        # Single layout for all buttons (demo + cameras), centered
        self.camera_buttons_layout = QHBoxLayout(self.camera_bar)
        self.camera_buttons_layout.setContentsMargins(12, 10, 12, 10)
        self.camera_buttons_layout.setSpacing(8)
        
        # Add stretch to center all buttons
        self.camera_buttons_layout.addStretch()
        
        # Demo button - "D" label, 80x80 square
        self.demo_btn = QPushButton("D")
        self.demo_btn.setObjectName("demoButton")
        self.demo_btn.setCheckable(True)
        self.demo_btn.setFixedSize(80, 80)
        self.demo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['secondary']};
                border: 3px solid {COLORS['secondary']};
                border-radius: 12px;
                color: white;
                font-weight: bold;
                font-size: 24px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        self.demo_btn.setToolTip("Demo Video")
        self.demo_btn.clicked.connect(self._toggle_demo_mode)
        self.camera_buttons_layout.addWidget(self.demo_btn)
        
        # Camera buttons group
        self.camera_button_group = QButtonGroup(self)
        self.camera_button_group.setExclusive(True)
        self.camera_buttons: dict = {}
        
        self.camera_button_group.idClicked.connect(self._on_camera_button_clicked)
        
        # Create buttons for configured cameras (added after demo button)
        self._rebuild_camera_buttons()
        
        # Add stretch at end to center all buttons
        self.camera_buttons_layout.addStretch()
        
        return self.camera_bar
    
    def _rebuild_camera_buttons(self):
        """Rebuild camera buttons - only show configured cameras"""
        # Clear existing camera buttons only (not demo button or stretches)
        for btn in self.camera_buttons.values():
            self.camera_button_group.removeButton(btn)
            self.camera_buttons_layout.removeWidget(btn)
            btn.deleteLater()
        self.camera_buttons.clear()
        
        # Find position to insert (after demo button, index 1 since stretch is at 0)
        # Layout is: [stretch] [demo] [cam1] [cam2] ... [stretch]
        insert_pos = 2  # After first stretch and demo button
        
        # Create button for each configured camera (80x80 square)
        for i, camera in enumerate(self.settings.cameras):
            # Use camera name from settings (truncated to fit)
            label = camera.name[:6] if len(camera.name) > 6 else camera.name
            btn = QPushButton(label)
            btn.setObjectName("cameraButton")
            btn.setCheckable(True)
            btn.setProperty("tallyState", "off")
            btn.setFixedSize(80, 80)  # 80x80 square buttons
            btn.setToolTip(f"{camera.name}\n{camera.ip_address}")
            
            self.camera_button_group.addButton(btn, i)
            self.camera_buttons[i] = btn
            self.camera_buttons_layout.insertWidget(insert_pos + i, btn)
    
    def _toggle_demo_mode(self):
        """Toggle demo video mode"""
        if self.demo_btn.isChecked():
            # Stop current camera stream
            if self.current_camera_id is not None:
                if self.current_camera_id in self.camera_streams:
                    self.camera_streams[self.current_camera_id].stop()
            
            # Uncheck all camera buttons
            checked_btn = self.camera_button_group.checkedButton()
            if checked_btn:
                self.camera_button_group.setExclusive(False)
                checked_btn.setChecked(False)
                self.camera_button_group.setExclusive(True)
            
            self.current_camera_id = None
            
            # Start demo mode
            self._start_demo_video()
        else:
            # Stop demo mode
            self._stop_demo_video()
    
    def _start_demo_video(self):
        """Start playing demo video with test pattern"""
        import threading
        
        self._demo_running = True
        self._demo_thread = threading.Thread(target=self._demo_video_loop, daemon=True)
        self._demo_thread.start()
    
    def _stop_demo_video(self):
        """Stop demo video"""
        self._demo_running = False
        if hasattr(self, '_demo_thread') and self._demo_thread:
            self._demo_thread.join(timeout=1)
        self.preview_widget.clear_frame()
    
    def _demo_video_loop(self):
        """Generate demo video frames with test pattern"""
        import cv2
        import numpy as np
        import time
        import math
        
        width, height = 1920, 1080
        frame_count = 0
        start_time = time.time()
        
        while self._demo_running:
            # Create test pattern frame
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Color bars (top 2/3)
            bar_height = int(height * 0.67)
            bar_width = width // 8
            colors = [
                (192, 192, 192),  # White/Gray
                (0, 192, 192),    # Yellow
                (192, 192, 0),    # Cyan
                (0, 192, 0),      # Green
                (192, 0, 192),    # Magenta
                (0, 0, 192),      # Red
                (192, 0, 0),      # Blue
                (16, 16, 16),     # Black
            ]
            for i, color in enumerate(colors):
                x1 = i * bar_width
                x2 = (i + 1) * bar_width
                frame[0:bar_height, x1:x2] = color
            
            # Moving gradient bar (bottom 1/3)
            t = time.time() - start_time
            offset = int((t * 100) % width)
            for x in range(width):
                intensity = int(128 + 127 * math.sin((x + offset) * 0.02))
                frame[bar_height:, x] = (intensity, intensity, intensity)
            
            # Add timestamp and info text
            timestamp = time.strftime("%H:%M:%S")
            fps_text = f"DEMO MODE | {timestamp} | Frame: {frame_count}"
            
            # Text background
            cv2.rectangle(frame, (50, height - 80), (600, height - 30), (0, 0, 0), -1)
            
            # Text
            cv2.putText(frame, fps_text, (60, height - 45), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            
            # PanaPiTouch logo text
            cv2.putText(frame, "PanaPiTouch", (width // 2 - 200, height // 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 4)
            cv2.putText(frame, "Demo Video", (width // 2 - 150, height // 2 + 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 2)
            
            # Send frame to preview
            self.preview_widget.update_frame(frame)
            
            frame_count += 1
            
            # Target 30fps
            time.sleep(0.033)
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Settings changed
        self.settings_page.settings_changed.connect(self._on_settings_changed)
        
        # ATEM tally callback
        self.atem_controller.add_tally_callback(self._on_tally_changed)
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)
        
        # FPS update timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.fps_timer.start(500)
    
    @pyqtSlot(int)
    def _on_nav_clicked(self, page_idx: int):
        """Handle navigation button click"""
        self.page_stack.setCurrentIndex(page_idx)
    
    @pyqtSlot(int)
    def _on_camera_button_clicked(self, button_id: int):
        """Handle camera button click"""
        # Stop demo mode if running
        if self._demo_running:
            self._stop_demo_video()
            self.demo_btn.setChecked(False)
        
        # Find camera by button index
        if button_id < len(self.settings.cameras):
            camera = self.settings.cameras[button_id]
            self._select_camera(camera.id)
    
    def _toggle_overlay(self, overlay_key: str):
        """Toggle an overlay"""
        if overlay_key == "false_color":
            enabled = self.preview_widget.toggle_false_color()
        elif overlay_key == "waveform":
            enabled = self.preview_widget.toggle_waveform()
        elif overlay_key == "vectorscope":
            enabled = self.preview_widget.toggle_vectorscope()
        elif overlay_key == "focus_assist":
            enabled = self.preview_widget.toggle_focus_assist()
        else:
            return
        
        self.overlay_buttons[overlay_key].setChecked(enabled)
    
    def _select_camera(self, camera_id: int):
        """Select a camera to preview"""
        # Stop current stream
        if self.current_camera_id is not None:
            if self.current_camera_id in self.camera_streams:
                self.camera_streams[self.current_camera_id].stop()
        
        self.current_camera_id = camera_id
        camera = self.settings.get_camera(camera_id)
        
        if not camera:
            self.preview_widget.clear_frame()
            return
        
        # Create or reuse stream
        if camera_id not in self.camera_streams:
            config = StreamConfig(
                ip_address=camera.ip_address,
                port=camera.port,
                username=camera.username,
                password=camera.password,
                resolution=(1920, 1080)
            )
            stream = CameraStream(config)
            stream.add_frame_callback(self._on_frame_received)
            self.camera_streams[camera_id] = stream
        
        # Start stream
        self.camera_streams[camera_id].start()
        
        # Update UI
        self._update_camera_selection_ui(camera_id)
        
        # Update tally state for preview
        self._update_preview_tally()
    
    def _on_frame_received(self, frame):
        """Handle received frame from camera"""
        self.preview_widget.update_frame(frame)
    
    def _update_camera_buttons(self):
        """Update camera buttons - rebuild to match settings"""
        self._rebuild_camera_buttons()
    
    def _update_camera_selection_ui(self, camera_id: int):
        """Update UI to reflect selected camera"""
        for i, camera in enumerate(self.settings.cameras):
            if camera.id == camera_id:
                self.camera_buttons[i].setChecked(True)
                break
    
    def _update_preview_tally(self):
        """Update preview tally based on ATEM state"""
        if self.current_camera_id is None:
            self.preview_widget.set_tally_state(TallyState.OFF)
            return
        
        # Get ATEM input for current camera
        atem_input = self.settings.atem.input_mapping.get(str(self.current_camera_id))
        if atem_input:
            state = self.atem_controller.get_tally_state(atem_input)
            self.preview_widget.set_tally_state(state)
        else:
            self.preview_widget.set_tally_state(TallyState.OFF)
    
    def _on_tally_changed(self, input_id: int, state: TallyState):
        """Handle ATEM tally change"""
        # Update camera buttons
        for i, camera in enumerate(self.settings.cameras):
            atem_input = self.settings.atem.input_mapping.get(str(camera.id))
            if atem_input == input_id:
                btn = self.camera_buttons[i]
                
                if state == TallyState.PROGRAM:
                    btn.setProperty("tallyState", "program")
                elif state == TallyState.PREVIEW:
                    btn.setProperty("tallyState", "preview")
                else:
                    btn.setProperty("tallyState", "off")
                
                # Force style update
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        
        # Update preview tally
        self._update_preview_tally()
    
    def _on_settings_changed(self):
        """Handle settings change"""
        # Reload settings
        self.settings = Settings.load()
        
        # Update camera buttons
        self._update_camera_buttons()
        
        # Reconnect ATEM if needed
        if self.settings.atem.enabled and self.settings.atem.ip_address:
            self.atem_controller.disconnect()
            self.atem_controller.connect(self.settings.atem.ip_address)
        else:
            self.atem_controller.disconnect()
        
        # Update companion URL
        self.companion_page.set_url(self.settings.companion_url)
    
    def _update_status(self):
        """Update status indicators"""
        # Camera connection status - 10px font, no background
        if self.current_camera_id is not None and self.current_camera_id in self.camera_streams:
            stream = self.camera_streams[self.current_camera_id]
            if stream.is_connected:
                self.connection_status.setText(f"CAM: <span style='color:{COLORS['success']}'>●</span> Connected")
                self.connection_status.setStyleSheet(f"""
                    color: {COLORS['text']}; 
                    font-size: 10px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                """)
                self.connection_status.setToolTip("Camera connected")
            else:
                self.connection_status.setText(f"CAM: <span style='color:{COLORS['error']}'>●</span> Disconnected")
                self.connection_status.setStyleSheet(f"""
                    color: {COLORS['text']}; 
                    font-size: 10px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                """)
                self.connection_status.setToolTip(f"Camera disconnected: {stream.error_message}")
        else:
            self.connection_status.setText(f"CAM: <span style='color:{COLORS['text_dark']}'>●</span> No Camera")
            self.connection_status.setStyleSheet(f"""
                color: {COLORS['text_dim']}; 
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            """)
            self.connection_status.setToolTip("No camera selected")
        
        # ATEM connection status - 10px font, no background
        if self.atem_controller.is_connected:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['success']}'>●</span> Connected")
            self.atem_status.setStyleSheet(f"""
                color: {COLORS['text']}; 
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            """)
            self.atem_status.setToolTip("ATEM connected")
        elif self.settings.atem.enabled:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['error']}'>●</span> Disconnected")
            self.atem_status.setStyleSheet(f"""
                color: {COLORS['text']}; 
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            """)
            self.atem_status.setToolTip("ATEM disconnected")
        else:
            self.atem_status.setText(f"ATEM: <span style='color:{COLORS['text_dark']}'>●</span> Not Configured")
            self.atem_status.setStyleSheet(f"""
                color: {COLORS['text_dim']}; 
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            """)
            self.atem_status.setToolTip("ATEM not configured")
    
    def _update_fps(self):
        """Update FPS display"""
        if self.current_camera_id is not None and self.current_camera_id in self.camera_streams:
            stream = self.camera_streams[self.current_camera_id]
            self.fps_label.setText(f"{stream.fps:.1f} fps")
        else:
            self.fps_label.setText("-- fps")
    
    def _confirm_close(self):
        """Show confirmation dialog before closing"""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Close PanaPiTouch",
            "Are you sure you want to close the application?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
    
    def _reboot_system(self):
        """Show confirmation dialog and reboot the system"""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        
        reply = QMessageBox.question(
            self,
            "Reboot System",
            "Are you sure you want to reboot the Raspberry Pi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.save()
            self.close()
            try:
                subprocess.run(['sudo', 'reboot'], check=True)
            except Exception as e:
                print(f"Reboot failed: {e}")
    
    def _shutdown_system(self):
        """Show confirmation dialog and shutdown the system"""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        
        reply = QMessageBox.question(
            self,
            "Shutdown System",
            "Are you sure you want to shutdown the Raspberry Pi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.save()
            self.close()
            try:
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
            except Exception as e:
                print(f"Shutdown failed: {e}")
    
    def closeEvent(self, event):
        """Handle window close"""
        # Stop demo mode if running
        if self._demo_running:
            self._stop_demo_video()
        
        # Stop all camera streams
        for stream in self.camera_streams.values():
            stream.stop()
        
        # Disconnect ATEM
        self.atem_controller.disconnect()
        
        # Save settings
        self.settings.save()
        
        event.accept()
    
    def keyPressEvent(self, event):
        """Handle key presses"""
        # F11 - Toggle fullscreen
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        
        # Escape - Exit fullscreen or close
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        
        # Number keys 1-9, 0 - Select camera
        elif Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_9:
            idx = event.key() - Qt.Key.Key_1
            if idx < len(self.settings.cameras):
                self._select_camera(self.settings.cameras[idx].id)
        elif event.key() == Qt.Key.Key_0:
            if len(self.settings.cameras) >= 10:
                self._select_camera(self.settings.cameras[9].id)
        
        # F1-F4 - Toggle overlays
        elif event.key() == Qt.Key.Key_F1:
            self._toggle_overlay("false_color")
        elif event.key() == Qt.Key.Key_F2:
            self._toggle_overlay("waveform")
        elif event.key() == Qt.Key.Key_F3:
            self._toggle_overlay("vectorscope")
        elif event.key() == Qt.Key.Key_F4:
            self._toggle_overlay("focus_assist")
        
        else:
            super().keyPressEvent(event)

