#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import time

# Get current time in UTC and local timezone
now = datetime.now(timezone.utc)

# Get local timezone info
is_dst = time.daylight and time.localtime().tm_isdst > 0
local_tz_offset = time.altzone if is_dst else time.timezone
local_tz_hours = local_tz_offset // 3600  # Positive for west of UTC
local_tz_name = time.tzname[1 if is_dst else 0]

def to_local(dt):
    """Convert UTC datetime to local time"""
    return dt - timedelta(seconds=local_tz_offset)

# Sessions are 5-hour windows that start when you first interact after a 5+ hour break
# To find the current session, we need to look at the JSONL files to find session boundaries

# First, let's find all JSONL files and get timestamps
claude_dir = Path.home() / ".claude" / "projects"
jsonl_files = list(claude_dir.rglob("*.jsonl"))

all_timestamps = []
for file_path in jsonl_files:
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'user':
                        ts_str = data.get('timestamp', '')
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            all_timestamps.append(ts)
                except:
                    pass
    except:
        pass

# Sort timestamps
all_timestamps.sort()

# Find session boundaries (gaps > 5 hours indicate new session)
session_starts = []
if all_timestamps:
    session_starts.append(all_timestamps[0])
    
    for i in range(1, len(all_timestamps)):
        time_gap = all_timestamps[i] - all_timestamps[i-1]
        if time_gap > timedelta(hours=5):
            # New session starts at this timestamp, rounded down to hour
            session_start = all_timestamps[i].replace(minute=0, second=0, microsecond=0)
            session_starts.append(session_start)

# Find current session (most recent session start <= now)
session_start = None
session_end = None

for start in reversed(session_starts):
    if start <= now:
        session_start = start
        session_end = start + timedelta(hours=5)
        break

if not session_start:
    print("No active session found")
    exit()

print("=== CURRENT SESSION DETAILS ===")
print(f"Current time: {to_local(now).strftime('%Y-%m-%d %H:%M:%S')} {local_tz_name}")
print(f"Session start: {to_local(session_start).strftime('%Y-%m-%d %H:%M:%S')} {local_tz_name}")
print(f"Session end: {to_local(session_end).strftime('%Y-%m-%d %H:%M:%S')} {local_tz_name}")
print(f"Time remaining: {session_end - now}")
print()

# Find all JSONL files
claude_dir = Path.home() / ".claude" / "projects"
jsonl_files = list(claude_dir.rglob("*.jsonl"))
print(f"Found {len(jsonl_files)} JSONL files across all projects")
print()

# Collect all user prompts from current session
user_prompts = []
total_user_entries = 0
tool_results = 0
entries_by_project = {}

for file_path in jsonl_files:
    project_name = file_path.parent.name
    if project_name not in entries_by_project:
        entries_by_project[project_name] = {"total": 0, "tool_results": 0, "prompts": 0}
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 'user':
                        # Parse timestamp
                        ts_str = data.get('timestamp', '')
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            
                            # Check if in current session (time-based)
                            if session_start <= ts < session_end:
                                    
                                total_user_entries += 1
                                entries_by_project[project_name]["total"] += 1
                                
                                # Get message content
                                msg = data.get('message', {})
                                content = msg.get('content', [])
                                
                                # Check if it's a tool result
                                is_tool_result = False
                                text_content = ""
                                
                                if isinstance(content, list) and content:
                                    first_content = content[0]
                                    if isinstance(first_content, dict):
                                        if first_content.get('type') == 'tool_result':
                                            is_tool_result = True
                                            tool_results += 1
                                            entries_by_project[project_name]["tool_results"] += 1
                                        else:
                                            text_content = first_content.get('text', '')
                                elif isinstance(content, str):
                                    text_content = content
                                
                                if not is_tool_result and text_content:
                                    # Filter out non-English text and system messages
                                    text_stripped = text_content.strip()
                                    
                                    # Skip empty or very short content
                                    if len(text_stripped) < 3:
                                        continue
                                        
                                    # Skip empty content
                                    if not text_stripped:
                                        continue
                                        
                                    # Skip interrupt messages
                                    if text_stripped.startswith('[Request interrupted'):
                                        continue
                                    
                                    # Skip specific system messages
                                    skip_patterns = [
                                        "Caveat: The messages below",
                                        "<command-name>",
                                        "<local-command-stdout>",
                                        "<user-memory-input>",
                                        "This session is being continued from a previous conversation"
                                    ]
                                    if any(pattern in text_stripped for pattern in skip_patterns):
                                        continue
                                    
                                    entries_by_project[project_name]["prompts"] += 1
                                    user_prompts.append({
                                        'timestamp': ts,
                                        'text': text_content,
                                        'project': project_name
                                    })
                except:
                    pass
    except:
        pass

