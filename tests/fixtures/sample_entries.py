from datetime import datetime, timezone

# Sample JSONL entries for testing
SAMPLE_ENTRIES = [
    # User prompt with tool use
    {
        "role": "user",
        "content": "Test the application",
        "timestamp": datetime(2025, 7, 26, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 10,
            "output_tokens": 50,
            "total_tokens": 60
        }
    },
    # Assistant response
    {
        "role": "assistant", 
        "content": "I'll help test the application",
        "timestamp": datetime(2025, 7, 26, 1, 0, 30, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 20,
            "output_tokens": 100,
            "total_tokens": 120
        }
    },
    # Tool result (should be filtered)
    {
        "role": "tool_result",
        "content": "Command output",
        "timestamp": datetime(2025, 7, 26, 1, 1, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 5,
            "output_tokens": 20,
            "total_tokens": 25
        }
    },
    # User interrupt (should be filtered)
    {
        "role": "user",
        "content": "[Request interrupted by user]",
        "timestamp": datetime(2025, 7, 26, 1, 2, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 5,
            "output_tokens": 0,
            "total_tokens": 5
        }
    },
    # Empty content (should be filtered)
    {
        "role": "user",
        "content": "",
        "timestamp": datetime(2025, 7, 26, 1, 3, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 1,
            "output_tokens": 0,
            "total_tokens": 1
        }
    },
    # Valid user prompt
    {
        "role": "user",
        "content": "Run the build process",
        "timestamp": datetime(2025, 7, 26, 1, 5, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 15,
            "output_tokens": 0,
            "total_tokens": 15
        }
    },
    # System reminder (should be filtered)
    {
        "role": "user",
        "content": "<system-reminder>Check memory usage</system-reminder>",
        "timestamp": datetime(2025, 7, 26, 1, 6, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 8,
            "output_tokens": 0,
            "total_tokens": 8
        }
    },
    # Opus model usage
    {
        "role": "assistant",
        "content": "Building the project now",
        "model": "claude-3-opus-20240229",
        "timestamp": datetime(2025, 7, 26, 1, 7, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 30,
            "output_tokens": 150,
            "total_tokens": 180
        }
    },
    # Sonnet model usage
    {
        "role": "assistant",
        "content": "Task completed",
        "model": "claude-3-5-sonnet-20241022",
        "timestamp": datetime(2025, 7, 26, 1, 8, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 20,
            "output_tokens": 80,
            "total_tokens": 100
        }
    }
]

# Entries from a previous day (for date filtering tests)
OLD_ENTRIES = [
    {
        "role": "user",
        "content": "Yesterday's prompt",
        "timestamp": datetime(2025, 7, 25, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 10,
            "output_tokens": 0,
            "total_tokens": 10
        }
    },
    {
        "role": "assistant",
        "content": "Yesterday's response",
        "timestamp": datetime(2025, 7, 25, 1, 0, 30, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 20,
            "output_tokens": 100,
            "total_tokens": 120
        }
    }
]

# Multiple session blocks for testing
MULTI_SESSION_ENTRIES = [
    # Session 1: 0:00-5:00 with 50 prompts
    *[{
        "role": "user" if i % 3 == 0 else "assistant",
        "content": f"Message {i}",
        "timestamp": datetime(2025, 7, 26, 0, i * 2, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 10,
            "output_tokens": 50 if i % 3 != 0 else 0,
            "total_tokens": 60 if i % 3 != 0 else 10
        }
    } for i in range(50)],
    
    # Session 2: 8:00-13:00 with 30 prompts  
    *[{
        "role": "user" if i % 3 == 0 else "assistant",
        "content": f"Message {i + 50}",
        "timestamp": datetime(2025, 7, 26, 8, i * 3, 0, tzinfo=timezone.utc).isoformat(),
        "usage": {
            "input_tokens": 15,
            "output_tokens": 100 if i % 3 != 0 else 0,
            "total_tokens": 115 if i % 3 != 0 else 15
        }
    } for i in range(30)]
]