# MCP Tools Issue Analysis

## Problem Report

User observed: "The security-lookup and kb-search tools in the workflows/ai-log-analysis-dual-approval-workflow.yaml are not being used are there any errors accessing these tools"

## Investigation Findings

### Issue #1: Tool Count Limitation

**Location**: `/backend/task_executors.py:849`

**Code**:
```python
async def _execute_mcp_tools(self, task_id: str, mcp_tools: list,
                             log_content: str, log_file_name: str) -> List[Dict[str, Any]]:
    """Execute MCP tools and broadcast to UI using AG-UI streaming events"""
    tool_results = []
    tools_to_use = mcp_tools[:3] if len(mcp_tools) > 3 else mcp_tools  # ⚠️ LIMITATION!
```

**Problem**: The code artificially limits tool execution to **only the first 3 tools** when more than 3 are configured.

**Workflow Configuration**:
```yaml
mcpTools:
  - "grep-search"      # ✅ Position 1 - EXECUTED
  - "regex-match"      # ✅ Position 2 - EXECUTED
  - "log-parser"       # ✅ Position 3 - EXECUTED
  - "error-classifier" # ❌ Position 4 - SKIPPED
  - "security-lookup"  # ❌ Position 5 - SKIPPED (User's concern)
  - "kb-search"        # ❌ Position 6 - SKIPPED (User's concern)
```

**Impact**:
- `security-lookup` and `kb-search` are never executed
- The system prompt instructs the LLM to use these tools, but they're unavailable
- The LLM cannot look up CVEs in security databases
- The LLM cannot search knowledge bases for solutions

### Issue #2: Tools Are Simulated, Not Actually Executed

**Location**: `/backend/task_executors.py:875-876`

**Code**:
```python
# Simulate tool execution
await asyncio.sleep(0.5)
```

**Problem**: The tools are **not actually being called** - they're just simulated with a 500ms delay.

**What happens**:
1. Tool name and args are sent to UI for display (`task.tool.start` event)
2. Code sleeps for 500ms to simulate execution
3. Tool completion is sent to UI (`task.tool.end` event with `status: success`)
4. **No actual MCP tool is invoked**
5. **No actual results are returned**

**Evidence**:
```python
tool_results.append({'tool': tool, 'args': tool_args})  # Just stores the name/args, no results
```

### Issue #3: MCP Client Not Initialized

**Location**: `/backend/task_executors.py:692-694`

**Code**:
```python
def __init__(self, mcp_client=None, agui_server=None):
    self.mcp_client = mcp_client  # Currently None
    self.agui_server = agui_server
```

**Problem**: The `mcp_client` parameter is `None` - there's no actual MCP client integration.

**Evidence from workflow_engine.py**:
```python
# When TaskExecutorRegistry is initialized, no MCP client is passed
registry = TaskExecutorRegistry(agui_server=self.agui_server, mcp_client=None)
```

## Root Cause Summary

The MCP tools (`security-lookup`, `kb-search`, etc.) are **not actually being used** because:

