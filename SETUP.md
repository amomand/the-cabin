# Setup Guide

This guide helps you set up The Cabin game with all dependencies.

## Prerequisites

- Python 3.10 or higher
- An OpenAI API key

## Quick Setup

1. **Clone the repository** (if you haven't already)
   ```bash
   git clone <repository-url>
   cd the-cabin
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

5. **Set up environment variables**
   ```bash
   # Copy the template
   cp .env.example .env
   
   # Edit .env and add your OpenAI API key
   # Get your key from: https://platform.openai.com/api-keys
   ```

6. **Run the game**
   ```bash
   python3 main.py
   ```

## Environment Variables

Create a `.env` file in the project root with:

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=your_actual_api_key_here

# Optional: Enable debug logging (0 = disabled, 1 = enabled)
CABIN_DEBUG=0

# Optional: override model defaults
OPENAI_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=none
```

## Troubleshooting

### "No module named 'dotenv'"
- Make sure you've activated the virtual environment
- Run `pip install -r requirements-dev.txt`

### "No module named 'fastapi'" when running tests
- The full test suite includes the web-session entrypoint
- Run `pip install -r requirements-dev.txt`

### AI giving repetitive responses
- Check that your OpenAI API key is set correctly in `.env`
- Verify the key is valid at https://platform.openai.com/api-keys
- Enable debug logging with `CABIN_DEBUG=1` to see what's happening

### Virtual environment issues
- If you get permission errors, create the virtual environment in a writable directory, for example: `python3 -m venv .venv`
- On some systems, you might need to install `python3-venv` first

## Development

When working on the game:

1. **Always activate the virtual environment first**
   ```bash
   source venv/bin/activate
   ```

2. **Install new dependencies**
   ```bash
   pip install package_name
   ```
   Add base/shared packages to `requirements.txt`, web/server packages to
   `requirements-server.txt`, and development-only packages that should only be
   installed through the aggregate dev set to `requirements-dev.txt`.

3. **Run tests**
   ```bash
   python3 -m pytest
   python3 -m tools.playtest_runner
   ```

## File Structure

```
the-cabin/
├── venv/                   # Virtual environment (created by you)
├── .env                    # Environment variables (created by you)
├── .env.example           # Template for .env file
├── requirements.txt       # Python dependencies
├── requirements-server.txt # Web/server dependencies
├── requirements-dev.txt   # Development/test dependencies
├── main.py               # Game entry point
├── game/                 # Game code
├── docs/                 # Documentation
└── logs/                 # Log files (created automatically)
```
