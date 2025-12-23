# Streaming Error Debugging

## Error Message

```
OpenRouter API call failed: An error occurred during streaming
Agent failed after 3 attempts
```

## Problem

The error message "An error occurred during streaming" is too generic and doesn't tell us the actual cause. This can be caused by several issues:

1. **OpenRouter API Key Issues**
2. **Network/Connection Problems**
3. **Model Availability**
4. **Rate Limiting**
5. **Invalid Request Parameters**

## Fix Applied

Added detailed error logging to capture the actual error during streaming.

### Changes Made

**File**: `/backend/task_executors.py`

**Line 836-840**: Added detailed traceback logging
```python
except Exception as e:
    import traceback
    logger.error(f"OpenRouter API call failed: {e}")
    logger.error(f"Full error traceback:\n{traceback.format_exc()}")  # ← NEW
    logger.warning("Falling back to simple analysis")
```

**Line 997-1136**: Wrapped streaming loop in try-catch
```python
try:
    async for chunk in stream:
        # ... streaming logic ...
except Exception as stream_error:
    import traceback
    logger.error(f"❌ STREAMING ERROR: {stream_error}")
    logger.error(f"Error type: {type(stream_error).__name__}")
    logger.error(f"Full traceback:\n{traceback.format_exc()}")
    logger.error(f"Partial response collected: {len(analysis_text)} chars")

    # Use partial response if available
    if not analysis_text:
        raise Exception(f"Streaming failed with no content: {stream_error}")
```

## How to Debug

### 1. Restart the Backend

The error logging improvements require restarting the server:

```bash
cd backend
# Kill existing server (Ctrl+C)
python main.py
```

### 2. Run the Workflow Again

Execute your workflow with the Agentic Task and check the logs.

### 3. Check the Detailed Error

You'll now see **much more detailed** error information:

**Before** (unhelpful):
```
ERROR - OpenRouter API call failed: An error occurred during streaming
```

**After** (detailed):
```
ERROR - OpenRouter API call failed: AuthenticationError
ERROR - Error type: AuthenticationError
ERROR - Full traceback:
Traceback (most recent call last):
  File "/Users/.../task_executors.py", line 997
  ...
  openai.AuthenticationError: Error code: 401 - Invalid API key
```

## Common Errors and Solutions

### Error: 401 - Authentication Error

**Cause**: Invalid or missing OpenRouter API key

**Solution**:
```bash
# Check if API key is set
echo $OPENROUTER_API_KEY

# If empty, set it
export OPENROUTER_API_KEY="sk-or-v1-..."

# Restart server
python main.py
```

### Error: 429 - Rate Limit

**Cause**: Too many requests to OpenRouter

**Solution**:
- Wait a few minutes
- Use a different model (free models have higher limits)
- Upgrade your OpenRouter plan

### Error: 400 - Bad Request

**Cause**: Invalid model ID or parameters

**Solution**:
- Check model ID has provider prefix: `anthropic/claude-3.5-sonnet`
- Verify model exists in OpenRouter catalog
- Check `max_tokens` isn't too high

### Error: Connection Timeout

**Cause**: Network issues or OpenRouter downtime

**Solution**:
- Check internet connection
- Try again in a few minutes
- Check OpenRouter status page

### Error: Model Not Available

**Cause**: Model is temporarily unavailable or removed

**Solution**:
- Try a different model
- Check OpenRouter's model list: https://openrouter.ai/models

## Testing After Fix

### 1. Check API Key

```bash
# Verify API key is set
echo $OPENROUTER_API_KEY

# Should output: sk-or-v1-...
```

### 2. Test Health Endpoint

```bash
curl http://localhost:8000/health
```

Should show:
```json
{
  "status": "healthy",
  "mcp_enabled": true
}
```

### 3. Run Simple Test

Execute workflow with a small log file and watch for detailed errors.

### 4. Check Logs

Look for these log sections:

**Streaming Start**:
```
🚀 STARTING STREAMING - Listening for chunks from OpenRouter
   Using SENTENCE BOUNDARY DETECTION for replay
```

**Streaming Success**:
```
✅ STREAMING COMPLETE
   Total OpenRouter chunks: 45
   Total content tokens: 423
   Total sentences detected: 12
```

**Streaming Error** (if any):
```
❌ STREAMING ERROR: [detailed error here]
Error type: [error class]
Full traceback: [full stack trace]
```

## Expected Behavior

### Success
```
INFO - Calling OpenRouter with model: anthropic/claude-3.5-sonnet (STREAMING)
INFO - 🚀 STARTING STREAMING
INFO - 📝 SENTENCE #1 COMPLETE
INFO - 📝 SENTENCE #2 COMPLETE
...
INFO - ✅ STREAMING COMPLETE
```

### Failure (with new logging)
```
INFO - Calling OpenRouter with model: anthropic/claude-3.5-sonnet
ERROR - ❌ STREAMING ERROR: AuthenticationError
ERROR - Error type: AuthenticationError
ERROR - Full traceback:
  [Complete error details]
ERROR - OpenRouter API call failed: AuthenticationError
WARNING - Falling back to simple analysis
```

## Next Steps

If you still see "An error occurred during streaming" after this fix:

1. **Copy the full traceback** from the logs
2. **Check the error type** (AuthenticationError, RateLimitError, etc.)
3. **Look up the specific error** in the solutions above
4. **If still stuck**, share the full traceback for more specific help

## Verification

After restarting the server, you should see detailed error information instead of the generic "An error occurred during streaming" message. The logs will now tell you exactly what went wrong!
