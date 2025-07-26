"""
Claude Dash - Simplified version focused on session tracking only
"""
import sys
import json
import os
import logging
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QRect, QPoint
from PyQt6.QtGui import QKeySequence, QShortcut, QPainter, QColor, QFont, QBrush, QPen, QMouseEvent

from .providers.claude_code_reader import ClaudeCodeReader
from .core.config_loader import get_config
from .ui.cards.claude_code_card import ClaudeCodeCard
from .ui.theme_manager import ThemeManager
from .__version__ import __version__

# Parse command line arguments first
parser = argparse.ArgumentParser(description="Claude Dash - Know exactly when your Claude Code session will run out")
parser.add_argument('--version', action='version', version=f'claude-dash {__version__}')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
parser.add_argument('--log-file', type=str, help='Write logs to specified file')
parser.add_argument('--quiet', action='store_true', help='Suppress console output')
args = parser.parse_args()

# Set up logging based on arguments
log_handlers = []
if args.log_file:
    log_handlers.append(logging.FileHandler(args.log_file, mode='w'))
elif args.debug:
    log_handlers.append(logging.FileHandler('/tmp/claude-dash-debug.log', mode='w'))

if not args.quiet:
    log_handlers.append(logging.StreamHandler())

if log_handlers:
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=log_handlers
    )
else:
    # No handlers means no logging
    logging.basicConfig(level=logging.CRITICAL + 1)

logger = logging.getLogger(__name__)

# Enable DEBUG for the provider if debug mode is on
if args.debug:
    logging.getLogger('claude_dash.providers.claude_code_reader').setLevel(logging.DEBUG)


class DataUpdateWorker(QThread):
    """Worker thread for fetching Claude data"""
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.reader = None  # Will be created in the worker thread
        self.running = True
        # Get update frequency from config
        config = get_config()
        self.update_frequency = config.get_ui_config().get('update_frequency_seconds', 30)
        self.historical_maximums = None
        self.last_historical_update = None
        
    def run(self):
        """Run the data fetching loop"""
        # Create the reader in the worker thread to avoid race conditions
        self.reader = ClaudeCodeReader()
        
        while self.running:
            try:
                data = self.fetch_claude_data()
                if data:
                    self.data_ready.emit(data)
            except Exception as e:
                logger.error(f"Error fetching Claude data: {e}")
                self.error_occurred.emit(str(e))
            
            # Wait for configured update frequency before next update
            for _ in range(self.update_frequency):
                if not self.running:
                    break
                self.sleep(1)
    
    def fetch_claude_data(self) -> Dict[str, Any]:
        """Fetch Claude usage data"""
        # Get session info
        session_info = self.reader.get_current_session_info()
        session_start = session_info['start_time']
        
        # Get current window tokens
        window_tokens = self.reader.get_5hour_window_tokens()
        
        # Calculate hourly burn rate
        hourly_burn_rate = self.reader.calculate_hourly_burn_rate()
        
        # Get prompt info for current session
        prompt_info = self.reader.get_current_session_prompts()
        
        # Get prompt bounds for the user's plan
        config = get_config()
        plan_name = config.get_subscription_plan()
        prompt_bounds = self.reader.get_prompt_bounds(
            plan_name, 
            prompt_info['prompts_used'],
            confidence=0.8  # 80% confidence by default
        )
        
        # Check if currently active (convert to UTC for comparison)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        is_active = session_start <= now <= (session_start + timedelta(hours=5))
        
        # Get historical prompt rate for predictions
        historical_prompt_rate = self.reader.calculate_historical_prompt_rate()
        
        # Update historical maximums periodically (every hour)
        if (self.last_historical_update is None or 
            datetime.now() - self.last_historical_update > timedelta(hours=1)):
            try:
                self.historical_maximums = self.reader.get_historical_session_maximums(days_back=7)
                self.last_historical_update = datetime.now()
                logger.info(f"Updated historical maximums: {self.historical_maximums}")
            except Exception as e:
                logger.error(f"Failed to get historical maximums: {e}")
        
        result = {
            'tokens': window_tokens,
            'is_active': is_active,
            'session_start': session_start,
            'model_breakdown': session_info.get('model_breakdown', {}),
            'hourly_burn_rate': hourly_burn_rate,
            'prompt_info': {
                'prompts_used': prompt_info['prompts_used'],
                'messages_sent': prompt_info['messages_sent'],
                'multiplication_factor': prompt_info['multiplication_factor'],
                'prompt_bounds': prompt_bounds,
                'historical_prompt_rate': historical_prompt_rate,
                'moving_average_rate': session_info.get('moving_average_rate')
            },
            'historical_maximums': self.historical_maximums,
            'last_update': datetime.now()
        }
        
        logger.info(f"Session check: active={is_active}, prompts={prompt_info['prompts_used']}")
        
        return result
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()


