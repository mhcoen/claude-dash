"""
Theme manager for Claude Dash
Handles card styling with colored borders
"""
from typing import Dict, Any
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, QObject, pyqtSignal


class ThemeManager(QObject):
    """Manages UI themes and card styling"""
    
    theme_changed = pyqtSignal(str)
    
    # Theme definitions from UsageGrid
    THEMES = {
        "light": {
            "name": "Light",
            "background": "#f5f5f5",
            "card_background": "white",
            "text_primary": "#000000",
            "text_secondary": "#666666",
            "border": "#e0e0e0",
            "accents": {
                "claude_code": "#ff6b35",
                "value_analysis": "#FF6B35",
                "theme_selector": "#795548"
            }
        },
        "dark": {
            "name": "Dark",
            "background": "#1e1e1e",
            "card_background": "#2d2d2d",
            "text_primary": "#ffffff",
            "text_secondary": "#d0d0d0",
            "border": "#404040",
            "accents": {
                "claude_code": "#ff8a65",
                "value_analysis": "#FF6B35",
                "theme_selector": "#a1887f"
            }
        },
        "midnight": {
            "name": "Midnight",
            "background": "#0d1117",
            "card_background": "#161b22",
            "text_primary": "#c9d1d9",
            "text_secondary": "#b1bac4",
            "border": "#30363d",
            "accents": {
                "claude_code": "#ff8a65",
                "value_analysis": "#FF6B35",
                "theme_selector": "#a1887f"
            }
        },
        "solarized": {
            "name": "Solarized",
            "background": "#fdf6e3",
            "card_background": "#eee8d5",
            "text_primary": "#657b83",
            "text_secondary": "#93a1a1",
            "border": "#93a1a1",
            "accents": {
                "claude_code": "#cb4b16",
                "value_analysis": "#dc322f",
                "theme_selector": "#6c71c4"
            }
        },
        "solarized_dark": {
            "name": "Solarized Dark",
            "background": "#002b36",
            "card_background": "#073642",
            "text_primary": "#839496",
            "text_secondary": "#93a1a1",
            "border": "#586e75",
            "accents": {
                "claude_code": "#cb4b16",
                "value_analysis": "#dc322f",
                "theme_selector": "#6c71c4"
            }
        },
        "nord": {
            "name": "Nord",
            "background": "#2e3440",
            "card_background": "#3b4252",
            "text_primary": "#eceff4",
            "text_secondary": "#e5e9f0",
            "border": "#4c566a",
            "accents": {
                "claude_code": "#bf616a",
                "value_analysis": "#d08770",
                "theme_selector": "#5e81ac"
            }
        },
        "dracula": {
            "name": "Dracula",
            "background": "#282a36",
            "card_background": "#44475a",
            "text_primary": "#f8f8f2",
            "text_secondary": "#bd93f9",
            "border": "#6272a4",
            "accents": {
                "claude_code": "#ff79c6",
                "value_analysis": "#ff6e67",
                "theme_selector": "#bd93f9"
            }
        },
        "material": {
            "name": "Material",
            "background": "#fafafa",
            "card_background": "#ffffff",
            "text_primary": "#212121",
            "text_secondary": "#757575",
            "border": "#e0e0e0",
            "accents": {
                "claude_code": "#ff5722",
                "value_analysis": "#ff6f00",
                "theme_selector": "#795548"
            }
        },
        "material_dark": {
            "name": "Material Dark",
            "background": "#212121",
            "card_background": "#424242",
            "text_primary": "#ffffff",
            "text_secondary": "#e0e0e0",
            "border": "#616161",
            "accents": {
                "claude_code": "#ff7043",
                "value_analysis": "#ff8a65",
                "theme_selector": "#8d6e63"
            }
        },
        "monokai": {
            "name": "Monokai",
            "background": "#272822",
            "card_background": "#3e3d32",
            "text_primary": "#f8f8f2",
            "text_secondary": "#cfcfc2",
            "border": "#75715e",
            "accents": {
                "claude_code": "#f92672",
                "value_analysis": "#fd971f",
                "theme_selector": "#ae81ff"
            }
        },
        "github": {
            "name": "GitHub",
            "background": "#ffffff",
            "card_background": "#f6f8fa",
            "text_primary": "#24292e",
            "text_secondary": "#586069",
            "border": "#e1e4e8",
            "accents": {
                "claude_code": "#f66a0a",
                "value_analysis": "#fb8532",
                "theme_selector": "#6f42c1"
            }
        },
        "github_dark": {
            "name": "GitHub Dark",
            "background": "#0d1117",
            "card_background": "#161b22",
            "text_primary": "#c9d1d9",
            "text_secondary": "#b1bac4",
            "border": "#30363d",
            "accents": {
                "claude_code": "#ffa657",
                "value_analysis": "#f0883e",
                "theme_selector": "#a371f7"
            }
        },
        "high_contrast": {
            "name": "High Contrast",
            "background": "#000000",
            "card_background": "#ffffff",
            "text_primary": "#000000",
            "text_secondary": "#000000",
            "border": "#000000",
            "accents": {
                "claude_code": "#ff0000",
                "value_analysis": "#ff6600",
                "theme_selector": "#0066ff"
            }
        }
    }
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, default_theme: str = "dark"):
        # Only initialize once
        if self._initialized:
            return
        # Always call super().__init__() first for QObject
        super().__init__()
        self.current_theme = default_theme
        self.theme_data = self.THEMES.get(default_theme, self.THEMES["dark"])
        self._initialized = True
        
    def set_theme(self, theme_name: str):
        """Set the current theme"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.theme_data = self.THEMES[theme_name]
            self.theme_changed.emit(theme_name)
            return True
        return False
        
    def get_color(self, color_key: str, default: str = "#000000") -> str:
        """Get a color value from the current theme"""
        return self.theme_data.get(color_key, default)
        
    def get_accent_color(self, provider: str, default: str) -> str:
        """Get accent color for a specific provider in current theme"""
        accents = self.theme_data.get('accents', {})
        return accents.get(provider, default)
        
    def get_available_themes(self) -> list:
        """Get list of available theme names"""
        return list(self.THEMES.keys())
    
    def get_card_style(self, provider_name: str) -> str:
        """Get style sheet for a card with colored border
        
        Args:
            provider_name: The name of the provider (e.g., 'claude_code')
            
        Returns:
            CSS style sheet for the card
        """
        # Get colors from current theme
        card_bg = self.get_color('card_background', '#2d2d2d')
        text_color = self.get_color('text_primary', '#ffffff')
        border_color = self.get_color('border', '#404040')
        
        # Get accent color for this provider
        accent_color = self.get_accent_color(provider_name, '#ff6b35')
            
        # Special handling for high contrast theme
        if self.current_theme == 'high_contrast':
            card_bg = "#ffffff"
            text_color = "#000000"
        
        # Create the style sheet
        return f"""
        QFrame {{
            background-color: {card_bg};
            border: 1px solid steelblue;
            border-radius: 4px;
            padding: 0px;
        }}
        /* Ensure labels inside frames don't inherit borders */
        QFrame > QLabel {{
            color: {text_color};
            border: none !important;
            background: transparent;
            padding: 0px;
        }}
        QFrame QLabel {{
            color: {text_color} !important;
            border: none !important;
        }}
        /* Ensure all text in cards uses theme color */
        QFrame * {{
            color: {text_color};
        }}
        QFrame QWidget {{
            border: none !important;
            background: transparent;
        }}
        QProgressBar {{
            border: 1px solid {border_color};
            border-radius: 3px;
            background-color: {border_color};
            text-align: center;
            color: {text_color};
        }}
        QProgressBar::chunk {{
            background-color: {accent_color};
            border-radius: 2px;
        }}
        """
    
    @staticmethod
    def get_dark_palette() -> QPalette:
        """Get dark theme palette"""
        palette = QPalette()
        
        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        
        # Base colors (for input widgets)
        palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
        
        # Text colors
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        
        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        
        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        # Link colors
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        
        # ToolTip colors
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        
        return palette
    
    def get_secondary_text_style(self, font_size: int) -> str:
        """Get style for secondary/muted text that works with current theme"""
        return f"color: {self.get_color('text_secondary', '#666666')}; font-size: {font_size}px;"
        
    def get_palette(self) -> QPalette:
        """Get palette for current theme"""
        palette = QPalette()
        
        # Get colors from theme
        bg = QColor(self.get_color('background'))
        card_bg = QColor(self.get_color('card_background'))
        text = QColor(self.get_color('text_primary'))
        text_secondary = QColor(self.get_color('text_secondary'))
        border = QColor(self.get_color('border'))
        
        # Window colors
        palette.setColor(QPalette.ColorRole.Window, bg)
        palette.setColor(QPalette.ColorRole.WindowText, text)
        
        # Base colors (for input widgets)
        palette.setColor(QPalette.ColorRole.Base, card_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, border)
        
        # Text colors
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        
        # Button colors
        palette.setColor(QPalette.ColorRole.Button, card_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, text)
        
        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white if self.current_theme != 'high_contrast' else Qt.GlobalColor.black)
        
        # Link colors
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        
        # ToolTip colors
        palette.setColor(QPalette.ColorRole.ToolTipBase, card_bg)
        palette.setColor(QPalette.ColorRole.ToolTipText, text)
        
        return palette
    
    @staticmethod
    def get_main_window_style() -> str:
        """Get style sheet for main window"""
        instance = ThemeManager()
        bg_color = instance.get_color('background', '#1e1e1e')
        text_color = instance.get_color('text_primary', '#ffffff')
        
        return f"""
        QMainWindow {{
            background-color: {bg_color};
        }}
        QLabel {{
            color: {text_color};
        }}
        """