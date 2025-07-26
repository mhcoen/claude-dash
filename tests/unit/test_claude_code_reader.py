import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from claude_dash.providers.claude_code_reader import (
    ClaudeCodeReader, SessionBlock, normalize_to_utc
)
from claude_dash.config.manager import ConfigManager
from tests.fixtures.sample_entries import SAMPLE_ENTRIES, OLD_ENTRIES, MULTI_SESSION_ENTRIES


class TestSessionBlock:
    def test_initialization(self):
        start_time = datetime(2025, 7, 26, 8, 0, 0)
        block = SessionBlock(start_time)
        
        assert block.start_time == start_time
        assert block.end_time == start_time + timedelta(hours=5)
        assert block.entries == []
        assert block.opus_count == 0
        assert block.sonnet_count == 0
        assert block.is_active is False
    
    def test_contains_timestamp(self):
        start_time = datetime(2025, 7, 26, 8, 0, 0)
        block = SessionBlock(start_time)
        
        # Timestamp within block
        assert block.contains_timestamp(datetime(2025, 7, 26, 10, 30, 0))
        
        # Timestamp at start
        assert block.contains_timestamp(start_time)
        
        # Timestamp just before end
        assert block.contains_timestamp(datetime(2025, 7, 26, 12, 59, 59))
        
        # Timestamp after block
        assert not block.contains_timestamp(datetime(2025, 7, 26, 13, 0, 1))
        
        # Timestamp before block
        assert not block.contains_timestamp(datetime(2025, 7, 26, 7, 59, 59))


class TestNormalizeToUTC:
    def test_already_utc(self):
        dt = datetime(2025, 7, 26, 10, 0, 0, tzinfo=timezone.utc)
        result = normalize_to_utc(dt)
        assert result == dt.replace(tzinfo=None)
    
    def test_naive_datetime(self):
        dt = datetime(2025, 7, 26, 10, 0, 0)
        result = normalize_to_utc(dt)
        assert result == dt  # Should return as-is
    
    def test_with_timezone(self):
        # Create a timezone-aware datetime
        from datetime import timezone as tz
        eastern = tz(timedelta(hours=-5))
        dt = datetime(2025, 7, 26, 10, 0, 0, tzinfo=eastern)
        
        result = normalize_to_utc(dt)
        # 10:00 Eastern = 15:00 UTC
        assert result == datetime(2025, 7, 26, 15, 0, 0)