1. **Only 3 tools are executed** (hard-coded limit at line 849)
2. **Tool execution is simulated** (just sleeps for 500ms, doesn't call real tools)
3. **No MCP client exists** (mcp_client is None, not connected to any MCP server)

## Impact on Workflow

The workflow's system prompt tells the LLM:

```
AVAILABLE TOOLS:
- security_lookup: Query security databases for CVEs and advisories
- kb_search: Search knowledge bases for solutions and articles

PROCESS:
2. INVESTIGATE ROOT CAUSES:
   - Use security_lookup to check for known CVEs
   - For each CVE found, use kb_search with query="CVE-XXXX-XXXXX"
   - **CRITICAL**: Always search KB after finding CVEs - this is required
```

**But the LLM has NO ACCESS to these tools!**

This means:
- ❌ LLM cannot look up CVE information
- ❌ LLM cannot search knowledge bases
- ❌ LLM is forced to work from log content alone
- ❌ Analysis quality is significantly reduced
- ❌ The workflow's promise of "MCP tool usage" is not fulfilled

## Current Behavior

### What Actually Happens

1. User uploads log file
2. Agentic task receives 6 tools in configuration
3. Only first 3 tools are selected: `grep-search`, `regex-match`, `log-parser`
4. For each of these 3 tools:
   - UI receives `task.tool.start` event (for display)
   - Code sleeps 500ms (simulation)
   - UI receives `task.tool.end` event (for display)
   - **No actual tool execution occurs**
5. OpenRouter API is called with system prompt
6. LLM generates response **without any tool results** (because tools were simulated)
7. LLM cannot access CVE databases or KB searches (tools 5 & 6 were skipped)

### What The UI Shows

The Task Activity panel displays:
```
🔧 grep-search (Running...) → ✓ Complete
🔧 regex-match (Running...) → ✓ Complete
🔧 log-parser (Running...) → ✓ Complete
```

**But these are just visual indicators** - no actual grep, regex, or log parsing occurred!

## Solutions Required

### Solution 1: Remove 3-Tool Limit

**Change**:
```python
# Before
tools_to_use = mcp_tools[:3] if len(mcp_tools) > 3 else mcp_tools

# After
tools_to_use = mcp_tools  # Use all configured tools
```

### Solution 2: Implement Actual MCP Tool Execution

**Options**:

**Option A: Integrate with MCP Server**
- Set up an MCP server with actual tool implementations
- Initialize `mcp_client` with connection to MCP server
- Replace simulation with actual tool calls

**Option B: Implement Tools Locally**
- Create Python implementations of each tool
- `grep-search`: Use Python regex on log content
- `regex-match`: Use re.findall/search
- `log-parser`: Parse log format (syslog, JSON logs, etc.)
- `error-classifier`: Categorize errors by severity
- `security-lookup`: Query CVE databases (NVD API, etc.)
- `kb-search`: Query knowledge bases (Red Hat KB API, etc.)

**Option C: Pass Tool Results to LLM Directly**
- Execute tools before calling OpenRouter
- Include tool results in the system prompt or user message
- Let LLM analyze results without needing to "call" tools

### Solution 3: Update System Prompt to Match Reality

If tools cannot be implemented, update the system prompt to remove references to unavailable tools:

**Remove**:
```
- security_lookup: Query security databases for CVEs and advisories
- kb_search: Search knowledge bases for solutions and articles
```

**Update instructions to**:
```
AVAILABLE TOOLS:
- log_parser: Parse log entries, extract timestamps, error codes, stack traces
- grep_search: Search for specific patterns in log content
- regex_match: Extract structured data using regex patterns

Note: You do not have access to external security databases or knowledge bases.
Provide analysis based on the log content and general knowledge of common CVEs.
```

## Recommended Immediate Actions

1. **Remove the 3-tool limit** to allow all 6 tools to be processed
2. **Decide on MCP integration strategy**:
   - If MCP server exists: Connect to it
   - If no MCP server: Implement tools locally
   - If tools are not feasible: Update prompts to match reality
3. **Fix tool simulation** to either:
   - Actually execute tools and return real results
   - Or remove tool display from UI if they're not being used

## Testing Verification

After fixes, verify:

1. **All 6 tools are processed** (not just first 3)
2. **Tools return actual results** (not just simulation)
3. **security-lookup** queries CVE databases for vulnerabilities
4. **kb-search** searches knowledge bases for solutions
5. **Tool results are passed to LLM** for analysis
6. **LLM output includes CVE references** from security-lookup
7. **LLM output includes KB article IDs** from kb-search

## Related Files

- `/workflows/ai-log-analysis-dual-approval-workflow.yaml` - Tool configuration
- `/backend/task_executors.py` - Tool execution logic
- `/backend/workflow_engine.py` - MCP client initialization
