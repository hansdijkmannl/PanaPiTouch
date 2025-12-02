"""
Bitfocus Companion Page

Embedded web view for Bitfocus Companion configuration.
With update detection and on-screen keyboard support.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QLineEdit, QLabel, QPushButton
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QProcess, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

from .keyboard_widget import KeyboardWidget
from .styles import COLORS


class CompanionPage(QWidget):
    """
    Embedded Bitfocus Companion web interface.
    
    Allows configuration of Stream Deck XL buttons via
    the Companion web interface at localhost:8000.
    
    Features:
    - Update detection (emits signal when update available)
    - On-screen keyboard support for web input fields
    """
    
    update_available = pyqtSignal(str)  # version string
    update_cleared = pyqtSignal()  # when update is done
    
    def __init__(self, companion_url: str = "http://localhost:8000", parent=None):
        super().__init__(parent)
        self.companion_url = companion_url
        self._update_version = None
        self._update_check_timer = None
        self._update_process = None
        self._web_input_focused = False
        self._current_input_type = "text"
        self._current_input_id = None
        self._setup_ui()
        self._start_update_detection()
        self._start_input_focus_detection()
    
    def _setup_ui(self):
        """Setup the page UI - web view with keyboard overlay"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Web view only - no toolbar
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(self.companion_url))
        
        # Configure settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Connect signals
        self.web_view.loadFinished.connect(self._on_load_finished)
        
        layout.addWidget(self.web_view)
        
        # Create keyboard overlay (initially hidden)
        self._setup_keyboard_overlay()
    
    def _setup_keyboard_overlay(self):
        """Setup keyboard overlay for web input fields"""
        self.keyboard_container = QWidget(self)
        self.keyboard_container.setVisible(False)
        self.keyboard_container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        
        keyboard_layout = QVBoxLayout(self.keyboard_container)
        keyboard_layout.setContentsMargins(20, 12, 20, 12)
        keyboard_layout.setSpacing(12)
        
        # Preview section
        preview_container = QWidget()
        preview_container.setStyleSheet("background: transparent;")
        preview_wrapper = QHBoxLayout(preview_container)
        preview_wrapper.setContentsMargins(0, 0, 0, 0)
        preview_wrapper.setSpacing(12)
        preview_wrapper.addStretch()
        
        # Field name label
        self.field_name_label = QLabel("Input:")
        self.field_name_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 16px;
                font-weight: 600;
                padding: 0px;
            }}
        """)
        preview_wrapper.addWidget(self.field_name_label)
        
        # Preview text field
        self.preview_field = QLineEdit()
        self.preview_field.setReadOnly(True)
        self.preview_field.setFixedWidth(400)
        self.preview_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface_light']};
                border: 2px solid #FF9500;
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 20px;
                font-weight: 400;
                padding: 12px 16px;
            }}
        """)
        preview_wrapper.addWidget(self.preview_field)
        preview_wrapper.addStretch()
        keyboard_layout.addWidget(preview_container)
        
        # Keyboard widget
        self.keyboard_widget = KeyboardWidget()
        self.keyboard_widget.key_pressed.connect(self._on_osk_key)
        self.keyboard_widget.backspace_pressed.connect(self._on_osk_backspace)
        self.keyboard_widget.enter_pressed.connect(self._hide_osk)
        self.keyboard_widget.close_pressed.connect(self._hide_osk)
        if hasattr(self.keyboard_widget, 'space_pressed'):
            self.keyboard_widget.space_pressed.connect(self._on_osk_space)
        keyboard_layout.addWidget(self.keyboard_widget)
    
    def _start_input_focus_detection(self):
        """Start periodic check for focused input fields in web page"""
        self._input_focus_timer = QTimer(self)
        self._input_focus_timer.timeout.connect(self._check_web_input_focus)
        self._input_focus_timer.start(300)  # Check every 300ms
    
    def _check_web_input_focus(self):
        """Check if an input field is focused in the web page"""
        js_code = """
        (function() {
            var el = document.activeElement;
            // Exclude SELECT (dropdown) elements - they don't need keyboard
            if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.tagName !== 'SELECT') {
                var inputType = el.type || 'text';
                // Also exclude input types that don't need keyboard (like 'select-one' dropdowns)
                if (inputType === 'select-one' || inputType === 'select-multiple') {
                    return JSON.stringify({focused: false});
                }
                var inputId = el.id || el.name || 'input';
                var inputValue = el.value || '';
                var placeholder = el.placeholder || '';
                return JSON.stringify({
                    focused: true,
                    type: inputType,
                    id: inputId,
                    value: inputValue,
                    placeholder: placeholder
                });
            }
            return JSON.stringify({focused: false});
        })();
        """
        self.web_view.page().runJavaScript(js_code, self._on_input_focus_result)
    
    def _on_input_focus_result(self, result):
        """Handle result of input focus check"""
        import json
        try:
            data = json.loads(result) if result else {"focused": False}
        except:
            data = {"focused": False}
        
        if data.get("focused"):
            if not self._web_input_focused:
                self._web_input_focused = True
                self._current_input_type = data.get("type", "text")
                self._current_input_id = data.get("id", "Input")
                self._show_osk(data.get("value", ""), data.get("placeholder", ""))
            else:
                # Update preview with current value
                self.preview_field.setText(data.get("value", ""))
        else:
            if self._web_input_focused:
                self._web_input_focused = False
                self._hide_osk()
    
    def _show_osk(self, value: str, placeholder: str):
        """Show on-screen keyboard"""
        # Set field name from input id/placeholder
        field_name = self._current_input_id.replace('_', ' ').replace('-', ' ').title()
        if not field_name or field_name == "Input":
            field_name = placeholder.replace('...', '').strip() if placeholder else "Input"
        self.field_name_label.setText(f"{field_name}:")
        self.preview_field.setText(value)
        
        # Preserve cursor position in web input - don't select all text
        js_code = """
        (function() {
            var el = document.activeElement;
            if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                // Preserve cursor position, don't select all
                var pos = el.selectionStart || el.value.length;
                el.setSelectionRange(pos, pos);
            }
        })();
        """
        self.web_view.page().runJavaScript(js_code)
        
        self.keyboard_container.setVisible(True)
        self._position_keyboard()
    
    def _hide_osk(self):
        """Hide on-screen keyboard"""
        self.keyboard_container.setVisible(False)
        # Blur the web input
        self.web_view.page().runJavaScript("document.activeElement.blur();")
    
    def _on_osk_key(self, char):
        """Handle key press from OSK"""
        # Check shift state
        if hasattr(self.keyboard_widget, '_shift_active') and self.keyboard_widget._shift_active:
            char = char.upper()
            self.keyboard_widget._shift_active = False
            for btn in self.keyboard_widget.findChildren(QPushButton):
                if btn.text() == "⇧":
                    btn.setChecked(False)
        
        # Insert character into web input
        js_code = f"""
        (function() {{
            var el = document.activeElement;
            if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {{
                var start = el.selectionStart;
                var end = el.selectionEnd;
                var value = el.value;
                el.value = value.substring(0, start) + '{char}' + value.substring(end);
                el.selectionStart = el.selectionEnd = start + 1;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js_code)
    
    def _on_osk_backspace(self):
        """Handle backspace from OSK"""
        js_code = """
        (function() {
            var el = document.activeElement;
            if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                var start = el.selectionStart;
                var end = el.selectionEnd;
                var value = el.value;
                if (start === end && start > 0) {
                    el.value = value.substring(0, start - 1) + value.substring(end);
                    el.selectionStart = el.selectionEnd = start - 1;
                } else if (start !== end) {
                    el.value = value.substring(0, start) + value.substring(end);
                    el.selectionStart = el.selectionEnd = start;
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })();
        """
        self.web_view.page().runJavaScript(js_code)
    
    def _on_osk_space(self):
        """Handle space from OSK"""
        self._on_osk_key(' ')
    
    def _position_keyboard(self):
        """Position keyboard at bottom of page"""
        if not self.keyboard_container.isVisible():
            return
        
        width = self.width()
        self.keyboard_container.setFixedWidth(width)
        self.keyboard_container.adjustSize()
        keyboard_height = self.keyboard_container.sizeHint().height()
        if keyboard_height < 200:
            keyboard_height = 350
        
        self.keyboard_container.setGeometry(0, self.height() - keyboard_height, width, keyboard_height)
        self.keyboard_container.raise_()
    
    def resizeEvent(self, event):
        """Handle resize to reposition keyboard"""
        super().resizeEvent(event)
        if self.keyboard_container.isVisible():
            self._position_keyboard()
    
    def _start_update_detection(self):
        """Start periodic check for update notifications in the page"""
        self._update_check_timer = QTimer(self)
        self._update_check_timer.timeout.connect(self._check_for_updates)
        self._update_check_timer.start(5000)  # Check every 5 seconds
    
    def _check_for_updates(self):
        """Inject JavaScript to detect update notification in the page"""
        # JavaScript to find update notification text
        js_code = """
        (function() {
            // Look for update notification text patterns
            var bodyText = document.body ? document.body.innerText : '';
            var updateMatch = bodyText.match(/new stable version \\(([\\d.]+)\\) is available/i);
            if (updateMatch) {
                return updateMatch[1];  // Return version number
            }
            // Also check for other common update patterns
            updateMatch = bodyText.match(/Update available[:\\s]+v?([\\d.]+)/i);
            if (updateMatch) {
                return updateMatch[1];
            }
            // Check for update banner/notification elements
            var updateElements = document.querySelectorAll('[class*="update"], [class*="notification"], [class*="banner"]');
            for (var el of updateElements) {
                var text = el.innerText || '';
                var match = text.match(/([\\d]+\\.[\\d]+\\.[\\d]+)/);
                if (match && text.toLowerCase().includes('update')) {
                    return match[1];
                }
            }
            return null;
        })();
        """
        self.web_view.page().runJavaScript(js_code, self._on_update_check_result)
    
    def _on_update_check_result(self, version):
        """Handle result of update check"""
        if version and version != self._update_version:
            self._update_version = version
            self.update_available.emit(version)
    
    def get_update_version(self) -> str:
        """Get the detected update version"""
        return self._update_version
    
    def update_companion(self):
        """Update Companion on Raspberry Pi - called externally"""
        if self._update_process and self._update_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "Update in Progress", 
                              "An update is already in progress. Please wait.")
            return False
        
        # Confirm update
        reply = QMessageBox.question(
            self, 
            "Update Companion",
            f"Do you want to update Companion to v{self._update_version}?\n\n"
            "This will restart the Companion service.\n"
            "Your buttons and configuration will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return False
        
        # Try different update methods
        self._try_update_methods()
        return True
    
    def _try_update_methods(self):
        """Try different methods to update Companion"""
        self._update_process = QProcess(self)
        self._update_process.finished.connect(self._on_update_finished)
        self._update_process.errorOccurred.connect(self._on_update_error)
        
        # Read stdout/stderr for debugging
        self._update_process.readyReadStandardOutput.connect(self._on_update_stdout)
        self._update_process.readyReadStandardError.connect(self._on_update_stderr)
        
        # Create update script - tries companionpi method first (most common on Pi)
        update_script = """#!/bin/bash
set -e

echo "Starting Companion update..."

# Method 1: CompanionPi installation (most common on Raspberry Pi)
if [ -f "/usr/local/src/companionpi/companion-update" ]; then
    echo "Found CompanionPi installation, running update..."
    cd /usr/local/src/companionpi
    
    # Stop companion
    systemctl stop companion || true
    
    # Pull latest companionpi code
    git pull -q
    
    # Run the update script (pass 'stable' to avoid prompts)
    ./update.sh stable
    
    # Restart companion
    systemctl start companion
    
    echo "Update complete!"
    exit 0
fi

# Method 2: Direct companion-update command
if [ -x "/usr/local/bin/companion-update" ]; then
    echo "Using companion-update command..."
    /usr/local/bin/companion-update stable
    exit 0
fi

# Method 3: Check for companion in /opt and use update.sh directly
if [ -f "/usr/local/src/companionpi/update.sh" ]; then
    echo "Running update.sh directly..."
    cd /usr/local/src/companionpi
    systemctl stop companion || true
    ./update.sh stable
    systemctl start companion
    exit 0
fi

echo "ERROR: Could not find Companion installation to update"
echo "Companion may be installed in an unsupported way."
exit 1
"""
        
        # Write and execute update script
        import tempfile
        import os
        
        script_path = tempfile.mktemp(suffix='.sh')
        with open(script_path, 'w') as f:
            f.write(update_script)
        os.chmod(script_path, 0o755)
        
        self._update_script_path = script_path
        # Run with sudo since companion-update requires root
        self._update_process.start('sudo', ['/bin/bash', script_path])
    
    def _on_update_stdout(self):
        """Handle stdout from update process"""
        data = self._update_process.readAllStandardOutput().data().decode()
        print(f"[Companion Update] {data.strip()}")
    
    def _on_update_stderr(self):
        """Handle stderr from update process"""
        data = self._update_process.readAllStandardError().data().decode()
        print(f"[Companion Update Error] {data.strip()}")
    
    def _on_update_finished(self, exit_code, exit_status):
        """Handle update process completion"""
        # Clean up script
        import os
        if hasattr(self, '_update_script_path') and os.path.exists(self._update_script_path):
            os.remove(self._update_script_path)
        
        if exit_code == 0:
            self._update_version = None
            self.update_cleared.emit()
            
            # Wait a bit for service to restart, then refresh
            QTimer.singleShot(3000, lambda: self.web_view.reload())
            
            QMessageBox.information(
                self,
                "Update Complete",
                "Companion has been updated successfully!\n\n"
                "The page will refresh automatically."
            )
        else:
            QMessageBox.warning(
                self,
                "Update Failed",
                "Could not update Companion automatically.\n\n"
                "You may need to update manually via SSH:\n\n"
                "  sudo /usr/local/src/companionpi/companion-update\n\n"
                "Or run with the 'stable' parameter:\n"
                "  sudo /usr/local/src/companionpi/update.sh stable"
            )
    
    def _on_update_error(self, error):
        """Handle update process error"""
        QMessageBox.warning(
            self,
            "Update Error", 
            "An error occurred while updating Companion."
        )
    
    def _on_load_finished(self, success):
        """Handle page load finish - check for updates"""
        if success:
            QTimer.singleShot(1000, self._check_for_updates)
    
    def set_url(self, url: str):
        """Set companion URL"""
        self.companion_url = url
        self.web_view.setUrl(QUrl(url))
