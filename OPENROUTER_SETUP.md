# OpenRouter Setup Guide

## Overview

Your BPMN Agentic Tasks now use **OpenRouter** for AI-powered log analysis! OpenRouter provides access to multiple AI models (Claude, GPT-4, Gemini, etc.) through a single API.

## ✅ What's Been Configured

1. **Environment Variables** - Secure API key storage
2. **OpenRouter Integration** - Real AI analysis instead of simulated
3. **Fallback Mode** - Works without API key (simple analysis)
4. **Git Safety** - `.env` file won't be committed

---

## 🔑 Step 1: Get Your OpenRouter API Key

### Sign Up for OpenRouter

1. **Visit:** https://openrouter.ai
2. **Click "Sign In"** (top right)
3. **Create account** with Google, GitHub, or email
4. **Free tier:** You get $1 in credits to start

### Get Your API Key

1. Go to: https://openrouter.ai/keys
2. Click **"Create Key"**
3. Give it a name: `BPMN-Workflow-Executor`
4. **Copy the key** (starts with `sk-or-v1-...`)
5. **Save it securely** - you'll need it in the next step

---

## 📝 Step 2: Add API Key to .env File

### Edit the .env File

```bash
# Open the .env file
nano .env

# Or use any text editor
code .env
```

### Add Your API Key

Replace the empty value with your actual key:

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-YOUR_ACTUAL_KEY_HERE

# Optional: Specify default model
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet

# Optional: Your app name (for OpenRouter analytics)
OPENROUTER_APP_NAME=BPMN-Workflow-Executor

# Optional: Your app URL
OPENROUTER_APP_URL=http://localhost:8000
```

### Save and Close

**IMPORTANT:**
- ✅ The `.env` file is already in `.gitignore`
- ✅ Your API key will **never** be committed to git
- ✅ The file stays on your local machine only

---

## 📦 Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**What this installs:**
- `openai==1.12.0` - OpenAI client (works with OpenRouter)
- `python-dotenv==1.0.0` - Environment variable loading

---

## 🎯 Step 4: Choose Your AI Model

OpenRouter gives you access to many models. Here are the best ones for log analysis:

### Recommended Models

| Model | ID | Best For | Cost |
|-------|-----|----------|------|
| **Claude 3.5 Sonnet** | `anthropic/claude-3.5-sonnet` | Complex analysis, JSON output | $3/1M tokens |
| **GPT-4 Turbo** | `openai/gpt-4-turbo` | Detailed reasoning | $10/1M tokens |
| **GPT-4o** | `openai/gpt-4o` | Fast, multimodal | $2.50/1M tokens |
| **Llama 3.1 70B** | `meta-llama/llama-3.1-70b-instruct` | Free alternative | Free |
| **Mixtral 8x7B** | `mistralai/mixtral-8x7b-instruct` | Fast, cheap | $0.24/1M tokens |

**See all models:** https://openrouter.ai/models

### Set Default Model

In your `.env` file:

```bash
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet
```

Or specify per-workflow in the UI when configuring the Agentic Task.

---

## 🧪 Step 5: Test the Integration

### Start the Backend

```bash
cd backend
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Execute a Workflow

1. **Open UI:**
   ```bash
   open index.html
   ```

2. **Import workflow:**
   - Click "Import YAML"
   - Select `ai-log-analysis-workflow.yaml`

3. **Execute:**
   - Click "▶ Execute Workflow"
   - Upload `sample-error.log`
   - Click "Start Execution"

4. **Watch for OpenRouter call:**
   - Backend logs should show:
     ```
     INFO:__main__:Running agent with model: claude-3-opus via OpenRouter
     INFO:__main__:Calling OpenRouter with model: anthropic/claude-3.5-sonnet
     INFO:__main__:OpenRouter analysis complete. Usage: ...
     ```

5. **Check approval form:**
   - Should show AI-generated analysis
   - Findings from actual Claude/GPT model
   - Token usage information

---

## 🔍 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│           BPMN Workflow (Frontend)                   │
│  ┌───────────────────────────────────────────────┐  │
│  │  Agentic Task: "Analyze Logs with MCP"       │  │
│  │  - Model: anthropic/claude-3.5-sonnet        │  │
│  │  - System Prompt: "You are an expert..."     │  │
│  │  - MCP Tools: filesystem-read, grep-search   │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                         │ WebSocket
                         ▼
