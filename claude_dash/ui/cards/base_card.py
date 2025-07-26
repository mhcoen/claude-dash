"""
Base card class for modular provider cards
"""
from abc import abstractmethod
from typing import Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QFont, QCursor, QDesktopServices, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import QUrl
from ..theme_manager import ThemeManager


class KeyIndicator(QLabel):
    """Small widget to show active key count with colored circle"""
    
    def __init__(self):
        super().__init__()
        self.total_keys = 0
        self.active_keys = 0
        self.setFixedSize(16, 16)
        
    def set_key_status(self, active: int, total: int):
        """Update the key status"""
        self.active_keys = active
        self.total_keys = total
        if total > 1:
            self.setVisible(True)
            self.update()
        else:
            self.setVisible(False)
            
    def paintEvent(self, event):
        """Paint the colored circle with number"""
        if self.total_keys <= 1:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine color based on status
        if self.active_keys == self.total_keys:
            color = QColor("#4CAF50")  # Green
        elif self.active_keys > 1:
            color = QColor("#FF9800")  # Orange
        elif self.active_keys == 1:
            color = QColor("#F44336")  # Red
        else:
            color = QColor("#9E9E9E")  # Gray
            
        # Draw circle
        painter.setPen(QPen(color.darker(120), 1))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(1, 1, 14, 14)
        
        # Draw text
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.active_keys))


