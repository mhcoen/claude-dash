import pytest
import numpy as np
from claude_dash.core.adaptive_bounds import AdaptiveBoundsCalculator, PromptBounds


class TestAdaptiveBoundsCalculator:
    def test_initialization(self):
        calc = AdaptiveBoundsCalculator()
        assert len(calc.recent_multipliers) == 0
        assert len(calc.pattern_history) == 0
        assert calc.pattern_defaults == {
            'simple': 3.0,
            'moderate': 7.0,
            'complex': 18.0,
            'mixed': 10.0
        }
        assert calc.SIMPLE_THRESHOLD == 3
        assert calc.COMPLEX_THRESHOLD == 9
    
    def test_add_prompt_simple_pattern(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add a simple pattern prompt (3 or fewer messages)
        calc.add_prompt(2)
        assert len(calc.recent_multipliers) == 1
        assert calc.recent_multipliers[0] == 2
        assert calc.pattern_history[0] == 'simple'
        
        calc.add_prompt(3)
        assert calc.pattern_history[1] == 'simple'
    
    def test_add_prompt_complex_pattern(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add a complex pattern prompt (9 or more messages)
        calc.add_prompt(10)
        assert calc.pattern_history[0] == 'complex'
        
        calc.add_prompt(15)
        assert calc.pattern_history[1] == 'complex'
    
    def test_add_prompt_moderate_pattern(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add moderate pattern prompts (4-8 messages)
        calc.add_prompt(5)
        assert calc.pattern_history[0] == 'moderate'
        
        calc.add_prompt(7)
        assert calc.pattern_history[1] == 'moderate'
    
    def test_get_current_pattern_insufficient_data(self):
        calc = AdaptiveBoundsCalculator()
        
        # Less than 3 prompts should return 'mixed'
        assert calc.get_current_pattern() == 'mixed'
        
        calc.add_prompt(2)
        assert calc.get_current_pattern() == 'mixed'
        
        calc.add_prompt(3)
        assert calc.get_current_pattern() == 'mixed'
    
    def test_get_current_pattern_dominant_simple(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add mostly simple patterns (need 60% for dominance)
        for _ in range(7):
            calc.add_prompt(2)  # Simple
        for _ in range(3):
            calc.add_prompt(5)  # Moderate
        
        # 70% simple, should return 'simple'
        assert calc.get_current_pattern() == 'simple'
    
    def test_get_current_pattern_no_dominant(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add equal mix of patterns
        for _ in range(3):
            calc.add_prompt(2)   # Simple
        for _ in range(3):
            calc.add_prompt(5)   # Moderate
        for _ in range(4):
            calc.add_prompt(10)  # Complex
        
        # No pattern has 60%, should return 'mixed'
        assert calc.get_current_pattern() == 'mixed'
    
    def test_calculate_bounds_insufficient_data(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add only 3 prompts (less than required 5)
        calc.add_prompt(2)
        calc.add_prompt(3)
        calc.add_prompt(2)
        
        bounds = calc.calculate_bounds(900, 50, 0.8)
        
        # Should use pattern-based defaults
        assert bounds.lower > 0
        assert bounds.expected > bounds.lower
        assert bounds.upper > bounds.expected
        assert bounds.pattern == 'simple'  # Based on the prompts we added
        
        # With simple pattern default (3.0x)
        # 900 messages / 3.0 = 300 prompts total
        # 300 - 50 = 250 remaining
        assert bounds.expected == 250
    
    def test_calculate_bounds_with_sufficient_data(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add consistent moderate prompts
        for i in range(10):
            calc.add_prompt(5)  # Consistent 5 messages per prompt
        
        bounds = calc.calculate_bounds(900, 100, 0.8)
        
        # With consistent 5x multiplier:
        # 900 messages / 5 = 180 prompts total
        # 180 - 100 = 80 remaining
        assert bounds.expected == 80
        assert bounds.pattern == 'moderate'
        
        # Bounds should be relatively tight with consistent data
        assert bounds.upper - bounds.lower < 100
    
    def test_calculate_bounds_with_variable_data(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add variable prompts across patterns
        message_counts = [2, 3, 8, 10, 5, 4, 6, 12, 2, 7]
        for count in message_counts:
            calc.add_prompt(count)
        
        bounds = calc.calculate_bounds(900, 50, 0.8)
        
        # Should return mixed pattern
        assert bounds.pattern == 'mixed'
        
        # Bounds should be wider with variable data
        assert bounds.upper - bounds.lower > 50
        assert bounds.lower < bounds.expected < bounds.upper
    
    def test_calculate_bounds_edge_cases(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add some data
        for _ in range(5):
            calc.add_prompt(5)
        
        # Test with zero messages remaining
        bounds = calc.calculate_bounds(0, 50, 0.8)
        assert bounds.lower == 0
        assert bounds.expected == 0
        assert bounds.upper == 0
        
        # Test with prompts already exceeding expected
        bounds = calc.calculate_bounds(100, 200, 0.8)
        assert bounds.lower == 0
        assert bounds.expected == 0
        assert bounds.upper == 0
    
    def test_rolling_window_behavior(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add more than 20 prompts (window size)
        for i in range(25):
            calc.add_prompt(i % 10 + 1)  # Variable message counts
        
        # Should only keep last 20
        assert len(calc.recent_multipliers) == 20
        assert len(calc.pattern_history) == 20
        
        # Check that early values were dropped
        assert 0 not in calc.recent_multipliers  # First value was 0
        assert 1 not in calc.recent_multipliers  # Second value was 1
    
    def test_confidence_interval_scaling(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add consistent data
        for _ in range(10):
            calc.add_prompt(5)
        
        # Test different confidence levels
        bounds_50 = calc.calculate_bounds(900, 50, 0.5)
        bounds_80 = calc.calculate_bounds(900, 50, 0.8)
        bounds_95 = calc.calculate_bounds(900, 50, 0.95)
        
        # Higher confidence should have wider bounds
        assert (bounds_95.upper - bounds_95.lower) >= (bounds_80.upper - bounds_80.lower)
        assert (bounds_80.upper - bounds_80.lower) >= (bounds_50.upper - bounds_50.lower)
        
        # Expected value should be the same
        assert bounds_50.expected == bounds_80.expected == bounds_95.expected
    
    def test_outlier_filtering(self):
        calc = AdaptiveBoundsCalculator()
        
        # Add mostly consistent data with one outlier
        for _ in range(8):
            calc.add_prompt(5)  # Normal
        calc.add_prompt(50)     # Outlier
        calc.add_prompt(5)      # Back to normal
        
        bounds = calc.calculate_bounds(900, 50, 0.8)
        
        # Expected should be close to 5, not influenced much by outlier
        # 900 / 5 = 180 total, 180 - 50 = 130 remaining
        assert 120 < bounds.expected < 140  # Allow some tolerance