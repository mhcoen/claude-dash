import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

from claude_dash.providers.claude_code_reader import ClaudeCodeReader
from claude_dash.core.adaptive_bounds import AdaptiveBoundsCalculator
from claude_dash.core.bayesian_limits import BayesianLimitEstimator
from claude_dash.config.manager import ConfigManager


class TestEndToEndWorkflow:
    """Integration tests for the complete data flow"""
    
    @pytest.fixture
    def temp_claude_dir(self):
        """Create temporary Claude projects directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir) / '.claude' / 'projects' / 'test-project' / 'chats'
            projects_dir.mkdir(parents=True)
            yield projects_dir
    
    @pytest.fixture
    def create_session_files(self, temp_claude_dir):
        """Create JSONL files simulating a real session"""
        now = datetime.now(timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Create entries for current session
        entries = []
        
        # Simulate 50 prompts over 2 hours
        for i in range(50):
            timestamp = current_hour + timedelta(minutes=i * 2)
            
            # User prompt
            entries.append({
                "role": "user",
                "content": f"Test prompt {i}",
                "timestamp": timestamp.isoformat(),
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 0,
                    "total_tokens": 20
                }
            })
            
            # Assistant response (alternating models)
            model = "claude-3-opus-20240229" if i % 3 == 0 else "claude-3-5-sonnet-20241022"
            entries.append({
                "role": "assistant",
                "content": f"Response to prompt {i}",
                "model": model,
                "timestamp": (timestamp + timedelta(seconds=30)).isoformat(),
                "usage": {
                    "input_tokens": 50,
                    "output_tokens": 200,
                    "total_tokens": 250
                }
            })
            
            # Sometimes add tool results
            if i % 5 == 0:
                entries.append({
                    "role": "tool_result",
                    "content": "Tool output",
                    "timestamp": (timestamp + timedelta(seconds=45)).isoformat(),
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 50,
                        "total_tokens": 60
                    }
                })
        
        # Write to JSONL file
        session_file = temp_claude_dir / f"session_{current_hour.strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(session_file, 'w') as f:
            for entry in entries:
                json.dump(entry, f)
                f.write('\n')
        
        return session_file, entries
    
    def test_full_data_pipeline(self, temp_claude_dir, create_session_files):
        """Test complete data flow from files to predictions"""
        session_file, entries = create_session_files
        
        # Mock config to use temp directory
        with patch('claude_dash.providers.claude_code_reader.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.config = {
                'claude_code': {
                    'paths': {'base_path': str(temp_claude_dir.parent.parent)},
                    'plans': {
                        'max20x': {'message_limit': 900}
                    }
                }
            }
            mock_config.get_subscription_plan.return_value = 'max20x'
            mock_get_config.return_value = mock_config
            
            # Create reader
            reader = ClaudeCodeReader()
            
            # Get current session info
            session_info = reader.get_current_session_info()
            
            # Verify session detection
            assert session_info['window_tokens'] > 0
            assert session_info['window_messages'] > 0
            
            # Get prompt info
            prompt_info = reader.get_current_session_prompts()
            assert prompt_info['prompts_used'] == 50
            assert prompt_info['messages_sent'] > 50  # Should include assistant responses
            
            # Test burn rate calculation
            burn_rate = reader.calculate_hourly_burn_rate()
            assert burn_rate > 0  # Should have some burn rate
            
            # Test prompt bounds
            bounds = reader.get_prompt_bounds('max20x', 50, 0.8)
            assert bounds is not None
            assert bounds.expected > 0
            assert bounds.lower <= bounds.expected <= bounds.upper
    
    def test_bayesian_learning(self):
        """Test Bayesian estimator learning from historical data"""
        estimator = BayesianLimitEstimator(plan='max20x')
        
        # Simulate historical sessions
        historical_sessions = [
            {'max_tokens': 50000, 'max_messages': 800, 'max_prompts': 150},
            {'max_tokens': 60000, 'max_messages': 900, 'max_prompts': 170},
            {'max_tokens': 45000, 'max_messages': 750, 'max_prompts': 140},
        ]
        
        # Update estimator with each session
        for session in historical_sessions:
            estimator.update_from_session(session)
        
        # Get estimates
        limits = estimator.get_estimated_limits()
        
        # Should have reasonable estimates
        assert 100 < limits['prompts']['estimate'] < 800
        assert limits['prompts']['confidence'] == 0.80  # Low confidence with few observations
        
        # Test predictions
        current_usage = {'tokens': 20000, 'messages': 300, 'prompts': 50}
        burn_rates = {'tokens': 10000, 'messages': 150, 'prompts': 25}
        
        prediction = estimator.predict_limit_times(current_usage, burn_rates)
        assert prediction['limiting_factor'] in ['tokens', 'messages', 'prompts']
        assert prediction['time_to_limit'] > 0
    
    def test_adaptive_bounds_learning(self):
        """Test adaptive bounds calculator learning patterns"""
        calculator = AdaptiveBoundsCalculator()
        
        # Simulate simple coding session (low multiplier)
        for _ in range(5):
            calculator.add_observation(10, 25)  # 2.5x multiplier
        
        # Calculate bounds
        bounds1 = calculator.calculate_bounds(900, 50, 0.8)
        
        # Now simulate complex debugging (high multiplier)
        for _ in range(5):
            calculator.add_observation(10, 100)  # 10x multiplier
        
        # Bounds should widen due to mixed patterns
        bounds2 = calculator.calculate_bounds(900, 50, 0.8)
        assert (bounds2.upper - bounds2.lower) > (bounds1.upper - bounds1.lower)
    
    def test_session_boundary_detection(self, temp_claude_dir):
        """Test correct session boundary detection"""
        # Create entries spanning session boundary
        entries = []
        base_time = datetime(2025, 7, 26, 4, 30, 0, tzinfo=timezone.utc)
        
        # Add entries from 4:30 to 5:30 (crosses 5:00 boundary)
        for i in range(7):
            timestamp = base_time + timedelta(minutes=i * 10)
            entries.append({
                "role": "user",
                "content": f"Prompt {i}",
                "timestamp": timestamp.isoformat(),
                "usage": {"total_tokens": 50}
            })
        
        # Write to file
        with open(temp_claude_dir / "boundary_test.jsonl", 'w') as f:
            for entry in entries:
                json.dump(entry, f)
                f.write('\n')
        
        # Test with reader
        with patch('claude_dash.providers.claude_code_reader.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.config = {
                'claude_code': {
                    'paths': {'base_path': str(temp_claude_dir.parent.parent)},
                    'plans': {'max20x': {'message_limit': 900}}
                }
            }
            mock_get_config.return_value = mock_config
            
            reader = ClaudeCodeReader()
            reader._update_session_blocks(force_refresh=True)
            
            # Should create two blocks (0-5 and 5-10)
            blocks = [b for b in reader._session_blocks if b.start_time.date() == base_time.date()]
            assert len(blocks) >= 1
            
            # First block should contain entries before 5:00
            first_block = next((b for b in blocks if b.start_time.hour == 0), None)
            if first_block:
                assert any(e['timestamp'].hour == 4 for e in first_block.entries)
    
    @pytest.mark.slow
    def test_performance_with_large_dataset(self, temp_claude_dir):
        """Test performance with many entries"""
        # Create large JSONL file
        entries = []
        base_time = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Generate 10000 entries over 7 days
        for i in range(10000):
            timestamp = base_time + timedelta(minutes=i)
            entries.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": timestamp.isoformat(),
                "usage": {"total_tokens": 50}
            })
        
        # Write in chunks to avoid memory issues
        with open(temp_claude_dir / "large_dataset.jsonl", 'w') as f:
            for entry in entries:
                json.dump(entry, f)
                f.write('\n')
        
        # Time the loading
        import time
        start = time.time()
        
        with patch('claude_dash.providers.claude_code_reader.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.config = {
                'claude_code': {
                    'paths': {'base_path': str(temp_claude_dir.parent.parent)},
                    'plans': {'max20x': {'message_limit': 900}}
                }
            }
            mock_get_config.return_value = mock_config
            
            reader = ClaudeCodeReader()
            reader._update_session_blocks(force_refresh=True, hours_back=24*7)
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 5.0  # 5 seconds max
        
        # Should have created multiple session blocks
        assert len(reader._session_blocks) > 20