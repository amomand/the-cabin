# Debugging Guide

This guide helps you troubleshoot issues with The Cabin game.

## AI Interpreter Issues

### Problem: AI giving stock responses
If the AI is giving the same response like "You start, then think better of it. The cold in your chest makes you careful." for different inputs, it means the OpenAI API is not working.

**Symptoms:**
- All inputs get the same response
- No varied or contextual replies
- Basic commands like "go north" work, but complex ones don't

**Causes:**
1. **Missing OpenAI API Key**: The most common cause
2. **Invalid API Key**: API key is set but incorrect
3. **API Rate Limits**: Too many requests
4. **Network Issues**: Cannot reach OpenAI servers

**Solutions:**

#### 1. Set up OpenAI API Key
```bash
# Create a .env file in the game directory
cp env.template .env

# Edit .env and add your API key
OPENAI_API_KEY=your_actual_api_key_here
```

Get your API key from: https://platform.openai.com/api-keys

#### 2. Enable Debug Logging
```bash
# Set debug environment variable
export CABIN_DEBUG=1

# Or add to .env file
CABIN_DEBUG=1
```

**Note**: When `CABIN_DEBUG=1` is set, debug messages will appear in the console during gameplay. For normal play, keep this set to `0` or unset.

#### 3. Check Logs
The game creates detailed logs in the `logs/` directory. Check the latest log file for:
- API call attempts
- Error messages
- Fallback behavior

#### 4. Test API Connection
```bash
# Test if your API key works
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}' \
     https://api.openai.com/v1/chat/completions
```

## Quest System Issues

### Problem: Quests not triggering
If quests aren't appearing when expected:

**Check:**
1. Are you in the correct rooms? (konttori, lakeside)
2. Are you performing the right actions? (lighting fire, turning on lights)
3. Check the logs for quest events

### Problem: Quest not completing
If quests don't complete when they should:

**Check:**
1. World state flags: `has_power` and `fire_lit`
2. Player inventory for required items
3. Logs for quest completion attempts

## Logging System

The game includes a comprehensive logging system that tracks:

### AI Calls
- Input text
- Context (room, items, inventory)
- API responses or fallback behavior
- Error messages

### Quest Events
- Quest triggers
- Quest updates
- Quest completions

### Game Actions
- Player actions
- Results and effects

### Log Files
Logs are stored in `logs/the_cabin_YYYYMMDD_HHMMSS.log`

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: General game events
- `WARNING`: Potential issues
- `ERROR`: Problems that need attention

**Console Output:**
- **Normal play** (`CABIN_DEBUG=0`): No debug output shown to player
- **Debug mode** (`CABIN_DEBUG=1`): Debug messages appear in console during gameplay
- **File logging**: Always active, regardless of debug setting

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | None (required) |
| `CABIN_DEBUG` | Enable debug logging | 0 (disabled) |
| `OPENAI_API_BASE` | Custom API endpoint | https://api.openai.com/v1 |

## Common Commands

```bash
# Enable debug mode
export CABIN_DEBUG=1

# Run game with debug logging
python3 main.py

# Check latest log file
tail -f logs/the_cabin_*.log

# Test AI interpreter directly
python3 -c "from game.ai_interpreter import interpret; print(interpret('test', {}))"
```

## Getting Help

If you're still having issues:

1. Check the logs for specific error messages
2. Verify your OpenAI API key is valid
3. Test with a simple command like "go north"
4. Check if the issue is with specific inputs or all inputs
