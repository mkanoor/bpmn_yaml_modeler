# OpenRouter Model Reference

## Error You're Seeing

```
Error code: 400 - {'error': {'message': 'gemini-pro is not a valid model ID'}}
```

**Problem**: You used `gemini-pro` but OpenRouter requires the full model ID with provider prefix.

## Valid Model IDs for OpenRouter

### ✅ Anthropic Claude Models (Recommended)

| Model ID | Description | Context | Cost |
|----------|-------------|---------|------|
| `anthropic/claude-3.5-sonnet` | **Best for analysis** | 200K | $$$ |
| `anthropic/claude-3.5-sonnet:beta` | Latest beta version | 200K | $$$ |
| `anthropic/claude-3-opus` | Most capable | 200K | $$$$ |
| `anthropic/claude-3-sonnet` | Balanced | 200K | $$ |
| `anthropic/claude-3-haiku` | Fastest/cheapest | 200K | $ |

### ✅ Google Gemini Models (Fixed Names)

| Model ID | Description | Context | Cost |
|----------|-------------|---------|------|
| `google/gemini-pro-1.5` | **NOT** `gemini-pro` | 2M | $$ |
| `google/gemini-pro` | Older version | 32K | $ |
| `google/gemini-flash-1.5` | Fast & cheap | 1M | $ |
| `google/gemini-flash-1.5-8b` | Very cheap | 1M | $ |

### ✅ OpenAI Models

| Model ID | Description | Context | Cost |
|----------|-------------|---------|------|
| `openai/gpt-4o` | Latest GPT-4 | 128K | $$$ |
| `openai/gpt-4o-mini` | Cheaper GPT-4 | 128K | $ |
| `openai/gpt-4-turbo` | GPT-4 Turbo | 128K | $$$ |
| `openai/gpt-3.5-turbo` | Fast & cheap | 16K | $ |

### ✅ Meta Llama Models (Free!)

| Model ID | Description | Context | Cost |
|----------|-------------|---------|------|
| `meta-llama/llama-3.1-405b-instruct` | Largest | 128K | **FREE** |
| `meta-llama/llama-3.1-70b-instruct` | Good balance | 128K | **FREE** |
| `meta-llama/llama-3.1-8b-instruct` | Fast | 128K | **FREE** |

### ✅ Other Good Options

| Model ID | Description | Context | Cost |
|----------|-------------|---------|------|
| `qwen/qwen-2.5-72b-instruct` | Chinese model, good quality | 32K | $ |
| `mistralai/mistral-large` | European alternative | 128K | $$ |
| `x-ai/grok-beta` | Elon's model | 128K | $$$ |

## How to Fix Your Error

### Option 1: Use the Correct Gemini Model ID

Change from:
```yaml
model: "gemini-pro"  # ❌ Wrong - missing provider prefix
```

To:
```yaml
model: "google/gemini-pro-1.5"  # ✅ Correct
```

### Option 2: Use Claude (Recommended for Log Analysis)

```yaml
model: "anthropic/claude-3.5-sonnet"  # ✅ Best for analysis
```

### Option 3: Use Free Llama Model

```yaml
model: "meta-llama/llama-3.1-70b-instruct"  # ✅ Free and good quality
```

## How to Change in UI

1. **Select the Agentic Task** on the canvas (click on "Analyze & Generate Diagnostics")
2. **Look at Properties Panel** (right side)
3. **Find "Model" field**
4. **Change to valid model ID** from the tables above
5. **Click "▶ Execute Workflow"** (no need to export/import!)

## Testing Model Availability

You can test if a model is available via OpenRouter API:

```bash
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

Or check their website: https://openrouter.ai/models

## Cost Considerations

For **log analysis** workflows:

- **Best Quality**: `anthropic/claude-3.5-sonnet` (~$3 per 1M input tokens)
- **Good & Free**: `meta-llama/llama-3.1-70b-instruct` (free!)
- **Budget Option**: `openai/gpt-4o-mini` (~$0.15 per 1M input tokens)

## Common Mistakes

### ❌ Wrong (Missing Provider Prefix)
- `gemini-pro`
- `gpt-4`
- `claude-3.5-sonnet`
- `llama-3.1-70b`

### ✅ Correct (With Provider Prefix)
- `google/gemini-pro-1.5`
- `openai/gpt-4o`
- `anthropic/claude-3.5-sonnet`
- `meta-llama/llama-3.1-70b-instruct`

## Quick Fix for Your Current Error

In the UI Properties Panel, change:
```
Model: gemini-pro
```

To one of these:
```
Model: google/gemini-pro-1.5           (if you want Gemini)
Model: anthropic/claude-3.5-sonnet     (if you want Claude - recommended)
Model: meta-llama/llama-3.1-70b-instruct  (if you want free)
```

Then click "▶ Execute Workflow" again - it will work! ✅
