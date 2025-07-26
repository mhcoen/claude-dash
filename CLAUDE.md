# CLAUDE.md

This file provides guidance to AI assistants when working with code in this repository.

## Project Overview

Claude Dash (cdash) is a PyQt6-based desktop application that monitors code assistant usage in real-time by reading JSONL files from `~/.claude/projects/`. It provides session tracking, prompt predictions, and usage statistics with a singular focus: answering how many more interactions remain in the current session.

## Design Philosophy

- **One Question, One Answer**: The app exists solely to show remaining interactions
- **Zero Configuration**: Automatically detects subscription plans from usage patterns
- **Minimal UI**: Ultra-compact 18px title bar, no unnecessary metrics
- **Smart Predictions**: Bayesian ML that learns from user's historical patterns

## Common Development Commands

### Installation and Running
```bash
# Install in development mode
pip install -e .

# Run the application
python -m claude_dash

# Build distribution packages
python -m build
```

### Development Workflow
Since there are no tests currently, focus on manual testing by running the application and verifying functionality.

## Architecture Overview

### Core Components

1. **Data Processing Pipeline**
   - `providers/claude_code_reader.py`: Reads JSONL files from Claude projects directory
   - `core/adaptive_bounds.py`: Calculates confidence intervals for prompt predictions
   - Background worker threads poll for new data every 30 seconds

2. **UI Architecture**
   - `ui/main_window.py`: Main application window with QSystemTrayIcon support
   - `ui/cards/claude_code_card.py`: Individual session display widgets
   - Uses PyQt6 signals/slots for thread-safe UI updates

3. **Configuration System**
   - `config/manager.py`: Handles user preferences and settings
   - Default configs in `config/defaults/` (config.json, pricing.json)
   - Subscription plans: Pro (14000), Max 5x (70000), Max 20x (280000) prompts

### Key Design Patterns

- **Model-View Separation**: Data providers are separate from UI components
- **Observer Pattern**: PyQt signals for communication between threads and UI
- **Background Processing**: ThreadPoolExecutor for non-blocking file I/O

### Important Implementation Details

- Session blocks are identified by gaps > 300 seconds between messages
- Prompt predictions use adaptive bounds based on historical usage patterns
- UI scales to system DPI settings (100%, 125%, 150%, 200%)
- Theme system supports Light, Dark, and Auto modes

### File Locations

- User data: `~/.claude/projects/*/chats/*.jsonl`
- Configuration: Platform-specific (macOS: `~/Library/Application Support/ClaudeDash/`)
- Entry point: `claude_dash/main.py`

### Development Notes

- The project uses modern Python packaging (pyproject.toml)
- No test suite exists - manual testing required
- PyQt6 requires special handling for thread safety - always use signals for UI updates
- NumPy is used but not listed in dependencies - consider adding it

### Known Claude Code Bugs We Handle

#### Batch-Write Bug (Affects macOS particularly)
When Claude Code sessions are resumed after running out of context, the conversation history from the resumed session is written to JSONL files with identical timestamps. This creates artificially inflated prompt counts as all prompts from the previous conversation appear to have been sent at the exact same moment.

**How we handle it**: The app detects groups of prompts with identical or near-identical timestamps (within 2 seconds) at the beginning of sessions and filters them out. Batch writes that occur within a session (not at the beginning) are allowed but generate a warning.

**Impact**: Without this fix, prompt counts can be inflated by 10-20 prompts or more, making it appear users have far exceeded their actual usage.

## Screenshot Workflow for UI Development

When working on UI layout issues, use the semi-automated screenshot workflow:

### Taking Screenshots of the Claude Dash Window

1. **Run the screenshot script**:
   ```bash
   ./screenshot-simple.sh
   ```
   This will prompt you to click on the Claude Dash window.

2. **View the screenshot in Claude Code**:
   ```
   Read /tmp/claude-dash-screenshot.png
   ```

### How It Works

- The script uses macOS's `screencapture -W` to capture just the application window (not the full screen)
- Screenshots are saved to `/tmp/claude-dash-screenshot.png`
- This is much more efficient than full-screen captures for iterative UI development
- The script attempts to bring the Claude Dash window to front automatically

### Alternative Methods

- **Manual**: Cmd+Shift+4 → Space → Click window → Paste with Ctrl+V in Claude Code
- **Full automation**: The MCP screenshot tools are installed but have issues with window-specific captures

### MCP Server Management

If the macOS Screen MCP server is needed:
```bash
./mcp-screen-start.sh   # Start the server
./mcp-screen-status.sh  # Check status
./mcp-screen-stop.sh    # Stop the server
```
