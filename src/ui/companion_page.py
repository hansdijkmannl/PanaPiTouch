"""
Bitfocus Companion Page

Embedded web view for Bitfocus Companion configuration with update detection.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QProcess, Qt, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings


class TouchWebEngineView(QWebEngineView):
    """WebEngineView with proper touch event handling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
    
    def event(self, event):
        """Handle touch events properly"""
        if event.type() == QEvent.Type.TouchBegin or event.type() == QEvent.Type.TouchUpdate or event.type() == QEvent.Type.TouchEnd:
            # Let the web engine handle touch events
            return super().event(event)
        return super().event(event)


class CompanionPage(QWidget):
    """
    Embedded Bitfocus Companion web interface.
    
    Allows configuration of Stream Deck XL buttons via
    the Companion web interface at localhost:8000.
    
    Features:
    - Update detection (emits signal when update available)
    """
    
    update_available = pyqtSignal(str)  # version string
    update_cleared = pyqtSignal()  # when update is done
    
    def __init__(self, companion_url: str = "http://localhost:8000", parent=None):
        super().__init__(parent)
        self.companion_url = companion_url
        self._update_version = None
        self._update_check_timer = None
        self._update_process = None
        
        self._setup_ui()
        self._start_update_detection()
    
    def _setup_ui(self):
        """Setup the page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Web view with touch support
        self.web_view = TouchWebEngineView()
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
        # Enable smooth scrolling
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        
        # Connect signals
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
            # Inject touch scrolling support - inject immediately and retry
            self._inject_touch_support()
            # Also inject after delays to catch dynamic content
            QTimer.singleShot(2000, self._inject_touch_support)
            QTimer.singleShot(5000, self._inject_touch_support)
    
    def _inject_touch_support(self):
        """Inject JavaScript for touch scrolling support"""
        js_code = """
        (function() {
            function setupScrolling(win) {
                if (!win || !win.document) return;
                var doc = win.document;
                
                // Remove old listeners
                if (win._panapitouchScrollSetup) {
                    if (win._panapitouchTouchStart) {
                        doc.removeEventListener('touchstart', win._panapitouchTouchStart, true);
                        doc.removeEventListener('touchmove', win._panapitouchTouchMove, true);
                        doc.removeEventListener('touchend', win._panapitouchTouchEnd, true);
                        doc.removeEventListener('pointerdown', win._panapitouchPointerStart, true);
                        doc.removeEventListener('pointermove', win._panapitouchPointerMove, true);
                        doc.removeEventListener('pointerup', win._panapitouchPointerEnd, true);
                    }
                }
                win._panapitouchScrollSetup = true;
                
                var startY = 0;
                var startX = 0;
                var startScrollTop = 0;
                var startScrollLeft = 0;
                var isDragging = false;
                var scrollTarget = null;
                
                function getScrollableParent(el) {
                    var maxDepth = 20;
                    var depth = 0;
                    while (el && el !== doc.body && el !== doc.documentElement && depth < maxDepth) {
                        var style = win.getComputedStyle(el);
                        var overflowY = style.overflowY;
                        var overflowX = style.overflowX;
                        if ((overflowY === 'auto' || overflowY === 'scroll' || overflowX === 'auto' || overflowX === 'scroll') &&
                            (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth)) {
                            return el;
                        }
                        el = el.parentElement;
                        depth++;
                    }
                    return doc.documentElement || doc.body;
                }
                
                function isInputElement(el) {
                    if (!el) return false;
                    var tag = el.tagName ? el.tagName.toUpperCase() : '';
                    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
                    if (el.isContentEditable || el.contentEditable === 'true') return true;
                    return false;
                }
                
                win._panapitouchTouchStart = function(e) {
                    if (isInputElement(e.target)) return;
                    if (e.touches && e.touches.length > 0) {
                        startY = e.touches[0].clientY;
                        startX = e.touches[0].clientX;
                        scrollTarget = getScrollableParent(e.target);
                        startScrollTop = scrollTarget.scrollTop;
                        startScrollLeft = scrollTarget.scrollLeft;
                        isDragging = false;
                    }
                };
                
                win._panapitouchTouchMove = function(e) {
                    if (!scrollTarget || !e.touches || e.touches.length === 0) return;
                    if (isInputElement(e.target)) return;
                    
                    var currentY = e.touches[0].clientY;
                    var currentX = e.touches[0].clientX;
                    var deltaY = startY - currentY;
                    var deltaX = startX - currentX;
                    
                    if (!isDragging && (Math.abs(deltaY) > 5 || Math.abs(deltaX) > 5)) {
                        isDragging = true;
                        e.preventDefault();
                        e.stopPropagation();
                        if (win.getSelection) {
                            win.getSelection().removeAllRanges();
                        }
                    }
                    
                    if (isDragging && scrollTarget) {
                        scrollTarget.scrollTop = startScrollTop + deltaY;
                        scrollTarget.scrollLeft = startScrollLeft + deltaX;
                        e.preventDefault();
                        e.stopPropagation();
                    }
                };
                
                win._panapitouchTouchEnd = function(e) {
                    isDragging = false;
                    scrollTarget = null;
                };
                
                // Pointer events fallback (when touch events are translated to pointer events)
                win._panapitouchPointerStart = function(e) {
                    if (e.pointerType !== 'touch') return;
                    if (isInputElement(e.target)) return;
                    startY = e.clientY;
                    startX = e.clientX;
                    scrollTarget = getScrollableParent(e.target);
                    startScrollTop = scrollTarget.scrollTop;
                    startScrollLeft = scrollTarget.scrollLeft;
                    isDragging = false;
                };
                
                win._panapitouchPointerMove = function(e) {
                    if (e.pointerType !== 'touch') return;
                    if (!scrollTarget) return;
                    if (isInputElement(e.target)) return;
                    var deltaY = startY - e.clientY;
                    var deltaX = startX - e.clientX;
                    if (!isDragging && (Math.abs(deltaY) > 5 || Math.abs(deltaX) > 5)) {
                        isDragging = true;
                        e.preventDefault();
                        e.stopPropagation();
                        if (win.getSelection) {
                            win.getSelection().removeAllRanges();
                        }
                    }
                    if (isDragging && scrollTarget) {
                        scrollTarget.scrollTop = startScrollTop + deltaY;
                        scrollTarget.scrollLeft = startScrollLeft + deltaX;
                        e.preventDefault();
                        e.stopPropagation();
                    }
                };
                
                win._panapitouchPointerEnd = function(e) {
                    if (e.pointerType !== 'touch') return;
                    isDragging = false;
                    scrollTarget = null;
                };
                
                doc.addEventListener('touchstart', win._panapitouchTouchStart, { passive: false, capture: true });
                doc.addEventListener('touchmove', win._panapitouchTouchMove, { passive: false, capture: true });
                doc.addEventListener('touchend', win._panapitouchTouchEnd, { passive: true, capture: true });
                
                doc.addEventListener('pointerdown', win._panapitouchPointerStart, { passive: false, capture: true });
                doc.addEventListener('pointermove', win._panapitouchPointerMove, { passive: false, capture: true });
                doc.addEventListener('pointerup', win._panapitouchPointerEnd, { passive: true, capture: true });
                
                // Add CSS for smooth scrolling
                if (!doc.getElementById('panapitouch-scroll-style')) {
                    var style = doc.createElement('style');
                    style.id = 'panapitouch-scroll-style';
                    style.textContent = '* { -webkit-overflow-scrolling: touch !important; touch-action: none !important; } body { overflow: auto !important; }';
                    doc.head.appendChild(style);
                }
            }
            
            // Setup on main window
            setupScrolling(window);
            
            // Try to setup on same-origin iframes (Companion uses same origin)
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                var frame = iframes[i];
                try {
                    if (frame.contentWindow) {
                        setupScrolling(frame.contentWindow);
                    }
                } catch (err) {
                    console.warn('PanaPiTouch: iframe touch setup skipped (cross-origin)', err);
                }
            }
            
            console.log('PanaPiTouch: Touch scrolling enabled');
        })();
        """
        try:
            # Inject immediately
            self.web_view.page().runJavaScript(js_code)
            # Retry after delays
            QTimer.singleShot(500, lambda: self.web_view.page().runJavaScript(js_code))
            QTimer.singleShot(2000, lambda: self.web_view.page().runJavaScript(js_code))
            QTimer.singleShot(5000, lambda: self.web_view.page().runJavaScript(js_code))
            print("Companion: Injected touch scrolling support")
        except Exception as e:
            print(f"Companion: Failed to inject touch support: {e}")
    
    def set_url(self, url: str):
        """Set companion URL"""
        self.companion_url = url
        self.web_view.setUrl(QUrl(url))
