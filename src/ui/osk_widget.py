"""
On-Screen Keyboard Widget

Touch-friendly keyboard that slides up from bottom (or top for preset rename).
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QApplication, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QKeyEvent, QFont
import json

from .styles import COLORS


class OSKWidget(QWidget):
    """On-Screen Keyboard widget with slide animation"""
    DEFAULT_HEIGHT = 430
    
    # Signal emitted when a key is pressed
    key_pressed = pyqtSignal(str)
    
    def __init__(self, parent=None, slide_from_top=False, preset_texts=None):
        super().__init__(parent)
        # Ensure OSK is opaque (non-transparent) and uses themed background.
        # Some Qt/driver combos can end up compositing child widgets; forcing a
        # styled, autofilled background makes the keyboard a solid panel.
        self.setObjectName("oskRoot")
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        # IMPORTANT: Don't steal focus from target fields (especially QWebEngineView).
        # We want the active text field to keep focus while tapping OSK buttons.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slide_from_top = slide_from_top
        self._top_offset_px = 0  # used when slide_from_top=True (e.g. below main menu)
        self._docked = False  # when True, OSK is managed by a layout (e.g. Companion page)
        self._keyboard_height = self.DEFAULT_HEIGHT
        self._target_widget = None
        self._is_visible = False
        self._shift_pressed = False
        self._caps_lock = False
        self._letter_buttons = {}  # Store letter buttons for case updates
        self._preset_texts = preset_texts or ["", "", "", "", "", ""]  # Default empty presets (6 total)
        self._preset_buttons = []  # Initialize preset buttons list
        
        self._setup_ui()
        self._setup_animation()
    
    def set_preset_texts(self, texts: list):
        """Update preset button texts"""
        if len(texts) >= 6:
            self._preset_texts = texts[:6]
            self._update_preset_buttons()
        else:
            # Pad with empty strings if less than 6
            self._preset_texts = (texts + [""] * (6 - len(texts)))[:6]
            self._update_preset_buttons()
    
    def _update_preset_buttons(self):
        """Update preset button labels"""
        if not hasattr(self, '_preset_buttons') or not self._preset_buttons:
            return
        for i, btn in enumerate(self._preset_buttons):
            if i < len(self._preset_texts):
                text = self._preset_texts[i] if self._preset_texts[i] else ""
                # Display just the text, or "(empty)" if no text
                if text:
                    display_text = text[:15]  # Show text (6 buttons fit in 12 columns)
                    btn.setText(display_text)
                else:
                    btn.setText("(empty)")
                # Force button to repaint
                btn.update()
    
    def _setup_ui(self):
        """Setup keyboard UI"""
        try:
            # Keyboard widget background (Option E: themeable, non-transparent)
            self.setStyleSheet(f"""
                #oskRoot {{
                    background-color: {COLORS['surface_light']};
                    border-top: 2px solid {COLORS['border']};
                }}
                #oskRoot QPushButton {{
                    background-color: {COLORS['surface_light']};
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    color: {COLORS['text']};
                    font-size: 14px;
                    font-weight: 600;
                    min-height: 60px;
                }}
                #oskRoot QPushButton:pressed {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                    color: {COLORS['background']};
                }}
                #oskRoot QPushButton:hover {{
                    background-color: {COLORS['surface_hover']};
                }}
            """)
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(6)  # 4px + 2px extra padding between preset row and keyboard
            
            # Preset buttons row (above keyboard)
            self.preset_grid = QGridLayout()
            self.preset_grid.setSpacing(8)
            self.preset_grid.setVerticalSpacing(0)  # No extra vertical spacing
            layout.addLayout(self.preset_grid)
            
            # Keyboard grid (includes top row with Hide/Backspace)
            self.keyboard_grid = QGridLayout()
            self.keyboard_grid.setSpacing(8)  # Increased spacing to prevent overlap
            self.keyboard_grid.setVerticalSpacing(10)  # Extra vertical spacing
            layout.addLayout(self.keyboard_grid)
            
            # Build preset buttons and keyboard layout
            self._build_preset_buttons()
            self._build_keyboard()
        except Exception as e:
            print(f"Error setting up OSK UI: {e}")
            import traceback
            traceback.print_exc()
            # Create minimal layout to prevent complete failure
            layout = QVBoxLayout(self)
            layout.addWidget(QPushButton("OSK Error"))
    
    def _build_preset_buttons(self):
        """Build preset text buttons row"""
        # Clear existing buttons
        while self.preset_grid.count():
            child = self.preset_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self._preset_buttons = []
        for i in range(6):
            preset_text = self._preset_texts[i] if i < len(self._preset_texts) else ""
            # Display just the text, or "(empty)" if no text
            if preset_text:
                display_text = preset_text[:15]  # Show text (6 buttons fit in 12 columns, so 2 cols each)
            else:
                display_text = "(empty)"
            
            btn = QPushButton(display_text)
            btn.setFixedHeight(60)  # Same height as keyboard letter buttons
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # Use same styling as keyboard buttons for consistency
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface_light']};
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    color: {COLORS['text']};
                    font-size: 14px;
                    font-weight: 600;
                    padding: 0px;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['primary']};
                    border-color: {COLORS['primary']};
                    color: {COLORS['background']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['surface_hover']};
                }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_preset_clicked(idx))
            # 6 buttons in 12 columns = 2 columns per button
            self.preset_grid.addWidget(btn, 0, i * 2, 1, 2)  # Each button spans 2 columns
            self._preset_buttons.append(btn)
    
    def _on_preset_clicked(self, index: int):
        """Handle preset button click - insert text into target field"""
        if index < len(self._preset_texts) and self._preset_texts[index]:
            text = self._preset_texts[index]
            # Send each character
            for char in text:
                self._send_key(char)
    
    def _build_keyboard(self):
        """Build keyboard layout with numbers above letters (Raspberry Pi style)"""
        # Clear existing buttons
        while self.keyboard_grid.count():
            child = self.keyboard_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Row 0: Hide button (left), Numbers, Backspace (right)
        self.close_btn = QPushButton("Hide")
        self.close_btn.setFixedSize(60, 60)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(self.hide_keyboard)
        # Lighter background for non-letter keys
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
        """)
        self.keyboard_grid.addWidget(self.close_btn, 0, 0)
        
        # Numbers row
        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        for col_offset, num in enumerate(numbers):
            btn = self._create_key_button(num)
            self.keyboard_grid.addWidget(btn, 0, col_offset + 1)
        
        # Backspace button (top right)
        backspace_btn = self._create_key_button("⌫")
        backspace_btn.setFixedSize(60, 60)
        self.keyboard_grid.addWidget(backspace_btn, 0, 11)
        
        # Row 1: Caps Lock, QWERTY top row + Enter button (2 rows tall)
        # Caps Lock button left of Q
        caps_btn = QPushButton("Caps")
        caps_btn.setFixedSize(60, 60)
        caps_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        caps_btn.clicked.connect(self._toggle_caps_lock)
        caps_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_hover']};
            }}
        """)
        self.keyboard_grid.addWidget(caps_btn, 1, 0)
        self._caps_lock_btn = caps_btn
        
        top_row = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']  # Lowercase by default
        for col_offset, key in enumerate(top_row):
            btn = self._create_key_button(key)
            self.keyboard_grid.addWidget(btn, 1, col_offset + 1)
            self._letter_buttons[key.lower()] = btn  # Store for case updates
        
        # Enter button (2 rows tall) next to P
        enter_btn = self._create_key_button("Enter")
        enter_btn.setFixedHeight(133)  # 2 rows tall (60 + 10 spacing + 60) + 3px extra
        self.keyboard_grid.addWidget(enter_btn, 1, 11, 2, 1)  # row 1, col 11, span 2 rows, 1 col
        
        # Row 2: Shift, QWERTY middle row + ":" button
        # Shift button left of A
        shift_btn = QPushButton("Shift")
        shift_btn.setFixedSize(60, 60)
        shift_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        shift_btn.clicked.connect(self._toggle_shift)
        shift_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_hover']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                color: {COLORS['background']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface_light']};
            }}
        """)
        self.keyboard_grid.addWidget(shift_btn, 2, 0)
        self._shift_btn = shift_btn
        
        middle_row = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l']  # Lowercase by default
        col_start = 1  # Start after Shift button
        for col_offset, key in enumerate(middle_row):
            btn = self._create_key_button(key)
            self.keyboard_grid.addWidget(btn, 2, col_start + col_offset)
            self._letter_buttons[key.lower()] = btn  # Store for case updates
        
        # ":" button next to L
        colon_btn = self._create_key_button(":")
        self.keyboard_grid.addWidget(colon_btn, 2, 10)
        
        # Row 3: "-" and "_" buttons, QWERTY bottom row, and punctuation buttons
        # "-" button left of Z
        dash_btn = self._create_key_button("-")
        self.keyboard_grid.addWidget(dash_btn, 3, 0)
        
        # "_" button next to "-"
        underscore_btn = self._create_key_button("_")
        self.keyboard_grid.addWidget(underscore_btn, 3, 1)
        
        bottom_row = ['z', 'x', 'c', 'v', 'b', 'n', 'm']  # Lowercase by default
        col_start = 2  # Start at col 2 (after - and _)
        for col_offset, key in enumerate(bottom_row):
            btn = self._create_key_button(key)
            self.keyboard_grid.addWidget(btn, 3, col_start + col_offset)
            self._letter_buttons[key.lower()] = btn  # Store for case updates
        
        # Punctuation buttons
        comma_btn = self._create_key_button(",")
        self.keyboard_grid.addWidget(comma_btn, 3, 9)
        
        period_btn = self._create_key_button(".")
        self.keyboard_grid.addWidget(period_btn, 3, 10)
        
        slash_btn = self._create_key_button("/")
        self.keyboard_grid.addWidget(slash_btn, 3, 11)
        
        # Row 4: Spacebar (centered)
        space_btn = self._create_key_button("Space", width_mult=6)
        self.keyboard_grid.addWidget(space_btn, 4, 3, 1, 6)  # Centered: start at col 3, span 6 cols
    
    def _create_key_button(self, text, width_mult=1):
        """Create a keyboard button"""
        btn = QPushButton(text)
        btn.setFixedHeight(60)  # Fixed height to prevent overlap
        btn.setFixedWidth(60)  # Fixed width for consistent sizing
        if width_mult > 1:
            # Multi-column button
            btn.setFixedWidth(60 * width_mult)
        
        if text == "Space":
            btn.setText(" ")
        elif text == "⌫":
            btn.setText("⌫")
        elif text == "Enter":
            btn.setText("↵")
        
        # Prevent button from stealing focus from text field
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda checked, t=text: self._on_key_clicked(t))
        return btn
    
    def _on_key_clicked(self, key):
        """Handle key button click"""
        if key == "Space":
            self._send_key(" ")
        elif key == "⌫":
            self._send_backspace()
        elif key == "Enter" or key == "↵":
            # Match "Hide" behavior: send Enter, then hide keyboard.
            self._send_key("\n")
            self.hide_keyboard()
        else:
            # Apply shift/caps lock to letters
            if key.isalpha():
                if self._shift_pressed or self._caps_lock:
                    key = key.upper()
                else:
                    key = key.lower()
                # Reset shift after use (not caps lock)
                if self._shift_pressed:
                    self._shift_pressed = False
                    self._update_shift_button_style()
            
            self._send_key(key)
    
    def _toggle_shift(self):
        """Toggle shift state"""
        self._shift_pressed = not self._shift_pressed
        self._update_shift_button_style()
        self._update_letter_button_labels()
    
    def _toggle_caps_lock(self):
        """Toggle caps lock state"""
        self._caps_lock = not self._caps_lock
        self._update_caps_lock_button_style()
        self._update_letter_button_labels()
    
    def _update_letter_button_labels(self):
        """Update letter button labels based on Shift/Caps Lock state"""
        should_uppercase = self._shift_pressed or self._caps_lock
        for letter, btn in self._letter_buttons.items():
            if should_uppercase:
                btn.setText(letter.upper())
            else:
                btn.setText(letter.lower())
    
    def _update_shift_button_style(self):
        """Update shift button visual state"""
        if hasattr(self, '_shift_btn'):
            if self._shift_pressed:
                self._shift_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['primary']};
                        border: 2px solid {COLORS['primary']};
                        border-radius: 8px;
                        color: {COLORS['background']};
                        font-size: 14px;
                        font-weight: 600;
                    }}
                """)
            else:
                self._shift_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['surface_light']};
                        border: 2px solid {COLORS['border']};
                        border-radius: 8px;
                        color: {COLORS['text']};
                        font-size: 14px;
                        font-weight: 600;
                    }}
                    QPushButton:pressed {{
                        background-color: {COLORS['primary']};
                        border-color: {COLORS['primary']};
                        color: {COLORS['background']};
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['surface_hover']};
                    }}
                """)
    
    def _update_caps_lock_button_style(self):
        """Update caps lock button visual state"""
        if hasattr(self, '_caps_lock_btn'):
            if self._caps_lock:
                self._caps_lock_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['primary']};
                        border: 2px solid {COLORS['primary']};
                        border-radius: 8px;
                        color: {COLORS['background']};
                        font-size: 14px;
                        font-weight: 600;
                    }}
                """)
            else:
                self._caps_lock_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['surface_light']};
                        border: 2px solid {COLORS['border']};
                        border-radius: 8px;
                        color: {COLORS['text']};
                        font-size: 14px;
                        font-weight: 600;
                    }}
                    QPushButton:pressed {{
                        background-color: {COLORS['primary']};
                        border-color: {COLORS['primary']};
                        color: {COLORS['background']};
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['surface_hover']};
                    }}
                """)
    
    def _send_key(self, key):
        """Send key to target widget"""
        if self._target_widget:
            # Special case: QWebEngineView (Companion). Qt key events are unreliable there,
            # so we inject text directly via JavaScript into the active HTML element.
            if hasattr(self._target_widget, "page") and callable(getattr(self._target_widget, "page", None)):
                try:
                    page = self._target_widget.page()
                    if page is not None and hasattr(page, "runJavaScript"):
                        # Send to OSK bridge (installed in all frames) via postMessage.
                        js_key = json.dumps(key)
                        msg = f"{{__panapiOsk:1, action:'insert', text:{js_key}}}"
                        js = f"""
                        (function() {{
                          var m = {msg};
                          try {{ window.postMessage(m, '*'); }} catch (e) {{}}
                          try {{
                            var frames = document.querySelectorAll('iframe');
                            for (var i = 0; i < frames.length; i++) {{
                              try {{
                                var f = frames[i];
                                if (f && f.contentWindow) f.contentWindow.postMessage(m, '*');
                              }} catch (e) {{}}
                            }}
                          }} catch (e) {{}}
                          return true;
                        }})();
                        """
                        page.runJavaScript(js)
                        self.key_pressed.emit(key)
                        return
                except Exception:
                    pass

            if key == "\n":
                # Send Enter key
                press_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
                release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
                QApplication.postEvent(self._target_widget, press_event)
                QApplication.postEvent(self._target_widget, release_event)
            else:
                # Send character key
                # Get key code from character
                key_code = ord(key.upper()) if len(key) == 1 else 0
                press_event = QKeyEvent(QKeyEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier, key)
                release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, key_code, Qt.KeyboardModifier.NoModifier, key)
                QApplication.postEvent(self._target_widget, press_event)
                QApplication.postEvent(self._target_widget, release_event)
            
            self.key_pressed.emit(key)

    def _send_key_events_to_webview(self, key: str):
        """Fallback for QtWebEngine: focus view and send key events."""
        w = self._target_widget
        if w is None:
            return
        try:
            # Ensure the web view keeps focus so it can route keys to the DOM.
            if hasattr(w, "setFocus"):
                w.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:
            pass

        if key == "\n":
            press_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
            release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
            QApplication.postEvent(w, press_event)
            QApplication.postEvent(w, release_event)
            return

        # Prefer text-based events for web engine
        try:
            press_event = QKeyEvent(QKeyEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, key)
            release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, key)
            QApplication.postEvent(w, press_event)
            QApplication.postEvent(w, release_event)
        except Exception:
            pass
    
    def _send_backspace(self):
        """Send backspace key"""
        if self._target_widget:
            # QWebEngineView (Companion): delete via JS for reliability.
            if hasattr(self._target_widget, "page") and callable(getattr(self._target_widget, "page", None)):
                try:
                    page = self._target_widget.page()
                    if page is not None and hasattr(page, "runJavaScript"):
                        msg = "{__panapiOsk:1, action:'backspace'}"
                        js = f"""
                        (function() {{
                          var m = {msg};
                          try {{ window.postMessage(m, '*'); }} catch (e) {{}}
                          try {{
                            var frames = document.querySelectorAll('iframe');
                            for (var i = 0; i < frames.length; i++) {{
                              try {{
                                var f = frames[i];
                                if (f && f.contentWindow) f.contentWindow.postMessage(m, '*');
                              }} catch (e) {{}}
                            }}
                          }} catch (e) {{}}
                          return true;
                        }})();
                        """
                        page.runJavaScript(js)
                        return
                except Exception:
                    pass

            press_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
            release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
            QApplication.postEvent(self._target_widget, press_event)
            QApplication.postEvent(self._target_widget, release_event)

    def _send_backspace_event_to_webview(self):
        w = self._target_widget
        if w is None:
            return
        try:
            if hasattr(w, "setFocus"):
                w.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:
            pass
        press_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        release_event = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        QApplication.postEvent(w, press_event)
        QApplication.postEvent(w, release_event)
    
    
    def _setup_animation(self):
        """Setup slide animation"""
        self._animation = QPropertyAnimation(self, b"pos")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def show_keyboard(self, target_widget=None):
        """Show keyboard"""
        # Skip if already visible for same widget
        if self._is_visible and self._target_widget == target_widget:
            return

        self._target_widget = target_widget
        self._is_visible = True

        # Docked mode: parent/layout controls geometry; just show and return.
        if self._docked:
            self.raise_()
            self.show()
            return

        # Position at bottom of parent
        parent = self.parent()
        if parent:
            keyboard_height = int(getattr(self, "_keyboard_height", self.DEFAULT_HEIGHT))
            parent_width = parent.width()
            parent_height = parent.height()
            
            if self.slide_from_top:
                # On Live page we want the OSK under the top nav (on top of preview).
                y_pos = int(getattr(self, "_top_offset_px", 0) or 0)
            else:
                y_pos = parent_height - keyboard_height
            
            self.setFixedSize(parent_width, keyboard_height)
            self.move(0, y_pos)

        self.raise_()
        self.show()

    def set_top_offset(self, px: int):
        """Set the Y offset used when slide_from_top=True."""
        try:
            self._top_offset_px = max(0, int(px))
        except Exception:
            self._top_offset_px = 0

    def set_docked(self, docked: bool, height: int = None):
        """Enable/disable docked mode (layout-managed sizing)."""
        self._docked = bool(docked)
        if height is not None:
            try:
                self._keyboard_height = max(1, int(height))
            except Exception:
                self._keyboard_height = self.DEFAULT_HEIGHT
        if self._docked:
            # Layout should size width; we fix height and remain opaque panel.
            self.setFixedHeight(int(getattr(self, "_keyboard_height", self.DEFAULT_HEIGHT)))
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            # Undocked: allow show_keyboard() to control geometry again.
            # Keep fixed height behavior from show_keyboard; don't force a size policy here.
            pass
    
    def hide_keyboard(self):
        """Hide keyboard immediately.

        Note: when docked (e.g. Companion page), we keep the widget visible and
        only clear the target/visible flag, because the keyboard is meant to be
        permanently present as a bottom panel.
        """
        if not self._is_visible and not self._docked:
            return

        self._is_visible = False
        self._target_widget = None
        if self._docked:
            # Keep showing the docked panel; just "detach" from any target.
            self.show()
            return
        self.hide()

    def focusOutEvent(self, event):
        """Hide OSK when it loses focus"""
        super().focusOutEvent(event)
        # Delay the hide slightly to allow focus to settle
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._check_hide_on_focus_loss)

    def _check_hide_on_focus_loss(self):
        """Check if OSK should hide after losing focus"""
        if not self._is_visible:
            return

        # Check if focus moved to a text field
        focused_widget = QApplication.focusWidget()
        if focused_widget and isinstance(focused_widget, QLineEdit):
            return  # Don't hide if focus moved to another text field

        # Hide OSK
        self.hide_keyboard()
    
    def _on_animation_finished(self):
        """Called when hide animation finishes"""
        self.hide()
        self._animation.finished.disconnect()
        self._target_widget = None










