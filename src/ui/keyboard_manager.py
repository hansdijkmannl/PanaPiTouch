"""
Keyboard Manager

Manages on-screen keyboard display for text inputs.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QEvent
from .keyboard_widget import KeyboardWidget, NumpadWidget
from .styles import COLORS


class KeyboardManager(QObject):
    """Manages on-screen keyboard for the application"""
    
    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.current_input = None
        self.keyboard_widget = None
        self.numpad_widget = None
        self.keyboard_container = None
        self.line_edits = []
        self._parent_widget_for_positioning = None
        
        # Install event filter on parent to catch focus events
        parent_widget.installEventFilter(self)
        
        # Find all QLineEdit widgets and install event filters
        self._find_line_edits(parent_widget)
    
    def _find_line_edits(self, widget):
        """Recursively find all QLineEdit widgets and install event filters"""
        from PyQt6.QtWidgets import QLineEdit
        
        for child in widget.findChildren(QLineEdit):
            if child not in self.line_edits:
                child.installEventFilter(self)
                self.line_edits.append(child)
    
    def setup_keyboard_overlay(self, parent_widget):
        """Setup keyboard overlay as floating widget on top of content"""
        # Create container for keyboard (initially hidden) - dark theme, positioned absolutely
        self.keyboard_container = QWidget(parent_widget)
        self.keyboard_container.setVisible(False)
        self.keyboard_container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        
        # Set as floating overlay (not in layout)
        self.keyboard_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        keyboard_layout = QVBoxLayout(self.keyboard_container)
        keyboard_layout.setContentsMargins(20, 12, 20, 12)
        keyboard_layout.setSpacing(12)
        
        # Preview section - shows the focused input value (centered)
        preview_container = QWidget()
        preview_container.setStyleSheet("background: transparent;")
        preview_wrapper = QHBoxLayout(preview_container)
        preview_wrapper.setContentsMargins(0, 0, 0, 0)
        preview_wrapper.setSpacing(12)
        preview_wrapper.addStretch()
        
        # Field name label (outside the text field)
        self.field_name_label = QLabel()
        self.field_name_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text']};
                font-size: 16px;
                font-weight: 600;
                padding: 0px;
            }}
        """)
        self.field_name_label.setVisible(False)
        preview_wrapper.addWidget(self.field_name_label)
        
        # Preview text field - shows only the value (centered, fixed width)
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
        self.preview_field.setVisible(False)
        preview_wrapper.addWidget(self.preview_field)
        preview_wrapper.addStretch()
        
        preview_container.setVisible(False)
        self.preview_container = preview_container
        keyboard_layout.addWidget(preview_container)
        
        # Create keyboard widgets
        self.keyboard_widget = KeyboardWidget()
        self.numpad_widget = NumpadWidget()
        
        # Connect signals
        self._connect_keyboard_signals(self.keyboard_widget)
        self._connect_keyboard_signals(self.numpad_widget)
        
        # Initially show keyboard (will be switched based on input type)
        keyboard_layout.addWidget(self.keyboard_widget)
        keyboard_layout.addWidget(self.numpad_widget)
        self.numpad_widget.setVisible(False)
        
        # Re-find line edits after pages are created
        QTimer.singleShot(100, lambda: self._find_line_edits(self.parent_widget))
        
        # Store parent for positioning and install resize event filter
        self._parent_widget_for_positioning = parent_widget
        parent_widget.installEventFilter(self)
    
    def _connect_keyboard_signals(self, keyboard):
        """Connect keyboard signals"""
        keyboard.key_pressed.connect(self._on_key_pressed)
        keyboard.backspace_pressed.connect(self._on_backspace)
        keyboard.enter_pressed.connect(self._on_enter)
        keyboard.close_pressed.connect(self._hide_keyboard)
        
        if hasattr(keyboard, 'space_pressed'):
            keyboard.space_pressed.connect(self._on_space)
    
    def eventFilter(self, obj, event):
        """Filter events to detect QLineEdit focus and parent resize"""
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.FocusIn:
            if isinstance(obj, QLineEdit):
                self._show_keyboard(obj)
        elif event.type() == QEvent.Type.FocusOut:
            if isinstance(obj, QLineEdit):
                # Don't hide immediately - wait a bit in case focus moves to keyboard
                pass
        elif event.type() == QEvent.Type.Resize:
            # Reposition keyboard when parent resizes
            if obj == self._parent_widget_for_positioning and self.keyboard_container and self.keyboard_container.isVisible():
                QTimer.singleShot(10, self._position_keyboard)
        
        return super().eventFilter(obj, event)
    
    def _show_keyboard(self, line_edit):
        """Show appropriate keyboard for the input"""
        self.current_input = line_edit
        
        # Show and update preview section
        self.preview_container.setVisible(True)
        self.field_name_label.setVisible(True)
        self.preview_field.setVisible(True)
        
        # Find the label for this input field - improved detection
        field_name = "Input"
        parent = line_edit.parent()
        
        # Try multiple strategies to find the associated label
        if parent:
            # Strategy 1: Check if parent or grandparent has a GridLayout - find label in same row
            from PyQt6.QtWidgets import QGridLayout
            grid = None
            check_parent = parent
            # Check parent and grandparent for GridLayout
            for _ in range(2):
                if check_parent and check_parent.layout():
                    layout = check_parent.layout()
                    if isinstance(layout, QGridLayout):
                        grid = layout
                        break
                if check_parent:
                    check_parent = check_parent.parent()
            
            if grid:
                # Find which row/col our input is in
                for row in range(grid.rowCount()):
                    for col in range(grid.columnCount()):
                        item = grid.itemAtPosition(row, col)
                        if item and item.widget() == line_edit:
                            # Found our input at row, col
                            # Label is typically at (row, 0) or (row, col-1)
                            for check_col in [0, col-1]:
                                if check_col >= 0:
                                    label_item = grid.itemAtPosition(row, check_col)
                                    if label_item and label_item.widget():
                                        widget = label_item.widget()
                                        if isinstance(widget, QLabel):
                                            label_text = widget.text().strip()
                                            if label_text and ':' in label_text:
                                                field_name = label_text.replace(':', '').strip()
                                                break
                            if field_name != "Input":
                                break
                    if field_name != "Input":
                        break
            
            # Strategy 2: For VBoxLayout structures (like in camera page), find the label above the input
            # The input may be in a nested layout, so we need to check parent layouts too
            if field_name == "Input":
                from PyQt6.QtWidgets import QVBoxLayout, QLayout
                
                def find_label_in_layout(layout, target_widget, depth=0):
                    """Recursively search layouts to find the label for the target widget"""
                    if not layout or depth > 5:
                        return None
                    
                    # Check if this layout directly contains the target widget or a layout containing it
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item:
                            # Check if this item is the target widget
                            if item.widget() == target_widget:
                                # Found the layout containing our input - look for label before it in SAME layout
                                for j in range(i-1, max(-1, i-3), -1):  # Check up to 2 items before
                                    prev_item = layout.itemAt(j)
                                    if prev_item:
                                        widget = prev_item.widget()
                                        if widget and isinstance(widget, QLabel):
                                            label_text = widget.text().strip()
                                            if label_text and ':' in label_text:
                                                return label_text.replace(':', '').strip()
                                return None  # Input found but no label
                            
                            # Check if this item is a layout that contains the target widget
                            elif item.layout():
                                # Check if the nested layout contains our widget
                                nested_result = find_label_in_layout(item.layout(), target_widget, depth + 1)
                                if nested_result:
                                    return nested_result
                                # If the nested layout contains our widget but didn't find a label,
                                # look for label before this layout item
                                if layout_contains_widget(item.layout(), target_widget):
                                    for j in range(i-1, max(-1, i-3), -1):
                                        prev_item = layout.itemAt(j)
                                        if prev_item:
                                            widget = prev_item.widget()
                                            if widget and isinstance(widget, QLabel):
                                                label_text = widget.text().strip()
                                                if label_text and ':' in label_text:
                                                    return label_text.replace(':', '').strip()
                    return None
                
                def layout_contains_widget(layout, target_widget):
                    """Check if a layout contains a widget (directly or nested)"""
                    if not layout:
                        return False
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item:
                            if item.widget() == target_widget:
                                return True
                            elif item.layout():
                                if layout_contains_widget(item.layout(), target_widget):
                                    return True
                    return False
                
                # Start searching from parent's layout
                parent_layout = parent.layout()
                if parent_layout:
                    result = find_label_in_layout(parent_layout, line_edit)
                    if result:
                        field_name = result
            
            # Strategy 3: Look for labels in the same parent (fallback)
            # Only use this if VBoxLayout strategy didn't work
            if field_name == "Input":
                all_labels = parent.findChildren(QLabel)
                # Prefer labels that are closer to our input (but this is less reliable)
                for label in all_labels:
                    label_text = label.text().strip()
                    # Check if this label is likely associated with our input
                    if ':' in label_text:
                        label_text_clean = label_text.replace(':', '').strip().lower()
                        # Check if it's a field name label (not just any label)
                        if any(keyword in label_text_clean for keyword in [
                            'ip', 'address', 'subnet', 'gateway', 'username', 'password', 
                            'name', 'camera', 'number', 'atem', 'port', 'host', 'mask'
                        ]):
                            field_name = label_text.replace(':', '').strip()
                            # For settings page, prefer more specific matches
                            # If we found a label, check if there's a better match
                            if 'subnet' in label_text_clean or 'gateway' in label_text_clean:
                                break  # These are specific enough
                            # Continue looking for a better match
            
            # Strategy 4: If no label found, try to get from object name
            if field_name == "Input":
                obj_name = line_edit.objectName()
                if obj_name:
                    # Convert object name to readable name
                    obj_name_clean = obj_name.replace('_', ' ').replace('input', '').strip()
                    if obj_name_clean:
                        field_name = obj_name_clean.title()
        
        # Store field name and update label
        self._current_field_name = field_name
        self.field_name_label.setText(f"{field_name}:")
        
        # Connect to input field's textChanged signal to sync preview
        try:
            line_edit.textChanged.disconnect(self._update_preview)
        except:
            pass
        line_edit.textChanged.connect(self._update_preview)
        
        # Determine if we need numpad (for IP addresses, numbers, camera numbers) or full keyboard
        placeholder = line_edit.placeholderText().lower()
        object_name = line_edit.objectName().lower()
        field_name_lower = field_name.lower()
        
        # Improved detection: Check field name more carefully
        is_numeric = False
        
        # Check field name first (most reliable)
        if any(keyword in field_name_lower for keyword in [
            'ip address', 'ip', 'address', 'subnet', 'gateway', 'port', 
            'atem input', 'camera number', 'number'
        ]):
            # But exclude text fields that might contain these words
            if not any(keyword in field_name_lower for keyword in ['username', 'password', 'name']):
                is_numeric = True
        
        # Also check placeholder and object name
        if not is_numeric:
            is_numeric = (
                any(keyword in placeholder for keyword in ['ip', 'address', 'subnet', 'gateway', 'port', '192.168', '255.255']) or
                any(keyword in object_name for keyword in ['ip', 'port', 'subnet', 'gateway', 'number', 'atem'])
            )
        
        if is_numeric:
            self.keyboard_widget.setVisible(False)
            self.numpad_widget.setVisible(True)
        else:
            self.keyboard_widget.setVisible(True)
            self.numpad_widget.setVisible(False)
        
        # Update preview with current value - ensure reliable updates
        def update_preview_immediate():
            if self.current_input == line_edit:  # Make sure we're still on the same field
                current_text = line_edit.text() if line_edit.text() else ""
                self._update_preview(current_text)
        
        def update_preview_delayed():
            if self.current_input == line_edit:  # Make sure we're still on the same field
                current_text = line_edit.text() if line_edit.text() else ""
                self._update_preview(current_text)
        
        # Immediate update
        update_preview_immediate()
        
        # Also schedule delayed updates to catch any async changes
        QTimer.singleShot(10, update_preview_delayed)
        QTimer.singleShot(100, update_preview_delayed)
        
        self.keyboard_container.setVisible(True)
        self._position_keyboard()
    
    def _update_preview(self, text=None):
        """Update preview field when input text changes"""
        if self.current_input and self.preview_field.isVisible():
            # Get current text from input if not provided
            if text is None:
                text = self.current_input.text() if self.current_input.text() else ""
            
            # Show only the value in the preview field (field name is in separate label)
            self.preview_field.setText(text)
            # Sync cursor position
            try:
                cursor_pos = self.current_input.cursorPosition()
                self.preview_field.setCursorPosition(cursor_pos)
            except:
                pass
    
    def _hide_keyboard(self):
        """Hide the keyboard"""
        self.keyboard_container.setVisible(False)
        self.preview_container.setVisible(False)
        self.field_name_label.setVisible(False)
        self.preview_field.setVisible(False)
        if self.current_input:
            # Disconnect textChanged signal
            try:
                self.current_input.textChanged.disconnect(self._update_preview)
            except:
                pass
            self.current_input.clearFocus()
            self.current_input = None
            self._current_field_name = None
    
    def _on_key_pressed(self, char):
        """Handle key press"""
        if self.current_input:
            # Apply shift if active (for keyboard widget)
            if self.keyboard_widget.isVisible() and hasattr(self.keyboard_widget, '_shift_active') and self.keyboard_widget._shift_active:
                char = char.upper()
                # Turn off shift after key press
                self.keyboard_widget._shift_active = False
                # Update shift button
                for btn in self.keyboard_widget.findChildren(QPushButton):
                    if btn.text() == "⇧":
                        btn.setChecked(False)
            
            # Get current cursor position
            cursor_pos = self.current_input.cursorPosition()
            current_text = self.current_input.text()
            
            # Insert character at cursor position
            new_text = current_text[:cursor_pos] + char + current_text[cursor_pos:]
            self.current_input.setText(new_text)
            
            # Move cursor forward
            self.current_input.setCursorPosition(cursor_pos + 1)
            
            # Preview field will update via textChanged signal
    
    def _on_backspace(self):
        """Handle backspace"""
        if self.current_input:
            cursor_pos = self.current_input.cursorPosition()
            if cursor_pos > 0:
                current_text = self.current_input.text()
                new_text = current_text[:cursor_pos-1] + current_text[cursor_pos:]
                self.current_input.setText(new_text)
                self.current_input.setCursorPosition(cursor_pos - 1)
                
                # Preview field will update via textChanged signal
    
    def _on_space(self):
        """Handle space"""
        if self.current_input:
            self._on_key_pressed(' ')
    
    def _on_enter(self):
        """Handle enter - hide keyboard"""
        self._hide_keyboard()
    
    def _position_keyboard(self):
        """Position keyboard overlay at bottom of parent widget"""
        if not self.keyboard_container or not self.keyboard_container.isVisible() or not self._parent_widget_for_positioning:
            return
        
        # Get parent widget geometry
        parent_rect = self._parent_widget_for_positioning.geometry()
        
        # Set width first, then let it calculate height
        width = parent_rect.width()
        self.keyboard_container.setFixedWidth(width)
        
        # Calculate keyboard height - use sizeHint or a reasonable default
        self.keyboard_container.adjustSize()
        keyboard_height = self.keyboard_container.sizeHint().height()
        
        # If height is still 0 or too small, use a reasonable default
        if keyboard_height < 200:
            keyboard_height = 350
        
        # Position at bottom
        x = 0
        y = parent_rect.height() - keyboard_height
        
        self.keyboard_container.setGeometry(x, y, width, keyboard_height)
        self.keyboard_container.raise_()  # Bring to front
        self.keyboard_container.update()  # Force update

