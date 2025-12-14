"""
Shared UI Widgets

Reusable widgets for touch-friendly interfaces.
"""
from PyQt6.QtWidgets import QScrollArea, QPushButton, QLineEdit, QComboBox, QLabel, QRadioButton
from PyQt6.QtCore import QEvent, Qt


class TouchScrollArea(QScrollArea):
    """Scroll area with touch scrolling support - drag anywhere to scroll, no visible scrollbars"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_touch_pos = None
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_threshold = 10  # Minimum pixels to move before scrolling starts
        
        # Enable touch events
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        
        # Hide scrollbars by default
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def _is_interactive_widget(self, widget):
        """Check if widget is interactive (button, input, etc.)"""
        if widget is None:
            return False
        # Check widget type and all parent widgets
        current = widget
        while current:
            if isinstance(current, (QPushButton, QRadioButton, QLineEdit, QComboBox, QLabel)):
                # Check if QLabel is clickable (has a link or is used as button)
                if isinstance(current, QLabel):
                    # Only consider it interactive if it has a link or specific object name
                    if current.openExternalLinks() or current.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
                        return True
                else:
                    return True
            current = current.parent()
        return False
    
    def event(self, event):
        """Handle touch and mouse events for scrolling"""
        # Handle touch events
        if event.type() == QEvent.Type.TouchBegin:
            try:
                touch_points = event.touchPoints()
                if touch_points and len(touch_points) > 0:
                    touch_point = touch_points[0]
                    pos = touch_point.pos()
                    self._last_touch_pos = pos
                    self._drag_start_pos = pos
                    self._is_dragging = False
                    # Don't accept here - let it propagate to child widgets first
            except Exception:
                pass
            return super().event(event)
        elif event.type() == QEvent.Type.TouchUpdate:
            try:
                touch_points = event.touchPoints()
                if self._last_touch_pos and touch_points and len(touch_points) > 0:
                    touch_point = touch_points[0]
                    current_pos = touch_point.pos()
                    delta = current_pos - self._last_touch_pos
                    
                    # Check if we've moved enough to start dragging
                    if self._drag_start_pos:
                        move_distance = (current_pos - self._drag_start_pos).manhattanLength()
                        if move_distance > self._drag_threshold:
                            self._is_dragging = True
                    
                    # Only scroll if dragging (not clicking on interactive widgets)
                    if self._is_dragging:
                        # Map to widget coordinates
                        widget_at_pos = self.widget().childAt(self.mapTo(self.widget(), current_pos)) if self.widget() else None
                        if not self._is_interactive_widget(widget_at_pos):
                            # Determine scroll direction based on movement
                            abs_delta_x = abs(delta.x())
                            abs_delta_y = abs(delta.y())
                            
                            # Scroll in the dominant direction
                            if abs_delta_y > abs_delta_x:
                                # Vertical scrolling (most common)
                                v_scrollbar = self.verticalScrollBar()
                                if v_scrollbar:
                                    new_value = v_scrollbar.value() - int(delta.y())
                                    v_scrollbar.setValue(new_value)
                                    event.accept()
                                    self._last_touch_pos = current_pos
                                    return True
                            elif abs_delta_x > abs_delta_y:
                                # Horizontal scrolling
                                h_scrollbar = self.horizontalScrollBar()
                                if h_scrollbar:
                                    new_value = h_scrollbar.value() - int(delta.x())
                                    h_scrollbar.setValue(new_value)
                                    event.accept()
                                    self._last_touch_pos = current_pos
                                    return True
            except Exception:
                pass
            return super().event(event)
        elif event.type() == QEvent.Type.TouchEnd:
            self._last_touch_pos = None
            self._drag_start_pos = None
            self._is_dragging = False
            return super().event(event)
        
        # Handle mouse drag events for touch scrolling (for mouse/trackpad)
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                try:
                    pos = event.pos()
                    self._last_touch_pos = pos
                    self._drag_start_pos = pos
                    self._is_dragging = False
                except Exception:
                    pass
        elif event.type() == QEvent.Type.MouseMove:
            if self._last_touch_pos and event.buttons() & Qt.MouseButton.LeftButton:
                try:
                    current_pos = event.pos()
                    
                    # Check if we've moved enough to start dragging
                    if self._drag_start_pos:
                        move_distance = (current_pos - self._drag_start_pos).manhattanLength()
                        if move_distance > self._drag_threshold:
                            self._is_dragging = True
                    
                    # Only scroll if dragging (not clicking on interactive widgets)
                    if self._is_dragging:
                        widget_at_pos = self.widget().childAt(self.mapTo(self.widget(), current_pos)) if self.widget() else None
                        if not self._is_interactive_widget(widget_at_pos):
                            delta = current_pos - self._last_touch_pos
                            
                            # Determine scroll direction based on movement
                            abs_delta_x = abs(delta.x())
                            abs_delta_y = abs(delta.y())
                            
                            # Scroll in the dominant direction
                            if abs_delta_y > abs_delta_x:
                                # Vertical scrolling (most common)
                                v_scrollbar = self.verticalScrollBar()
                                if v_scrollbar:
                                    new_value = v_scrollbar.value() - int(delta.y())
                                    v_scrollbar.setValue(new_value)
                                    self._last_touch_pos = current_pos
                                    return True
                            elif abs_delta_x > abs_delta_y:
                                # Horizontal scrolling
                                h_scrollbar = self.horizontalScrollBar()
                                if h_scrollbar:
                                    new_value = h_scrollbar.value() - int(delta.x())
                                    h_scrollbar.setValue(new_value)
                                    self._last_touch_pos = current_pos
                                    return True
                except Exception:
                    pass
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self._last_touch_pos = None
                self._drag_start_pos = None
                self._is_dragging = False
        
        return super().event(event)