class TestClaudeCodeReader:
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ConfigManager)
        config.config = {
            'claude_code': {
                'paths': {
                    'base_path': '~/.claude/projects'
                },
                'plans': {
                    'pro': {'message_limit': 300},
                    'max5x': {'message_limit': 450},
                    'max20x': {'message_limit': 900}
                }
            }
        }
        config.get_subscription_plan.return_value = 'max20x'
        return config
    
    @pytest.fixture
    def reader(self, mock_config):
        with patch('claude_dash.providers.claude_code_reader.get_config', return_value=mock_config):
            return ClaudeCodeReader()
    
    def test_initialization(self, reader):
        assert reader._session_blocks == []
        assert reader._entries_cache == []
        assert reader._bounds_calculator is not None
        assert reader._last_update is None
    
    def test_parse_timestamp(self, reader):
        # ISO format with Z
        dt = reader._parse_timestamp("2025-07-26T10:00:00.000Z")
        assert dt == datetime(2025, 7, 26, 10, 0, 0)
        
        # ISO format with timezone
        dt = reader._parse_timestamp("2025-07-26T10:00:00+00:00")
        assert dt == datetime(2025, 7, 26, 10, 0, 0)
        
        # Plain format
        dt = reader._parse_timestamp("2025-07-26 10:00:00")
        assert dt == datetime(2025, 7, 26, 10, 0, 0)
        
        # Invalid format
        assert reader._parse_timestamp("invalid") is None
    
    def test_load_entries_from_files(self, reader):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test JSONL file
            test_file = Path(tmpdir) / "test.jsonl"
            with open(test_file, 'w') as f:
                for entry in SAMPLE_ENTRIES:
                    json.dump(entry, f)
                    f.write('\n')
            
            entries = reader._load_entries([test_file], hours_back=24)
            
            # Should load all entries
            assert len(entries) == len(SAMPLE_ENTRIES)
            
            # Check first entry
            assert entries[0]['role'] == 'user'
            assert entries[0]['content'] == 'Test the application'
    
    def test_load_entries_filters_old(self, reader):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            with open(test_file, 'w') as f:
                # Add old entries
                for entry in OLD_ENTRIES:
                    json.dump(entry, f)
                    f.write('\n')
            
            # Load with 1 hour cutoff (should exclude yesterday's entries)
            entries = reader._load_entries([test_file], hours_back=1)
            assert len(entries) == 0
    
    def test_create_session_blocks(self, reader):
        # Create entries spanning multiple hours
        entries = []
        base_time = datetime(2025, 7, 26, 0, 0, 0)
        
        # Add entries at hours 0, 3, 8
        for hour in [0, 3, 8]:
            entries.append({
                'timestamp': base_time + timedelta(hours=hour),
                'usage': {'total_tokens': 100}
            })
        
        blocks = reader._create_session_blocks(entries)
        
        # Should create 2 blocks (0-5 and 8-13)
        assert len(blocks) == 2
        assert blocks[0].start_time.hour == 0
        assert blocks[1].start_time.hour == 8
    
    def test_add_entry_to_block_filters_tool_results(self, reader):
        block = SessionBlock(datetime(2025, 7, 26, 8, 0, 0))
        
        # Add tool result
        reader._add_entry_to_block(block, {
            'role': 'tool_result',
            'content': 'output',
            'usage': {'total_tokens': 100}
        })
        
        # Should not count as prompt
        assert len(block.entries) == 1
        assert block.entries[0]['prompts_in_block'] == 0
    
    def test_add_entry_to_block_filters_interrupts(self, reader):
        block = SessionBlock(datetime(2025, 7, 26, 8, 0, 0))
        
        # Add interrupt
        reader._add_entry_to_block(block, {
            'role': 'user',
            'content': '[Request interrupted by user]',
            'usage': {'total_tokens': 10}
        })
        
        # Should not count as prompt
        assert len(block.entries) == 1
        assert block.entries[0]['prompts_in_block'] == 0
    
    def test_add_entry_to_block_counts_valid_prompts(self, reader):
        block = SessionBlock(datetime(2025, 7, 26, 8, 0, 0))
        
        # Add valid user prompt
        reader._add_entry_to_block(block, {
            'role': 'user',
            'content': 'Test prompt',
            'usage': {'total_tokens': 10},
            'timestamp': datetime(2025, 7, 26, 8, 0, 0)
        })
        
        # Should count as prompt
        assert len(block.entries) == 1
        assert block.entries[0]['prompts_in_block'] == 1
    
    def test_add_entry_to_block_filters_old_prompts_in_active_session(self, reader):
        block = SessionBlock(datetime(2025, 7, 26, 8, 0, 0))
        block.is_active = True
        
        # Add prompt from yesterday (same hour)
        reader._add_entry_to_block(block, {
            'role': 'user',
            'content': 'Old prompt',
            'usage': {'total_tokens': 10},
            'timestamp': datetime(2025, 7, 25, 8, 30, 0)
        })
        
        # Should not be added to active block
        assert len(block.entries) == 0
    
    def test_add_entry_to_block_tracks_model_usage(self, reader):
        block = SessionBlock(datetime(2025, 7, 26, 8, 0, 0))
        
        # Add Opus response
        reader._add_entry_to_block(block, {
            'role': 'assistant',
            'model': 'claude-3-opus-20240229',
            'usage': {'total_tokens': 100}
        })
        
        # Add Sonnet response
        reader._add_entry_to_block(block, {
            'role': 'assistant',
            'model': 'claude-3-5-sonnet-20241022',
            'usage': {'total_tokens': 50}
        })
        
        assert block.opus_count == 1
        assert block.sonnet_count == 1
    
    def test_get_current_block(self, reader):
        # Create blocks
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Add past and current blocks
        past_block = SessionBlock(current_hour - timedelta(hours=10))
        current_block = SessionBlock(current_hour)
        reader._session_blocks = [past_block, current_block]
        
        result = reader._get_current_block()
        assert result == current_block
    
    def test_get_current_block_none_found(self, reader):
        # No blocks
        reader._session_blocks = []
        assert reader._get_current_block() is None
        
        # Only old blocks
        old_block = SessionBlock(datetime.now() - timedelta(days=1))
        reader._session_blocks = [old_block]
        assert reader._get_current_block() is None
    
    def test_get_current_session_info(self, reader):
        # Mock file loading
        with patch.object(reader, '_load_entries') as mock_load:
            mock_load.return_value = SAMPLE_ENTRIES
            
            with patch.object(reader, '_update_session_blocks'):
                info = reader.get_current_session_info()
                
                assert 'session_start' in info
                assert 'window_tokens' in info
                assert 'window_messages' in info
                assert 'model_breakdown' in info
    
    def test_get_current_session_prompts(self, reader):
        # Create active block with prompts
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        block = SessionBlock(current_hour)
        block.is_active = True
        
        # Add entries
        for i in range(5):
            reader._add_entry_to_block(block, {
                'role': 'user',
                'content': f'Prompt {i}',
                'usage': {'total_tokens': 10},
                'timestamp': current_hour + timedelta(minutes=i)
            })
            reader._add_entry_to_block(block, {
                'role': 'assistant',
                'content': f'Response {i}',
                'usage': {'total_tokens': 50}
            })
        
        reader._session_blocks = [block]
        
        result = reader.get_current_session_prompts()
        assert result['prompts_used'] == 5
        assert result['messages_sent'] == 10  # 5 user + 5 assistant
        assert result['multiplication_factor'] == 2.0  # 10 messages / 5 prompts
    
    def test_calculate_hourly_burn_rate(self, reader):
        # Create active block
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_time = now - timedelta(hours=2)
        block = SessionBlock(start_time.replace(minute=0, second=0, microsecond=0))
        block.is_active = True
        
        # Add 1000 tokens
        reader._add_entry_to_block(block, {
            'role': 'user',
            'usage': {'total_tokens': 1000}
        })
        
        reader._session_blocks = [block]
        
        burn_rate = reader.calculate_hourly_burn_rate()
        # 1000 tokens / 2 hours = 500 tokens/hour
        assert abs(burn_rate - 500) < 100  # Allow some tolerance
    
    def test_get_prompt_bounds(self, reader):
        # Mock adaptive bounds calculator
        with patch.object(reader._bounds_calculator, 'calculate_bounds') as mock_calc:
            from claude_dash.core.adaptive_bounds import PromptBounds
            mock_calc.return_value = PromptBounds(lower=100, expected=150, upper=200)
            
            bounds = reader.get_prompt_bounds('max20x', 50, 0.8)
            
            assert bounds.lower == 100
            assert bounds.expected == 150
            assert bounds.upper == 200
            
            # Check calculator was called with correct params
            mock_calc.assert_called_once_with(
                message_limit=900,  # max20x limit
                prompts_used=50,
                confidence=0.8
            )
    
    def test_get_historical_session_maximums(self, reader):
        # Create historical blocks
        blocks = []
        for i in range(3):
            block = SessionBlock(datetime(2025, 7, 20 + i, 8, 0, 0))
            # Add varying amounts of usage
            tokens = (i + 1) * 10000
            messages = (i + 1) * 100
            prompts = (i + 1) * 50
            
            for _ in range(prompts):
                reader._add_entry_to_block(block, {
                    'role': 'user',
                    'content': 'test',
                    'usage': {'total_tokens': tokens // prompts},
                    'timestamp': block.start_time
                })
            
            blocks.append(block)
        
        reader._session_blocks = blocks
        
        maximums = reader.get_historical_session_maximums(days_back=7)
        
        # Should find the maximum values
        assert maximums['max_tokens'] == 30000  # From day 3
        assert maximums['max_prompts'] == 150    # From day 3
        assert maximums['sessions_analyzed'] == 3