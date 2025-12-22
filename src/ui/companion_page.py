"""
Bitfocus Companion Page

Embedded web view for Bitfocus Companion configuration with update detection.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFrame, QLabel
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QProcess, Qt, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineScript


class TouchWebEngineView(QWebEngineView):
    """WebEngineView with proper touch event handling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Accept touch events so Companion can focus inputs reliably.
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        # Disable Chromium/QtWebEngine built-in context/edit menu (the "blue drop" popup)
        # so our custom OSK is the only on-screen input UI.
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    
    def event(self, event):
        """Handle touch events properly"""
        if event.type() in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            return super().event(event)
        return super().event(event)

    def contextMenuEvent(self, event):
        """Suppress web context menu / touch edit popup."""
        event.ignore()
        return


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
        """Setup the page UI with web view container and OSK slot"""
        from PyQt6.QtWidgets import QSizePolicy

        # Ensure page doesn't expand beyond parent
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(0, 0)

        # Main vertical layout: [Web View Container] [OSK Slot]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Web view container - takes all available space
        self.web_container = QWidget()
        self.web_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.web_container_layout = QVBoxLayout(self.web_container)
        self.web_container_layout.setContentsMargins(0, 0, 0, 0)
        self.web_container_layout.setSpacing(0)

        # Placeholder widget - shown until web view is created
        self.placeholder = QWidget()
        self.placeholder.setStyleSheet(f"""
            QWidget {{
                background-color: {self.parent().settings.theme.surface if hasattr(self.parent(), 'settings') else '#1a1a24'};
                border: 1px solid {self.parent().settings.theme.border if hasattr(self.parent(), 'settings') else '#2a2a38'};
                border-radius: 8px;
            }}
        """)
        placeholder_layout = QVBoxLayout(self.placeholder)
        loading_label = QLabel("Loading Companion...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet(f"""
            QLabel {{
                color: {self.parent().settings.theme.text if hasattr(self.parent(), 'settings') else '#ffffff'};
                font-size: 16px;
                font-weight: 600;
            }}
        """)
        placeholder_layout.addWidget(loading_label)
        self.web_container_layout.addWidget(self.placeholder)

        # Add web container to main layout with stretch factor
        layout.addWidget(self.web_container, stretch=1)

        # Web view will be created lazily when page becomes visible
        self.web_view = None

        # OSK slot at bottom - starts hidden, expands only when OSK is docked
        self.osk_slot = QFrame()
        self.osk_slot.setObjectName("companionOskSlot")
        self.osk_slot.setStyleSheet("QFrame#companionOskSlot { background: transparent; border: none; }")
        self.osk_slot.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.osk_slot.setFixedHeight(0)
        self.osk_slot.hide()
        # Add OSK slot with NO stretch - it only takes space when visible
        layout.addWidget(self.osk_slot, stretch=0)

    def _create_web_view(self):
        """Create web view lazily when page becomes visible"""
        if self.web_view is not None:
            print("Web view already exists, skipping creation")
            return  # Already created

        print("Creating Companion web view...")
        try:
            # Check if Qt WebEngine is available
            try:
                from PyQt6.QtWebEngineWidgets import QWebEngineView
            except ImportError as e:
                print(f"Qt WebEngine not available: {e}")
                raise Exception("Qt WebEngine not available")

            # Remove placeholder from web container
            if hasattr(self, 'placeholder') and self.placeholder is not None:
                self.web_container_layout.removeWidget(self.placeholder)
                self.placeholder.deleteLater()
                self.placeholder = None

            # Create web view
            print("Instantiating TouchWebEngineView...")
            self.web_view = TouchWebEngineView()

            # Ensure web view fills container but doesn't request more space
            from PyQt6.QtWidgets import QSizePolicy
            self.web_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            self.web_view.setMinimumSize(0, 0)

            # Install OSK bridge script (runs in all frames) for reliable text injection
            # Must be installed BEFORE navigation starts so it injects on initial load
            self._install_osk_bridge_script()
            self.web_view.setUrl(QUrl(self.companion_url))

            # Set zoom factor to 75% (0.75) to scale down the display
            self.web_view.setZoomFactor(0.75)

            # Configure settings
            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.TouchIconsEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

            # Connect signals
            self.web_view.loadFinished.connect(self._on_load_finished)

            # Add web view to web container (NOT main layout)
            self.web_container_layout.addWidget(self.web_view, stretch=1)

            # Ensure the web view is visible
            self.web_view.show()
            print("Companion web view shown")

            # Connect web view to OSK if main window has the connection method
            try:
                if hasattr(self.parent(), '_connect_companion_webview_to_osk'):
                    self.parent()._connect_companion_webview_to_osk(self.web_view)
                    print("Connected web view to OSK")
                else:
                    print("Main window does not have OSK connection method")
            except Exception as e:
                print(f"Could not connect companion web view to OSK: {e}")

            # Start update detection now that web view is ready
            self._start_update_detection()
            print("Companion web view creation completed successfully")

        except Exception as e:
            print(f"Error creating web view: {e}")
            import traceback
            traceback.print_exc()
            # Reset web_view to None so it can be retried
            self.web_view = None

            # Fallback: show error message
            error_label = QLabel(f"Failed to load Companion web interface.\nError: {e}\nURL: {self.companion_url}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("QLabel { color: red; font-size: 14px; }")
            self.layout().addWidget(error_label, 1)

    def showEvent(self, event):
        """Handle page becoming visible"""
        super().showEvent(event)
        # Only create web view if it hasn't been created yet and we're actually visible
        # This prevents duplicate creation that might cause UI issues
        if self.web_view is None and self.isVisible():
            # Use a longer delay to ensure the page switch is complete
            QTimer.singleShot(200, self._create_web_view)

    def _install_osk_bridge_script(self):
        """Install a JS bridge that receives OSK keystrokes via postMessage."""
        if self.web_view is None:
            return  # Web view not created yet

        try:
            page = self.web_view.page()
            scripts = page.scripts()

            # Remove any previous version so we can update flags/world/injection point.
            for s in scripts.toList():
                try:
                    if s.name() == "panapi-osk-bridge":
                        scripts.remove(s)
                except Exception:
                    pass

            src = r"""
            (function() {
              if (window.__panapiOskBridgeInstalled) return;
              window.__panapiOskBridgeInstalled = true;

              function isInput(el) {
                if (!el) return false;
                var tag = (el.tagName || '').toUpperCase();
                if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
                if (el.isContentEditable === true) return true;
                // Some UIs use divs with role=textbox instead of real inputs.
                try {
                  var role = (el.getAttribute && el.getAttribute('role')) || '';
                  if (String(role).toLowerCase() === 'textbox') return true;
                } catch (e) {}
                return false;
              }

              function deepActiveElement(doc) {
                try {
                  var el = doc.activeElement;
                  // drill into iframes in this frame (same-origin only here)
                  var depth = 0;
                  while (el && (el.tagName || '').toUpperCase() === 'IFRAME' && el.contentWindow && depth < 5) {
                    doc = el.contentWindow.document;
                    el = doc.activeElement;
                    depth++;
                  }
                  // drill into shadow roots
                  var sdepth = 0;
                  while (el && el.shadowRoot && el.shadowRoot.activeElement && sdepth < 10) {
                    el = el.shadowRoot.activeElement;
                    sdepth++;
                  }
                  return el;
                } catch (e) {
                  return null;
                }
              }

              function closestInput(node) {
                try {
                  var el = node && node.nodeType === 1 ? node : (node && node.parentElement ? node.parentElement : null);
                  while (el && el !== document.documentElement) {
                    if (isInput(el)) return el;
                    el = el.parentElement;
                  }
                } catch (e) {}
                return null;
              }

              function getTarget() {
                var el = deepActiveElement(document);
                if (isInput(el)) return el;
                try {
                  if (window.__panapiLastInput && isInput(window.__panapiLastInput)) return window.__panapiLastInput;
                } catch (e) {}
                // Fallback: selection-based (works for contenteditable/custom editors)
                try {
                  var sel = document.getSelection && document.getSelection();
                  if (sel && sel.anchorNode) {
                    var c = closestInput(sel.anchorNode);
                    if (c) return c;
                  }
                } catch (e) {}
                return null;
              }

              function setValueWithNativeSetter(el, next) {
                var tag = (el.tagName || '').toUpperCase();
                try {
                  var proto = (tag === 'TEXTAREA') ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  var desc = Object.getOwnPropertyDescriptor(proto, 'value');
                  if (desc && desc.set) desc.set.call(el, next);
                  else el.value = next;
                } catch (e) {
                  try { el.value = next; } catch (e2) {}
                }
              }

              function insertText(txt) {
                var el = getTarget();
                if (!el) return false;
                try { el.focus({preventScroll:true}); } catch (e) { try { el.focus(); } catch (e2) {} }

                if (txt === '\n') {
                  try {
                    var evDown = new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true});
                    el.dispatchEvent(evDown);
                    var evPress = new KeyboardEvent('keypress', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true});
                    el.dispatchEvent(evPress);
                    var evUp = new KeyboardEvent('keyup', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true});
                    el.dispatchEvent(evUp);
                  } catch (e) {}
                  var tag = (el.tagName || '').toUpperCase();
                  if (tag === 'TEXTAREA' || el.isContentEditable === true) {
                    try { if (document.execCommand) document.execCommand('insertText', false, '\n'); } catch (e) {}
                  }
                  return true;
                }

                try {
                  if (el.isContentEditable === true) {
                    if (document.execCommand) document.execCommand('insertText', false, txt);
                    return true;
                  }
                  var tag = (el.tagName || '').toUpperCase();
                  if (tag === 'INPUT' || tag === 'TEXTAREA') {
                    var start = (typeof el.selectionStart === 'number') ? el.selectionStart : (el.value || '').length;
                    var end = (typeof el.selectionEnd === 'number') ? el.selectionEnd : start;
                    var val = (el.value || '');
                    var next = val.slice(0, start) + txt + val.slice(end);
                    setValueWithNativeSetter(el, next);
                    try { el.setSelectionRange(start + txt.length, start + txt.length); } catch (e) {}
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return true;
                  }
                  if ('value' in el) {
                    try { el.value = (el.value || '') + txt; } catch (e) {}
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return true;
                  }
                } catch (e) {}
                return false;
              }

              function backspace() {
                var el = getTarget();
                if (!el) return false;
                try { el.focus({preventScroll:true}); } catch (e) { try { el.focus(); } catch (e2) {} }
                try {
                  if (el.isContentEditable === true) {
                    if (document.execCommand) document.execCommand('delete', false, null);
                    return true;
                  }
                  var tag = (el.tagName || '').toUpperCase();
                  if (tag === 'INPUT' || tag === 'TEXTAREA') {
                    var val = (el.value || '');
                    var start = (typeof el.selectionStart === 'number') ? el.selectionStart : val.length;
                    var end = (typeof el.selectionEnd === 'number') ? el.selectionEnd : start;
                    var next;
                    if (start !== end) next = val.slice(0, start) + val.slice(end);
                    else if (start > 0) next = val.slice(0, start - 1) + val.slice(start);
                    else next = val;
                    setValueWithNativeSetter(el, next);
                    var caret = (start !== end) ? start : Math.max(0, start - 1);
                    try { el.setSelectionRange(caret, caret); } catch (e) {}
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return true;
                  }
                  if ('value' in el) {
                    el.value = (el.value || '').slice(0, -1);
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return true;
                  }
                } catch (e) {}
                return false;
              }

              // Track last focused input in this frame
              document.addEventListener('focusin', function(e) {
                try { if (isInput(e.target)) window.__panapiLastInput = e.target; } catch (err) {}
              }, true);

              // Also track last "touched/clicked" element (some UIs don't focus real inputs)
              function rememberFromEvent(ev) {
                try {
                  var path = (ev.composedPath && ev.composedPath()) || null;
                  var candidate = null;
                  if (path && path.length) {
                    for (var i = 0; i < path.length; i++) {
                      if (isInput(path[i])) { candidate = path[i]; break; }
                    }
                  }
                  if (!candidate && ev.target && isInput(ev.target)) candidate = ev.target;
                  if (!candidate && ev.target) candidate = closestInput(ev.target);
                  if (candidate) window.__panapiLastInput = candidate;
                } catch (e) {}
              }
              document.addEventListener('pointerdown', rememberFromEvent, true);
              document.addEventListener('mousedown', rememberFromEvent, true);
              document.addEventListener('touchstart', rememberFromEvent, {passive:true, capture:true});

              window.addEventListener('message', function(ev) {
                try {
                  var d = ev.data;
                  if (!d || d.__panapiOsk !== 1) return;
                  if (d.action === 'insert') insertText(String(d.text || ''));
                  else if (d.action === 'backspace') backspace();
                } catch (e) {}
              }, true);
            })();
            """

            script = QWebEngineScript()
            script.setName("panapi-osk-bridge")
            script.setSourceCode(src)
            # Inject as early as possible so dialogs/overlays also get it.
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setRunsOnSubFrames(True)
            # IMPORTANT: must be MainWorld so window.postMessage + event listeners
            # work reliably with the page (ApplicationWorld can miss message events).
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            scripts.insert(script)
        except Exception:
            # If install fails, OSK will fall back to runJavaScript in top frame only.
            pass
    
    def _start_update_detection(self):
        """Start periodic check for update notifications in the page"""
        if hasattr(self, '_update_check_timer') and self._update_check_timer is not None:
            return  # Already started

        self._update_check_timer = QTimer(self)
        self._update_check_timer.timeout.connect(self._check_for_updates)
        self._update_check_timer.start(5000)  # Check every 5 seconds
    
    def _check_for_updates(self):
        """Inject JavaScript to detect update notification in the page"""
        if self.web_view is None:
            return  # Web view not created yet
        # JavaScript to find update notification text
        js_code = """
        (function() {
            // Look for update notification text patterns
            var bodyText = document.body ? document.body.innerText : '';
            var updateMatch = bodyText.match(/new stable version \\(\\s*v?([\\d.]+)\\s*\\) is available/i);
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
            # Track last-focused input for OSK JS injection fallback
            self._inject_osk_focus_tracker()
            # Reduce/disable Chromium touch selection UI ("blue drop") via CSS.
            self._inject_disable_touch_handles_css()

    def _inject_osk_focus_tracker(self):
        """Inject JS to remember last-focused HTML input/textarea/contenteditable."""
        js_code = """
        (function() {
          if (window.__panapiFocusTrackerInstalled) return;
          window.__panapiFocusTrackerInstalled = true;
          function isInput(el) {
            if (!el) return false;
            var tag = (el.tagName || '').toUpperCase();
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
            if (el.isContentEditable === true) return true;
            return false;
          }
          document.addEventListener('focusin', function(e) {
            try {
              if (isInput(e.target)) window.__panapiLastInput = e.target;
            } catch (err) {}
          }, true);

          // Also install into same-origin iframes (Companion uses them).
          try {
            var frames = document.querySelectorAll('iframe');
            for (var i = 0; i < frames.length; i++) {
              var f = frames[i];
              try {
                if (f.contentWindow && f.contentWindow.document && !f.contentWindow.__panapiFocusTrackerInstalled) {
                  f.contentWindow.__panapiFocusTrackerInstalled = true;
                  f.contentWindow.document.addEventListener('focusin', function(ev) {
                    try {
                      if (isInput(ev.target)) this.__panapiLastInput = ev.target;
                    } catch (err) {}
                  }.bind(f.contentWindow), true);
                }
              } catch (err) {}
            }
          } catch (err) {}
        })();
        """
        try:
            self.web_view.page().runJavaScript(js_code)
        except Exception:
            pass

    def _inject_disable_touch_handles_css(self):
        """Inject CSS to reduce touch callouts/selection handles."""
        js_code = """
        (function() {
          if (document.getElementById('panapi-no-touch-handles')) return;
          var style = document.createElement('style');
          style.id = 'panapi-no-touch-handles';
          style.textContent = `
            /* Disable long-press callouts and selection UI broadly */
            * { -webkit-touch-callout: none !important; -webkit-user-select: none !important; user-select: none !important; }
            /* Re-enable selection/editing inside actual fields (avoid breaking inputs) */
            input, textarea, select, [contenteditable="true"], [role="textbox"] { -webkit-user-select: text !important; user-select: text !important; -webkit-touch-callout: none !important; }
          `;
          (document.head || document.documentElement).appendChild(style);
        })();
        """
        try:
            self.web_view.page().runJavaScript(js_code)
        except Exception:
            pass
    
    def _inject_touch_support(self):
        """Inject JavaScript for touch/mouse drag scrolling support"""
        if self.web_view is None:
            return  # Web view not created yet
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
                        doc.removeEventListener('mousedown', win._panapitouchMouseStart, true);
                        doc.removeEventListener('mousemove', win._panapitouchMouseMove, true);
                        doc.removeEventListener('mouseup', win._panapitouchMouseEnd, true);
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

                // Mouse events fallback (for touch->mouse synthesized input)
                win._panapitouchMouseStart = function(e) {
                    // Only left button
                    if (e.button !== 0) return;
                    if (isInputElement(e.target)) return;
                    startY = e.clientY;
                    startX = e.clientX;
                    scrollTarget = getScrollableParent(e.target);
                    startScrollTop = scrollTarget.scrollTop;
                    startScrollLeft = scrollTarget.scrollLeft;
                    isDragging = false;
                };

                win._panapitouchMouseMove = function(e) {
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

                win._panapitouchMouseEnd = function(e) {
                    isDragging = false;
                    scrollTarget = null;
                };
                
                doc.addEventListener('touchstart', win._panapitouchTouchStart, { passive: false, capture: true });
                doc.addEventListener('touchmove', win._panapitouchTouchMove, { passive: false, capture: true });
                doc.addEventListener('touchend', win._panapitouchTouchEnd, { passive: true, capture: true });
                
                doc.addEventListener('pointerdown', win._panapitouchPointerStart, { passive: false, capture: true });
                doc.addEventListener('pointermove', win._panapitouchPointerMove, { passive: false, capture: true });
                doc.addEventListener('pointerup', win._panapitouchPointerEnd, { passive: true, capture: true });

                doc.addEventListener('mousedown', win._panapitouchMouseStart, { passive: false, capture: true });
                doc.addEventListener('mousemove', win._panapitouchMouseMove, { passive: false, capture: true });
                doc.addEventListener('mouseup', win._panapitouchMouseEnd, { passive: true, capture: true });
                
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