class CustomTitleBar(QWidget):
    """Custom title bar with minimal height"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(18)  # Ultra-compact height
        self.setAutoFillBackground(True)
        
        # For window dragging
        self.mouse_pressed = False
        self.drag_position = QPoint()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize title bar UI"""
        # Don't use a layout - position elements absolutely
        
        # Title label (truly centered in the window)
        self.title_label = QLabel("Claude Dash", self)
        self.title_label.setStyleSheet("font-size: 10px; color: #888888;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # We'll position it in resizeEvent to keep it centered
        
        # Minimize button (positioned on the right)
        self.minimize_btn = QPushButton("─", self)
        self.minimize_btn.setFixedSize(16, 16)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888888;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.2);
                border-radius: 3px;
            }
        """)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        
        # Close button (positioned on the right)
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888888;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
                border-radius: 3px;
            }
        """)
        self.close_btn.clicked.connect(self.parent.close)
        
    def resizeEvent(self, event):
        """Position elements when widget is resized"""
        super().resizeEvent(event)
        
        # Center the title label in the full width
        self.title_label.resize(self.width(), self.height())
        self.title_label.move(0, 0)
        
        # Position buttons on the right
        button_y = (self.height() - 16) // 2
        self.close_btn.move(self.width() - 20, button_y)
        self.minimize_btn.move(self.width() - 40, button_y)
        
    def update_theme(self, theme_data):
        """Update title bar colors based on theme"""
        bg_color = theme_data.get('card_background', '#2d2d2d')
        text_color = theme_data.get('text_secondary', '#888888')
        
        self.setStyleSheet(f"background-color: {bg_color};")
        self.title_label.setStyleSheet(f"font-size: 10px; color: {text_color};")
        
        # Update button colors
        self.minimize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {text_color};
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(128, 128, 128, 0.2);
                border-radius: 3px;
            }}
        """)
        
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {text_color};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #e81123;
                color: white;
                border-radius: 3px;
            }}
        """)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging"""
        if self.mouse_pressed and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        self.mouse_pressed = False
        event.accept()


class ClaudeDashWindow(QMainWindow):
    """Simplified main window focused on session tracking"""
    
    def __init__(self):
        super().__init__()
        self.data_worker = None
        
        # Theme manager
        self.theme_manager = ThemeManager()
        
        # Theme selector state
        self.theme_selector_active = False
        self.theme_selector_first_press = True
        self.theme_preview_index = 0
        self.original_theme = None
        self.theme_overlay = None
        
        # Load UI settings from config
        config = get_config()
        ui_config = config.config.get('ui', {})
        
        # Load saved theme
        saved_theme = ui_config.get('theme', None)
        if saved_theme and saved_theme in self.theme_manager.themes:
            self.theme_manager.current_theme = saved_theme
        
        # Load saved scale
        self.scale_factor = ui_config.get('scale', 1.0)
        self.font_scale = self.scale_factor
        
        self.init_ui()
        self.check_data_source_and_launch()
        
    def init_ui(self):
        """Initialize the user interface"""
        # Make window frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Card size: 260x240 with 5px border
        card_width = 260
        card_height = 240
        border = 5
        title_bar_height = 18
        base_width = card_width + (2 * border)  # 270
        base_height = title_bar_height + card_height + (2 * border)  # 275 (25 + 250)
        self.setFixedSize(int(base_width * self.scale_factor), int(base_height * self.scale_factor))

        # Create main widget that contains title bar and content
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main vertical layout (no margins)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add custom title bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        # Create content widget with margins
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        # 5px margin all around
        margin = int(border * self.scale_factor)
        content_layout.setContentsMargins(margin, margin, margin, margin)
        content_layout.setSpacing(0)  # No spacing between widgets
        
        # Create a larger, focused Claude Code card
        self.claude_card = ClaudeCodeCard(scale_factor=self.scale_factor)
        # Set card to exact size
        self.claude_card.setMinimumSize(card_width, card_height)
        self.claude_card.setMaximumSize(card_width, card_height)
        content_layout.addWidget(self.claude_card)
        
        # Add content widget to main layout
        main_layout.addWidget(content_widget)
        
        # Apply theme
        self.apply_theme(self.theme_manager.current_theme)
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
    def check_data_source_and_launch(self):
        """Check if Claude data directory exists and contains data"""
        # Get Claude directory from config
        config = get_config()
        claude_dir = config.get_claude_data_path()
        
        # Check if directory exists and contains any .jsonl files
        if not claude_dir.exists() or not any(claude_dir.rglob("*.jsonl")):
            self.show_data_error(str(claude_dir))
        else:
            self.init_data_worker()

    def show_data_error(self, path: str):
        """Display an error message about the missing data source"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        
        error_label = QLabel(
            f'<h3>Could not find Claude Code data</h3>'
            f'<p>Looking in: {path}</p>'
            f'<p>Please ensure Claude Code is installed and has been used.</p>'
        )
        error_label.setWordWrap(True)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.addWidget(error_label)
        
        self.setCentralWidget(error_widget)
        
    def init_data_worker(self):
        """Initialize the data update worker"""
        self.data_worker = DataUpdateWorker()
        self.data_worker.data_ready.connect(self.on_data_ready)
        self.data_worker.error_occurred.connect(self.on_error)
        self.data_worker.start()
        
    def on_data_ready(self, data: Dict[str, Any]):
        """Handle new data from the worker thread"""
        # Update Claude card
        self.claude_card.update_display(data)
        
    def on_error(self, error_msg: str):
        """Handle errors from the worker thread"""
        logger.error(f"Data worker error: {error_msg}")
        # Show error in UI
        if hasattr(self, 'claude_card'):
            self.claude_card.show_error(f"Error updating data: {error_msg}")
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Command+Q to quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close)
        
        # Command+W to close window
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)
        
        # T for theme switching
        theme_shortcut = QShortcut(QKeySequence("T"), self)
        theme_shortcut.activated.connect(self.handle_theme_key)
        
        # Enter to accept theme
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self.accept_theme)
        
        # ESC to cancel theme selection
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.cancel_theme_selection)
        
        # +/- for scaling
        scale_up = QShortcut(QKeySequence("Ctrl++"), self)
        scale_up.activated.connect(lambda: self.adjust_scale(0.05))
        
        scale_down = QShortcut(QKeySequence("Ctrl+-"), self)
        scale_down.activated.connect(lambda: self.adjust_scale(-0.05))
        
    def handle_theme_key(self):
        """Handle T key press for theme selection"""
        if not self.theme_selector_active:
            # First press - show current theme
            self.theme_selector_active = True
            self.theme_selector_first_press = True
            self.original_theme = self.theme_manager.current_theme
            themes = self.theme_manager.get_available_themes()
            self.theme_preview_index = themes.index(self.original_theme)
            self.show_theme_overlay(self.original_theme)
        elif self.theme_selector_first_press:
            # Second press - start cycling
            self.theme_selector_first_press = False
            self.cycle_theme_preview()
        else:
            # Subsequent presses - continue cycling
            self.cycle_theme_preview()
    
    def cycle_theme_preview(self):
        """Cycle through themes in preview mode"""
        themes = self.theme_manager.get_available_themes()
        self.theme_preview_index = (self.theme_preview_index + 1) % len(themes)
        next_theme = themes[self.theme_preview_index]
        self.apply_theme(next_theme)
        self.show_theme_overlay(next_theme)
    
    def accept_theme(self):
        """Accept the currently previewed theme"""
        if self.theme_selector_active:
            self.theme_selector_active = False
            self.theme_selector_first_press = True
            self.hide_theme_overlay()
            # Save theme to config
            config = get_config()
            if 'ui' not in config.config:
                config.config['ui'] = {}
            config.config['ui']['theme'] = self.theme_manager.current_theme
            config.save_config()
    
    def cancel_theme_selection(self):
        """Cancel theme selection and revert to original"""
        if self.theme_selector_active:
            self.theme_selector_active = False
            self.theme_selector_first_press = True
            self.hide_theme_overlay()
            # Revert to original theme
            if self.original_theme:
                self.apply_theme(self.original_theme)
    
    def show_theme_overlay(self, theme_name: str):
        """Show theme name overlay"""
        if not self.theme_overlay:
            self.theme_overlay = ThemeOverlay(self)
        self.theme_overlay.set_theme_name(theme_name)
        self.theme_overlay.resize(self.size())
        self.theme_overlay.show()
    
    def hide_theme_overlay(self):
        """Hide theme overlay"""
        if self.theme_overlay:
            self.theme_overlay.hide()
        
    def apply_theme(self, theme_name: str):
        """Apply a theme to the application"""
        self.theme_manager.set_theme(theme_name)
        theme = self.theme_manager.theme_data
        
        # Apply to main window
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
            }}
            QLabel {{
                color: {theme['text_primary']};
            }}
        """)
        
        # Update title bar
        if hasattr(self, 'title_bar'):
            self.title_bar.update_theme(theme)
        
        # Update cards
        if hasattr(self, 'claude_card'):
            self.claude_card.update_theme()
            
    def adjust_scale(self, delta: float):
        """Adjust UI scale"""
        new_scale = self.scale_factor + delta
        if 0.75 <= new_scale <= 2.0:
            self.scale_factor = new_scale
            self.font_scale = new_scale
            
            # Save scale to config
            config = get_config()
            if 'ui' not in config.config:
                config.config['ui'] = {}
            config.config['ui']['scale'] = new_scale
            config.save_config()
            
            # Resize window - keep consistent with init_ui
            card_width = 260
            card_height = 240
            border = 5
            title_bar_height = 18
            base_width = card_width + (2 * border)  # 270
            base_height = title_bar_height + card_height + (2 * border)  # 275
            self.setFixedSize(int(base_width * self.scale_factor), int(base_height * self.scale_factor))
            
            # Update card
            self.claude_card.update_scale(self.scale_factor)
            
    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup()
        event.accept()
    
    def cleanup(self):
        """Clean up resources before exit"""
        if self.data_worker:
            logger.info("Stopping data worker...")
            self.data_worker.stop()
            self.data_worker.wait()  # Wait for thread to finish
            self.data_worker.deleteLater()  # Schedule for deletion
            self.data_worker = None


def setup_signal_handlers(window, app):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        # Close the window, which triggers cleanup
        if window:
            window.close()
        # Quit the application
        app.quit()
    
    # Handle Ctrl-C (SIGINT) and termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Also allow Ctrl-C to work by processing events
    # This is needed for Qt to handle signals properly
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Process events
    timer.start(100)  # Check every 100ms
    
    return timer


class ThemeOverlay(QWidget):
    """Overlay widget to display theme name"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_name = ""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
    def set_theme_name(self, name: str):
        """Set the theme name to display"""
        self.theme_name = name
        self.update()
        
    def paintEvent(self, event):
        """Paint the overlay"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create a rounded rectangle for the overlay
        overlay_width = 160
        overlay_height = 90
        margin = 10
        
        # Position at bottom center
        overlay_rect = QRect(
            (self.width() - overlay_width) // 2,
            self.height() - overlay_height - margin,
            overlay_width,
            overlay_height
        )
        
        # Draw semi-transparent white/gray background with rounded corners
        painter.setBrush(QBrush(QColor(250, 250, 250, 180)))  # Light background
        painter.setPen(QPen(QColor(200, 200, 200, 200), 1))  # Subtle border
        painter.drawRoundedRect(overlay_rect, 8, 8)
        
        # Draw theme name
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(50, 50, 50))  # Dark text on light background
        
        # Theme name
        theme_rect = painter.fontMetrics().boundingRect(self.theme_name)
        x = overlay_rect.center().x() - theme_rect.width() // 2
        y = overlay_rect.top() + 25
        painter.drawText(x, y, self.theme_name)
        
        # Draw instructions in smaller text
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(100, 100, 100))  # Lighter text for instructions
        
        instructions = [
            "T: cycle",
            "Enter: accept",
            "ESC: cancel"
        ]
        
        y = overlay_rect.top() + 45
        for instruction in instructions:
            inst_rect = painter.fontMetrics().boundingRect(instruction)
            x = overlay_rect.center().x() - inst_rect.width() // 2
            painter.drawText(x, y, instruction)
            y += 15  # Compact line spacing


def main():
    """Main entry point"""
    # Create app first
    app = QApplication(sys.argv)
    app.setApplicationName("Claude Dash")
    app.setQuitOnLastWindowClosed(True)
    
    # Create window
    window = ClaudeDashWindow()
    
    # Setup signal handlers
    signal_timer = setup_signal_handlers(window, app)
    
    # Show window
    window.show()
    
    # Run the app
    exit_code = app.exec()
    
    # Cleanup after app exits
    logger.info("Application exiting...")
    if signal_timer:
        signal_timer.stop()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
