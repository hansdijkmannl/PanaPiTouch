"""
Bitfocus Companion Page

Embedded web view for Bitfocus Companion configuration.
With update detection and Pi OS keyboard support.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QProcess
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

import subprocess
import shutil


class CompanionPage(QWidget):
    """
    Embedded Bitfocus Companion web interface.
    
    Allows configuration of Stream Deck XL buttons via
    the Companion web interface at localhost:8000.
    
    Features:
    - Update detection (emits signal when update available)
    - Pi OS keyboard support for web input fields (triggers system keyboard on focus)
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
        self._keyboard_process = None
        self._keyboard_command = self._find_keyboard_command()
        if self._keyboard_command:
            print(f"Companion page: Found keyboard command: {self._keyboard_command}")
        else:
            print("Companion page: No keyboard command found - OSK will not work")
        
        self._setup_ui()
        self._start_update_detection()
        self._start_input_focus_detection()
    
    def _setup_ui(self):
        """Setup the page UI - web view with keyboard overlay"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Web view
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(self.companion_url))
        
        # Set zoom factor to 75% (0.75) to scale down the display
        self.web_view.setZoomFactor(0.75)
        
        # Configure settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        # Enable touch scrolling and touch features
        settings.setAttribute(QWebEngineSettings.WebAttribute.TouchIconsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, False)
        
        # Connect signals
        self.web_view.loadFinished.connect(self._on_load_finished)
        
        layout.addWidget(self.web_view)
    
    def _find_keyboard_command(self):
        """Find available Pi OS keyboard command"""
        # Try common keyboard commands in order of preference
        keyboard_commands = [
            'matchbox-keyboard',  # Common on Raspberry Pi OS
            'onboard',            # Alternative keyboard
            'florence',           # Another alternative
            'squeekboard',        # Squeekboard (used on some Pi OS versions)
        ]
        
        for cmd in keyboard_commands:
            if shutil.which(cmd):
                return cmd
        
        return None
    
    def _start_input_focus_detection(self):
        """Start periodic check for focused input fields in web page"""
        self._input_focus_timer = QTimer(self)
        self._input_focus_timer.timeout.connect(self._check_web_input_focus)
        self._input_focus_timer.start(150)  # Check every 150ms for very responsive detection
    
    def _check_web_input_focus(self):
        """Check if an input field is focused in the web page"""
        js_code = """
        (function() {
            var el = document.activeElement;
            if (!el || !el.tagName) {
                return JSON.stringify({focused: false, reason: 'no active element'});
            }
            var tagName = el.tagName.toUpperCase();
            var isInput = tagName === 'INPUT' || tagName === 'TEXTAREA';
            var isContentEditable = el.contentEditable === 'true' || el.contentEditable === true || el.isContentEditable === true;
            
            if (isInput) {
                var inputType = (el.type || 'text').toLowerCase();
                var excludeTypes = ['button', 'submit', 'reset', 'checkbox', 'radio', 'file', 'hidden', 'image'];
                if (excludeTypes.indexOf(inputType) !== -1 || tagName === 'SELECT') {
                    return JSON.stringify({focused: false, reason: 'excluded type: ' + inputType});
                }
                return JSON.stringify({focused: true, type: inputType, tag: tagName});
            }
            
            if (isContentEditable) {
                return JSON.stringify({focused: true, type: 'contenteditable', tag: tagName});
            }
            
            return JSON.stringify({focused: false, reason: 'not input: ' + tagName});
        })();
        """
        try:
            self.web_view.page().runJavaScript(js_code, self._on_input_focus_result)
        except Exception as e:
            print(f"Companion: Error checking web input focus: {e}")
    
    def _on_input_focus_result(self, result):
        """Handle result of input focus check"""
        import json
        try:
            if not result:
                result = '{"focused": false}'
            data = json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            print(f"Companion: Error parsing result: {e}, result: {result}")
            data = {"focused": False}
        
        is_focused = data.get("focused", False)
        
        if is_focused:
            if not self._web_input_focused:
                self._web_input_focused = True
                self._current_input_type = data.get("type", "text")
                print(f"Companion: INPUT FOCUSED - type={self._current_input_type}, tag={data.get('tag')}")
                self._show_pi_keyboard()
        else:
            if self._web_input_focused:
                self._web_input_focused = False
                print(f"Companion: INPUT BLURRED - reason={data.get('reason')}")
                self._hide_pi_keyboard()
    
    
    def _show_pi_keyboard(self):
        """Show Pi OS on-screen keyboard"""
        if not self._keyboard_command:
            print("No keyboard command available")
            return  # No keyboard command available
        
        # Kill any existing keyboard process
        self._hide_pi_keyboard()
        
        # Small delay to ensure previous keyboard is fully closed
        QTimer.singleShot(100, self._actually_show_keyboard)
    
    def _actually_show_keyboard(self):
        """Actually show the keyboard (called after delay)"""
        if not self._keyboard_command:
            return
        
        try:
            if self._keyboard_command == 'squeekboard':
                # Squeekboard uses sm.puri.OSK0 D-Bus interface
                result = subprocess.run(
                    ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'true'],
                    timeout=2, capture_output=True, text=True
                )
                if result.returncode == 0:
                    print("Companion: Showed squeekboard via D-Bus")
                else:
                    print(f"Companion: squeekboard D-Bus error: {result.stderr}")
            elif self._keyboard_command == 'matchbox-keyboard':
                self._keyboard_process = subprocess.Popen(
                    [self._keyboard_command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"Companion: Started {self._keyboard_command}")
            elif self._keyboard_command in ('onboard', 'florence'):
                self._keyboard_process = subprocess.Popen(
                    [self._keyboard_command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"Companion: Started {self._keyboard_command}")
        except Exception as e:
            print(f"Companion: Failed to show keyboard: {e}")
    
    def _hide_pi_keyboard(self):
        """Hide Pi OS on-screen keyboard"""
        if self._keyboard_process:
            try:
                self._keyboard_process.terminate()
                try:
                    self._keyboard_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._keyboard_process.kill()
                    self._keyboard_process.wait()
            except Exception:
                pass
            finally:
                self._keyboard_process = None
        
        try:
            if self._keyboard_command == 'squeekboard':
                # Squeekboard uses sm.puri.OSK0 D-Bus interface
                result = subprocess.run(
                    ['busctl', 'call', '--user', 'sm.puri.OSK0', '/sm/puri/OSK0', 'sm.puri.OSK0', 'SetVisible', 'b', 'false'],
                    timeout=2, capture_output=True, text=True
                )
                if result.returncode == 0:
                    print("Companion: Hid squeekboard via D-Bus")
                else:
                    print(f"Companion: squeekboard hide error: {result.stderr}")
            elif self._keyboard_command == 'matchbox-keyboard':
                subprocess.run(['pkill', '-f', 'matchbox-keyboard'], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self._keyboard_command in ('onboard', 'florence'):
                subprocess.run(['pkill', '-f', self._keyboard_command], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Companion: Error hiding keyboard: {e}")
    
    def closeEvent(self, event):
        """Clean up keyboard process on close"""
        self._hide_pi_keyboard()
        super().closeEvent(event)
    
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
        """Handle page load finish - check for updates and inject touch support"""
        if success:
            QTimer.singleShot(1000, self._check_for_updates)
            # Inject touch scrolling support
            self._inject_touch_support()
    
    def _inject_touch_support(self):
        """Inject JavaScript for touch scrolling support"""
        js_code = """
        (function() {
            if (window._panapitouchScrollSetup) return;
            window._panapitouchScrollSetup = true;
            
            var startY = 0;
            var startX = 0;
            var startScrollTop = 0;
            var startScrollLeft = 0;
            var isDragging = false;
            var scrollTarget = null;
            
            function getScrollableParent(el) {
                while (el && el !== document.body) {
                    var style = window.getComputedStyle(el);
                    var overflowY = style.overflowY;
                    var overflowX = style.overflowX;
                    if ((overflowY === 'auto' || overflowY === 'scroll' || overflowX === 'auto' || overflowX === 'scroll') &&
                        (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth)) {
                        return el;
                    }
                    el = el.parentElement;
                }
                return document.documentElement;
            }
            
            document.addEventListener('touchstart', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                    return;
                }
                startY = e.touches[0].clientY;
                startX = e.touches[0].clientX;
                scrollTarget = getScrollableParent(e.target);
                startScrollTop = scrollTarget.scrollTop;
                startScrollLeft = scrollTarget.scrollLeft;
                isDragging = false;
            }, { passive: true });
            
            document.addEventListener('touchmove', function(e) {
                if (!scrollTarget) return;
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                    return;
                }
                
                var deltaY = startY - e.touches[0].clientY;
                var deltaX = startX - e.touches[0].clientX;
                
                if (!isDragging && (Math.abs(deltaY) > 5 || Math.abs(deltaX) > 5)) {
                    isDragging = true;
                    if (window.getSelection) {
                        window.getSelection().removeAllRanges();
                    }
                }
                
                if (isDragging) {
                    scrollTarget.scrollTop = startScrollTop + deltaY;
                    scrollTarget.scrollLeft = startScrollLeft + deltaX;
                }
            }, { passive: true });
            
            document.addEventListener('touchend', function(e) {
                isDragging = false;
                scrollTarget = null;
            }, { passive: true });
            
            console.log('PanaPiTouch: Touch scrolling enabled');
        })();
        """
        try:
            self.web_view.page().runJavaScript(js_code)
            print("Companion: Injected touch scrolling support")
        except Exception as e:
            print(f"Companion: Failed to inject touch support: {e}")
    
    def set_url(self, url: str):
        """Set companion URL"""
        self.companion_url = url
        self.web_view.setUrl(QUrl(url))
