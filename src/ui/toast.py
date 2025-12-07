"""
Toast Notification Widget

Displays temporary error/success messages at the top of the screen.
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath


class ToastWidget(QWidget):
    """Toast notification widget that slides in from top"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._opacity = 1.0
        self._y_offset = -100  # Start above screen
        
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(40, 40, 50, 240);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 0)
        layout.addWidget(self.label)
        
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._hide)
        
        self.animation = QPropertyAnimation(self, b"y_offset")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def show_message(self, message: str, duration: int = 3000, error: bool = False):
        """
        Show a toast message.
        
        Args:
            message: Message text
            duration: Display duration in milliseconds
            error: If True, use error styling (red background)
        """
        self.label.setText(message)
        
        if error:
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(200, 50, 50, 240);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
        else:
            self.label.setStyleSheet("""
                QLabel {
                    background-color: rgba(40, 40, 50, 240);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
        
        # Position at top center of parent
        if self.parent():
            parent_rect = self.parent().geometry()
            self.setFixedWidth(min(400, parent_rect.width() - 40))
            self.adjustSize()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            self.move(x, parent_rect.y() + 20)
        
        # Animate in
        self._y_offset = -100
        self.show()
        self.raise_()
        
        self.animation.setStartValue(-100)
        self.animation.setEndValue(0)
        self.animation.start()
        
        # Auto-hide after duration
        self.hide_timer.start(duration)
    
    def _hide(self):
        """Animate out and hide"""
        self.animation.setStartValue(0)
        self.animation.setEndValue(-100)
        self.animation.finished.connect(self.hide)
        self.animation.start()
    
    def get_y_offset(self) -> int:
        """Get Y offset for animation"""
        return self._y_offset
    
    def set_y_offset(self, value: int):
        """Set Y offset for animation"""
        self._y_offset = value
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            self.move(x, parent_rect.y() + 20 + value)
    
    y_offset = pyqtProperty(int, get_y_offset, set_y_offset)




