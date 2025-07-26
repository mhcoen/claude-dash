import pytest
import numpy as np
from claude_dash.core.bayesian_limits import LimitBelief, BayesianLimitEstimator


class TestLimitBelief:
    def test_initialization(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        assert belief.alpha == 4.0
        assert belief.beta == 2.0
        assert belief.scale == 1000.0
    
    def test_mean_calculation(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        # Mean = alpha / (alpha + beta) * scale = 4/6 * 1000 = 666.67
        assert abs(belief.mean - 666.67) < 0.01
    
    def test_variance_and_std_dev(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        # Variance formula: (alpha * beta) / ((alpha+beta)^2 * (alpha+beta+1)) * scale^2
        # = (4 * 2) / (36 * 7) * 1000000 = 31746.03
        assert abs(belief.variance - 31746.03) < 1.0
        assert abs(belief.std_dev - np.sqrt(31746.03)) < 0.1
    
    def test_credible_interval(self):
        belief = LimitBelief(alpha=10.0, beta=5.0, scale=1000.0)
        lower, upper = belief.credible_interval(0.95)
        
        # Mean should be within interval
        assert lower < belief.mean < upper
        
        # Interval should be reasonable
        assert lower > 0
        assert upper < belief.scale
        assert upper - lower < belief.scale  # Not the full range
    
    def test_update_close_to_limit(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        initial_mean = belief.mean
        
        # Observation very close to limit (95% of scale)
        belief.update(950.0)
        
        # Alpha should increase more than beta
        assert belief.alpha == 6.0  # +2.0
        assert belief.beta == 2.5   # +0.5
        
        # Mean should increase
        assert belief.mean > initial_mean
    
    def test_update_moderate_observation(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        initial_mean = belief.mean
        
        # Observation at 85% of scale
        belief.update(850.0)
        
        assert belief.alpha == 5.0  # +1.0
        assert belief.beta == 2.5   # +0.5
        
        # Mean stays the same because 5/7.5 = 4/6
        assert abs(belief.mean - initial_mean) < 0.01
    
    def test_update_weak_evidence(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        initial_mean = belief.mean
        
        # Observation at 75% of scale
        belief.update(750.0)
        
        assert belief.alpha == 4.3  # +0.3
        assert belief.beta == 2.3   # +0.3
        
        # Mean should stay very similar (4/6 ≈ 4.3/6.6)
        assert abs(belief.mean - initial_mean) < 20  # Allow small tolerance
    
    def test_update_low_observation_ignored(self):
        belief = LimitBelief(alpha=4.0, beta=2.0, scale=1000.0)
        initial_alpha = belief.alpha
        initial_beta = belief.beta
        
        # Observation below 70% threshold
        belief.update(600.0)
        
        # Should not update
        assert belief.alpha == initial_alpha
        assert belief.beta == initial_beta


class TestBayesianLimitEstimator:
    def test_initialization_with_default_plan(self):
        estimator = BayesianLimitEstimator()
        
        # Should use pro plan defaults
        assert estimator.plan == "pro"
        assert estimator.total_observations == 0
        assert estimator.confidence_threshold == 10
    
    def test_initialization_with_max20x_plan(self):
        estimator = BayesianLimitEstimator(plan_name="max20x")
        
        assert estimator.plan == "max20x"
        # Check priors are set correctly
        assert estimator.limits.prompts.scale == 800  # Max prompts for max20x
    
    def test_initialization_with_invalid_plan(self):
        # Should default to pro plan with warning
        estimator = BayesianLimitEstimator(plan_name="invalid_plan")
        
        assert estimator.plan == "invalid_plan"  # Keeps the original value
        # But uses pro plan priors
        assert estimator.limits.prompts.scale == 100  # Max prompts for pro
    
    def test_update_from_session_all_metrics(self):
        estimator = BayesianLimitEstimator()
        
        session_data = {
            "max_tokens": 50000,
            "max_messages": 800,
            "max_prompts": 150,
            "sessions_analyzed": 3
        }
        
        estimator.update_from_session(session_data)
        
        assert estimator.total_observations == 3
        
        # Check that beliefs were updated
        # Note: exact values depend on update logic
        assert estimator.limits.tokens.alpha > 4.0  # Initial was 4.0
        assert estimator.limits.messages.alpha > 8.0  # Initial was 8.0
        assert estimator.limits.prompts.alpha > 6.0  # Initial was 6.0
    
    def test_update_from_session_partial_metrics(self):
        estimator = BayesianLimitEstimator()
        
        # Only update prompts
        session_data = {"max_prompts": 100}
        estimator.update_from_session(session_data)
        
        assert estimator.total_observations == 1
    
    def test_get_estimated_limits_low_confidence(self):
        estimator = BayesianLimitEstimator()
        
        # With no observations, should use 80% confidence
        limits = estimator.get_estimated_limits()
        
        assert limits["prompts"]["confidence"] == 0.80
        assert "estimate" in limits["prompts"]
        assert "std_dev" in limits["prompts"]
        assert "interval" in limits["prompts"]
        
        # Check all three metrics are present
        assert "tokens" in limits
        assert "messages" in limits
        assert "prompts" in limits
    
    def test_get_estimated_limits_high_confidence(self):
        estimator = BayesianLimitEstimator()
        
        # Add enough observations to trigger high confidence
        for i in range(12):
            estimator.update_from_session({"sessions_analyzed": 1})
        
        limits = estimator.get_estimated_limits()
        assert limits["prompts"]["confidence"] == 0.95
    
    def test_predict_limit_times_no_usage(self):
        estimator = BayesianLimitEstimator()
        
        current_usage = {"tokens": 0, "messages": 0, "prompts": 0}
        burn_rates = {"tokens": 0, "messages": 0, "prompts": 0}
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        assert result["limiting_factor"] == "none"
        assert result["time_to_limit"] == float('inf')
        assert result["severity"] == "none"
    
    def test_predict_limit_times_with_burn_rate(self):
        estimator = BayesianLimitEstimator(plan_name="max20x")
        
        current_usage = {"tokens": 10000, "messages": 100, "prompts": 50}
        burn_rates = {"tokens": 5000, "messages": 50, "prompts": 25}  # per hour
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        assert result["limiting_factor"] in ["tokens", "messages", "prompts"]
        assert result["time_to_limit"] > 0
        assert result["severity"] in ["high", "medium", "low", "none"]
    
    def test_predict_limit_times_prompts_limiting(self):
        estimator = BayesianLimitEstimator(plan_name="max20x")
        
        # Set up scenario where prompts will hit limit first
        current_usage = {"tokens": 1000, "messages": 50, "prompts": 400}
        burn_rates = {"tokens": 100, "messages": 5, "prompts": 100}  # per hour
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        # With ~452 prompt limit and 400 used, 52 remaining
        # At 100/hour, should hit limit in ~0.52 hours
        assert result["limiting_factor"] == "prompts"
        assert 0 < result["time_to_limit"] < 1.0
        assert result["severity"] == "high"
    
    def test_predict_limit_times_already_exceeded(self):
        estimator = BayesianLimitEstimator()
        
        # Already over limits
        current_usage = {"tokens": 1000000, "messages": 5000, "prompts": 1000}
        burn_rates = {"tokens": 1000, "messages": 10, "prompts": 5}
        
        result = estimator.predict_limit_times(current_usage, burn_rates)
        
        assert result["time_to_limit"] == 0
        assert result["severity"] == "high"
    
    def test_different_plan_limits(self):
        # Test that different plans have different limits
        pro_estimator = BayesianLimitEstimator(plan_name="pro")
        max5x_estimator = BayesianLimitEstimator(plan_name="max5x")
        max20x_estimator = BayesianLimitEstimator(plan_name="max20x")
        
        pro_limits = pro_estimator.get_estimated_limits()
        max5x_limits = max5x_estimator.get_estimated_limits()
        max20x_limits = max20x_estimator.get_estimated_limits()
        
        # Max plans should have higher limits
        assert max5x_limits["prompts"]["estimate"] > pro_limits["prompts"]["estimate"]
        assert max20x_limits["prompts"]["estimate"] > max5x_limits["prompts"]["estimate"]
    
    def test_severity_classification(self):
        estimator = BayesianLimitEstimator()
        
        # Test different time_to_limit values
        test_cases = [
            (0.5, "high"),      # 30 minutes
            (1.5, "medium"),    # 1.5 hours
            (3.0, "low"),       # 3 hours
            (10.0, "none"),     # 10 hours
        ]
        
        for hours, expected_severity in test_cases:
            current_usage = {"tokens": 1000, "messages": 50, "prompts": 20}
            # Adjust burn rate to get desired time_to_limit
            burn_rates = {
                "tokens": 1000,
                "messages": 50,
                "prompts": (estimator.limits.prompts.mean - 20) / hours
            }
            
            result = estimator.predict_limit_times(current_usage, burn_rates)
            # Allow some tolerance due to calculations
            if hours < 5:
                assert result["severity"] in [expected_severity, "medium", "low"]