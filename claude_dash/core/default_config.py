"""
Default configuration for Claude Dash
"""

DEFAULT_CONFIG = {
    "app_name": "Claude Dash",
    "window": {
        "width": 800,
        "height": 600,
        "min_width": 600,
        "min_height": 400
    },
    "claude_code": {
        "subscription_plan": "auto",  # "auto" to detect from usage, or specify "pro", "max5x", "max20x"
        "auto_detect_plan": True,  # Enable automatic plan detection from usage history
        "plans": {
            "pro": {
                "name": "Pro",
                "monthly_cost": 20,
                "session_token_limit": 19000,
                "session_cost_limit": 18.0,
                "message_limit": 45,  # Pro has 45 messages per 5 hours
                "prompt_limit": 800,  # Claude Code CLI maximum
                "display_name": "Claude Pro",
                "sessions_per_month": 120,  # Effectively unlimited
                "detection_threshold": 45  # Max messages in a session to detect this plan
            },
            "max5x": {
                "name": "Max 5×",
                "monthly_cost": 100,
                "session_token_limit": 88000,
                "session_cost_limit": 35.0,
                "message_limit": 225,  # 5x Pro = 5 * 45 = 225
                "prompt_limit": 800,  # Claude Code CLI maximum
                "display_name": "Claude Max 5×",
                "sessions_per_month": 120,  # Effectively unlimited
                "detection_threshold": 225  # Max messages in a session to detect this plan
            },
            "max20x": {
                "name": "Max 20×",
                "monthly_cost": 200,
                "session_token_limit": 220000,
                "session_cost_limit": 140.0,
                "message_limit": 900,  # 20x Pro = 20 * 45 = 900
                "prompt_limit": 800,  # Claude Code CLI maximum
                "display_name": "Claude Max 20×",
                "sessions_per_month": 120,
                "detection_threshold": 900  # Max messages in a session to detect this plan
            }
        },
        "session_duration_hours": 5,
        "session_gap_minutes": 5
    },
    "ui": {
        "theme": "dark",
        "update_frequency_seconds": 30,  # How often to refresh data
        "font_sizes": {
            "tiny": 10,
            "small": 12,
            "medium": 14,
            "large": 16,
            "huge": 20
        }
    },
    "analysis": {
        "cost_thresholds": {
            "api_optimal": 100,
            "max5_optimal": 200
        },
        "quick_start_hours": 24,
        "cache_duration_seconds": 30
    },
    "paths": {
        "claude_data": "~/.claude/projects",
        "logs": "~/.claude-dash/logs"
    },
    "themes": {
        "light": {
            "name": "Light",
            "background": "#f5f5f5",
            "card_background": "white",
            "text_primary": "#000000",
            "text_secondary": "#666666",
            "border": "#e0e0e0",
            "accent": "#ff6b35"
        },
        "dark": {
            "name": "Dark",
            "background": "#1e1e1e",
            "card_background": "#2d2d2d",
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0",
            "border": "#404040",
            "accent": "#ff8a65"
        },
        "dusk": {
            "name": "Dusk",
            "background": "#2a2a3e",
            "card_background": "#353548",
            "text_primary": "#e1e1e6",
            "text_secondary": "#a0a0b8",
            "border": "#4a4a6a",
            "accent": "#ff7970"
        },
        "midnight": {
            "name": "Midnight",
            "background": "#0d1117",
            "card_background": "#161b22",
            "text_primary": "#c9d1d9",
            "text_secondary": "#8b949e",
            "border": "#30363d",
            "accent": "#58a6ff"
        }
    },
    "default_theme": "dark"
}

DEFAULT_PRICING = {
    "claude-opus-4-20250514": {
        "input": 15.0,
        "output": 75.0,
        "cache_creation": 18.75,
        "cache_read": 1.5
    },
    "default": {
        "input": 3.0,
        "output": 15.0,
        "cache_creation": 3.75,
        "cache_read": 0.3
    }
}

DEFAULT_PRICING_FULL = {
    "last_updated": "2025-01-23",
    "currency": "USD",
    "per_million_tokens": True,
    "models": {
        "claude-3-opus-20240229": {
            "name": "Claude 3 Opus",
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5
        },
        "claude-opus-4-20250514": {
            "name": "Claude 4 Opus",
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5
        },
        "claude-3.5-sonnet": {
            "name": "Claude 3.5 Sonnet",
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3
        },
        "claude-3-sonnet": {
            "name": "Claude 3 Sonnet",
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3
        },
        "claude-sonnet-4-20250514": {
            "name": "Claude 4 Sonnet",
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3
        },
        "claude-3-haiku": {
            "name": "Claude 3 Haiku",
            "input": 0.25,
            "output": 1.25,
            "cache_creation": 0.3125,
            "cache_read": 0.025
        },
        "claude-3.5-haiku": {
            "name": "Claude 3.5 Haiku",
            "input": 0.8,
            "output": 4.0,
            "cache_creation": 1.0,
            "cache_read": 0.08
        },
        "<synthetic>": {
            "name": "Synthetic",
            "input": 0.0,
            "output": 0.0,
            "cache_creation": 0.0,
            "cache_read": 0.0
        },
        "default": {
            "name": "Default",
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3
        }
    }
}