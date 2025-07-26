"""
Centralized configuration loader for Claude Dash
Loads configuration from ~/.claude-dash/config.json and pricing.json
"""
import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from .default_config import DEFAULT_CONFIG, DEFAULT_PRICING

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages Claude Dash configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".claude-dash"
        self.config_path = self.config_dir / "config.json"
        self.pricing_path = self.config_dir / "pricing.json"
        
        # Get default config directory
        self.defaults_dir = Path(__file__).parent.parent / "config" / "defaults"
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize config files if they don't exist
        self._initialize_configs()
        
        # Load configurations
        self.config = self._load_config()
        self.pricing = self._load_pricing()
    
    def _initialize_configs(self) -> None:
        """Initialize config files from defaults if they don't exist"""
        # Copy default config.json if it doesn't exist
        if not self.config_path.exists():
            default_config = self.defaults_dir / "config.json"
            if default_config.exists():
                try:
                    shutil.copy2(default_config, self.config_path)
                    logger.info(f"Initialized config.json from defaults")
                except Exception as e:
                    logger.error(f"Error copying default config: {e}")
            else:
                # Create from embedded defaults if file not found
                self._create_default_config()
        
        # Copy default pricing.json if it doesn't exist
        if not self.pricing_path.exists():
            default_pricing = self.defaults_dir / "pricing.json"
            if default_pricing.exists():
                try:
                    shutil.copy2(default_pricing, self.pricing_path)
                    logger.info(f"Initialized pricing.json from defaults")
                except Exception as e:
                    logger.error(f"Error copying default pricing: {e}")
            else:
                # Create from embedded defaults if file not found
                self._create_default_pricing()
    
    def _create_default_config(self) -> None:
        """Create default config.json file"""
        default_config = self._get_default_config()
        try:
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config.json")
        except Exception as e:
            logger.error(f"Error creating default config: {e}")
    
    def _create_default_pricing(self) -> None:
        """Create default pricing.json file"""
        default_pricing = self._get_default_pricing()
        try:
            with open(self.pricing_path, 'w') as f:
                json.dump(default_pricing, f, indent=2)
            logger.info(f"Created default pricing.json")
        except Exception as e:
            logger.error(f"Error creating default pricing: {e}")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration file"""
        # Start with default config
        config = self._get_default_config()
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Deep merge user config with defaults
                    config = self._deep_merge(config, user_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return config
    
    def _load_pricing(self) -> Dict[str, Any]:
        """Load pricing configuration file"""
        if self.pricing_path.exists():
            try:
                with open(self.pricing_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading pricing: {e}")
        
        # Return default pricing if file doesn't exist
        return self._get_default_pricing()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration from centralized default_config module"""
        # Create a deep copy of the DEFAULT_CONFIG to avoid mutations
        import copy
        return copy.deepcopy(DEFAULT_CONFIG)
    
    def _get_default_pricing(self) -> Dict[str, Any]:
        """Get default pricing configuration from centralized default_config module"""
        import copy
        return copy.deepcopy(DEFAULT_PRICING)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override the value
                result[key] = value
        
        return result
    
    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a specific model"""
        # Check if pricing has a nested structure (from file) or flat structure (DEFAULT_PRICING)
        if "models" in self.pricing:
            # Nested structure from pricing.json file
            models = self.pricing.get("models", {})
            if model in models:
                pricing = models[model]
                return {
                    "input": pricing["input"],
                    "output": pricing["output"],
                    "cache_creation": pricing["cache_creation"],
                    "cache_read": pricing["cache_read"]
                }
            # Return default pricing if model not found
            default = models.get("default", {})
            return {
                "input": default.get("input", 3.0),
                "output": default.get("output", 15.0),
                "cache_creation": default.get("cache_creation", 3.75),
                "cache_read": default.get("cache_read", 0.3)
            }
        else:
            # Flat structure from DEFAULT_PRICING
            if model in self.pricing:
                return self.pricing[model]
            # Return default pricing if model not found
            return self.pricing.get("default", {
                "input": 3.0,
                "output": 15.0,
                "cache_creation": 3.75,
                "cache_read": 0.3
            })
    
    def get_subscription_plan(self) -> str:
        """Get current subscription plan, with auto-detection if enabled"""
        claude_config = self.config.get("claude_code", {})
        plan = claude_config.get("subscription_plan", "auto")
        
        # If plan is set to "auto" or auto_detect is enabled, detect from usage
        if plan == "auto" or claude_config.get("auto_detect_plan", False):
            detected_plan = self._detect_plan_from_usage()
            if detected_plan:
                return detected_plan
        
        # Return configured plan or default
        return plan if plan != "auto" else "max20x"
    
    def _detect_plan_from_usage(self) -> Optional[str]:
        """Detect subscription plan based on historical usage"""
        try:
            # Import here to avoid circular dependency
            from ..providers.claude_code_reader import ClaudeCodeReader
            
            reader = ClaudeCodeReader()
            # Get recent session data (last 30 days)
            sessions = reader.get_session_history(days_back=30)
            
            if not sessions:
                return None
            
            # Find the maximum messages sent in any session
            max_messages = 0
            for session in sessions:
                messages = session.get('messages_sent', 0)
                if messages > max_messages:
                    max_messages = messages
            
            # Get plan thresholds from config
            plans = self.config.get("claude_code", {}).get("plans", {})
            
            # Check plans in order (smallest to largest)
            plan_order = [
                ("pro", plans.get("pro", {}).get("detection_threshold", 45)),
                ("max5x", plans.get("max5x", {}).get("detection_threshold", 225)),
                ("max20x", plans.get("max20x", {}).get("detection_threshold", 900))
            ]
            
            # Find the appropriate plan based on max messages
            for plan_name, threshold in plan_order:
                if max_messages <= threshold:
                    logger.info(f"Auto-detected plan: {plan_name} (max messages: {max_messages})")
                    return plan_name
            
            # If exceeds all thresholds, return the highest plan
            logger.info(f"Auto-detected plan: max20x (max messages: {max_messages} exceeds all thresholds)")
            return "max20x"
            
        except Exception as e:
            logger.error(f"Error detecting plan from usage: {e}")
            return None
    
    def get_plan_info(self, plan: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a subscription plan"""
        if plan is None:
            plan = self.get_subscription_plan()
        
        plans = self.config.get("claude_code", {}).get("plans", {})
        return plans.get(plan, plans.get("max20", {}))
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration"""
        return self.config.get("ui", {})
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration"""
        return self.config.get("analysis", {})
    
    def get_claude_data_path(self) -> Path:
        """Get path to Claude data directory"""
        path_str = self.config.get("paths", {}).get("claude_data", "~/.claude/projects")
        return Path(os.path.expanduser(path_str))
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def save_pricing(self) -> None:
        """Save current pricing to file"""
        try:
            with open(self.pricing_path, 'w') as f:
                json.dump(self.pricing, f, indent=2)
            logger.info(f"Pricing saved to {self.pricing_path}")
        except Exception as e:
            logger.error(f"Error saving pricing: {e}")
    
    def reload_config(self) -> None:
        """Reload configuration from files"""
        self.config = self._load_config()
        self.pricing = self._load_pricing()
        logger.info("Configuration reloaded")


# Global config instance
_config_loader = None


def get_config() -> ConfigLoader:
    """Get global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader