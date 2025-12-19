# MCP Tools Configuration Guide for Agentic Tasks

## Overview

Agentic Tasks now have full support for configuring System Prompts and MCP Tools directly in the UI! This makes it easy to connect your BPMN workflows to your MCP servers in the `mcp_servers` directory.

## New Features

### 1. System Prompt Editor

Configure exactly what you want your AI agent to do with a multi-line text editor.

### 2. MCP Tools Manager

- ✅ Add/remove MCP tools
- ✅ Quick-add common tool categories
- ✅ Tools stored in YAML workflow
- ✅ Tools accessible during execution

## How to Configure Agentic Tasks

### Step 1: Add an Agentic Task

1. From the palette, click **"Agentic Task"**
2. Click on the canvas to place it
3. Select the task to open the properties panel

### Step 2: Configure Basic Properties

In the **Task-Specific Properties** section:

- **Agent Type**: `log-analyzer`, `code-reviewer`, `decision-maker`, etc.
- **AI Model**: Select from `claude-3-opus`, `gpt-4`, etc.
- **Capabilities**: `log-parsing, pattern-recognition, root-cause-analysis`
- **Confidence Threshold**: `0.8` (0.0-1.0)
- **Max Retries**: `3`
- **Learning Enabled**: ☑️ Check if you want the agent to learn

### Step 3: Configure System Prompt

Scroll to the **AI Configuration** section:

**System Prompt** textarea:
```
You are an expert DevOps engineer analyzing system logs.

Your tasks:
1. Read and parse log files using MCP tools
2. Search for error patterns using grep-search
3. Identify root causes
4. Classify issue severity
5. Generate actionable diagnostic steps

Use the following MCP tools:
- filesystem-read: To read log files
- grep-search: To search for error patterns
- log-parser: To parse structured logs
```

### Step 4: Add MCP Tools

In the **MCP Tools** section, you have two options:

**Option A: Quick Add (Recommended)**

Click category buttons to add all tools at once:

- **filesystem** → Adds: `filesystem-read`, `filesystem-write`, `filesystem-list`
- **search** → Adds: `grep-search`, `regex-match`
- **logs** → Adds: `log-parser`, `error-classifier`
- **web** → Adds: `fetch-url`, `scrape-content`
- **database** → Adds: `query-db`, `schema-info`

**Option B: Manual Add**

1. Click **"+ Add MCP Tool"**
2. Enter tool name (e.g., `filesystem-read`)
3. Repeat for each tool
4. Click × to remove unwanted tools

## MCP Server Integration

### Your MCP Servers Directory

```
mcp_servers/
├── filesystem/
│   ├── server.py
│   └── tools: filesystem-read, filesystem-write, filesystem-list
├── search/
│   ├── server.py
│   └── tools: grep-search, regex-match
└── logs/
    ├── server.py
    └── tools: log-parser, error-classifier
```

### Tool Naming Convention

MCP tools should match your server's tool names:

```python
# In your MCP server
@server.tool()
def filesystem_read(path: str, encoding: str = 'utf-8'):
    """Read file from filesystem"""
    with open(path, 'r', encoding=encoding) as f:
        return f.read()
```

In UI, add tool as: `filesystem-read` (kebab-case)

### Connecting Backend to MCP Servers

Update `backend/task_executors.py` to actually call your MCP servers:

```python
class AgenticTaskExecutor(TaskExecutor):
    def __init__(self, mcp_client=None, agui_server=None):
        self.mcp_client = mcp_client or MCPClient()
        self.agui_server = agui_server

    async def run_agent(self, task_id, model, system_prompt, mcp_tools, context):
        # Initialize AI client
        if model.startswith('claude'):
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        elif model.startswith('gpt'):
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Use MCP tools
        for tool_name in mcp_tools:
            # Get tool from MCP server
            tool = await self.mcp_client.get_tool(tool_name)

            # Broadcast to UI
            await self.agui_server.send_agent_tool_use(
                task_id,
                tool_name,
                {'status': 'invoking'}
            )

            # Execute tool
            if tool_name == 'filesystem-read':
                log_file = context.get('logFileUrl')
                result = await tool(path=log_file)
                context['logContent'] = result

            elif tool_name == 'grep-search':
                log_content = context.get('logContent', '')
                result = await tool(pattern='ERROR|CRITICAL', content=log_content)
                context['errors'] = result

        # Call AI model with system prompt
        response = await client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{
                'role': 'user',
                'content': f"Analyze this data: {context}"
            }]
        )

        return {
            'analysis': response.content,
            'tools_used': mcp_tools,
            'confidence': 0.95
        }
```

## Example Workflows

### Example 1: Log Analysis

**Task Configuration:**

```yaml
type: agenticTask
name: Analyze Application Logs
properties:
  agentType: "log-analyzer"
  model: "claude-3-opus"
  confidenceThreshold: 0.8
  maxRetries: 3
  custom:
    systemPrompt: |
      You are a senior SRE analyzing application logs.

      Process:
      1. Use filesystem-read to load the log file
      2. Use grep-search to find ERROR and CRITICAL entries
      3. Use log-parser to structure the findings
      4. Identify patterns and root causes
      5. Generate remediation steps

      Be thorough but concise in your analysis.

    mcpTools:
      - filesystem-read
      - grep-search
      - log-parser
      - error-classifier
```

### Example 2: Code Review

**Task Configuration:**

```yaml
type: agenticTask
name: Review Code Changes
properties:
  agentType: "code-reviewer"
  model: "gpt-4"
  confidenceThreshold: 0.85
  custom:
    systemPrompt: |
      You are an expert code reviewer.

      Review process:
      1. Use filesystem-read to load source files
      2. Use grep-search to find security issues
      3. Check for best practices
      4. Identify performance concerns
      5. Suggest improvements

    mcpTools:
      - filesystem-read
      - filesystem-list
      - grep-search
      - regex-match
```

### Example 3: Database Analysis

**Task Configuration:**

```yaml
type: agenticTask
name: Analyze Database Performance
properties:
  agentType: "db-analyzer"
  model: "claude-3-sonnet"
  custom:
    systemPrompt: |
      You are a database performance expert.

      Tasks:
      1. Use query-db to get slow query logs
      2. Use schema-info to understand table structure
      3. Identify missing indexes
      4. Suggest query optimizations
      5. Generate migration scripts

    mcpTools:
      - query-db
      - schema-info
```

## UI Walkthrough

### Before: No Configuration Visible

```
Properties Panel (Agentic Task selected)
├── ID: element_4
├── Name: Agentic Task
├── Type: agenticTask
└── Documentation: (empty)
```

### After: Full Configuration Available

```
Properties Panel (Agentic Task selected)
├── ID: element_4
├── Name: Analyze Logs with MCP
├── Type: agenticTask
├── Documentation: AI-powered log analysis
│
├── Task-Specific Properties
│   ├── Agent Type: log-analyzer
│   ├── AI Model: claude-3-opus
│   ├── Capabilities: log-parsing, pattern-recognition
│   ├── Confidence Threshold: 0.8
│   ├── Max Retries: 3
│   └── Learning Enabled: ☑️
│
├── AI Configuration
│   └── System Prompt: (8 rows)
│       You are an expert DevOps engineer...
│       Use MCP tools to analyze logs...
│
├── MCP Tools
│   ├── filesystem-read          [×]
│   ├── grep-search              [×]
│   ├── log-parser               [×]
│   └── [+ Add MCP Tool]
│
│   Quick Add Common Tools:
│   [filesystem] [search] [logs] [web] [database]
│
└── Custom Properties
    └── (additional key-value pairs)
```

## Exported YAML Structure

When you configure an Agentic Task, it exports to YAML like this:

```yaml
- id: element_4
  type: agenticTask
  name: Analyze Logs with MCP
  x: 390
  y: 330
  properties:
    agentType: "log-analyzer"
    model: "claude-3-opus"
    capabilities: "log-parsing, pattern-recognition, root-cause-analysis"
    confidenceThreshold: 0.8
    maxRetries: 3
    learningEnabled: true
    custom:
      systemPrompt: |
        You are an expert DevOps engineer analyzing system logs.

        Your tasks:
        1. Read and parse log files using MCP tools
        2. Search for error patterns
        3. Identify root causes
        4. Classify issue severity
        5. Generate diagnostic steps

      mcpTools:
        - filesystem-read
        - grep-search
        - log-parser
        - error-classifier
```

