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
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   ```bash
   # Copy the template
   cp env.template .env
   
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
```

## Troubleshooting

### "No module named 'dotenv'"
- Make sure you've activated the virtual environment
- Run `pip install -r requirements.txt`

### AI giving repetitive responses
- Check that your OpenAI API key is set correctly in `.env`
- Verify the key is valid at https://platform.openai.com/api-keys
- Enable debug logging with `CABIN_DEBUG=1` to see what's happening

### Virtual environment issues
- If you get permission errors, try: `python3 -m venv venv --user`
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
   pip freeze > requirements.txt
   ```

3. **Run tests**
   ```bash
   python3 -c "from game.game_engine import GameEngine; print('Game loads successfully')"
   ```

## File Structure

```
the-cabin/
├── venv/                   # Virtual environment (created by you)
├── .env                    # Environment variables (created by you)
├── env.template           # Template for .env file
├── requirements.txt       # Python dependencies
├── main.py               # Game entry point
├── game/                 # Game code
├── docs/                 # Documentation
└── logs/                 # Log files (created automatically)
```
