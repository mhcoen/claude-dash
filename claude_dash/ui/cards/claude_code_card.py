"""
Enhanced Claude Code card that shows subscription and usage costs
"""
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from PyQt6.QtWidgets import QLabel, QProgressBar, QFrame, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from .base_card import BaseProviderCard
from ...core.config_loader import get_config
from ..theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class DualColorProgressBar(QProgressBar):
    """Progress bar that shows two colors for Opus/Sonnet ratio"""
    
    def __init__(self):
        super().__init__()
        self.opus_percentage = 50.0
        self.setTextVisible(True)
        
    def set_percentages(self, opus_pct: float, sonnet_pct: float):
        """Update the percentages"""
        self.opus_percentage = opus_pct
        self.setValue(100)  # Always full to show both colors
        self.setFormat(f"{int(opus_pct)}% Opus, {int(sonnet_pct)}% Sonnet")
        self.update()
        
    def paintEvent(self, event):
        """Custom paint to show two colors"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(230, 230, 230))
        
        # Calculate split point
        width = self.width()
        split_x = int(width * self.opus_percentage / 100)
        
        # Draw Opus portion (blue)
        if split_x > 0:
            painter.fillRect(0, 0, split_x, self.height(), QColor(41, 98, 255))
        
        # Draw Sonnet portion (orange) 
        if split_x < width:
            painter.fillRect(split_x, 0, width - split_x, self.height(), QColor(255, 106, 53))
            
        # Draw text on top
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class ClaudeCodeCard(BaseProviderCard):
    """Claude Code card with subscription and usage display"""
    
    def __init__(self, scale_factor: float = 1.0):
        self.config = get_config()
        self.session_start_time = None
        self.current_tokens = 0
        self.is_active = False
        
        # Get plan info from config
        self.plan_name = self.config.get_subscription_plan()
        plan_info = self.config.get_plan_info(self.plan_name)
        self.token_limit = plan_info.get("session_token_limit", 220000)
        self.message_limit = plan_info.get("message_limit", 900)
        
        # Prompt tracking
        self.prompts_used = 0
        self.messages_sent = 0
        self.multiplication_factor = 5.6  # Default
        self.prompt_bounds = None
        self.historical_prompt_rate = None  # Will hold PromptBounds object
        
        # Initialize Bayesian estimator
        from ...core.bayesian_limits import BayesianLimitEstimator
        self.bayesian_estimator = BayesianLimitEstimator(self.plan_name)
        
        self.recent_token_rates = []  # Track token usage rate
        self.hourly_burn_rate = 0.0  # Tokens per minute based on last hour
        
        # Get plan display name from config
        plan_display = plan_info.get("display_name", plan_info.get("name", "Max20x"))
        
        self.plan_display = plan_display
        super().__init__(
            provider_name="anthropic",
            display_name="Claude Code",
            color="#ff6b35",  # Vibrant orange
            scale_factor=scale_factor
        )
        self.billing_url = "https://console.anthropic.com/settings/billing"
        self.enable_billing_link()
        # Update every 30 seconds
        self.update_interval = 30000
        
        # Theme colors
        self.progress_bar_bg = "#e0e0e0"
        self.progress_bar_text = "#000000"
        
        # Timer to update time remaining
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_time_display)
        self.time_update_timer.start(1000)  # Update every second
        
    def get_font_size(self) -> int:
        """Get current font size for dynamic text"""
        # Check if parent window has font scale
        parent = self.window()
        if parent and hasattr(parent, 'font_scale'):
            return int(self.base_font_sizes['small'] * parent.font_scale)
        return self.base_font_sizes['small']
        
    def setup_content(self):
        """Setup Claude Code specific content"""
        
        # Remove the default title and use compact header instead
        self.layout.takeAt(0)  # Remove default title layout
        
        # Create compact header
        header_layout = self.create_compact_header("Claude Code")
        self.header_value_label.setText(self.plan_display)  # Show plan in value font
        
        # Make header fonts use secondary size
        header_font = QFont()
        header_font.setPointSize(self.base_font_sizes['secondary'])
        header_font.setBold(True)
        self.provider_label.setFont(header_font)
        
        value_font = QFont()
        value_font.setPointSize(self.base_font_sizes['secondary'])
        value_font.setBold(True)
        self.header_value_label.setFont(value_font)
        
        self.layout.insertLayout(0, header_layout)

        self.layout.addSpacing(14)  # Add vertical space after headers

        # Create rows with aligned columns using QHBoxLayout
        from PyQt6.QtWidgets import QHBoxLayout
        
        # Interactions progress bar
        self.interactions_progress_bar = QProgressBar()
        self.interactions_progress_bar.setMaximum(100)
        self.interactions_progress_bar.setMinimumHeight(14)
        self.interactions_progress_bar.setMaximumHeight(14)
        self.interactions_progress_bar.setTextVisible(True)
        self.interactions_progress_bar.setFormat("%p% of interactions used")
        self.layout.addWidget(self.interactions_progress_bar)
        
        # Small spacing
        self.layout.addSpacing(4)
        
        # Row 1: Interactions used
        interactions_row = QHBoxLayout()
        interactions_row.setContentsMargins(0, 0, 0, 0)
        interactions_row.setSpacing(8)
        
        self.interactions_label = QLabel("Interactions:")
        self.interactions_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        
        self.interactions_value = QLabel("-")
        self.interactions_value.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; font-weight: bold;")
        
        interactions_row.addWidget(self.interactions_label)
        interactions_row.addWidget(self.interactions_value)
        interactions_row.addStretch()
        self.layout.addLayout(interactions_row)
        
        # Row 2: Remaining
        remaining_row = QHBoxLayout()
        remaining_row.setContentsMargins(0, 0, 0, 0)
        remaining_row.setSpacing(8)
        
        self.remaining_label = QLabel("Remaining:")
        theme_manager = ThemeManager()
        accent_color = theme_manager.get_accent_color('claude_code', '#ff6b35')
        self.remaining_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; color: {accent_color};")
        
        self.remaining_value = QLabel("-")
        self.remaining_value.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; font-weight: bold; color: {accent_color};")
        
        remaining_row.addWidget(self.remaining_label)
        remaining_row.addWidget(self.remaining_value)
        remaining_row.addStretch()
        self.layout.addLayout(remaining_row)
        
        # Row 3: Burn rate
        burn_row = QHBoxLayout()
        burn_row.setContentsMargins(0, 0, 0, 0)
        burn_row.setSpacing(8)
        
        self.burn_label = QLabel("Burn rate:")
        self.burn_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        
        self.burn_value = QLabel("-")
        self.burn_value.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        
        burn_row.addWidget(self.burn_label)
        burn_row.addWidget(self.burn_value)
        burn_row.addStretch()
        self.layout.addLayout(burn_row)
        
        # Spacing between groups
        self.layout.addSpacing(10)
        
        # Session Time Progress Bar
        self.time_label = QLabel("Session Time")
        self.time_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        self.layout.addWidget(self.time_label)

        # Small spacing
        self.layout.addSpacing(3)
        
        # Time progress bar
        self.time_progress_bar = QProgressBar()
        self.time_progress_bar.setMaximum(100)
        self.time_progress_bar.setMinimumHeight(10)
        self.time_progress_bar.setMaximumHeight(10)
        self.time_progress_bar.setTextVisible(True)
        self.time_progress_bar.setFormat("%p%")
        self.time_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgb(230, 230, 230);
                text-align: center;
                color: #000000;
                font-size: {self.base_font_sizes['small'] - 1}px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: rgb(41, 98, 255);
                border: none;
            }}
        """)
        self.layout.addWidget(self.time_progress_bar)
        
        # Small spacing
        self.layout.addSpacing(3)
        
        # Session time info (directly under time bar)
        self.time_remaining_label = QLabel("Time left: -")
        self.time_remaining_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        self.layout.addWidget(self.time_remaining_label)
        
        # Spacing
        self.layout.addSpacing(10)
        
        # Model Usage Section
        self.model_label = QLabel("Model Usage")
        self.model_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px;")
        self.layout.addWidget(self.model_label)

        # Small spacing
        self.layout.addSpacing(3)
        
        # Model usage progress bar (custom dual-color)
        self.model_progress_bar = DualColorProgressBar()
        self.model_progress_bar.setMinimumHeight(10)
        self.model_progress_bar.setMaximumHeight(10)
        # Set font size for the text
        font = self.model_progress_bar.font()
        font.setPointSize(self.base_font_sizes['small'] - 1)
        self.model_progress_bar.setFont(font)
        self.layout.addWidget(self.model_progress_bar)
        
        # Small spacing
        self.layout.addSpacing(3)
        
        # Model legend
        self.model_legend = QLabel('<span style="color: #2962FF;">■</span> Opus  <span style="color: #FF6A35;">■</span> Sonnet')
        self.model_legend.setTextFormat(Qt.TextFormat.RichText)
        self.model_legend.setStyleSheet(f"font-size: {self.base_font_sizes['small'] - 1}px;")
        self.layout.addWidget(self.model_legend)
        
        # Spacing before prediction section
        self.layout.addSpacing(4)
        
        # GROUP 4: Prediction & Status
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(separator)
        
        self.layout.addSpacing(8)
        
        # Prediction
        self.prediction_label = QLabel("")  # Start empty
        self.prediction_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; font-weight: bold;")
        self.layout.addWidget(self.prediction_label)
        
        # Limiting factor
        self.limiting_factor_label = QLabel("")
        self.limiting_factor_label.setStyleSheet(f"font-size: {self.base_font_sizes['small'] - 1}px; color: #666666;")
        self.layout.addWidget(self.limiting_factor_label)
        
        # Confidence
        self.confidence_label = QLabel("")
        self.confidence_label.setStyleSheet(f"font-size: {self.base_font_sizes['small'] - 1}px; color: #666666;")
        self.layout.addWidget(self.confidence_label)
        
    def update_display(self, data: Dict[str, Any]):
        """Update the display with usage data"""
        # Extract data
        tokens = data.get('tokens', 0)
        is_active = data.get('is_active', False)
        session_start = data.get('session_start')
        model_breakdown = data.get('model_breakdown', {})
        
        # Extract prompt data
        prompt_info = data.get('prompt_info', {})
        self.prompts_used = prompt_info.get('prompts_used', 0)
        self.messages_sent = prompt_info.get('messages_sent', 0)
        
        # Update session start time
        if session_start:
            self.session_start_time = session_start
        
        # Store active state
        self.is_active = is_active
        self.current_tokens = tokens
        
        # Update Bayesian estimator with historical data if available
        historical_maximums = data.get('historical_maximums')
        if historical_maximums:
            self.bayesian_estimator.update_from_session(historical_maximums)
        
        # Get Bayesian estimates
        estimates = self.bayesian_estimator.get_estimated_limits()
        logger.info(f"Bayesian estimates: messages={estimates['messages']['estimate']:.0f}, prompts={estimates['prompts']['estimate']:.0f}")
        
        # Calculate burn rates
        burn_rates = self._calculate_burn_rates(session_start)
        
        # Calculate which limit we'll hit first
        prompt_limit = estimates["prompts"]["estimate"]
        interactions_limit = prompt_limit  # For now, use prompts as interactions
        
        # But adjust based on model usage if needed
        # (Future: could scale based on Opus vs Sonnet usage)
        
        # Update progress bar
        interaction_percentage = (self.prompts_used / interactions_limit * 100) if interactions_limit > 0 else 0
        self.interactions_progress_bar.setValue(min(100, int(interaction_percentage)))
        
        # Update interaction count
        if is_active:
            self.interactions_value.setText(f"{self.prompts_used} used")
            remaining = max(0, int(interactions_limit - self.prompts_used))
            self.remaining_value.setText(str(remaining))
            
            # Update burn rate
            if burn_rates["prompts"] > 0:
                self.burn_value.setText(f"{int(burn_rates['prompts'])} / hour")
            else:
                self.burn_value.setText("calculating...")
        else:
            self.interactions_value.setText("No active session")
            self.remaining_value.setText("-")
            self.burn_value.setText("-")
        
        # Color the progress bar
        self._update_progress_bar_color(self.interactions_progress_bar, interaction_percentage)
        
        # Calculate predictions using all three metrics
        if is_active and any(burn_rates[k] > 0 for k in burn_rates):
            logger.info(f"Current usage: tokens={tokens}, messages={self.messages_sent}, prompts={self.prompts_used}")
            logger.info(f"Burn rates: {burn_rates}")
            logger.info(f"Limits: prompts={prompt_limit}, interactions={interactions_limit}")
            
            predictions = self.bayesian_estimator.predict_limit_times(
                {"tokens": tokens, "messages": self.messages_sent, "prompts": self.prompts_used},
                burn_rates
            )
            
            logger.info(f"Predictions: {predictions}")
            
            # Update prediction display
            self._update_prediction_display(predictions)
        else:
            self.prediction_label.setText("")
            self.limiting_factor_label.setText("")
            
        # Update confidence
        confidence_text = self.bayesian_estimator.get_confidence_description()
        # Add ML badge to confidence text
        self.confidence_label.setText(f"{confidence_text}")
        
        # Update status
        last_update = data.get('last_update', datetime.now())
        update_time_str = last_update.strftime("%H:%M:%S")
        
        if is_active:
            status_text = f"Active Session • Updated: {update_time_str}"
            self.update_status(status_text, "active")
        else:
            status_text = f"No active session • Updated: {update_time_str}"
            self.update_status(status_text, "normal")
        
        # Update time display
        self.update_time_display()
        
        # Update model usage graph
        if model_breakdown:
            self._update_model_usage(model_breakdown)
            
    def _calculate_burn_rates(self, session_start) -> Dict[str, float]:
        """Calculate burn rates for all three metrics"""
        if not session_start or not self.is_active:
            return {"tokens": 0, "messages": 0, "prompts": 0}
            
        elapsed = datetime.now(timezone.utc).replace(tzinfo=None) - session_start
        hours_elapsed = elapsed.total_seconds() / 3600
        
        if hours_elapsed < 0.1:  # Less than 6 minutes
            return {"tokens": 0, "messages": 0, "prompts": 0}
            
        return {
            "tokens": self.current_tokens / hours_elapsed,
            "messages": self.messages_sent / hours_elapsed,
            "prompts": self.prompts_used / hours_elapsed
        }
        
    def _update_prediction_display(self, predictions: Dict[str, float]):
        """Update prediction labels based on calculated predictions"""
        time_to_limit = predictions["time_to_limit"]
        limiting_factor = predictions["limiting_factor"]
        
        # Get session remaining time
        if self.session_start_time:
            session_end = self.session_start_time + timedelta(hours=5)
            remaining = session_end - datetime.now(timezone.utc).replace(tzinfo=None)
            session_remaining_hours = remaining.total_seconds() / 3600
        else:
            session_remaining_hours = 0
            
        # Set prediction text - FIXED LOGIC
        # If time_to_limit > session_remaining_hours, we WON'T hit the limit
        # If time_to_limit < session_remaining_hours, we WILL hit the limit
        logger.info(f"Prediction: time_to_limit={time_to_limit:.1f}h, session_remaining={session_remaining_hours:.1f}h, factor={limiting_factor}")
        
        # Get theme colors
        theme_manager = ThemeManager()
        accent_color = theme_manager.get_accent_color('claude_code', '#ff6b35')
        
        if time_to_limit >= session_remaining_hours * 3:
            self.prediction_label.setText("Very unlikely to hit any limits this session")
            self.prediction_label.setStyleSheet(f"color: #28a745; font-size: {self.get_font_size()}px;")
        elif time_to_limit >= session_remaining_hours * 1.5:
            self.prediction_label.setText("Unlikely to hit any limits this session")
            self.prediction_label.setStyleSheet(f"font-size: {self.get_font_size()}px;")
        elif time_to_limit >= session_remaining_hours * 0.9:
            self.prediction_label.setText("Likely to hit limits this session")
            self.prediction_label.setStyleSheet(f"color: {accent_color}; font-size: {self.get_font_size()}px; font-weight: bold;")
        else:
            self.prediction_label.setText("Very likely to hit limits this session")
            self.prediction_label.setStyleSheet(f"color: #dc3545; font-size: {self.get_font_size()}px; font-weight: bold;")
            
        # Set limiting factor
        factor_text = {
            "tokens": "Token limit will be reached first",
            "messages": "Message limit will be reached first",
            "prompts": "Prompt limit will be reached first"
        }
        self.limiting_factor_label.setText(factor_text.get(limiting_factor, ""))
        
    def update_time_display(self):
        """Update time-related displays"""
        # Use UTC time for calculations
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Check if we have an active session
        if not self.is_active or not self.session_start_time:
            self.time_remaining_label.setText("Time left: -")
            self.time_progress_bar.setValue(0)
            return
            
        # Calculate times
        session_end = self.session_start_time + timedelta(hours=5)
        remaining = session_end - now
        elapsed = now - self.session_start_time
        
        # Calculate time percentage
        session_duration = timedelta(hours=5)
        time_percentage = (elapsed.total_seconds() / session_duration.total_seconds() * 100)
        time_percentage = min(100, max(0, time_percentage))
        
        # Update time progress bar
        self.time_progress_bar.setValue(int(time_percentage))
        
        # Format time remaining
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            # Show next session time
            from zoneinfo import ZoneInfo
            utc_session_end = session_end.replace(tzinfo=ZoneInfo('UTC'))
            local_session_end = utc_session_end.astimezone()
            next_time = local_session_end.strftime("%I:%M %p").lstrip('0')
            
            self.time_remaining_label.setText(f"Time left: {hours}h {minutes}m • Next session: {next_time}")
        else:
            self.time_remaining_label.setText("Time left: Expired")
            
        
        
    def scale_content_fonts(self, scale: float):
        """Scale Claude Code specific fonts"""
        font_size = int(self.base_font_sizes['small'] * scale)
        small_font_size = int((self.base_font_sizes['small'] - 1) * scale)
        
        # Scale interaction labels
        self.interactions_label.setStyleSheet(f"font-size: {font_size}px;")
        self.interactions_value.setStyleSheet(f"font-size: {font_size}px; font-weight: bold;")
        self.remaining_label.setStyleSheet(f"font-size: {font_size}px;")
        self.remaining_value.setStyleSheet(f"font-size: {font_size}px; font-weight: bold; color: #ff6b35;")
        self.burn_label.setStyleSheet(f"font-size: {font_size}px;")
        self.burn_value.setStyleSheet(f"font-size: {font_size}px;")
        
        # Scale time labels
        self.time_label.setStyleSheet(f"font-size: {font_size}px;")
        
        # Scale model labels
        self.model_label.setStyleSheet(f"font-size: {font_size}px;")
        self.model_legend.setStyleSheet(f"font-size: {small_font_size}px;")
        
        # Scale prediction labels
        self.time_remaining_label.setStyleSheet(f"font-size: {font_size}px;")
        self.limiting_factor_label.setStyleSheet(f"font-size: {small_font_size}px; color: #666666;")
        self.confidence_label.setStyleSheet(f"font-size: {small_font_size}px; color: #666666;")
        
        # Scale prediction label with dynamic styling
        current_style = self.prediction_label.styleSheet()
        if "color: #dc3545" in current_style:  # Red
            self.prediction_label.setStyleSheet(f"color: #dc3545; font-size: {font_size}px; font-weight: bold;")
        elif "color: #ff6b35" in current_style:  # Orange
            self.prediction_label.setStyleSheet(f"color: #ff6b35; font-size: {font_size}px; font-weight: bold;")
        elif "color: #28a745" in current_style:  # Green
            self.prediction_label.setStyleSheet(f"color: #28a745; font-size: {font_size}px;")
        else:  # Default
            self.prediction_label.setStyleSheet(f"font-size: {font_size}px; font-weight: bold;")
            
    def update_theme(self):
        """Update the card when theme changes"""
        super().update_theme()  # This updates the card border
        
        # Update remaining label colors
        theme_manager = ThemeManager()
        accent_color = theme_manager.get_accent_color('claude_code', '#ff6b35')
        self.remaining_label.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; color: {accent_color};")
        self.remaining_value.setStyleSheet(f"font-size: {self.base_font_sizes['small']}px; font-weight: bold; color: {accent_color};")
        
        # Update progress bar
        self.model_progress_bar.update()
        
    def update_theme_colors(self, is_dark: bool):
        """Update progress bar colors based on theme"""
        if is_dark:
            # Dark theme - use lighter backgrounds and white text
            self.progress_bar_bg = "#404040"
            self.progress_bar_text = "#ffffff"
        else:
            # Light theme - use darker text on light backgrounds
            self.progress_bar_bg = "#e0e0e0"
            self.progress_bar_text = "#000000"
            
        # Re-apply progress bar colors with theme
        if hasattr(self, 'interactions_progress_bar'):
            # Re-calculate percentage and update color
            estimates = self.bayesian_estimator.get_estimated_limits()
            interaction_percentage = (self.prompts_used / estimates["prompts"]["estimate"] * 100) if estimates["prompts"]["estimate"] > 0 else 0
            self._update_progress_bar_color(self.interactions_progress_bar, interaction_percentage)
            
    def _update_progress_bar_color(self, progress_bar: QProgressBar, percentage: float):
        """Update progress bar color based on percentage"""
        if percentage >= 90:
            chunk_color = "#dc3545"  # Red
        elif percentage >= 75:
            chunk_color = "#ff6b35"  # Orange
        else:
            chunk_color = "#28a745"  # Green
            
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.progress_bar_bg};
                text-align: center;
                color: {self.progress_bar_text};
                font-size: {self.base_font_sizes['small'] - 1}px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border: none;
            }}
        """)
        
    def _update_model_usage(self, model_breakdown: Dict[str, Any]):
        """Update model usage progress bar"""
        # Calculate percentages from total session usage
        opus_tokens = 0
        sonnet_tokens = 0
        
        for model, stats in model_breakdown.items():
            total_tokens = stats.get('input_tokens', 0) + stats.get('output_tokens', 0)
            if 'opus' in model.lower():
                opus_tokens += total_tokens
            elif 'sonnet' in model.lower():
                sonnet_tokens += total_tokens
                
        total = opus_tokens + sonnet_tokens
        if total > 0:
            opus_percentage = (opus_tokens / total) * 100
            sonnet_percentage = 100 - opus_percentage
        else:
            opus_percentage = 50.0
            sonnet_percentage = 50.0
            
        # Update the custom progress bar
        self.model_progress_bar.set_percentages(opus_percentage, sonnet_percentage)
