import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_qt_app(monkeypatch):
    """Mock PyQt6 application for testing without GUI"""
    mock_app = Mock()
    mock_app.exec.return_value = 0
    monkeypatch.setattr('PyQt6.QtWidgets.QApplication', Mock(return_value=mock_app))
    return mock_app


@pytest.fixture(autouse=True)
def prevent_qt_init(monkeypatch):
    """Prevent actual Qt initialization in tests"""
    # Mock PyQt6 imports for non-GUI tests
    if 'PyQt6' not in sys.modules:
        mock_qt = Mock()
        mock_qt.QtCore = Mock()
        mock_qt.QtWidgets = Mock()
        mock_qt.QtGui = Mock()
        sys.modules['PyQt6'] = mock_qt
        sys.modules['PyQt6.QtCore'] = mock_qt.QtCore
        sys.modules['PyQt6.QtWidgets'] = mock_qt.QtWidgets
        sys.modules['PyQt6.QtGui'] = mock_qt.QtGui


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
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
            "update_frequency_seconds": 30,
            "window": {
                "width": 500,
                "height": 350
            }
        },
        "themes": {
            "dark": {
                "background": "#1e1e1e",
                "foreground": "#ffffff",
                "accent": "#007acc"
            },
            "light": {
                "background": "#ffffff",
                "foreground": "#000000",
                "accent": "#0066cc"
            }
        }
    }