┌─────────────────────────────────────────────────────┐
│      Backend (Python/FastAPI)                        │
│  ┌───────────────────────────────────────────────┐  │
│  │  AgenticTaskExecutor.run_agent()             │  │
│  │  1. Execute MCP tools                         │  │
│  │  2. Build analysis prompt                     │  │
│  │  3. Call OpenRouter API                       │  │
│  │  4. Parse response                            │  │
│  │  5. Return findings                           │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────┐
│           OpenRouter API                             │
│  ┌───────────────────────────────────────────────┐  │
│  │  Routes to: Anthropic, OpenAI, etc.          │  │
│  │  Returns: AI-generated analysis               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Code Flow

**backend/task_executors.py:**

```python
async def run_agent(self, task_id, model, system_prompt, mcp_tools, context):
    # 1. Execute MCP tools (broadcast to UI)
    tool_results = await self._execute_mcp_tools(...)

    # 2. Check if OpenRouter is configured
    if os.getenv('OPENROUTER_API_KEY'):
        # 3. Call OpenRouter
        result = await self._call_openrouter(
            model=model,  # e.g., "anthropic/claude-3.5-sonnet"
            system_prompt=system_prompt,
            tool_results=tool_results,
            log_content=log_content
        )
        return result
    else:
        # Fallback to simple pattern matching
        return await self._simple_analysis(...)
```

**OpenRouter call:**

```python
async def _call_openrouter(self, model, system_prompt, ...):
    from openai import AsyncOpenAI

    # Initialize OpenRouter client
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv('OPENROUTER_API_KEY')
    )

    # Call the API
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt}
        ],
        temperature=0.3,
        max_tokens=2000
    )

    # Extract findings
    analysis_text = response.choices[0].message.content
    return parse_findings(analysis_text)
```

---

## 💰 Cost Management

### Estimate Your Costs

**Example workflow execution:**
- Log file: 2 KB (~500 tokens)
- System prompt: ~100 tokens
- Response: ~500 tokens
- **Total per execution:** ~1,100 tokens

**With Claude 3.5 Sonnet ($3/1M tokens):**
- Cost per execution: $0.0033 (less than half a cent)
- 100 executions: $0.33
- 1,000 executions: $3.30

**Your $1 free credit = ~300 executions!**

### Monitor Usage

1. **Visit:** https://openrouter.ai/credits
2. **See:** Remaining credits and usage history
3. **Set:** Budget limits and alerts

### Tips to Save Money

1. **Use cheaper models** for simple tasks:
   ```bash
   OPENROUTER_DEFAULT_MODEL=meta-llama/llama-3.1-70b-instruct  # Free!
   ```

2. **Limit log content** in prompt (already done):
   ```python
   log_content[:4000]  # Only first 4000 chars
   ```

3. **Cache analysis results** (future enhancement)

---

## 🛠️ Troubleshooting

### API Key Not Working

**Error:** `401 Unauthorized` or `Invalid API key`

**Solutions:**
1. Check your API key is correct in `.env`
2. Make sure it starts with `sk-or-v1-`
3. Verify credits at: https://openrouter.ai/credits
4. Try regenerating the key

**Test your key:**
```bash
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-3.5-sonnet",
    "messages": [{"role": "user", "content": "Say hello"}]
  }'
```

### Backend Not Loading .env

**Error:** `OPENROUTER_API_KEY not set, using simple analysis`

**Solutions:**
1. Make sure `.env` file exists in root directory:
   ```bash
   ls -la .env
   ```

2. Restart backend:
   ```bash
   cd backend
   python main.py
   ```

3. Check `.env` is loaded:
   ```python
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print(os.getenv('OPENROUTER_API_KEY'))  # Should print your key
   ```

### Model Not Found

**Error:** `404 Not Found` or `Model not available`

**Solutions:**
1. Check model ID at: https://openrouter.ai/models
2. Use exact ID (case-sensitive):
   - ✅ `anthropic/claude-3.5-sonnet`
   - ❌ `claude-3.5-sonnet`
   - ❌ `Anthropic/Claude-3.5-Sonnet`

3. Verify model is available (some require special access)

### Rate Limits

**Error:** `429 Too Many Requests`

**Solutions:**
1. You're making requests too fast
2. Wait 1 minute and try again
3. Reduce concurrent workflow executions
4. Upgrade OpenRouter plan for higher limits

---

## 📊 Example: Real AI Analysis Output