## Tips & Best Practices

### 1. System Prompt Design

**Good System Prompt:**
```
You are an expert [role] performing [task].

Process:
1. [Step 1 with specific MCP tool]
2. [Step 2 with specific MCP tool]
3. [Analysis step]
4. [Output generation]

Guidelines:
- Be thorough but concise
- Prioritize by severity
- Provide actionable recommendations
```

**Avoid:**
```
Do stuff with logs and tell me what you find.
```

### 2. MCP Tool Selection

**Choose tools that match your task:**

Log Analysis:
- ✅ filesystem-read, grep-search, log-parser
- ❌ database tools (not relevant)

Code Review:
- ✅ filesystem-read, filesystem-list, grep-search
- ❌ log-parser (not relevant)

Database Work:
- ✅ query-db, schema-info
- ❌ filesystem tools (unless needed)

### 3. Tool Order

List tools in the order they'll be used:

```yaml
mcpTools:
  - filesystem-read      # 1. Load file first
  - grep-search          # 2. Then search
  - log-parser           # 3. Then parse
  - error-classifier     # 4. Finally classify
```

### 4. Confidence Thresholds

Set based on criticality:

- **0.95+**: Critical operations (production deployments)
- **0.85-0.95**: Important operations (code reviews)
- **0.75-0.85**: Standard operations (log analysis)
- **<0.75**: Exploratory operations

## Testing Your Configuration

### 1. Configure the Task

- Add Agentic Task
- Set system prompt
- Add MCP tools

### 2. Export and Review

- Click "Export YAML"
- Check `custom.systemPrompt` is populated
- Check `custom.mcpTools` array has your tools

### 3. Execute and Monitor

- Click "▶ Execute Workflow"
- Watch for tool usage notifications
- Verify tools are called in order

### 4. Check Results

- Approval form should show analysis
- Console should log tool usage
- Backend logs should show MCP calls

## Troubleshooting

### Tools Not Showing in UI

**Problem:** MCP tools list is empty after adding

**Solution:**
- Check browser console for errors
- Verify element.properties.custom.mcpTools array
- Export YAML and check structure

### System Prompt Not Saved

**Problem:** System prompt disappears after page reload

**Solution:**
- Export YAML before reloading
- Re-import to restore configuration
- Check that textarea value is being saved

### Tools Not Called During Execution

**Problem:** Workflow runs but MCP tools aren't used

**Solution:**
1. Check backend logs for errors
2. Verify MCP server is running
3. Check tool names match server exactly
4. Ensure MCPClient is initialized

### Quick-Add Buttons Not Working

**Problem:** Clicking category buttons doesn't add tools

**Solution:**
- Check that mcpTools array is initialized
- Browser console for JavaScript errors
- Try manual add instead

## Advanced: Creating Custom Tool Categories

You can modify `app.js` to add your own quick-add categories:

```javascript
const commonTools = [
    { name: 'filesystem', tools: ['filesystem-read', 'filesystem-write', 'filesystem-list'] },
    { name: 'search', tools: ['grep-search', 'regex-match'] },
    { name: 'logs', tools: ['log-parser', 'error-classifier'] },

    // Add your custom categories here
    { name: 'monitoring', tools: ['prometheus-query', 'grafana-fetch', 'alert-check'] },
    { name: 'cloud', tools: ['aws-s3-read', 'aws-ec2-list', 'gcp-storage-read'] },
    { name: 'security', tools: ['vulnerability-scan', 'secret-detect', 'cve-check'] }
];
```

## Summary

✅ **System Prompt Editor** - Configure AI behavior
✅ **MCP Tools Manager** - Add/remove tools easily
✅ **Quick-Add Categories** - Common tool sets with one click
✅ **YAML Export** - Full configuration stored
✅ **Visual Feedback** - See tool usage in real-time
✅ **Flexible** - Works with any MCP server

**Your Agentic Tasks are now fully configurable and ready to use real MCP tools!** 🚀
