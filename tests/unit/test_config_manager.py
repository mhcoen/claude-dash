import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from claude_dash.config.manager import ConfigManager, get_config


class TestConfigManager:
    @pytest.fixture
    def temp_config_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def default_config(self):
        return {
            "claude_code": {
                "paths": {
                    "base_path": "~/.claude/projects"
                },
                "plans": {
                    "pro": {
                        "message_limit": 300,
                        "description": "14,000 prompts/month"
                    },
                    "max5x": {
                        "message_limit": 450,
                        "description": "70,000 prompts/month"
                    },
                    "max20x": {
                        "message_limit": 900,
                        "description": "280,000 prompts/month"
                    }
                }
            },
            "ui": {
                "theme": "auto",
                "scale": 100,
                "update_frequency_seconds": 30
            }
        }
    
    @pytest.fixture
    def default_pricing(self):
        return {
            "plans": {
                "pro": {
                    "monthly_cost": 20,
                    "prompts_per_month": 14000
                },
                "max5x": {
                    "monthly_cost": 100,
                    "prompts_per_month": 70000
                },
                "max20x": {
                    "monthly_cost": 400,
                    "prompts_per_month": 280000
                }
            }
        }
    
    def test_initialization_creates_config_dir(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            
            # Config directory should be created
            assert temp_config_dir.exists()
            assert config.config_dir == temp_config_dir
    
    def test_load_default_config(self, temp_config_dir, default_config, default_pricing):
        # Create default config files
        defaults_dir = temp_config_dir / 'defaults'
        defaults_dir.mkdir()
        
        with open(defaults_dir / 'config.json', 'w') as f:
            json.dump(default_config, f)
        
        with open(defaults_dir / 'pricing.json', 'w') as f:
            json.dump(default_pricing, f)
        
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            with patch('claude_dash.config.manager.Path') as mock_path:
                # Mock the module path to point to our temp defaults
                mock_path.return_value.parent.parent = temp_config_dir
                
                config = ConfigManager()
                
                assert config.config == default_config
                assert config.pricing == default_pricing
    
    def test_load_user_config_overrides_defaults(self, temp_config_dir, default_config):
        # Create user config that overrides theme
        user_config = {
            "ui": {
                "theme": "dark",
                "scale": 125
            }
        }
        
        with open(temp_config_dir / 'user_config.json', 'w') as f:
            json.dump(user_config, f)
        
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config.copy()  # Start with defaults
            config._load_user_config()
            
            # User config should override defaults
            assert config.config['ui']['theme'] == 'dark'
            assert config.config['ui']['scale'] == 125
            # Other defaults should remain
            assert config.config['ui']['update_frequency_seconds'] == 30
    
    def test_save_user_config(self, temp_config_dir):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            
            # Modify config
            config.user_config = {
                "ui": {"theme": "light"},
                "custom": {"setting": "value"}
            }
            
            config.save_user_config()
            
            # Check file was saved
            user_config_file = temp_config_dir / 'user_config.json'
            assert user_config_file.exists()
            
            # Verify contents
            with open(user_config_file) as f:
                saved_config = json.load(f)
            
            assert saved_config == config.user_config
    
    def test_get_config_dir_macos(self):
        with patch('platform.system', return_value='Darwin'):
            with patch.dict('os.environ', {'HOME': '/Users/test'}):
                config = ConfigManager()
                expected = Path('/Users/test/Library/Application Support/ClaudeDash')
                assert config._get_default_config_dir() == expected
    
    def test_get_config_dir_windows(self):
        with patch('platform.system', return_value='Windows'):
            with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\test\\AppData\\Roaming'}):
                config = ConfigManager()
                expected = Path('C:\\Users\\test\\AppData\\Roaming\\ClaudeDash')
                assert config._get_default_config_dir() == expected
    
    def test_get_config_dir_linux(self):
        with patch('platform.system', return_value='Linux'):
            with patch.dict('os.environ', {'HOME': '/home/test'}):
                config = ConfigManager()
                expected = Path('/home/test/.config/ClaudeDash')
                assert config._get_default_config_dir() == expected
    
    def test_get_claude_paths(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            
            paths = config.get_claude_paths()
            assert paths == ["~/.claude/projects"]
    
    def test_get_ui_config(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            
            ui_config = config.get_ui_config()
            assert ui_config['theme'] == 'auto'
            assert ui_config['scale'] == 100
            assert ui_config['update_frequency_seconds'] == 30
    
    def test_update_ui_config(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            
            # Update theme
            config.update_ui_config(theme='dark')
            assert config.user_config['ui']['theme'] == 'dark'
            
            # Update scale
            config.update_ui_config(scale=150)
            assert config.user_config['ui']['scale'] == 150
            
            # Update multiple
            config.update_ui_config(theme='light', scale=125)
            assert config.user_config['ui']['theme'] == 'light'
            assert config.user_config['ui']['scale'] == 125
    
    def test_get_subscription_plan_auto_detect(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            
            # No user override, should return 'pro' as default
            assert config.get_subscription_plan() == 'pro'
    
    def test_get_subscription_plan_user_override(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            config.user_config = {"subscription": {"plan": "max20x"}}
            
            assert config.get_subscription_plan() == 'max20x'
    
    def test_set_subscription_plan(self, temp_config_dir):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            
            config.set_subscription_plan('max5x')
            assert config.user_config['subscription']['plan'] == 'max5x'
            
            # Verify it saves
            user_config_file = temp_config_dir / 'user_config.json'
            assert user_config_file.exists()
    
    def test_get_pricing_info(self, temp_config_dir, default_pricing):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.pricing = default_pricing
            
            pro_pricing = config.get_pricing_info('pro')
            assert pro_pricing['monthly_cost'] == 20
            assert pro_pricing['prompts_per_month'] == 14000
            
            max20x_pricing = config.get_pricing_info('max20x')
            assert max20x_pricing['monthly_cost'] == 400
            assert max20x_pricing['prompts_per_month'] == 280000
    
    def test_get_theme_config(self, temp_config_dir, default_config):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            config.config = default_config
            
            theme_config = config.get_theme_config()
            assert 'dark' in theme_config['themes']
            assert 'light' in theme_config['themes']
    
    def test_deep_merge(self, temp_config_dir):
        with patch.object(ConfigManager, '_get_default_config_dir', return_value=temp_config_dir):
            config = ConfigManager()
            
            base = {
                "a": 1,
                "b": {"c": 2, "d": 3},
                "e": [1, 2, 3]
            }
            
            override = {
                "a": 10,
                "b": {"c": 20, "f": 4},
                "g": 5
            }
            
            result = config._deep_merge(base, override)
            
            assert result["a"] == 10  # Overridden
            assert result["b"]["c"] == 20  # Nested override
            assert result["b"]["d"] == 3  # Original preserved
            assert result["b"]["f"] == 4  # New key added
            assert result["e"] == [1, 2, 3]  # List preserved
            assert result["g"] == 5  # New top-level key


class TestGetConfig:
    def test_get_config_singleton(self):
        # Clear any existing instance
        if hasattr(get_config, '_instance'):
            delattr(get_config, '_instance')
        
        with patch('claude_dash.config.manager.ConfigManager') as mock_config:
            instance1 = get_config()
            instance2 = get_config()
            
            # Should return same instance
            assert instance1 is instance2
            
            # Should only create one instance
            mock_config.assert_called_once()
    
    def test_get_config_returns_config_manager(self):
        # Clear any existing instance
        if hasattr(get_config, '_instance'):
            delattr(get_config, '_instance')
        
        config = get_config()
        assert isinstance(config, ConfigManager)