### Input (Log File)
```
2024-12-19 10:24:20 [ERROR] Failed to connect to cache server
2024-12-19 10:25:20 [ERROR] Database query timeout
2024-12-19 10:26:18 [CRITICAL] Application crashed - OOM
```

### OpenRouter Response (Claude 3.5 Sonnet)
```json
{
  "findings": [
    "Analysis Summary: Found 3 critical issues affecting system stability",

    "Issue 1 - Cache Connection Failure (High Priority):
     - Root Cause: Redis server unreachable at cache:6379
     - Impact: Degraded performance, database overload
     - Recommendation: Check Redis service status, verify network connectivity",

    "Issue 2 - Database Timeout (High Priority):
     - Root Cause: Query execution exceeding 10s limit
     - Impact: User request failures, poor UX
     - Recommendation: Add database indexes, optimize query, implement connection pooling",

    "Issue 3 - Out of Memory Crash (Critical Priority):
     - Root Cause: Memory exhaustion in image processing module
     - Impact: Service downtime, data loss risk
     - Recommendation: Increase memory limits, implement memory profiling, add garbage collection",

    "Immediate Actions:
     1. Restart Redis service
     2. Scale up memory allocation to 4GB minimum
     3. Add monitoring alerts for memory usage >80%
     4. Review and optimize database queries
     5. Implement circuit breaker for cache failures"
  ]
}
```

**This level of analysis is only possible with real AI!**

---

## 🔐 Security Best Practices

### DO ✅

- ✅ Store API key in `.env` file only
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Use environment variables in production
- ✅ Rotate API keys periodically
- ✅ Set budget limits on OpenRouter
- ✅ Monitor usage regularly

### DON'T ❌

- ❌ Commit `.env` to git
- ❌ Share your API key
- ❌ Hardcode API key in code
- ❌ Include API key in screenshots
- ❌ Use the same key for multiple apps

### If You Accidentally Commit Your Key

1. **Immediately revoke** at: https://openrouter.ai/keys
2. **Create new key**
3. **Update `.env` file**
4. **Rewrite git history** (or make repo private)

---

## 📚 Available Models

### See All Models

Visit: https://openrouter.ai/models

### Top Picks for Log Analysis

**Best Overall:**
```bash
anthropic/claude-3.5-sonnet    # Excellent reasoning, JSON output
```

**Fastest:**
```bash
openai/gpt-4o                  # Very fast, good quality
```

**Free:**
```bash
meta-llama/llama-3.1-70b-instruct      # No cost
google/gemma-2-9b-it                   # No cost, smaller
```

**Specialized:**
```bash
google/gemini-pro-1.5          # Long context (2M tokens)
openai/o1-preview              # Advanced reasoning
```

### Change Model in UI

When configuring Agentic Task:
1. Set **AI Model** field to: `anthropic/claude-3.5-sonnet`
2. Or use any model from OpenRouter

---

## 🎓 Next Steps

### 1. Advanced System Prompts

Customize the system prompt for better results:

```
You are a senior DevOps engineer with expertise in:
- Linux system administration
- Database performance tuning
- Network troubleshooting
- Container orchestration

Analyze this log file and provide:
1. Root cause analysis
2. Step-by-step remediation
3. Prevention strategies
4. Related monitoring alerts to set up

Format as JSON with clear action items.
```

### 2. Use Different Models for Different Tasks

- **Security analysis:** Claude (better at security reasoning)
- **Quick triage:** GPT-4o (faster)
- **Cost-sensitive:** Llama 3.1 (free)

### 3. Implement Caching

Cache AI responses to save costs on repeated analysis.

### 4. Add More MCP Tools

Integrate real MCP tool results into the AI prompt for richer context.

---

## ✨ Summary

You now have:

✅ **OpenRouter integration** - Real AI analysis
✅ **Secure API key storage** - Never committed to git
✅ **Multiple model options** - Choose best for your needs
✅ **Fallback mode** - Works without API key
✅ **Cost control** - Free tier + budget limits

**Your Agentic Tasks are now powered by real AI!** 🚀

### Quick Test

```bash
# 1. Add your API key to .env
nano .env

# 2. Install dependencies
cd backend && pip install -r requirements.txt

# 3. Start backend
python main.py

# 4. Execute workflow
open index.html
# Import ai-log-analysis-workflow.yaml
# Upload sample-error.log
# Watch real AI analysis!
```

**Have questions?** Check:
- OpenRouter Docs: https://openrouter.ai/docs
- OpenRouter Discord: https://discord.gg/openrouter
