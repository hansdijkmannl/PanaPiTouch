"""
Settings Page

Configuration for ATEM, network, display, and system settings.
Sidebar navigation with content panels.
"""
import re
import subprocess
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGroupBox, QFrame, QMessageBox, QComboBox,
    QGridLayout, QInputDialog, QStackedWidget, QSlider,
    QSizePolicy, QRadioButton, QButtonGroup, QProgressBar, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QEvent, QProcess, QUrl

from ..config.settings import Settings
from .widgets import TouchScrollArea


class StyledComboBox(QComboBox):
    """ComboBox with properly styled dropdown"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def showPopup(self):
        """Override to style dropdown when shown"""
        super().showPopup()
        QTimer.singleShot(10, self._style_dropdown)
    
    def _style_dropdown(self):
        """Style the dropdown view"""
        view = self.view()
        if view:
            # Ensure the popup container + viewport also use dark background
            view.setAutoFillBackground(True)
            popup = view.window()
            if popup:
                popup.setStyleSheet("""
                    QWidget, QFrame {
                        background-color: #242430 !important;
                        border: 2px solid #2a2a38;
                    }
                """)
            view.setStyleSheet("""
                QAbstractItemView {
                    background-color: #242430 !important;
                    border: 2px solid #2a2a38;
                    selection-background-color: #FF9500;
                    color: #FFFFFF !important;
                    padding: 0px;
                    font-size: 16px;
                    outline: none;
                }
                QAbstractScrollArea, QAbstractScrollArea::viewport {
                    background-color: #242430 !important;
                }
                QWidget {
                    background-color: #242430 !important;
                }
                QAbstractItemView::item {
                    background-color: #242430 !important;
                    min-height: 56px !important;
                    padding: 16px 20px;
                    border-radius: 4px;
                    color: #FFFFFF !important;
                }
                QAbstractItemView::item:hover {
                    background-color: #2a2a38 !important;
                }
                QAbstractItemView::item:selected {
                    background-color: #FF9500 !important;
                    color: #121218 !important;
                }
            """)


class SettingsPage(QWidget):
    """
    Settings page with sidebar navigation.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._current_section = 0
        self.osk_preset_inputs = []  # Initialize list
        self._companion_update_version = None
        self._setup_ui()
        self._load_settings()
        self._start_system_monitor()
        self._start_companion_monitor()
    
    def _setup_ui(self):
        """Setup the settings page UI with sidebar"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === LEFT SIDEBAR ===
        sidebar = QFrame()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #121218;
                border-right: 1px solid #2a2a38;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(8)
        
        # Sidebar buttons
        self.sidebar_buttons = []
        sections = [
            ("🌐", "Network"),
            ("🎬", "ATEM"),
            ("📷", "Camera Control"),
            ("💾", "Backup"),
            ("🎛️", "Companion"),
            ("⌨️", "Keyboard presets"),
            ("📊", "System"),
        ]
        
        for i, (icon, name) in enumerate(sections):
            btn = QPushButton(f"{icon}\n{name}")
            btn.setCheckable(True)
            btn.setMinimumHeight(80)
            btn.setStyleSheet(self._get_sidebar_button_style())
            btn.clicked.connect(lambda checked, idx=i: self._on_section_clicked(idx))
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)
        
        # === RIGHT CONTENT AREA ===
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #121218;")
        
        # Create content panels
        self.content_stack.addWidget(self._create_network_panel())
        self.content_stack.addWidget(self._create_atem_panel())
        self.content_stack.addWidget(self._create_camera_control_panel())
        self.content_stack.addWidget(self._create_backup_panel())
        self.content_stack.addWidget(self._create_companion_panel())
        self.content_stack.addWidget(self._create_keyboard_presets_panel())
        self.content_stack.addWidget(self._create_system_panel())
        
        main_layout.addWidget(self.content_stack, 1)
        
        # Select first section by default
        self._on_section_clicked(0)
    
    def _get_sidebar_button_style(self):
        """Get sidebar button styling"""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 12px;
                color: #888898;
                font-size: 13px;
                font-weight: 500;
                padding: 12px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #242430;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #FF9500;
                color: #121218;
                font-weight: 600;
            }
            QPushButton:pressed {
                background-color: #CC7700;
            }
        """
    
    def _on_section_clicked(self, index):
        """Handle sidebar section click"""
        self._current_section = index
        self.content_stack.setCurrentIndex(index)
        
        # If keyboard presets panel is shown, ensure settings are loaded
        if index == 4:  # Keyboard presets is index 4 (after Companion)
            self._load_osk_presets()
        if index == 3:  # Companion panel
            self._refresh_companion_status_ui()
        
        # Update button states
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == index)

    # === Companion monitor (Option C) ===

    def _start_companion_monitor(self):
        """Background check for Companion update availability (Option C)."""
        self._companion_timer = QTimer(self)
        self._companion_timer.timeout.connect(self._check_companion_update_background)
        self._companion_timer.start(10000)  # every 10s
        QTimer.singleShot(500, self._check_companion_update_background)

    def _check_companion_update_background(self):
        """Check Companion update status in the background (Option C)."""
        main_window = self.parent()
        companion_page = getattr(main_window, "companion_page", None) if main_window else None

        version = None
        try:
            if companion_page is not None and hasattr(companion_page, "get_update_version"):
                version = companion_page.get_update_version()
        except Exception:
            version = None

        # IMPORTANT: Don't overwrite a known update version with None.
        # CompanionPage may temporarily report None while the page is reloading,
        # which would make the Settings button "disappear" again.
        if version:
            if version != self._companion_update_version:
                self._companion_update_version = version
        # Refresh UI if panel is visible
        if self._current_section == 3:
            self._refresh_companion_status_ui()

    def _refresh_companion_status_ui(self):
        """Update Companion panel widgets based on latest background state."""
        if not hasattr(self, "companion_status_label"):
            return

        if self._companion_update_version:
            self.companion_status_label.setText(f"● Update available: v{self._companion_update_version}")
            self.companion_status_label.setStyleSheet(self._get_status_style("info"))
            self.companion_update_btn.setEnabled(True)
            self.companion_update_btn.setText(f"Update Companion to v{self._companion_update_version}")
        else:
            self.companion_status_label.setText("● No update detected")
            self.companion_status_label.setStyleSheet(self._get_status_style("success"))
            self.companion_update_btn.setEnabled(False)
            self.companion_update_btn.setText("Update Companion")

    def _run_companion_update(self):
        """Run Companion update via terminal command: sudo companion-update stable"""
        # Prevent double-runs
        if hasattr(self, "_companion_update_process") and self._companion_update_process:
            try:
                if self._companion_update_process.state() != QProcess.ProcessState.NotRunning:
                    QMessageBox.information(self, "Update in Progress", "Companion update is already running.")
                    return
            except Exception:
                pass

        # Confirm update
        if self._companion_update_version:
            prompt = (
                f"Update Companion to v{self._companion_update_version}?\n\n"
                "This will run:\n"
                "  sudo companion-update stable\n\n"
                "And restart Companion."
            )
        else:
            prompt = (
                "Run Companion update?\n\n"
                "This will run:\n"
                "  sudo companion-update stable\n\n"
                "And restart Companion."
            )
        reply = QMessageBox.question(
            self,
            "Update Companion",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Run: sudo companion-update stable (non-interactive)
        self._companion_update_process = QProcess(self)
        self._companion_update_log = ""

        def on_stdout():
            try:
                data = self._companion_update_process.readAllStandardOutput().data().decode(errors="ignore")
                self._companion_update_log += data
            except Exception:
                pass

        def on_stderr():
            try:
                data = self._companion_update_process.readAllStandardError().data().decode(errors="ignore")
                self._companion_update_log += data
            except Exception:
                pass

        def on_finished(exit_code, exit_status):
            # Re-check after completion
            self._companion_update_version = None
            self._refresh_companion_status_ui()
            QTimer.singleShot(4000, self._check_companion_update_background)

            # Hide progress UI
            try:
                if hasattr(self, "companion_update_progress"):
                    self.companion_update_progress.hide()
            except Exception:
                pass

            # Re-enable update button (state will be corrected by refresh)
            try:
                self.companion_update_btn.setEnabled(True)
            except Exception:
                pass

            # Refresh Companion page after update (delayed + retry), because the service restarts.
            if exit_code == 0:
                try:
                    self._schedule_companion_webview_reload()
                except Exception:
                    pass

            if exit_code == 0:
                QMessageBox.information(self, "Update Complete", "Companion update completed successfully.")
            else:
                tail = (self._companion_update_log or "").strip()
                if len(tail) > 2000:
                    tail = tail[-2000:]
                QMessageBox.warning(self, "Update Failed", f"Companion update failed (exit {exit_code}).\n\n{tail}")

        self._companion_update_process.readyReadStandardOutput.connect(on_stdout)
        self._companion_update_process.readyReadStandardError.connect(on_stderr)
        self._companion_update_process.finished.connect(on_finished)

        # Update UI while running
        self.companion_status_label.setText("● Updating Companion…")
        self.companion_status_label.setStyleSheet(self._get_status_style("info"))
        self.companion_update_btn.setEnabled(False)
        self.companion_update_btn.setText("Updating…")
        # Indeterminate progress bar while command runs
        if hasattr(self, "companion_update_progress"):
            self.companion_update_progress.setRange(0, 0)  # busy indicator
            self.companion_update_progress.show()

        self._companion_update_process.start("sudo", ["companion-update", "stable"])

    def _schedule_companion_webview_reload(self):
        """Reload Companion web view after update with retries (service restart delay)."""
        main_window = self.window()
        companion_page = getattr(main_window, "companion_page", None)
        web = getattr(companion_page, "web_view", None) if companion_page else None
        if web is None:
            return

        # Reset attempt counter
        self._companion_reload_attempt = 0

        def attempt_reload():
            self._companion_reload_attempt += 1
            attempt = self._companion_reload_attempt

            def on_load_finished(success: bool):
                try:
                    web.loadFinished.disconnect(on_load_finished)
                except Exception:
                    pass
                if success:
                    return
                # Retry a few times with backoff
                if attempt < 5:
                    QTimer.singleShot(1500 * attempt, attempt_reload)

            # Attach one-shot handler for this attempt
            web.loadFinished.connect(on_load_finished)

            # Ensure URL is correct, then reload
            try:
                url = getattr(companion_page, "companion_url", None) or getattr(self.settings, "companion_url", "http://localhost:8000")
                web.setUrl(QUrl(url))
            except Exception:
                try:
                    web.reload()
                except Exception:
                    pass

        # Give Companion time to restart before first reload
        QTimer.singleShot(6000, attempt_reload)

    def _create_companion_panel(self) -> QWidget:
        """Create Companion settings panel (Option B + Option C)."""
        wrapper, layout = self._create_content_wrapper("Companion", "🎛️")

        info_frame = self._create_info_card(
            "Manage Bitfocus Companion.\n"
            "Shows update availability and can run the update."
        )
        layout.addWidget(info_frame)

        self.companion_status_label = QLabel("● Checking for updates…")
        self.companion_status_label.setStyleSheet(self._get_status_style("info"))
        layout.addWidget(self.companion_status_label)

        # Progress bar (shown only while update runs)
        self.companion_update_progress = QProgressBar()
        self.companion_update_progress.setTextVisible(False)
        self.companion_update_progress.setFixedHeight(16)
        self.companion_update_progress.setStyleSheet("""
            QProgressBar {
                background-color: #242430;
                border: 1px solid #2a2a38;
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background-color: #FF9500;
                border-radius: 8px;
            }
        """)
        self.companion_update_progress.hide()
        layout.addWidget(self.companion_update_progress)

        self.companion_update_btn = QPushButton("Update Companion")
        self.companion_update_btn.setStyleSheet(self._get_button_style(True))
        self.companion_update_btn.clicked.connect(self._run_companion_update)
        self.companion_update_btn.setEnabled(False)
        layout.addWidget(self.companion_update_btn)

        layout.addStretch()

        # Initialize UI state
        QTimer.singleShot(0, self._refresh_companion_status_ui)
        return wrapper
    
    def _get_input_style(self):
        """Get consistent input field styling"""
        return """
            QLineEdit, QComboBox {
                background-color: #242430;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                padding: 12px 14px;
                font-size: 15px;
                color: #FFFFFF;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #FF9500;
            }
            QLineEdit::placeholder {
                color: #666676;
            }
            QComboBox::drop-down {
                border: none;
                width: 40px;
            }
            QComboBox QAbstractItemView {
                background-color: #242430 !important;
                border: 2px solid #2a2a38;
                selection-background-color: #FF9500;
                color: #FFFFFF !important;
                padding: 4px;
                font-size: 16px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                background-color: #242430 !important;
                min-height: 56px !important;
                padding: 16px 20px;
                border-radius: 4px;
                color: #FFFFFF !important;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2a2a38 !important;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #FF9500 !important;
                color: #121218 !important;
            }
        """
    
    def _get_button_style(self, primary=False):
        """Get consistent button styling"""
        if primary:
            return """
                QPushButton {
                    background-color: #FF9500;
                    border: none;
                    border-radius: 8px;
                    color: #121218;
                    font-size: 15px;
                    font-weight: 600;
                    padding: 14px 24px;
                    min-height: 48px;
                }
                QPushButton:hover {
                    background-color: #FFAA33;
                }
                QPushButton:pressed {
                    background-color: #CC7700;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #2a2a38;
                    border: 2px solid #3a3a48;
                    border-radius: 8px;
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: 500;
                    padding: 14px 24px;
                    min-height: 48px;
                }
                QPushButton:hover {
                    border-color: #FF9500;
                    background-color: #3a3a48;
                }
                QPushButton:pressed {
                    background-color: #FF9500;
                    border-color: #FF9500;
                    color: #121218;
                }
            """
    
    def _get_slider_style(self):
        """Get slider styling"""
        return """
            QSlider::groove:horizontal {
                border: none;
                height: 8px;
                background: #2a2a38;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #FF9500;
                border: none;
                width: 28px;
                height: 28px;
                margin: -10px 0;
                border-radius: 14px;
            }
            QSlider::handle:horizontal:hover {
                background: #FFAA33;
            }
            QSlider::handle:horizontal:pressed {
                background: #CC7700;
            }
            QSlider::sub-page:horizontal {
                background: #FF9500;
                border-radius: 4px;
            }
        """
    
    def _create_content_wrapper(self, title, icon):
        """Create a scrollable content wrapper with header"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border-bottom: 1px solid #2a2a38;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        title_label = QLabel(f"{icon}  {title}")
        title_label.setStyleSheet("font-size: 22px; font-weight: 600; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        wrapper_layout.addWidget(header)
        
        # Scrollable content
        scroll = TouchScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        scroll.setWidget(content)
        wrapper_layout.addWidget(scroll)
        
        return wrapper, content_layout

    def _create_camera_control_panel(self) -> QWidget:
        """Create Camera Control settings panel with Multi-Cam configuration"""
        wrapper, layout = self._create_content_wrapper("Camera Control", "📷")

        # Multi-Camera Presets section
        multi_cam_group = QGroupBox("Multi-Camera Presets")
        multi_cam_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #2a2a38;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
            }
        """)

        multi_layout = QVBoxLayout(multi_cam_group)

        # Instructions
        instructions = QLabel("Configure which cameras to include in the multi-camera preset view. Each camera can have a different grid layout.")
        instructions.setStyleSheet("color: #b0b0b0; font-size: 12px; padding: 8px 0;")
        instructions.setWordWrap(True)
        multi_layout.addWidget(instructions)

        # Camera selection area
        cameras_frame = QFrame()
        cameras_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 6px;
            }
        """)
        cameras_layout = QVBoxLayout(cameras_frame)
        cameras_layout.setContentsMargins(12, 12, 12, 12)
        cameras_layout.setSpacing(8)

        # Store references for later use
        self.multi_camera_checkboxes = {}
        self.multi_camera_layout_combos = {}

        # Add camera selection for each configured camera
        for camera in self.settings.cameras:
            camera_row = QHBoxLayout()
            camera_row.setSpacing(12)

            # Checkbox
            checkbox = QCheckBox(f"📹 {camera.name}")
            checkbox.setChecked(self.settings.multi_camera_presets.get(str(camera.id), {}).get('enabled', False))
            checkbox.stateChanged.connect(lambda state, cam_id=camera.id: self._on_multi_camera_toggle(cam_id, state))
            self.multi_camera_checkboxes[camera.id] = checkbox
            camera_row.addWidget(checkbox)

            # Layout combo
            layout_combo = QComboBox()
            layout_combo.addItems(["4×3 (12 presets)", "1×8 (8 presets)", "4×2 (8 presets)"])
            current_layout = self.settings.multi_camera_presets.get(str(camera.id), {}).get('layout', '4×3 (12 presets)')
            layout_combo.setCurrentText(current_layout)
            layout_combo.setEnabled(checkbox.isChecked())
            layout_combo.currentTextChanged.connect(lambda text, cam_id=camera.id: self._on_multi_camera_layout_change(cam_id, text))
            self.multi_camera_layout_combos[camera.id] = layout_combo
            camera_row.addWidget(layout_combo)

            camera_row.addStretch()
            cameras_layout.addLayout(camera_row)

        multi_layout.addWidget(cameras_frame)

        # Preview and actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        # Preview label
        self.multi_camera_preview_label = QLabel("No cameras selected")
        self.multi_camera_preview_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.multi_camera_preview_label.setWordWrap(True)
        actions_layout.addWidget(self.multi_camera_preview_label)

        actions_layout.addStretch()

        # Action buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: #121218;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_btn.clicked.connect(self._save_multi_camera_config)
        button_layout.addWidget(save_btn)

        reset_btn = QPushButton("🔄 Reset")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        reset_btn.clicked.connect(self._reset_multi_camera_config)
        button_layout.addWidget(reset_btn)

        actions_layout.addLayout(button_layout)
        multi_layout.addLayout(actions_layout)

        layout.addWidget(multi_cam_group)
        layout.addStretch()

        # Update preview initially
        self._update_multi_camera_preview()

        return wrapper

    def _on_multi_camera_toggle(self, camera_id: int, state: int):
        """Handle camera checkbox toggle"""
        enabled = state == 2  # Qt.CheckState.Checked.value
        if camera_id in self.multi_camera_layout_combos:
            self.multi_camera_layout_combos[camera_id].setEnabled(enabled)
        self._update_multi_camera_preview()

    def _on_multi_camera_layout_change(self, camera_id: int, layout_text: str):
        """Handle layout combo change"""
        self._update_multi_camera_preview()

    def _update_multi_camera_preview(self):
        """Update the preview of current multi-camera configuration"""
        selected_cameras = []
        total_presets = 0

        for camera_id, checkbox in self.multi_camera_checkboxes.items():
            if checkbox.isChecked():
                camera = self.settings.get_camera(camera_id)
                if camera:
                    layout_combo = self.multi_camera_layout_combos[camera_id]
                    layout_text = layout_combo.currentText()

                    if "12 presets" in layout_text:
                        preset_count = 12
                    elif "8 presets" in layout_text:
                        preset_count = 8
                    else:
                        preset_count = 8

                    selected_cameras.append(f"{camera.name}: {layout_text}")
                    total_presets += preset_count

        if selected_cameras:
            preview_text = f"Selected ({len(selected_cameras)}):\n" + "\n".join(selected_cameras)
            preview_text += f"\n\nTotal: {total_presets}/48 presets"
            if total_presets > 48:
                preview_text += " ⚠️ Over limit!"
        else:
            preview_text = "No cameras selected"

        self.multi_camera_preview_label.setText(preview_text)

    def _save_multi_camera_config(self):
        """Save the current multi-camera configuration"""
        config = {}

        for camera_id, checkbox in self.multi_camera_checkboxes.items():
            if checkbox.isChecked():
                layout_combo = self.multi_camera_layout_combos[camera_id]
                layout_text = layout_combo.currentText()

                if "12 presets" in layout_text:
                    preset_count = 12
                elif "8 presets" in layout_text:
                    preset_count = 8
                else:
                    preset_count = 8

                config[str(camera_id)] = {
                    'enabled': True,
                    'layout': layout_text,
                    'preset_count': preset_count
                }

        self.settings.multi_camera_presets = config
        self.settings.save()

        # Refresh multi-camera panel in main window
        main_window = self.parent()
        if main_window and hasattr(main_window, '_refresh_multi_camera_presets_panel'):
            main_window._refresh_multi_camera_presets_panel()

        # Show success message
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Configuration Saved")
        msg.setText("Multi-camera configuration has been saved successfully!")
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a22;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3498db;
                color: #121218;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
            }
        """)
        msg.exec()

    def _reset_multi_camera_config(self):
        """Reset multi-camera configuration to default"""
        for checkbox in self.multi_camera_checkboxes.values():
            checkbox.setChecked(False)

        for combo in self.multi_camera_layout_combos.values():
            combo.setCurrentText("4×3 (12 presets)")
            combo.setEnabled(False)

        self.settings.multi_camera_presets = {}
        self.settings.save()
        self._update_multi_camera_preview()

    def _create_atem_panel(self) -> QWidget:
        """Create ATEM configuration panel"""
        wrapper, layout = self._create_content_wrapper("ATEM Switcher", "🎬")
        
        # Info card
        info_frame = self._create_info_card(
            "Connect to a Blackmagic ATEM switcher for tally indication.\n"
            "Red border = Program (Live), Green border = Preview."
        )
        layout.addWidget(info_frame)
        
        # IP Address input
        ip_frame = self._create_input_group("ATEM IP Address", "192.168.1.240")
        self.atem_ip_input = ip_frame.findChild(QLineEdit)
        layout.addWidget(ip_frame)
        
        # Model label (shown after connection)
        self.atem_model_label = QLabel("")
        self.atem_model_label.setStyleSheet("""
            QLabel {
                padding: 14px 20px;
                border-radius: 8px;
                background-color: rgba(0, 180, 216, 0.15);
                color: #FF9500;
                border: 1px solid rgba(0, 180, 216, 0.3);
                font-size: 14px;
            }
        """)
        self.atem_model_label.hide()
        layout.addWidget(self.atem_model_label)
        
        # Status
        self.atem_status_label = QLabel("● Not Connected")
        self.atem_status_label.setStyleSheet(self._get_status_style("error"))
        layout.addWidget(self.atem_status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        test_btn = QPushButton("Test Connection")
        test_btn.setStyleSheet(self._get_button_style(False))
        test_btn.clicked.connect(self._test_atem)
        btn_layout.addWidget(test_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self._get_button_style(True))
        save_btn.clicked.connect(self._save_atem)
        btn_layout.addWidget(save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Tally mapping info
        mapping_frame = QFrame()
        mapping_frame.setStyleSheet("""
            QFrame {
                background-color: #242430;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        mapping_layout = QVBoxLayout(mapping_frame)
        mapping_layout.setContentsMargins(20, 16, 20, 16)
        
        mapping_header = QLabel("💡 Tally Mapping")
        mapping_header.setStyleSheet("font-size: 15px; font-weight: 600; color: #ffffff;")
        mapping_layout.addWidget(mapping_header)
        
        mapping_info = QLabel(
            "Map cameras to ATEM inputs in the Camera page.\n"
            "🔴 RED = Program (Live)  •  🟢 GREEN = Preview"
        )
        mapping_info.setStyleSheet("color: #888898; font-size: 13px;")
        mapping_layout.addWidget(mapping_info)
        
        layout.addWidget(mapping_frame)
        layout.addStretch()
        
        return wrapper
    
    def _create_network_panel(self) -> QWidget:
        """Create network configuration panel"""
        wrapper, layout = self._create_content_wrapper("Network Configuration", "🌐")
        
        # Info card
        info_frame = self._create_info_card("Configure network settings for the Raspberry Pi.")
        layout.addWidget(info_frame)
        
        # Interface selection
        interface_frame = QFrame()
        interface_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        interface_layout = QVBoxLayout(interface_frame)
        interface_layout.setContentsMargins(20, 16, 20, 16)
        interface_layout.setSpacing(10)
        
        interface_label = QLabel("Network Interface")
        interface_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #ffffff;")
        interface_layout.addWidget(interface_label)
        
        # Radio buttons (match Camera Control radio look: orange only when selected)
        self.interface_group = QButtonGroup(interface_frame)
        self.interface_group.setExclusive(True)

        radio_row = QHBoxLayout()
        radio_row.setContentsMargins(0, 0, 0, 0)
        radio_row.setSpacing(24)

        radio_style = """
            QRadioButton {
                color: #ffffff;
                font-size: 14px;
                spacing: 10px;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #2a2a38;
                border-radius: 10px;
                background-color: #121218;
            }
            QRadioButton::indicator:checked {
                background-color: #FF9500;
                border-color: #FF9500;
            }
        """

        self.interface_eth_radio = QRadioButton("Ethernet (eth0)")
        self.interface_eth_radio.setStyleSheet(radio_style)
        self.interface_eth_radio.setChecked(True)
        self.interface_eth_radio.toggled.connect(self._on_interface_changed)
        self.interface_group.addButton(self.interface_eth_radio, 0)
        radio_row.addWidget(self.interface_eth_radio)

        self.interface_wlan_radio = QRadioButton("WiFi (wlan0)")
        self.interface_wlan_radio.setStyleSheet(radio_style)
        self.interface_wlan_radio.toggled.connect(self._on_interface_changed)
        self.interface_group.addButton(self.interface_wlan_radio, 1)
        radio_row.addWidget(self.interface_wlan_radio)

        radio_row.addStretch()
        interface_layout.addLayout(radio_row)
        
        layout.addWidget(interface_frame)
        
        # IP Settings
        ip_frame = self._create_input_group("IP Address", "192.168.1.100")
        self.ip_input = ip_frame.findChild(QLineEdit)
        layout.addWidget(ip_frame)
        
        # Subnet and Gateway row
        row = QHBoxLayout()
        row.setSpacing(16)
        
        subnet_frame = self._create_input_group("Subnet Mask", "255.255.255.0")
        self.subnet_input = subnet_frame.findChild(QLineEdit)
        row.addWidget(subnet_frame)
        
        gateway_frame = self._create_input_group("Gateway", "192.168.1.1")
        self.gateway_input = gateway_frame.findChild(QLineEdit)
        row.addWidget(gateway_frame)
        
        layout.addLayout(row)
        
        # Status
        self.network_status_label = QLabel("● Ready")
        self.network_status_label.setStyleSheet(self._get_status_style("success"))
        layout.addWidget(self.network_status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        load_btn = QPushButton("Load Current")
        load_btn.setStyleSheet(self._get_button_style(False))
        load_btn.clicked.connect(self._load_current_network)
        btn_layout.addWidget(load_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(self._get_button_style(True))
        apply_btn.clicked.connect(self._apply_network_settings)
        btn_layout.addWidget(apply_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        return wrapper
    
    def _create_display_panel(self) -> QWidget:
        """Create display settings panel"""
        wrapper, layout = self._create_content_wrapper("Display Settings", "🖥️")
        
        # Info card
        info_frame = self._create_info_card(
            "Adjust display settings for the Wisecoco AMOLED display.\n"
            "Changes are applied in real-time via xrandr."
        )
        layout.addWidget(info_frame)
        
        # Brightness
        brightness_frame = self._create_slider_group(
            "Brightness", 10, 100, 100, "%",
            "Controls overall display brightness"
        )
        self.brightness_slider = brightness_frame.findChild(QSlider)
        self.brightness_value = brightness_frame.findChild(QLabel, "value_label")
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        layout.addWidget(brightness_frame)
        
        # Gamma/Contrast
        gamma_frame = self._create_slider_group(
            "Gamma (Contrast)", 50, 150, 100, "%",
            "Adjust gamma curve - lower = more contrast"
        )
        self.gamma_slider = gamma_frame.findChild(QSlider)
        self.gamma_value = gamma_frame.findChild(QLabel, "value_label")
        self.gamma_slider.valueChanged.connect(self._on_gamma_changed)
        layout.addWidget(gamma_frame)
        
        # Color Temperature
        temp_frame = self._create_slider_group(
            "Color Temperature", 3000, 9000, 6500, "K",
            "Warm (3000K) to Cool (9000K) - affects RGB balance"
        )
        self.temp_slider = temp_frame.findChild(QSlider)
        self.temp_value = temp_frame.findChild(QLabel, "value_label")
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        layout.addWidget(temp_frame)
        
        # RGB Balance section
        rgb_frame = QFrame()
        rgb_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        rgb_layout = QVBoxLayout(rgb_frame)
        rgb_layout.setContentsMargins(20, 16, 20, 16)
        rgb_layout.setSpacing(16)
        
        rgb_header = QLabel("RGB Balance")
        rgb_header.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        rgb_layout.addWidget(rgb_header)
        
        rgb_info = QLabel("Fine-tune individual color channels")
        rgb_info.setStyleSheet("color: #888898; font-size: 13px;")
        rgb_layout.addWidget(rgb_info)
        
        # Red
        red_row = self._create_rgb_slider("Red", "#ef4444")
        self.red_slider = red_row.findChild(QSlider)
        self.red_value = red_row.findChild(QLabel, "value_label")
        self.red_slider.valueChanged.connect(self._on_rgb_changed)
        rgb_layout.addWidget(red_row)
        
        # Green
        green_row = self._create_rgb_slider("Green", "#22c55e")
        self.green_slider = green_row.findChild(QSlider)
        self.green_value = green_row.findChild(QLabel, "value_label")
        self.green_slider.valueChanged.connect(self._on_rgb_changed)
        rgb_layout.addWidget(green_row)
        
        # Blue
        blue_row = self._create_rgb_slider("Blue", "#3b82f6")
        self.blue_slider = blue_row.findChild(QSlider)
        self.blue_value = blue_row.findChild(QLabel, "value_label")
        self.blue_slider.valueChanged.connect(self._on_rgb_changed)
        rgb_layout.addWidget(blue_row)
        
        layout.addWidget(rgb_frame)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        reset_btn = QPushButton("Reset to Default")
        reset_btn.setStyleSheet(self._get_button_style(False))
        reset_btn.clicked.connect(self._reset_display_settings)
        btn_layout.addWidget(reset_btn)
        
        save_display_btn = QPushButton("Save Settings")
        save_display_btn.setStyleSheet(self._get_button_style(True))
        save_display_btn.clicked.connect(self._save_display_settings)
        btn_layout.addWidget(save_display_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        # Load saved display settings
        self._load_display_settings()
        
        return wrapper
    
    def _create_rgb_slider(self, name, color):
        """Create an RGB channel slider row"""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)
        
        label = QLabel(name)
        label.setFixedWidth(60)
        label.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {color};")
        row_layout.addWidget(label)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(50)
        slider.setMaximum(150)
        slider.setValue(100)
        slider.setStyleSheet(self._get_slider_style().replace("#FF9500", color).replace("#FFAA33", color).replace("#CC7700", color))
        row_layout.addWidget(slider, 1)
        
        value = QLabel("100%")
        value.setObjectName("value_label")
        value.setFixedWidth(60)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value.setStyleSheet("font-size: 14px; color: #ffffff; font-weight: 500;")
        row_layout.addWidget(value)
        
        return row
    
    def _create_slider_group(self, title, min_val, max_val, default, unit, description=""):
        """Create a slider with label and value display"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # Header row
        header_row = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        header_row.addWidget(title_label)
        
        header_row.addStretch()
        
        value_label = QLabel(f"{default}{unit}")
        value_label.setObjectName("value_label")
        value_label.setStyleSheet("font-size: 16px; color: #FF9500; font-weight: 600;")
        header_row.addWidget(value_label)
        
        layout.addLayout(header_row)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #888898; font-size: 13px;")
            layout.addWidget(desc_label)
        
        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setStyleSheet(self._get_slider_style())
        layout.addWidget(slider)
        
        return frame
    
    def _on_brightness_changed(self, value):
        """Handle brightness slider change"""
        self.brightness_value.setText(f"{value}%")
        self._schedule_display_update()
    
    def _on_gamma_changed(self, value):
        """Handle gamma slider change"""
        self.gamma_value.setText(f"{value}%")
        self._schedule_display_update()
    
    def _schedule_display_update(self):
        """Schedule display update with debounce"""
        if not hasattr(self, '_display_timer'):
            self._display_timer = QTimer(self)
            self._display_timer.setSingleShot(True)
            self._display_timer.timeout.connect(self._emit_display_settings)
        self._display_timer.start(100)  # 100ms debounce
    
    def _on_temp_changed(self, value):
        """Handle color temperature change"""
        self.temp_value.setText(f"{value}K")
        # Adjust RGB based on temperature
        r, g, b = self._kelvin_to_rgb(value)
        self.red_slider.blockSignals(True)
        self.green_slider.blockSignals(True)
        self.blue_slider.blockSignals(True)
        self.red_slider.setValue(int(r * 100))
        self.green_slider.setValue(int(g * 100))
        self.blue_slider.setValue(int(b * 100))
        self.red_value.setText(f"{int(r * 100)}%")
        self.green_value.setText(f"{int(g * 100)}%")
        self.blue_value.setText(f"{int(b * 100)}%")
        self.red_slider.blockSignals(False)
        self.green_slider.blockSignals(False)
        self.blue_slider.blockSignals(False)
        self._schedule_display_update()
    
    def _on_rgb_changed(self, value):
        """Handle RGB slider change"""
        sender = self.sender()
        if sender == self.red_slider:
            self.red_value.setText(f"{value}%")
        elif sender == self.green_slider:
            self.green_value.setText(f"{value}%")
        elif sender == self.blue_slider:
            self.blue_value.setText(f"{value}%")
        self._schedule_display_update()
    
    def _kelvin_to_rgb(self, kelvin):
        """Convert color temperature to RGB multipliers"""
        # Attempt algorithm based on Tanner Helland's formula
        temp = kelvin / 100.0
        
        # Red
        if temp <= 66:
            r = 1.0
        else:
            r = temp - 60
            r = 329.698727446 * (r ** -0.1332047592)
            r = max(0, min(255, r)) / 255.0
        
        # Green
        if temp <= 66:
            g = temp
            g = 99.4708025861 * (g ** 0.5) - 161.1195681661
            g = max(0, min(255, g)) / 255.0
        else:
            g = temp - 60
            g = 288.1221695283 * (g ** -0.0755148492)
            g = max(0, min(255, g)) / 255.0
        
        # Blue
        if temp >= 66:
            b = 1.0
        elif temp <= 19:
            b = 0.0
        else:
            b = temp - 10
            b = 138.5177312231 * (b ** 0.5) - 305.0447927307
            b = max(0, min(255, b)) / 255.0
        
        # Normalize to around 1.0
        max_val = max(r, g, b)
        if max_val > 0:
            r /= max_val
            g /= max_val
            b /= max_val
        
        return r, g, b
    
    def _emit_display_settings(self):
        """Emit in-app display adjustment settings"""
        try:
            payload = {
                "brightness": self.brightness_slider.value() / 100.0,
                "gamma": self.gamma_slider.value() / 100.0,
                "temperature": self.temp_slider.value(),
                "red": self.red_slider.value() / 100.0,
                "green": self.green_slider.value() / 100.0,
                "blue": self.blue_slider.value() / 100.0,
            }
            self.display_settings_changed.emit(payload)
        except Exception as e:
            print(f"Display settings emit error: {e}")
    
    def _reset_display_settings(self):
        """Reset display settings to default"""
        self.brightness_slider.setValue(100)
        self.gamma_slider.setValue(100)
        self.temp_slider.setValue(6500)
        self.red_slider.setValue(100)
        self.green_slider.setValue(100)
        self.blue_slider.setValue(100)
        self._emit_display_settings()
    
    def _save_display_settings(self):
        """Save display settings"""
        try:
            display_settings = {
                'brightness': self.brightness_slider.value(),
                'gamma': self.gamma_slider.value(),
                'temperature': self.temp_slider.value(),
                'red': self.red_slider.value(),
                'green': self.green_slider.value(),
                'blue': self.blue_slider.value(),
            }
            
            settings_dir = Path.home() / ".panapitouch"
            settings_dir.mkdir(parents=True, exist_ok=True)
            
            with open(settings_dir / "display_settings.json", 'w') as f:
                json.dump(display_settings, f, indent=2)
            
            QMessageBox.information(self, "Saved", "Display settings saved successfully")
            self._emit_display_settings()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")
    
    def _load_display_settings(self):
        """Load saved display settings"""
        try:
            settings_file = Path.home() / ".panapitouch" / "display_settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                self.brightness_slider.setValue(settings.get('brightness', 100))
                self.gamma_slider.setValue(settings.get('gamma', 100))
                self.temp_slider.setValue(settings.get('temperature', 6500))
                self.red_slider.setValue(settings.get('red', 100))
                self.green_slider.setValue(settings.get('green', 100))
                self.blue_slider.setValue(settings.get('blue', 100))
                
                # Apply loaded settings to preview
                self._emit_display_settings()
        except Exception as e:
            print(f"Failed to load display settings: {e}")
    
    def _create_backup_panel(self) -> QWidget:
        """Create backup and restore panel"""
        wrapper, layout = self._create_content_wrapper("Backup & Restore", "💾")
        
        # Info card
        info_frame = self._create_info_card(
            "Save and restore your camera configurations and settings."
        )
        layout.addWidget(info_frame)
        
        # Create backup section
        create_frame = QFrame()
        create_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        create_layout = QVBoxLayout(create_frame)
        create_layout.setContentsMargins(20, 16, 20, 16)
        create_layout.setSpacing(12)
        
        create_header = QLabel("Create New Backup")
        create_header.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        create_layout.addWidget(create_header)
        
        self.backup_name_input = QLineEdit()
        self.backup_name_input.setPlaceholderText("Enter backup name")
        self.backup_name_input.setStyleSheet(self._get_input_style())
        create_layout.addWidget(self.backup_name_input)
        
        create_btn = QPushButton("Create Backup")
        create_btn.setStyleSheet(self._get_button_style(True))
        create_btn.clicked.connect(self._create_backup)
        create_layout.addWidget(create_btn)
        
        layout.addWidget(create_frame)
        
        # Restore section
        restore_frame = QFrame()
        restore_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        restore_layout = QVBoxLayout(restore_frame)
        restore_layout.setContentsMargins(20, 16, 20, 16)
        restore_layout.setSpacing(12)
        
        restore_header = QLabel("Restore from Backup")
        restore_header.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        restore_layout.addWidget(restore_header)
        
        self.backup_combo = StyledComboBox()
        self.backup_combo.setStyleSheet(self._get_input_style())
        restore_layout.addWidget(self.backup_combo)
        
        # Action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        
        restore_btn = QPushButton("Restore")
        restore_btn.setStyleSheet(self._get_button_style(True))
        restore_btn.clicked.connect(self._restore_backup)
        action_row.addWidget(restore_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a38;
                border: 2px solid #ef4444;
                border-radius: 8px;
                color: #ef4444;
                font-size: 15px;
                font-weight: 500;
                padding: 14px 24px;
                min-height: 48px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.3);
            }
        """)
        delete_btn.clicked.connect(self._delete_backup)
        action_row.addWidget(delete_btn)
        
        action_row.addStretch()
        restore_layout.addLayout(action_row)
        
        layout.addWidget(restore_frame)
        
        # Status
        self.backup_status_label = QLabel("● Ready")
        self.backup_status_label.setStyleSheet(self._get_status_style("success"))
        layout.addWidget(self.backup_status_label)
        
        layout.addStretch()
        
        # Initialize backup list
        self._refresh_backup_list()
        
        return wrapper
    
    def _create_keyboard_presets_panel(self) -> QWidget:
        """Create keyboard presets panel"""
        wrapper, layout = self._create_content_wrapper("Keyboard Presets", "⌨️")
        
        # Info card
        info_frame = self._create_info_card(
            "Customize the four preset buttons that appear above the on-screen keyboard. "
            "These buttons allow quick insertion of frequently used text."
        )
        layout.addWidget(info_frame)
        
        # Preset input fields
        preset_frame = QFrame()
        preset_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        preset_layout = QVBoxLayout(preset_frame)
        preset_layout.setContentsMargins(20, 16, 20, 16)
        preset_layout.setSpacing(16)
        
        # Create 6 preset input fields in 2 columns × 3 rows (2×3)
        self.osk_preset_inputs = []

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        preset_layout.addLayout(grid)

        for i in range(6):
            row = i // 2  # 0..2
            col = i % 2   # 0..1

            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(8)

            preset_label = QLabel(f"Preset {i+1}")
            preset_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
            cell_layout.addWidget(preset_label)

            preset_input = QLineEdit()
            preset_input.setPlaceholderText(f"Enter text for Preset {i+1}")
            preset_input.setStyleSheet(self._get_input_style())
            cell_layout.addWidget(preset_input)

            self.osk_preset_inputs.append(preset_input)
            grid.addWidget(cell, row, col)
        
        # Save button
        save_btn = QPushButton("💾 Save Presets")
        save_btn.setStyleSheet(self._get_button_style(True))
        save_btn.clicked.connect(self._save_osk_presets)
        preset_layout.addWidget(save_btn)
        
        layout.addWidget(preset_frame)
        
        layout.addStretch()
        
        # Load preset texts after creating inputs (use callLater to ensure QApplication exists)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._load_osk_presets)
        
        return wrapper
    
    def _save_osk_presets(self):
        """Save OSK preset texts and update OSK immediately"""
        # Update settings
        if not hasattr(self.settings, 'osk_presets'):
            self.settings.osk_presets = ["", "", "", "", "", ""]
        self.settings.osk_presets = [inp.text() for inp in self.osk_preset_inputs]
        self.settings.save()
        
        # Update OSK widget if it exists in main window
        main_window = self.parent()
        if main_window and hasattr(main_window, 'osk') and main_window.osk:
            # Update preset texts - this rebuilds the buttons
            main_window.osk._preset_texts = self.settings.osk_presets.copy()
            main_window.osk._build_preset_buttons()
        
        self.settings_changed.emit()
        
        # Show confirmation toast if available
        if main_window and hasattr(main_window, 'toast'):
            main_window.toast.show("Keyboard presets saved", duration=2000)
    
    def _create_system_panel(self) -> QWidget:
        """Create system information panel"""
        wrapper, layout = self._create_content_wrapper("System Information", "📊")
        
        # System info grid
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(16)
        info_layout.setColumnStretch(1, 1)
        info_layout.setColumnStretch(3, 1)
        
        self.system_info_labels = {}
        
        info_items = [
            ("model", "🔧 Model", 0, 0),
            ("os", "💿 OS", 0, 2),
            ("cpu_temp", "🌡️ CPU Temp", 1, 0),
            ("cpu_usage", "⚡ CPU Usage", 1, 2),
            ("memory", "🧠 Memory", 2, 0),
            ("storage", "💾 Storage", 2, 2),
            ("uptime", "⏱️ Uptime", 3, 0),
            ("ip_address", "🌐 IP Address", 3, 2),
        ]
        
        for key, label_text, row, col in info_items:
            label = QLabel(label_text)
            label.setStyleSheet("color: #888898; font-size: 13px;")
            info_layout.addWidget(label, row, col)
            
            value_label = QLabel("Loading...")
            value_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 500;")
            info_layout.addWidget(value_label, row, col + 1)
            self.system_info_labels[key] = value_label
        
        layout.addWidget(info_frame)
        
        # Temperature gauge
        temp_frame = QFrame()
        temp_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        temp_layout = QHBoxLayout(temp_frame)
        temp_layout.setContentsMargins(20, 16, 20, 16)
        
        temp_label = QLabel("CPU Temperature:")
        temp_label.setStyleSheet("color: #888898; font-size: 14px;")
        temp_layout.addWidget(temp_label)
        
        self.temp_bar = QFrame()
        self.temp_bar.setFixedHeight(24)
        self.temp_bar.setFixedWidth(100)
        self.temp_bar.setStyleSheet("""
            QFrame {
                background-color: #22c55e;
                border-radius: 6px;
            }
        """)
        temp_layout.addWidget(self.temp_bar)
        
        self.temp_value_label = QLabel("--°C")
        self.temp_value_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; min-width: 70px;")
        temp_layout.addWidget(self.temp_value_label)
        
        temp_layout.addStretch()
        
        self.throttle_label = QLabel("✓ No Throttling")
        self.throttle_label.setStyleSheet("color: #22c55e; font-size: 13px;")
        temp_layout.addWidget(self.throttle_label)
        
        layout.addWidget(temp_frame)
        
        # Refresh button
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet(self._get_button_style(False))
        refresh_btn.clicked.connect(self._update_system_info)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        return wrapper
    
    def _create_info_card(self, text):
        """Create an info card widget"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 149, 0, 0.1);
                border: 1px solid rgba(255, 149, 0, 0.3);
                border-radius: 12px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        
        icon = QLabel("ℹ️")
        icon.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon)
        
        label = QLabel(text)
        label.setStyleSheet("color: #FF9500; font-size: 13px;")
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        
        return frame
    
    def _create_input_group(self, title, placeholder):
        """Create an input group with label"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a22;
                border: 1px solid #2a2a38;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        
        label = QLabel(title)
        label.setStyleSheet("font-size: 14px; font-weight: 500; color: #ffffff;")
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setStyleSheet(self._get_input_style())
        layout.addWidget(input_field)
        
        return frame
    
    def _get_status_style(self, status_type="info"):
        """Get status label styling"""
        colors = {
            "success": ("#22c55e", "rgba(34, 197, 94, 0.15)", "rgba(34, 197, 94, 0.3)"),
            "error": ("#ef4444", "rgba(239, 68, 68, 0.15)", "rgba(239, 68, 68, 0.3)"),
            "info": ("#FF9500", "rgba(255, 149, 0, 0.15)", "rgba(255, 149, 0, 0.3)"),
        }
        text_color, bg_color, border_color = colors.get(status_type, colors["info"])
        return f"""
            QLabel {{
                padding: 14px 20px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                font-size: 14px;
            }}
        """
    
    # === Backup methods ===
    def _get_backup_dir(self) -> Path:
        backup_dir = Path.home() / ".panapitouch" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def _refresh_backup_list(self):
        self.backup_combo.clear()
        backup_dir = self._get_backup_dir()
        backups = list(backup_dir.glob("*.json"))
        
        if not backups:
            self.backup_combo.addItem("No backups found", None)
            return
        
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup_file in backups:
            name = backup_file.stem
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            date_str = mtime.strftime("%b %d, %Y %H:%M")
            self.backup_combo.addItem(f"{name}  •  {date_str}", str(backup_file))
    
    def _create_backup(self):
        name = self.backup_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a backup name")
            return
        
        safe_name = re.sub(r'[^\w\s-]', '', name).strip()
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        
        if not safe_name:
            QMessageBox.warning(self, "Error", "Please enter a valid backup name")
            return
        
        backup_dir = self._get_backup_dir()
        backup_file = backup_dir / f"{safe_name}.json"
        
        if backup_file.exists():
            reply = QMessageBox.question(self, "Backup Exists",
                f"A backup named '{name}' already exists.\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            backup_data = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "name": name,
                "settings": self.settings.to_dict()
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self._set_backup_status(f"Backup '{name}' created", "success")
            self.backup_name_input.clear()
            self._refresh_backup_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup:\n{str(e)}")
            self._set_backup_status("Backup failed", "error")
    
    def _restore_backup(self):
        backup_path = self.backup_combo.currentData()
        if not backup_path:
            QMessageBox.warning(self, "Error", "Please select a backup to restore")
            return
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            QMessageBox.warning(self, "Error", "Backup file not found")
            self._refresh_backup_list()
            return
        
        reply = QMessageBox.question(self, "Restore Backup",
            "This will replace your current settings.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            if "settings" in backup_data:
                self.settings.load_from_dict(backup_data["settings"])
                self.settings.save()
                self._load_settings()
                self._set_backup_status("Restored from backup", "success")
                self.settings_changed.emit()
                QMessageBox.information(self, "Restore Complete", 
                    "Settings restored. Some changes may require restart.")
            else:
                QMessageBox.warning(self, "Error", "Invalid backup file format")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore:\n{str(e)}")
            self._set_backup_status("Restore failed", "error")
    
    def _delete_backup(self):
        backup_path = self.backup_combo.currentData()
        if not backup_path:
            QMessageBox.warning(self, "Error", "Please select a backup to delete")
            return
        
        backup_file = Path(backup_path)
        backup_name = backup_file.stem
        
        reply = QMessageBox.question(self, "Delete Backup",
            f"Delete '{backup_name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            backup_file.unlink()
            self._set_backup_status(f"Deleted '{backup_name}'", "success")
            self._refresh_backup_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete:\n{str(e)}")
    
    def _set_backup_status(self, text, status_type="info"):
        self.backup_status_label.setText(f"● {text}")
        self.backup_status_label.setStyleSheet(self._get_status_style(status_type))
    
    # === System monitor methods ===
    def _start_system_monitor(self):
        self._update_system_info()
        self._system_timer = QTimer(self)
        self._system_timer.timeout.connect(self._update_system_info)
        self._system_timer.start(5000)
    
    def _update_system_info(self):
        try:
            # Model
            try:
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip().replace('\x00', '')
                    self.system_info_labels["model"].setText(model[:40])
            except:
                self.system_info_labels["model"].setText("Unknown")
            
            # OS
            try:
                result = subprocess.run(['lsb_release', '-d'], capture_output=True, text=True)
                os_info = result.stdout.split(':')[1].strip() if ':' in result.stdout else "Unknown"
                self.system_info_labels["os"].setText(os_info[:30])
            except:
                self.system_info_labels["os"].setText("Linux")
            
            # CPU Temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = int(f.read().strip()) / 1000
                    self.system_info_labels["cpu_temp"].setText(f"{temp:.1f}°C")
                    self.temp_value_label.setText(f"{temp:.1f}°C")
                    
                    if temp < 50:
                        color = "#22c55e"
                    elif temp < 70:
                        color = "#eab308"
                    else:
                        color = "#ef4444"
                    
                    width = min(200, max(20, int((temp / 85) * 200)))
                    self.temp_bar.setFixedWidth(width)
                    self.temp_bar.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 6px; }}")
            except:
                self.system_info_labels["cpu_temp"].setText("N/A")
                self.temp_value_label.setText("N/A")
            
            # CPU Usage
            try:
                result = subprocess.run(['grep', 'cpu ', '/proc/stat'], capture_output=True, text=True)
                values = [int(v) for v in result.stdout.split()[1:8]]
                idle = values[3]
                total = sum(values)
                
                if hasattr(self, '_last_cpu_idle'):
                    idle_diff = idle - self._last_cpu_idle
                    total_diff = total - self._last_cpu_total
                    usage = 100 * (1 - idle_diff / total_diff) if total_diff > 0 else 0
                    self.system_info_labels["cpu_usage"].setText(f"{usage:.1f}%")
                else:
                    self.system_info_labels["cpu_usage"].setText("--")
                
                self._last_cpu_idle = idle
                self._last_cpu_total = total
            except:
                self.system_info_labels["cpu_usage"].setText("N/A")
            
            # Memory
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                total = int(re.search(r'MemTotal:\s+(\d+)', meminfo).group(1)) / 1024 / 1024
                available = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1)) / 1024 / 1024
                used = total - available
                self.system_info_labels["memory"].setText(f"{used:.1f} / {total:.1f} GB")
            except:
                self.system_info_labels["memory"].setText("N/A")
            
            # Storage
            try:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    self.system_info_labels["storage"].setText(f"{parts[2]} / {parts[1]}")
            except:
                self.system_info_labels["storage"].setText("N/A")
            
            # Uptime
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                if days > 0:
                    self.system_info_labels["uptime"].setText(f"{days}d {hours}h {minutes}m")
                else:
                    self.system_info_labels["uptime"].setText(f"{hours}h {minutes}m")
            except:
                self.system_info_labels["uptime"].setText("N/A")
            
            # IP Address
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                self.system_info_labels["ip_address"].setText(ips[0] if ips else "No network")
            except:
                self.system_info_labels["ip_address"].setText("N/A")
            
            # Throttling
            try:
                result = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True)
                if 'throttled=0x0' in result.stdout:
                    self.throttle_label.setText("✓ No Throttling")
                    self.throttle_label.setStyleSheet("color: #22c55e; font-size: 13px;")
                else:
                    self.throttle_label.setText("⚠️ Throttling Detected")
                    self.throttle_label.setStyleSheet("color: #ef4444; font-size: 13px;")
            except:
                self.throttle_label.setText("")
        except Exception as e:
            print(f"Error updating system info: {e}")
    
    # === Network methods ===
    def _get_selected_interface(self) -> tuple[str, str]:
        """Return (interface_type_prefix, interface_name) e.g. ('eth','Ethernet')"""
        # Prefer radios (new UI)
        if hasattr(self, "interface_eth_radio") and hasattr(self, "interface_wlan_radio"):
            if self.interface_wlan_radio.isChecked():
                return "wlan", "WiFi"
            return "eth", "Ethernet"

        # Fallback for older UI if present
        if hasattr(self, "interface_combo"):
            return ("eth", "Ethernet") if self.interface_combo.currentIndex() == 0 else ("wlan", "WiFi")

        return "eth", "Ethernet"

    def _on_interface_changed(self, *args):
        self._load_current_network()
    
    def _load_current_network(self):
        try:
            interface_type, _ = self._get_selected_interface()
            
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if interface_type in line:
                    match = re.search(rf'\d+:\s+({interface_type}\d+)', line)
                    if match:
                        interfaces.append(match.group(1))
            
            if not interfaces:
                self._set_network_status("Interface not found", "error")
                return
            
            interface = interfaces[0]
            
            result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/', result.stdout)
            if ip_match:
                self.ip_input.setText(ip_match.group(1))
            
            subnet_match = re.search(r'inet\s+\d+\.\d+\.\d+\.\d+/(\d+)', result.stdout)
            if subnet_match:
                cidr = int(subnet_match.group(1))
                self.subnet_input.setText(self._cidr_to_subnet(cidr))
            
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            gateway_match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if gateway_match:
                self.gateway_input.setText(gateway_match.group(1))
            
            self._set_network_status(f"Loaded: {interface}", "success")
        except Exception as e:
            self._set_network_status("Error loading settings", "error")
    
    def _set_network_status(self, text, status_type="info"):
        self.network_status_label.setText(f"● {text}")
        self.network_status_label.setStyleSheet(self._get_status_style(status_type))
    
    def _cidr_to_subnet(self, cidr):
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{mask >> 24}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    
    def _subnet_to_cidr(self, subnet):
        parts = subnet.split('.')
        binary_str = ''.join(format(int(part), '08b') for part in parts)
        return str(binary_str.count('1'))
    
    def _apply_network_settings(self):
        ip = self.ip_input.text().strip()
        subnet = self.subnet_input.text().strip()
        gateway = self.gateway_input.text().strip()
        
        if not ip or not subnet or not gateway:
            QMessageBox.warning(self, "Error", "Please fill in all network fields")
            return
        
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not all(re.match(ip_pattern, x) for x in [ip, subnet, gateway]):
            QMessageBox.warning(self, "Error", "Please enter valid IP addresses")
            return
        
        interface_type, interface_name = self._get_selected_interface()
        reply = QMessageBox.question(self, "Apply Network Settings",
            f"Apply settings to {interface_name}?\n\nIP: {ip}\nSubnet: {subnet}\nGateway: {gateway}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if interface_type in line:
                    match = re.search(rf'\d+:\s+({interface_type}\d+)', line)
                    if match:
                        interfaces.append(match.group(1))
            
            if not interfaces:
                QMessageBox.warning(self, "Error", f"No {interface_type} interface found")
                return
            
            interface = interfaces[0]
            cidr = self._subnet_to_cidr(subnet)
            success = False
            
            # Try NetworkManager
            try:
                result = subprocess.run(['nmcli', '-t', '-f', 'NAME,DEVICE', 'connection', 'show', '--active'],
                                       capture_output=True, text=True, check=True)
                connection_name = None
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        name, device = line.split(':', 1)
                        if device == interface:
                            connection_name = name
                            break
                
                if connection_name:
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name, 
                                   f'ipv4.addresses', f'{ip}/{cidr}'], check=True, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name,
                                   'ipv4.gateway', gateway], check=True, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'modify', connection_name,
                                   'ipv4.method', 'manual'], check=True, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'down', connection_name], 
                                   check=False, capture_output=True)
                    subprocess.run(['sudo', 'nmcli', 'connection', 'up', connection_name], 
                                   check=True, capture_output=True)
                    success = True
            except:
                pass
            
            if success:
                QMessageBox.information(self, "Success", f"Network settings applied to {interface}")
                self._set_network_status(f"Applied to {interface}", "success")
            else:
                QMessageBox.warning(self, "Error", "Could not apply network settings automatically")
                self._set_network_status("Configuration failed", "error")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
            self._set_network_status("Failed to apply", "error")
    
    # === ATEM methods ===
    def _set_atem_status(self, text, status_type="info", model=None):
        self.atem_status_label.setText(f"● {text}")
        self.atem_status_label.setStyleSheet(self._get_status_style(status_type))
        
        if model:
            self.atem_model_label.setText(f"🎬 {model}")
            self.atem_model_label.show()
        else:
            self.atem_model_label.hide()
    
    def _test_atem(self):
        from ..atem.tally import ATEMTallyController
        
        ip = self.atem_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter an ATEM IP address")
            return
        
        self._set_atem_status("Connecting...", "info")
        
        controller = ATEMTallyController()
        success, message = controller.test_connection(ip)
        
        if success:
            model = None
            try:
                if hasattr(controller, 'atem') and controller.atem:
                    model = getattr(controller.atem, 'atemModel', None) or getattr(controller.atem, 'productName', None)
            except:
                pass
            
            if not model and 'ATEM' in message:
                model = message
            
            self._set_atem_status("Connected", "success", model)
            QMessageBox.information(self, "Success", f"Connection successful!\n{message}")
        else:
            self._set_atem_status("Connection Failed", "error")
            QMessageBox.warning(self, "Connection Failed", f"Could not connect:\n{message}")
    
    def _save_atem(self):
        ip = self.atem_ip_input.text().strip()
        self.settings.atem.ip_address = ip
        self.settings.atem.enabled = bool(ip)
        self.settings.save()
        QMessageBox.information(self, "Saved", "ATEM settings saved successfully")
        self.settings_changed.emit()
    
    def _load_settings(self):
        self.atem_ip_input.setText(self.settings.atem.ip_address)
        
        # Load OSK preset texts (will be loaded when panel is accessed)
        # Don't try to load here as osk_preset_inputs may not exist yet
        self._load_current_network()
    
    def _load_osk_presets(self):
        """Load OSK preset texts into input fields"""
        if not hasattr(self, 'osk_preset_inputs') or not self.osk_preset_inputs:
            return

        # Ensure settings has osk_presets attribute
        if not hasattr(self.settings, 'osk_presets'):
            self.settings.osk_presets = ["", "", "", "", "", ""]

        # Load preset texts (no signal connection needed - Save button handles saving)
        for i, preset_text in enumerate(self.settings.osk_presets):
            if i < len(self.osk_preset_inputs):
                # Just set the text - no auto-save, user clicks Save button
                self.osk_preset_inputs[i].setText(preset_text)

        # Connect keyboard preset fields to OSK if not already connected
        self._connect_osk_to_preset_fields()

    def _connect_osk_to_preset_fields(self):
        """Connect keyboard preset input fields to OSK"""
        if not hasattr(self, 'osk_preset_inputs') or not self.osk_preset_inputs:
            return

        # Get main window to connect OSK
        main_window = self.parent()
        if main_window and hasattr(main_window, '_connect_field_to_osk'):
            for field in self.osk_preset_inputs:
                if field:
                    # Always try to connect - the _connect_field_to_osk method has its own guard
                    main_window._connect_field_to_osk(field)
