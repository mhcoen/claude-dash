"""
Path management for Claude Dash application
All user data is stored in ~/.claude-dash
"""
from pathlib import Path
import os
import shutil
import logging
import json
from .default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ClaudeDashPaths:
    """Manages all paths for the Claude Dash application"""
    
    @staticmethod
    def get_data_dir() -> Path:
        """Get the main Claude Dash data directory (~/.claude-dash)"""
        data_dir = Path.home() / ".claude-dash"
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    @staticmethod
    def get_config_path() -> Path:
        """Get the config file path"""
        return ClaudeDashPaths.get_data_dir() / "config.json"
    
    @staticmethod
    def get_logs_dir() -> Path:
        """Get the logs directory"""
        logs_dir = ClaudeDashPaths.get_data_dir() / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    @staticmethod
    def migrate_from_old_paths():
        """Migrate data from old locations to ~/.claude-dash"""
        data_dir = ClaudeDashPaths.get_data_dir()
        
        # Migrate config.json from UsageGrid if it exists
        old_usagegrid_dir = Path.home() / ".usagegrid"
        old_config = old_usagegrid_dir / "config.json"
        new_config = ClaudeDashPaths.get_config_path()
        
        if old_config.exists() and not new_config.exists():
            logger.info(f"Migrating config from {old_config} to {new_config}")
            # Read old config and extract only Claude-related settings
            try:
                with open(old_config, 'r') as f:
                    old_data = json.load(f)
                    # Extract only claude_code settings
                    claude_config = {
                        "claude_code": old_data.get("claude_code", DEFAULT_CONFIG["claude_code"]),
                        "themes": DEFAULT_CONFIG["themes"],
                        "default_theme": old_data.get("default_theme", "dark")
                    }
                    with open(new_config, 'w') as f:
                        json.dump(claude_config, f, indent=2)
            except Exception as e:
                logger.error(f"Error migrating config: {e}")
    
    @staticmethod
    def ensure_default_config():
        """Ensure a default config exists if none is present"""
        config_path = ClaudeDashPaths.get_config_path()
        
        if not config_path.exists():
            # Create default config with complete settings
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logger.info(f"Created default config at {config_path}")

# For backward compatibility
UsageGridPaths = ClaudeDashPaths