# Claude Dash

<p align="center">
  <img src="https://raw.githubusercontent.com/mhcoen/claude-dash/main/claude-dash-screenshot.png" alt="Claude Dash Dark Theme" width="400">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/mhcoen/claude-dash/main/claude-dash-screenshot-light.png" alt="Claude Dash Light Theme" width="400">
</p>

<p align="center">
  <strong>One question answered: How many more interactions do I have left?</strong>
</p>

<p align="center">
  <em>A minimalist session tracker that shows only what matters - your remaining Claude Code prompts</em>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#development">Development</a> •
  <a href="#building">Building</a>
</p>

## Overview

Claude Dash answers one critical question: **How many more interactions can I have with Claude Code in this session?**

Unlike other usage trackers that bombard you with metrics, Claude Dash has a singular focus - showing you exactly how many prompts you have left before your session expires. Every design decision prioritizes this core mission.

**Key Insight**: Claude Code primarily enforces message limits, not token limits*. You get some number of interactions per 5-hour session, and Claude Dash helps you track what really matters - how many more you have.

*Note: Very long messages, large files, or extensive session context can sometimes reduce the number of interactions below your plan's nominal quota.

### Design Philosophy

- **One Question, One Answer**: How many prompts do you have left? That's it
- **Minimal Interface**: No clutter, no unnecessary metrics, just what you need
- **Adaptive Learning**: Personalizes to your unique coding patterns over time
- **Actionable Information**: Know when to switch to Sonnet for more interactions

## Features

### Core Functionality
- **Interactions Remaining**: The ONE number that matters - how many more prompts you can send
- **Bayesian Predictions**: Statistical analysis that tells you if you'll hit limits this session
- **Model Usage Tracking**: See your Opus/Sonnet mix and know when to switch for more interactions
- **Real-Time Updates**: Always current with 30-second refresh cycles

### Why Our Approach Works
- **Focused Design**: We show only what affects your remaining interactions
- **Personalized Learning**: The app learns YOUR patterns, not generic averages
- **Actionable Insights**: Clear guidance on whether to continue or switch models
- **Zero Configuration**: Just launch and go - automatically determines your subscription plan and reads Claude's local data

### Technical Details
- **Compact Interface**: Minimal window footprint
- **Themeable**: 13 themes including high contrast options
- **Scalable UI**: 75%-200% scaling for any display
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Installation

### Requirements
- Python 3.8 or higher
- Claude Code installed and used on your system

### Install with uvx (Recommended)

