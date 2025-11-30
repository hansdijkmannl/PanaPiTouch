"""
Virtual Joystick Widget for PTZ Control

A touch/mouse-friendly joystick for controlling pan and tilt.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QRadialGradient


class JoystickWidget(QWidget):
    """
    Virtual joystick widget for PTZ control.
    
    Emits position_changed signal with (x, y) values from -1.0 to 1.0.
    Emits released signal when joystick is released.
    """
    
    position_changed = pyqtSignal(float, float)  # x, y from -1.0 to 1.0
    released = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setMinimumSize(120, 120)
        self.setMaximumSize(160, 160)
        
        # Joystick position (0, 0 = center)
        self._position = QPointF(0, 0)
        self._pressed = False
        
        # Deadzone (no movement within this radius)
        self._deadzone = 0.15
        
        # Colors
        self._bg_color = QColor(30, 30, 30)
        self._ring_color = QColor(80, 80, 80)
        self._knob_color = QColor(0, 150, 255)
        self._knob_pressed_color = QColor(0, 200, 255)
        
        # Emit timer for continuous movement
        self._emit_timer = QTimer(self)
        self._emit_timer.timeout.connect(self._emit_position)
        self._emit_timer.setInterval(50)  # 20Hz update rate
    
    def paintEvent(self, event):
        """Draw the joystick"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate dimensions
        w = self.width()
        h = self.height()
        size = min(w, h)
        center_x = w / 2
        center_y = h / 2
        radius = size / 2 - 4
        
        # Draw background circle
        painter.setPen(QPen(self._ring_color, 2))
        painter.setBrush(QBrush(self._bg_color))
        painter.drawEllipse(
            int(center_x - radius), int(center_y - radius),
            int(radius * 2), int(radius * 2)
        )
        
        # Draw crosshairs
        painter.setPen(QPen(self._ring_color, 1))
        painter.drawLine(int(center_x), int(center_y - radius + 10),
                        int(center_x), int(center_y + radius - 10))
        painter.drawLine(int(center_x - radius + 10), int(center_y),
                        int(center_x + radius - 10), int(center_y))
        
        # Draw knob
        knob_radius = radius * 0.35
        knob_x = center_x + self._position.x() * (radius - knob_radius)
        knob_y = center_y + self._position.y() * (radius - knob_radius)
        
        # Gradient for 3D effect
        gradient = QRadialGradient(knob_x - knob_radius/3, knob_y - knob_radius/3, knob_radius * 1.5)
        knob_color = self._knob_pressed_color if self._pressed else self._knob_color
        gradient.setColorAt(0, knob_color.lighter(130))
        gradient.setColorAt(0.5, knob_color)
        gradient.setColorAt(1, knob_color.darker(130))
        
        painter.setPen(QPen(knob_color.darker(150), 2))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(
            int(knob_x - knob_radius), int(knob_y - knob_radius),
            int(knob_radius * 2), int(knob_radius * 2)
        )
    
    def mousePressEvent(self, event):
        """Handle mouse/touch press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._update_position(event.position())
            self._emit_timer.start()
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse/touch move"""
        if self._pressed:
            self._update_position(event.position())
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse/touch release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self._position = QPointF(0, 0)
            self._emit_timer.stop()
            self.released.emit()
            self.update()
    
    def _update_position(self, pos: QPointF):
        """Update knob position based on mouse position"""
        w = self.width()
        h = self.height()
        center_x = w / 2
        center_y = h / 2
        size = min(w, h)
        radius = size / 2 - 4
        
        # Calculate relative position
        dx = (pos.x() - center_x) / radius
        dy = (pos.y() - center_y) / radius
        
        # Clamp to circle
        distance = (dx * dx + dy * dy) ** 0.5
        if distance > 1.0:
            dx /= distance
            dy /= distance
        
        self._position = QPointF(dx, dy)
    
    def _emit_position(self):
        """Emit position signal (with deadzone)"""
        x = self._position.x()
        y = self._position.y()
        
        # Apply deadzone
        distance = (x * x + y * y) ** 0.5
        if distance < self._deadzone:
            return
        
        # Scale to full range outside deadzone
        scale = (distance - self._deadzone) / (1.0 - self._deadzone)
        if distance > 0:
            x = x / distance * scale
            y = y / distance * scale
        
        self.position_changed.emit(x, y)
    
    def get_position(self) -> tuple:
        """Get current joystick position"""
        return (self._position.x(), self._position.y())
    
    def is_active(self) -> bool:
        """Check if joystick is being pressed"""
        return self._pressed