# Sort by timestamp
user_prompts.sort(key=lambda x: x['timestamp'])

# Filter out batch-written prompts at the beginning of the session
if user_prompts:
    filtered_prompts = []
    
    # Find the first actual activity timestamp
    first_activity = user_prompts[0]['timestamp'] if user_prompts else session_start
    first_activity_buffer = first_activity + timedelta(minutes=5)  # 5 minute buffer from first activity
    
    # Group prompts by timestamp (within 2 seconds)
    timestamp_groups = {}
    for prompt in user_prompts:
        # Round to nearest 2 seconds to group nearly-identical timestamps
        ts_key = prompt['timestamp'].replace(microsecond=0)
        ts_key = ts_key.replace(second=(ts_key.second // 2) * 2)
        
        if ts_key not in timestamp_groups:
            timestamp_groups[ts_key] = []
        timestamp_groups[ts_key].append(prompt)
    
    # Check each timestamp group
    batch_write_count = 0
    for ts_key, prompts in sorted(timestamp_groups.items()):
        if len(prompts) > 3 and ts_key <= first_activity_buffer:
            # This is likely a batch write at the beginning of the session
            batch_write_count += len(prompts)
            local_ts = to_local(prompts[0]['timestamp'])
            print(f"WARNING: Detected {len(prompts)} batch-written prompts at {local_ts.strftime('%Y-%m-%d %H:%M:%S')} {local_tz_name} (beginning of session)")
        else:
            # Keep these prompts
            filtered_prompts.extend(prompts)
            if len(prompts) > 3:
                # Warning for batch writes within the session
                local_ts = to_local(prompts[0]['timestamp'])
                print(f"WARNING: Detected {len(prompts)} prompts with near-identical timestamps at {local_ts.strftime('%Y-%m-%d %H:%M:%S')} {local_tz_name} (within session)")
    
    # Re-sort after filtering
    filtered_prompts.sort(key=lambda x: x['timestamp'])
    
    # Update user_prompts to filtered list
    user_prompts = filtered_prompts
    
    if batch_write_count > 0:
        print(f"Filtered out {batch_write_count} batch-written prompts from the beginning of the session")
        print()

print(f"=== SESSION STATISTICS ===")
print(f"Total user entries: {total_user_entries}")
print(f"Tool results: {tool_results}")
print(f"Actual user prompts: {len(user_prompts)}")
print()

print("=== BREAKDOWN BY PROJECT ===")
# Recalculate project stats based on filtered prompts
project_prompt_counts = {}
for prompt in user_prompts:
    project = prompt['project']
    project_prompt_counts[project] = project_prompt_counts.get(project, 0) + 1

for project, stats in sorted(entries_by_project.items()):
    if stats["total"] > 0:
        print(f"{project}:")
        print(f"  Total entries: {stats['total']}")
        print(f"  Tool results: {stats['tool_results']}")
        print(f"  Actual prompts: {project_prompt_counts.get(project, 0)}")
        
print()

print("=== ALL USER PROMPTS IN CURRENT SESSION ===")
for i, prompt in enumerate(user_prompts, 1):
    local_time = to_local(prompt['timestamp'])
    time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{i}. [{time_str} {local_tz_name}] Project: {prompt['project']}")
    # Show full prompt or truncate if too long
    text = prompt['text'].strip()
    lines = text.split('\n')
    if len(lines) > 5 or len(text) > 300:
        # Show first few lines
        for line in lines[:3]:
            print(f"   {line}")
        if len(lines) > 3:
            print(f"   ... ({len(lines) - 3} more lines)")
    else:
        for line in lines:
            print(f"   {line}")

if not user_prompts:
    print("No user prompts found in current session")