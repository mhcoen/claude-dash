"""
Adaptive bounds calculator for prompt predictions based on recent usage patterns
"""
import numpy as np
from collections import deque
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PromptBounds:
    """Represents confidence bounds for prompt predictions"""
    lower: int
    expected: int
    upper: int
    confidence_level: float
    pattern: str  # "simple", "moderate", "complex", "mixed"
    
    def __str__(self):
        return f"{self.expected} ({self.lower}-{self.upper})"


class AdaptiveBoundsCalculator:
    """Calculate adaptive confidence bounds based on recent prompt patterns"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.recent_multipliers = deque(maxlen=window_size)
        self.pattern_history = deque(maxlen=window_size)
        
        # Pattern thresholds
        self.SIMPLE_THRESHOLD = 3
        self.COMPLEX_THRESHOLD = 9
        
        # Default multipliers by pattern (conservative estimates)
        self.pattern_defaults = {
            'simple': 3.0,    # Was 2.0
            'moderate': 7.0,  # Was 5.5
            'complex': 18.0,  # Was 15.0
            'mixed': 10.0     # Was 7.0
        }
    
    def add_prompt(self, message_count: int) -> None:
        """Add a new prompt's message count to the history"""
        self.recent_multipliers.append(message_count)
        
        # Categorize the pattern
        if message_count <= self.SIMPLE_THRESHOLD:
            pattern = 'simple'
        elif message_count >= self.COMPLEX_THRESHOLD:
            pattern = 'complex'
        else:
            pattern = 'moderate'
        
        self.pattern_history.append(pattern)
        logger.debug(f"Added prompt with {message_count} messages (pattern: {pattern})")
    
    def get_current_pattern(self) -> str:
        """Determine the current usage pattern"""
        if len(self.pattern_history) < 3:
            return 'mixed'
        
        # Count recent patterns
        pattern_counts = {'simple': 0, 'moderate': 0, 'complex': 0}
        for pattern in list(self.pattern_history)[-10:]:  # Last 10 prompts
            pattern_counts[pattern] += 1
        
        # Determine dominant pattern
        total = sum(pattern_counts.values())
        if total == 0:
            return 'mixed'
        
        for pattern, count in pattern_counts.items():
            if count / total >= 0.6:  # 60% threshold for dominance
                return pattern
        
        return 'mixed'
    
    def calculate_bounds(self, message_limit: int, prompts_used: int, 
                        confidence: float = 0.8) -> PromptBounds:
        """
        Calculate prompt bounds for remaining capacity
        
        Args:
            message_limit: Total message limit (e.g., 900 for Max20x)
            prompts_used: Number of prompts already used
            confidence: Confidence level (0.8 = 80% confidence interval)
        """
        pattern = self.get_current_pattern()
        
        if len(self.recent_multipliers) < 5:
            # Not enough data - use pattern-based defaults
            multiplier = self.pattern_defaults[pattern]
            
            # Wide bounds due to uncertainty
            if pattern == 'mixed':
                lower_mult = 4.0
                upper_mult = 10.0
            else:
                lower_mult = multiplier * 0.7
                upper_mult = multiplier * 1.4
        else:
            # Use recent data for tighter bounds
            recent = list(self.recent_multipliers)[-10:]  # Last 10 prompts
            
            # Remove outliers using IQR method
            q1 = np.percentile(recent, 25)
            q3 = np.percentile(recent, 75)
            iqr = q3 - q1
            
            # Filter outliers
            filtered = [x for x in recent if q1 - 1.5*iqr <= x <= q3 + 1.5*iqr]
            
            if not filtered:
                filtered = recent
            
            # Calculate statistics on filtered data
            median = np.median(filtered)
            mean = np.mean(filtered)
            std = np.std(filtered)
            p75 = np.percentile(filtered, 75)  # 75th percentile for conservative estimate
            
            logger.info(f"Multiplier stats - Mean: {mean:.2f}, Median: {median:.2f}, Std: {std:.2f}, "
                       f"75th percentile: {p75:.2f}, Data points: {len(filtered)}, Pattern: {pattern}")
            
            # Use median for balanced estimate (75th percentile was too conservative)
            multiplier = median
            
            if pattern in ['simple', 'moderate'] and len(filtered) >= 5:
                # Low variability patterns - tight bounds
                std = np.std(filtered)
                lower_mult = max(median - std, 1.0)
                upper_mult = median + std
            else:
                # High variability or complex pattern - wider bounds
                if confidence == 0.8:
                    lower_mult = np.percentile(filtered, 10)
                    upper_mult = np.percentile(filtered, 90)
                elif confidence == 0.5:
                    lower_mult = np.percentile(filtered, 25)
                    upper_mult = np.percentile(filtered, 75)
                else:
                    # 95% confidence
                    lower_mult = np.percentile(filtered, 2.5)
                    upper_mult = np.percentile(filtered, 97.5)
        
        # Apply very tight bounds for practical usefulness
        # Since we're using 75th percentile, we can use even tighter bounds
        lower_mult = max(1.0, multiplier * 0.9)  # 90% of p75 (optimistic)
        upper_mult = multiplier * 1.1  # 110% of p75 (conservative)
        
        logger.info(f"Bounds calculation - Multiplier: {multiplier:.2f}, Lower: {lower_mult:.2f}, "
                   f"Upper: {upper_mult:.2f}, Message limit: {message_limit}")
        
        # Ensure bounds make sense
        if upper_mult < lower_mult:
            lower_mult, upper_mult = upper_mult, lower_mult
        
        # Calculate prompt bounds
        # Note: Lower multiplier = more prompts possible, higher multiplier = fewer prompts
        prompts_total_upper = int(message_limit / lower_mult)  # Most optimistic
        prompts_total_expected = int(message_limit / multiplier) if multiplier > 0 else 0
        prompts_total_lower = int(message_limit / upper_mult)  # Most conservative
        
        # Subtract already used prompts
        prompts_remaining_upper = max(0, prompts_total_upper - prompts_used)
        prompts_remaining_expected = max(0, prompts_total_expected - prompts_used)
        prompts_remaining_lower = max(0, prompts_total_lower - prompts_used)
        
        return PromptBounds(
            lower=prompts_remaining_lower,
            expected=prompts_remaining_expected,
            upper=prompts_remaining_upper,
            confidence_level=confidence,
            pattern=pattern
        )
    
    def get_pattern_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for each usage pattern"""
        if not self.recent_multipliers:
            return {}
        
        # Group by pattern
        pattern_groups = {'simple': [], 'moderate': [], 'complex': []}
        
        for msg_count in self.recent_multipliers:
            if msg_count <= self.SIMPLE_THRESHOLD:
                pattern_groups['simple'].append(msg_count)
            elif msg_count >= self.COMPLEX_THRESHOLD:
                pattern_groups['complex'].append(msg_count)
            else:
                pattern_groups['moderate'].append(msg_count)
        
        # Calculate stats for each pattern
        stats = {}
        for pattern, values in pattern_groups.items():
            if values:
                stats[pattern] = {
                    'mean': np.mean(values),
                    'median': np.median(values),
                    'std': np.std(values) if len(values) > 1 else 0,
                    'count': len(values),
                    'percentage': len(values) / len(self.recent_multipliers) * 100
                }
        
        return stats