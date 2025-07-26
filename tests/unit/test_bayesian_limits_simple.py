import pytest
import numpy as np
from claude_dash.core.bayesian_limits import LimitBelief, BayesianLimitEstimator


class TestBayesianLimitEstimatorSimple:
    """Simplified tests that match the actual implementation"""
    
    def test_predict_limit_times_no_burn_rate(self):
        estimator = BayesianLimitEstimator()
        
        # Zero burn rates should return infinity
        current_usage = {"tokens": 1000, "messages": 50, "prompts": 20}
        burn_rates = {"tokens": 0, "messages": 0, "prompts": 0}
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        assert result["tokens"] == float('inf')
        assert result["messages"] == float('inf')
        assert result["prompts"] == float('inf')
        # With all infinities, min() will pick the first key
        assert result["limiting_factor"] in ["tokens", "messages", "prompts"]
        assert result["time_to_limit"] == float('inf')
    
    def test_predict_limit_times_with_usage(self):
        estimator = BayesianLimitEstimator()
        
        # Normal usage scenario
        current_usage = {"tokens": 10000, "messages": 30, "prompts": 25}
        burn_rates = {"tokens": 5000, "messages": 15, "prompts": 10}  # per hour
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        # All metrics should have finite predictions
        assert result["tokens"] < float('inf')
        assert result["messages"] < float('inf') 
        assert result["prompts"] < float('inf')
        
        # Should identify a limiting factor
        assert result["limiting_factor"] in ["tokens", "messages", "prompts"]
        assert result["time_to_limit"] == result[result["limiting_factor"]]
    
    def test_predict_limit_times_already_exceeded(self):
        estimator = BayesianLimitEstimator()
        
        # Usage exceeds limits
        current_usage = {"tokens": 100000, "messages": 500, "prompts": 200}
        burn_rates = {"tokens": 1000, "messages": 10, "prompts": 5}
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        # Should return 0 for exceeded limits
        assert result["time_to_limit"] == 0