class BaseProviderCard(QFrame):
    """Abstract base class for all provider cards"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, provider_name: str, display_name: str, color: str, size: Tuple[int, int] = (220, 210), show_status: bool = True, scale_factor: float = 1.0):
        super().__init__()
        self.provider_name = provider_name
        self.display_name = display_name
        self.color = color
        self.scale_factor = scale_factor
        # Scale the size
        base_width, base_height = size
        self.width = int(base_width * scale_factor)
        self.height = int(base_height * scale_factor)
        self.show_status = show_status
        # Scale font sizes
        self.base_font_sizes = {
            'title': int(15 * scale_factor),
            'primary': int(24 * scale_factor),
            'secondary': int(13 * scale_factor),
            'small': int(11 * scale_factor),
            'value': int(14 * scale_factor)  # For value displays (1pt smaller than title)
        }
        # Billing URL - to be set by subclasses
        self.billing_url = None
        # Update interval in milliseconds - to be set by subclasses
        self.update_interval = 300000  # Default 5 minutes
        # Whether this card should auto-update
        self.auto_update = True
        # Multi-key support
        self.total_keys = 0
        self.active_keys = 0
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the basic card UI"""
        self.setFixedSize(self.width, self.height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Apply colored border styling
        theme_manager = ThemeManager()
        self.setStyleSheet(theme_manager.get_card_style(self.provider_name))
        
        # Create main layout
        self.layout = QVBoxLayout()
        margin = int(2 * self.scale_factor)
        self.layout.setContentsMargins(margin, margin, margin, margin)  # Very tight margins
        self.layout.setSpacing(0)
        
        # Add title with horizontal layout for key indicator
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        self.title_label = QLabel(self.display_name)
        font = QFont()
        font.setFamily(QFont().defaultFamily())  # Explicitly set font family
        font.setPointSize(self.base_font_sizes['title'])
        font.setBold(True)
        self.title_label.setFont(font)
        title_layout.addWidget(self.title_label)
        
        # Key indicator widget
        self.key_indicator = KeyIndicator()
        self.key_indicator.setVisible(False)  # Hidden by default
        title_layout.addWidget(self.key_indicator)
        
        title_layout.addStretch()
        self.layout.addLayout(title_layout)
        
        # Let subclasses add their content
        self.setup_content()
        
        # Add status label at bottom if enabled
        if self.show_status:
            # Small spacing before status to ensure consistent positioning
            self.layout.addSpacing(8)
            self.status_label = QLabel("Checking...")
            self.status_label.setStyleSheet(f"color: gray; font-size: {self.base_font_sizes['small']}px;")
            self.layout.addWidget(self.status_label)
        else:
            self.status_label = None
            
        # Add stretch at the very end to push everything up
        self.layout.addStretch()
        
        self.setLayout(self.layout)
        
    @abstractmethod
    def setup_content(self):
        """Subclasses must implement this to add their specific content"""
        pass
        
    def enable_billing_link(self):
        """Enable clickable title if billing URL is set"""
        self.billing_enabled = True
        if self.billing_url and self.title_label:
            self.title_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.title_label.setToolTip(f"Click to open {self.display_name} billing page")
            self.title_label.setMouseTracking(True)
            self.title_label.installEventFilter(self)
            # Add hover effect styling
            self.title_label.setStyleSheet("""
                QLabel:hover {
                    text-decoration: underline;
                }
            """)
        
    @abstractmethod
    def update_display(self, data: Dict[str, Any]):
        """Update the card display with new data"""
        pass
        
        
    def update_status(self, status: str, status_type: str = "normal", use_html: bool = False):
        """Update the status label"""
        if not self.status_label:
            return
            
        if use_html:
            self.status_label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setText(status)
        
        # Get theme manager for secondary text color
        theme_manager = ThemeManager()
        
        # Update status color based on type
        if status_type == "active":
            self.status_label.setStyleSheet(f"color: #28a745; font-size: {self.base_font_sizes['small']}px;")
        elif status_type == "warning":
            self.status_label.setStyleSheet(f"color: #ff6b35; font-size: {self.base_font_sizes['small']}px; font-weight: bold;")
        elif status_type == "error":
            self.status_label.setStyleSheet(f"color: #dc3545; font-size: {self.base_font_sizes['small']}px;")
        elif status_type == "italic":
            self.status_label.setStyleSheet(theme_manager.get_secondary_text_style(self.base_font_sizes['small'] - 2) + "; font-style: italic;")
        else:
            self.status_label.setStyleSheet(theme_manager.get_secondary_text_style(self.base_font_sizes['small']))
            
    def update_key_status(self, active_keys: int, total_keys: int):
        """Update the key indicator"""
        self.key_indicator.set_key_status(active_keys, total_keys)
    
    def create_compact_header(self, provider_name: str = None) -> QHBoxLayout:
        """Create a compact header layout with provider name and value display"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        # Provider name (use title font, smaller for half-height cards)
        provider_label = QLabel(f"{provider_name or self.display_name}:")
        font = QFont()
        font.setFamily(QFont().defaultFamily())  # Explicitly set font family
        # Use smaller font for half-height cards if desired
        is_half_height = self.height < 150
        title_size = self.base_font_sizes['title'] - 1 if is_half_height else self.base_font_sizes['title']
        font.setPointSize(title_size)
        font.setBold(True)
        provider_label.setFont(font)
        header_layout.addWidget(provider_label)
        
        # Store provider label for font scaling
        self.provider_label = provider_label
        # Also store as title_label for click handling
        self.title_label = provider_label
        
        # Add stretch to push value to the right
        header_layout.addStretch()
        
        # Value label (will be set by subclass)
        self.header_value_label = QLabel("")
        value_font = QFont()
        value_font.setFamily(QFont().defaultFamily())  # Explicitly set font family
        # Also scale value font for half-height cards
        value_size = self.base_font_sizes['value'] - 1 if is_half_height else self.base_font_sizes['value']
        value_font.setPointSize(value_size)
        self.header_value_label.setFont(value_font)
        header_layout.addWidget(self.header_value_label)
        
        # Key indicator (after value, with small spacing)
        header_layout.addSpacing(4)
        header_layout.addWidget(self.key_indicator)
        self.key_indicator.setVisible(False)  # Hidden by default
        
        return header_layout
            
    def eventFilter(self, source, event):
        """Handle events for child widgets"""
        if source == self.title_label and self.billing_url:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Open billing URL
                    QDesktopServices.openUrl(QUrl(self.billing_url))
                    return True
            elif event.type() == event.Type.Enter:
                # Add underline on hover
                font = self.title_label.font()
                font.setUnderline(True)
                self.title_label.setFont(font)
                return True
            elif event.type() == event.Type.Leave:
                # Remove underline
                font = self.title_label.font()
                font.setUnderline(False)
                self.title_label.setFont(font)
                return True
        return super().eventFilter(source, event)
    
    def mousePressEvent(self, event):
        """Handle mouse clicks"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is on the title label and billing is enabled
            if hasattr(self, 'title_label') and hasattr(self, 'billing_enabled') and self.billing_enabled:
                title_pos = self.title_label.mapTo(self, QPoint(0, 0))
                title_rect = QRect(title_pos, self.title_label.size())
                if title_rect.contains(event.pos()):
                    self.clicked.emit(self.provider_name)
            
    def scale_fonts(self, scale: float):
        """Scale all fonts in the card"""
        # Scale title
        font = QFont()
        font.setPointSize(int(self.base_font_sizes['title'] * scale))
        font.setBold(True)
        self.title_label.setFont(font)
        
        # Scale status (preserve color and style)
        if self.status_label:
            current_style = self.status_label.styleSheet()
            size = int(self.base_font_sizes['small'] * scale)
            theme_manager = ThemeManager()
            if "color: #28a745" in current_style:  # Active
                self.status_label.setStyleSheet(f"color: #28a745; font-size: {size}px;")
            elif "color: #ff6b35" in current_style:  # Warning
                self.status_label.setStyleSheet(f"color: #ff6b35; font-size: {size}px; font-weight: bold;")
            elif "color: #dc3545" in current_style:  # Error
                self.status_label.setStyleSheet(f"color: #dc3545; font-size: {size}px;")
            elif "font-style: italic" in current_style:  # Italic (1pt smaller)
                self.status_label.setStyleSheet(theme_manager.get_secondary_text_style(size - 1) + "; font-style: italic;")
            else:  # Normal
                self.status_label.setStyleSheet(theme_manager.get_secondary_text_style(size))
            
        # Let subclasses scale their content
        self.scale_content_fonts(scale)
        
    def scale_content_fonts(self, scale: float):
        """Subclasses can override this to scale their specific content"""
        pass
        
    def fetch_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data for this provider. Override in subclasses that fetch their own data."""
        return None
        
    def update_theme(self):
        """Update the card when theme changes"""
        # Apply updated colored border styling
        theme_manager = ThemeManager()
        self.setStyleSheet(theme_manager.get_card_style(self.provider_name))
        
        # Update status label color if it exists
        if self.status_label:
            # Preserve the current status type
            current_style = self.status_label.styleSheet()
            if "color: #28a745" in current_style:  # Active
                self.update_status(self.status_label.text(), "active")
            elif "color: #ff6b35" in current_style:  # Warning
                self.update_status(self.status_label.text(), "warning")
            elif "color: #dc3545" in current_style:  # Error
                self.update_status(self.status_label.text(), "error")
            elif "font-style: italic" in current_style:  # Italic
                self.update_status(self.status_label.text(), "italic")
            else:  # Normal
                self.update_status(self.status_label.text(), "normal")