"""
Adaptive Bayesian Limit Estimator for Claude Code Usage

This module implements a Bayesian approach to discovering and updating
beliefs about session limits (tokens, messages, prompts) based on
historical usage data.
"""
import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LimitBelief:
    """Represents our belief about a limit using a Beta distribution"""
    # We use Beta distribution scaled to the expected range
    alpha: float  # Shape parameter 1
    beta: float   # Shape parameter 2
    scale: float  # Maximum possible value
    
    @property
    def mean(self) -> float:
        """Expected value of the limit"""
        return self.alpha / (self.alpha + self.beta) * self.scale
    
    @property
    def variance(self) -> float:
        """Variance of our belief"""
        ab = self.alpha + self.beta
        return (self.alpha * self.beta) / (ab * ab * (ab + 1)) * self.scale * self.scale
    
    @property
    def std_dev(self) -> float:
        """Standard deviation"""
        return np.sqrt(self.variance)
    
    def credible_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate credible interval for the limit"""
        # For Beta distribution, we can use the quantile function
        from scipy import stats
        dist = stats.beta(self.alpha, self.beta)
        lower = dist.ppf((1 - confidence) / 2) * self.scale
        upper = dist.ppf(1 - (1 - confidence) / 2) * self.scale
        return (lower, upper)
    
    def update(self, observation: float) -> None:
        """Update belief based on observed maximum"""
        # Convert observation to [0, 1] scale
        normalized = observation / self.scale
        
        # Bayesian update: if we observed a value close to the limit,
        # increase alpha; otherwise increase beta
        if normalized > 0.9:  # Close to limit
            self.alpha += 2.0
            self.beta += 0.5
        elif normalized > 0.8:
            self.alpha += 1.5
            self.beta += 1.0
        else:
            self.alpha += 0.5
            self.beta += 2.0


@dataclass
class SessionLimits:
    """Container for all three limit types"""
    tokens: LimitBelief
    messages: LimitBelief
    prompts: LimitBelief


class BayesianLimitEstimator:
    """
    Adaptive Bayesian estimator for Claude Code session limits.
    
    Uses Bayesian inference to maintain and update beliefs about
    the true limits based on observed usage patterns.
    """
    
    def __init__(self, plan_name: str = "max20x"):
        self.plan_name = plan_name
        self.limits = self._initialize_priors(plan_name)
        self.confidence_threshold = 10  # Min observations for "high confidence"
        self.total_observations = 0
        
    def _initialize_priors(self, plan_name: str) -> SessionLimits:
        """Initialize prior beliefs based on documented limits"""
        
        # Prior beliefs based on documentation
        priors = {
            "pro": {
                "tokens": (19000, 30000),      # Documented ~10-20k typical
                "messages": (45, 60),           # Documented 45
                "prompts": (40, 100),           # Documented 10-40
            },
            "max5x": {
                "tokens": (65000, 100000),     # Documented ~65k typical
                "messages": (125, 500),         # 50-200 prompts * 2.5 messages/prompt
                "prompts": (50, 200),           # Documented 50-200
            },
            "max20x": {
                "tokens": (200000, 400000),    # Can be much higher with caching
                "messages": (500, 2000),        # 200-800 prompts * 2.5 messages/prompt
                "prompts": (200, 800),          # Documented 200-800
            }
        }
        
        plan_priors = priors.get(plan_name, priors["max20x"])
        
        # Initialize with stronger priors based on documented limits
        return SessionLimits(
            tokens=LimitBelief(alpha=4.0, beta=2.0, scale=plan_priors["tokens"][1]),
            messages=LimitBelief(alpha=8.0, beta=2.0, scale=plan_priors["messages"][1]),
            prompts=LimitBelief(alpha=6.0, beta=3.0, scale=plan_priors["prompts"][1])
        )
    
    def update_from_session(self, session_data: Dict[str, float]) -> None:
        """Update beliefs based on observed session maximums"""
        
        if "max_tokens" in session_data:
            self.limits.tokens.update(session_data["max_tokens"])
            
        if "max_messages" in session_data:
            self.limits.messages.update(session_data["max_messages"])
            
        if "max_prompts" in session_data:
            self.limits.prompts.update(session_data["max_prompts"])
            
        # If we analyzed multiple sessions, count them all
        sessions_count = session_data.get('sessions_analyzed', 1)
        self.total_observations += sessions_count
        logger.info(f"Updated Bayesian limits after {self.total_observations} observations (added {sessions_count})")
        
    def get_estimated_limits(self) -> Dict[str, Dict[str, float]]:
        """Get current limit estimates with confidence intervals"""
        
        confidence = 0.95 if self.total_observations >= self.confidence_threshold else 0.80
        
        return {
            "tokens": {
                "estimate": self.limits.tokens.mean,
                "std_dev": self.limits.tokens.std_dev,
                "interval": self.limits.tokens.credible_interval(confidence),
                "confidence": confidence
            },
            "messages": {
                "estimate": self.limits.messages.mean,
                "std_dev": self.limits.messages.std_dev,
                "interval": self.limits.messages.credible_interval(confidence),
                "confidence": confidence
            },
            "prompts": {
                "estimate": self.limits.prompts.mean,
                "std_dev": self.limits.prompts.std_dev,
                "interval": self.limits.prompts.credible_interval(confidence),
                "confidence": confidence
            },
            "total_observations": self.total_observations,
            "confidence_level": "high" if self.total_observations >= self.confidence_threshold else "learning"
        }
    
    def predict_limit_times(self, current_usage: Dict[str, float], 
                          burn_rates: Dict[str, float]) -> Dict[str, float]:
        """Predict time until each limit is reached"""
        
        estimates = self.get_estimated_limits()
        predictions = {}
        
        for metric in ["tokens", "messages", "prompts"]:
            if metric in current_usage and metric in burn_rates:
                remaining = estimates[metric]["estimate"] - current_usage[metric]
                if burn_rates[metric] > 0:
                    hours_until_limit = remaining / burn_rates[metric]
                    predictions[metric] = max(0, hours_until_limit)
                else:
                    predictions[metric] = float('inf')
            else:
                predictions[metric] = float('inf')
                
        # Find which limit will be hit first
        limiting_factor = min(predictions.keys(), key=lambda k: predictions[k])
        predictions["limiting_factor"] = limiting_factor
        predictions["time_to_limit"] = predictions[limiting_factor]
        
        return predictions
    
    def get_confidence_description(self) -> str:
        """Get human-readable confidence description"""
        if self.total_observations >= self.confidence_threshold:
            return "High confidence - Trained on your usage patterns"
        elif self.total_observations >= 5:
            return "Medium confidence - Still learning your patterns"
        else:
            return "Low confidence - Gathering initial data"