The easiest way to run Claude Dash is with [uvx](https://github.com/astral-sh/uv):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh  # On macOS/Linux
# Or see https://github.com/astral-sh/uv for other platforms

# Run Claude Dash (once published to PyPI)
uvx claude-dash
```

### Install with pip

```bash
# Once published to PyPI
pip install claude-dash
claude-dash
```

### Install from source

1. **Clone the repository:**
```bash
git clone https://github.com/mhcoen/claude-dash.git
cd claude-dash
```

2. **Install in development mode:**
```bash
pip install -e .
```

4. **Run Claude Dash:**
```bash
python src/main.py
```

## Usage

Simply launch Claude Dash - **no configuration needed**. The app automatically:

1. **Determines your subscription plan** from your usage patterns
2. **Shows your remaining prompts** with ML-powered predictions
3. **Learns your coding style** to improve accuracy over time (tracks message frequency, session duration, and usage spikes from your past 7 days)
4. **Updates every 30 seconds** with real-time data

That's it. Just run it and get your answer.

Claude Dash parses `~/.claude/projects/*/chats/*.jsonl` files in real-time with no upload or cloud processing - your data never leaves your machine.

### Command Line Options

```bash
claude-dash [options]
```

- `--version` - Show version information
- `--debug` - Enable debug logging (saves to `/tmp/claude-dash-debug.log`)
- `--log-file FILE` - Write logs to specified file
- `--quiet` - Suppress all console output

### Understanding the Display

The main card shows:
- **Interactions: X used** - Number of prompts you've sent in this session
- **Remaining: ~X** - Estimated prompts left based on your usage patterns (~ indicates approximation)
- **Burn rate: X / hour** - Current rate of prompt consumption
- **Session Time** - Progress bar showing time elapsed and remaining
- **Model Usage** - Percentage of Opus vs Sonnet usage

Below that:
- **Prediction text** - Whether you're likely to hit limits this session
- **Limiting factor** - Which resource (messages/prompts/tokens) will run out first
- **Confidence level** - How reliable the prediction is based on available data

### Keyboard Shortcuts
- **T**: Cycle through themes
- **Ctrl/Cmd +**: Increase UI scale
- **Ctrl/Cmd -**: Decrease UI scale

## Configuration

Claude Dash works out of the box with **zero configuration required**. It automatically:
- Determines your Claude subscription plan from your usage patterns
- Learns your personal usage style over time
- Adapts predictions based on your history

Advanced users can find configuration files in `~/.claude-dash/` if they want to customize themes or UI settings, but this is completely optional.

To reset configuration to defaults, simply delete `~/.claude-dash/` and restart the app.

### Advanced Configuration

For power users who want to fine-tune prediction accuracy, the following values can be adjusted in `~/.claude-dash/config.json`:

```json
"analysis": {
    "adaptive_bounds": {
        "simple_threshold": 3,      // Messages below this = simple pattern
        "complex_threshold": 9,     // Messages above this = complex pattern
        "pattern_defaults": {
            "simple": 3.0,          // Expected multiplier for simple tasks
            "moderate": 7.0,        // Expected multiplier for moderate tasks
            "complex": 18.0,        // Expected multiplier for complex tasks
            "mixed": 10.0           // Expected multiplier for mixed patterns
        }
    }
}
```

These thresholds affect how the app categorizes your coding patterns and predicts future usage. Adjust them if you find predictions consistently over or under-estimating your remaining prompts.

## How Predictions Work

Claude Dash uses a **Bayesian machine learning algorithm** to predict when you'll hit session limits. This system learns from your actual usage patterns to provide increasingly accurate predictions.

### For Users with Existing Claude Code History

If you've been using Claude Code before installing Claude Dash:
- **Immediate predictions**: The app analyzes your past 7 days of usage history on first launch
- **Accurate from day one**: Your historical sessions train the model instantly
- **Continuous improvement**: Each new session refines the predictions further

### For New Claude Code Users

If you're new to Claude Code or have limited history:
- **Initial estimates**: The app starts with conservative estimates based on your subscription plan
- **Learning phase**: Shows "Low confidence - Gathering initial data" while learning your patterns
- **Quick adaptation**: After 5-10 sessions, predictions become highly accurate
- **Personalized limits**: The app discovers YOUR actual limits, not theoretical maximums

### Understanding the Predictions

The app predicts whether you'll hit limits based on:
1. **Current burn rate**: How fast you're using prompts/messages/tokens in this session
2. **Historical patterns**: Your typical usage intensity from past sessions
3. **Time remaining**: Hours left in your current 5-hour session window
4. **Limiting factor**: Which resource (messages, prompts, or tokens) you'll exhaust first

**Why we show approximate numbers**: The "~" before remaining prompts indicates these are estimates, not guarantees. Your actual limit depends on task complexity - simple queries use fewer messages than complex debugging sessions. More importantly, there's inherent randomness in responses that cannot be predicted or modeled. 

**What we don't predict**: We don't try to tell you exactly when your session will expire (e.g., "you'll run out at 3:47 PM"). Instead, we answer the question that actually matters: are you likely to run out of interactions before the session ends?

**Prediction states:**
- 🟢 **Very unlikely to hit any limits**: You'll run out of time before hitting limits
- ⚪ **Unlikely to hit any limits**: Comfortable margin before session ends
- 🟠 **Likely to hit limits**: Current pace suggests you'll hit limits near session end
- 🔴 **Very likely to hit limits**: You'll hit limits well before session expires

### Pro Tip: Model Choice Affects Your Limits

The Model Usage bar shows your Opus vs Sonnet usage:

- **Opus**: More powerful but has significantly stricter usage limits
- **Sonnet**: Lighter model with much more generous limits

**When running low on interactions**: Switch to Sonnet to extend your session. You'll get many more interactions, though responses may be less sophisticated for complex tasks.

### Confidence Levels

The prediction confidence depends on how much data the system has analyzed:
- **High confidence**: 10+ sessions analyzed - predictions are highly reliable
- **Medium confidence**: 5-10 sessions analyzed - good predictions, still refining
- **Low confidence**: <5 sessions analyzed - initial learning phase

The confidence indicator appears below the prediction and shows whether the system is using your personalized data or still learning your patterns.

## How It Works

Claude Dash reads usage data from Claude Code's local JSONL files in `~/.claude/projects/`:

1. **Prompt Detection**: Identifies user prompts vs assistant messages
2. **Pattern Analysis**: Tracks message multiplication (simple: 2-3x, complex: 10-20x)
3. **Adaptive Bounds**: Calculates confidence ranges based on recent usage
4. **Real-Time Updates**: Refreshes every 30 seconds with current session data

### Technical Details: Bayesian Prediction System

The app uses a Beta-Binomial Bayesian model to predict session limits:

- **Prior Beliefs**: Starts with plan-specific priors (e.g., Pro: 12-18 prompts)
- **Evidence Collection**: Each session that hits limits provides evidence about your actual limits
- **Posterior Updates**: The Beta distribution parameters (α, β) update based on how close you get to limits
- **Personalization**: After 5-10 sessions, predictions converge to YOUR specific usage patterns

The key insight: Not all users hit the same limits. Some consistently hit token limits, others message limits. The Bayesian approach discovers which limit affects YOU most, not what the documentation claims.

For implementation details, see [`claude_dash/core/bayesian_limits.py`](claude_dash/core/bayesian_limits.py).

## Development

For development setup and contribution guidelines, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Building

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --name="Claude Dash" --windowed --onefile src/main.py
```

The executable will be created in the `dist/` directory.

## Troubleshooting

### Common Issues

**"No Claude data found"**
- Ensure Claude Code is installed and you've used it recently
- Check that `~/.claude/projects/` contains JSONL files

**"Prompts showing 0"**
- This means no active session was found
- Start using Claude Code and the display will update within 30 seconds

**"Confidence bounds seem wide"**
- This is normal when switching between simple and complex tasks
- The bounds will tighten as you develop consistent usage patterns

## Contributing

Contributions welcome! For major changes, please open an issue first.

## Author

**Michael Coen**  
Email: [mhcoen@gmail.com](mailto:mhcoen@gmail.com), [mhcoen@alum.mit.edu](mailto:mhcoen@alum.mit.edu)

## Acknowledgments

Special thanks to:
[Maciek Dymarczyk](https://github.com/Maciek-roboblog) for [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) and to [Ryotaro Kimura](https://github.com/ryoppippi) for [ccusage](https://github.com/ryoppippi/ccusage). These were instrumental in giving me the idea for this and in understanding how to read and parse Claude's log files.

Development of this work was assisted by Claude Code, Gemini Code Assist, Warp, GPT-o3, and Zen-MCP.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

Claude Dash is an independent project and is not affiliated with or endorsed by Anthropic. It analyzes local Claude Code usage data to provide insights about session limits.
