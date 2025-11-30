"""
Bitfocus Companion Page

Embedded web view for Bitfocus Companion configuration.
With navigation toolbar and update detection.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QProgressDialog
)
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QProcess
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtGui import QFont


class CompanionPage(QWidget):
    """
    Embedded Bitfocus Companion web interface.
    
    Allows configuration of Stream Deck XL buttons via
    the Companion web interface at localhost:8000.
    
    Features:
    - Navigation toolbar (Back, Forward, Refresh, Home)
    - Update detection and one-click update
    """
    
    update_available = pyqtSignal(str)  # version string
    
    def __init__(self, companion_url: str = "http://localhost:8000", parent=None):
        super().__init__(parent)
        self.companion_url = companion_url
        self._update_version = None
        self._update_check_timer = None
        self._update_process = None
        self._setup_ui()
        self._start_update_detection()
    
    def _setup_ui(self):
        """Setup the page UI with toolbar and web view"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Navigation toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #12121a;
                border-bottom: 1px solid #2a2a38;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(8)
        
        # Navigation buttons style
        nav_btn_style = """
            QPushButton {
                background-color: #2a2a38;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 16px;
                min-width: 44px;
                min-height: 34px;
            }
            QPushButton:hover {
                background-color: #3a3a48;
            }
            QPushButton:pressed {
                background-color: #4a4a58;
            }
            QPushButton:disabled {
                background-color: #1a1a24;
                color: #666676;
            }
        """
        
        # Back button
        self.back_btn = QPushButton("◀")
        self.back_btn.setToolTip("Go Back")
        self.back_btn.setStyleSheet(nav_btn_style)
        self.back_btn.clicked.connect(self._go_back)
        toolbar_layout.addWidget(self.back_btn)
        
        # Forward button
        self.forward_btn = QPushButton("▶")
        self.forward_btn.setToolTip("Go Forward")
        self.forward_btn.setStyleSheet(nav_btn_style)
        self.forward_btn.clicked.connect(self._go_forward)
        toolbar_layout.addWidget(self.forward_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.setStyleSheet(nav_btn_style)
        self.refresh_btn.clicked.connect(self._refresh)
        toolbar_layout.addWidget(self.refresh_btn)
        
        # Home button
        self.home_btn = QPushButton("🏠")
        self.home_btn.setToolTip("Go to Companion Home")
        self.home_btn.setStyleSheet(nav_btn_style)
        self.home_btn.clicked.connect(self._go_home)
        toolbar_layout.addWidget(self.home_btn)
        
        toolbar_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Companion")
        self.status_label.setStyleSheet("color: #888898; font-size: 12px;")
        toolbar_layout.addWidget(self.status_label)
        
        toolbar_layout.addStretch()
        
        # Update button (hidden by default)
        self.update_btn = QPushButton("⬆️ Update Available")
        self.update_btn.setToolTip("Click to update Companion")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                border: none;
                border-radius: 6px;
                color: #0a0a0f;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
                min-height: 34px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:pressed {
                background-color: #15803d;
            }
        """)
        self.update_btn.clicked.connect(self._update_companion)
        self.update_btn.hide()
        toolbar_layout.addWidget(self.update_btn)
        
        layout.addWidget(toolbar)
        
        # Web view
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(self.companion_url))
        
        # Configure settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Connect signals for navigation state
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadFinished.connect(self._on_load_finished)
        
        layout.addWidget(self.web_view)
    
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
            self.update_btn.setText(f"⬆️ Update to v{version}")
            self.update_btn.show()
            self.update_available.emit(version)
            self.status_label.setText(f"Update v{version} available")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: 600;")
    
    def _update_companion(self):
        """Update Companion on Raspberry Pi"""
        if self._update_process and self._update_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "Update in Progress", 
                              "An update is already in progress. Please wait.")
            return
        
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
            return
        
        # Start update process
        self.update_btn.setEnabled(False)
        self.update_btn.setText("⏳ Updating...")
        self.status_label.setText("Updating Companion...")
        self.status_label.setStyleSheet("color: #eab308; font-size: 12px;")
        
        # Try different update methods
        self._try_update_methods()
    
    def _try_update_methods(self):
        """Try different methods to update Companion"""
        self._update_process = QProcess(self)
        self._update_process.finished.connect(self._on_update_finished)
        self._update_process.errorOccurred.connect(self._on_update_error)
        
        # Method 1: companion-pi update command (if using companion-pi)
        # Method 2: Use the companion update script
        # Method 3: Pull latest via git and restart service
        
        # Create update script that tries multiple methods
        update_script = """
        #!/bin/bash
        set -e
        
        # Try companion-pi update first
        if command -v companion-pi &> /dev/null; then
            echo "Using companion-pi update..."
            companion-pi update
            exit 0
        fi
        
        # Try companion update command
        if command -v companion &> /dev/null; then
            echo "Using companion update..."
            companion update
            exit 0
        fi
        
        # Try updating via npm if installed that way
        COMPANION_DIR="$HOME/companion"
        if [ -d "$COMPANION_DIR" ]; then
            echo "Updating via git..."
            cd "$COMPANION_DIR"
            git pull
            yarn install
            sudo systemctl restart companion 2>/dev/null || sudo systemctl restart companion-pi 2>/dev/null || true
            exit 0
        fi
        
        # Try apt update if installed via package
        if dpkg -l | grep -q companion; then
            echo "Updating via apt..."
            sudo apt update
            sudo apt install -y companion
            exit 0
        fi
        
        echo "Could not find Companion installation to update"
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
        self._update_process.start('/bin/bash', [script_path])
    
    def _on_update_finished(self, exit_code, exit_status):
        """Handle update process completion"""
        # Clean up script
        import os
        if hasattr(self, '_update_script_path') and os.path.exists(self._update_script_path):
            os.remove(self._update_script_path)
        
        if exit_code == 0:
            self.update_btn.hide()
            self._update_version = None
            self.status_label.setText("✅ Update complete! Refreshing...")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            
            # Wait a bit for service to restart, then refresh
            QTimer.singleShot(3000, self._refresh)
            QTimer.singleShot(5000, lambda: self.status_label.setText("Companion"))
            QTimer.singleShot(5000, lambda: self.status_label.setStyleSheet("color: #888898; font-size: 12px;"))
        else:
            self.update_btn.setEnabled(True)
            self.update_btn.setText(f"⬆️ Update to v{self._update_version}")
            self.status_label.setText("❌ Update failed")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            
            QMessageBox.warning(
                self,
                "Update Failed",
                "Could not update Companion automatically.\n\n"
                "You may need to update manually via SSH:\n"
                "  companion-pi update\n"
                "or\n"
                "  sudo apt update && sudo apt upgrade companion"
            )
    
    def _on_update_error(self, error):
        """Handle update process error"""
        self.update_btn.setEnabled(True)
        self.update_btn.setText(f"⬆️ Update to v{self._update_version}")
        self.status_label.setText("❌ Update error")
        self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
    
    def _go_back(self):
        """Navigate back"""
        self.web_view.back()
    
    def _go_forward(self):
        """Navigate forward"""
        self.web_view.forward()
    
    def _refresh(self):
        """Refresh page"""
        self.web_view.reload()
    
    def _go_home(self):
        """Navigate to companion home"""
        self.web_view.setUrl(QUrl(self.companion_url))
    
    def _on_url_changed(self, url):
        """Handle URL change - update navigation button states"""
        history = self.web_view.history()
        self.back_btn.setEnabled(history.canGoBack())
        self.forward_btn.setEnabled(history.canGoForward())
    
    def _on_load_started(self):
        """Handle page load start"""
        self.status_label.setText("Loading...")
        self.status_label.setStyleSheet("color: #00b4d8; font-size: 12px;")
        self.refresh_btn.setText("✕")
        self.refresh_btn.setToolTip("Stop loading")
        try:
            self.refresh_btn.clicked.disconnect()
        except:
            pass
        self.refresh_btn.clicked.connect(self.web_view.stop)
    
    def _on_load_finished(self, success):
        """Handle page load finish"""
        if self._update_version:
            self.status_label.setText(f"Update v{self._update_version} available")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: 600;")
        elif success:
            self.status_label.setText("Companion")
            self.status_label.setStyleSheet("color: #888898; font-size: 12px;")
        else:
            self.status_label.setText("⚠️ Connection failed")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        
        self.refresh_btn.setText("⟳")
        self.refresh_btn.setToolTip("Refresh")
        try:
            self.refresh_btn.clicked.disconnect()
        except:
            pass
        self.refresh_btn.clicked.connect(self._refresh)
        
        # Check for updates after page loads
        if success:
            QTimer.singleShot(1000, self._check_for_updates)
    
    def set_url(self, url: str):
        """Set companion URL"""
        self.companion_url = url
        self.web_view.setUrl(QUrl(url))
