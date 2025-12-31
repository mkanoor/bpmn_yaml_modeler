# AI Task Consolidation - Workflow Changes

## Summary

Consolidated two separate AI tasks (Analyze Logs + Generate Diagnostics) into a single comprehensive Agentic Task that performs complete log analysis, root cause identification, and remediation plan generation.

## Changes Made

### 1. Removed Element

**Deleted: element_5 - Generate Diagnostics (agenticTask)**
- Previously generated diagnostic steps from analysis results
- Was positioned at (550, 330) in lane_2
- Had its own AI agent configuration

### 2. Enhanced Element

#### element_4 - Analyze & Generate Diagnostics (agenticTask)

**Before:**
```yaml
- id: element_4
  type: agenticTask
  name: Analyze Logs with MCP
  properties:
    agentType: "log-analyzer"
    model: "anthropic/claude-3.5-sonnet"
    capabilities: "log-parsing, pattern-recognition"
    custom:
      mcpTools:
        - "filesystem-read"
        - "grep-search"
        - "regex-match"
        - "log-parser"
        - "error-classifier"
      systemPrompt: |
        Use MCP tools to:
        1. Read and parse log files
        2. Search for error patterns
        3. Extract relevant information
```

**After:**
```yaml
- id: element_4
  type: agenticTask
  name: Analyze & Generate Diagnostics
  x: 390
  y: 330
  poolId: pool_1
  laneId: lane_2
  properties:
    agentType: "diagnostic-analyzer"
    model: "anthropic/claude-3.5-sonnet"
    capabilities: "log-parsing, pattern-recognition, root-cause-analysis, remediation-generation, mcp-tool-usage"
    confidenceThreshold: 0.85
    maxRetries: 3
    learningEnabled: true
    allowCancellation: true
    documentation: "AI agent performs complete log analysis, root cause identification, and remediation step generation"
    custom:
      inputVariable: "logFileContent"
      mcpTools:
        - "grep-search"
        - "regex-match"
        - "log-parser"
        - "error-classifier"
        - "security-lookup"
        - "kb-search"
      analysisDepth: "comprehensive"
      contextWindow: "16384"
      temperature: "0.2"
      maxIterations: 20
      aguiEventCategories:
        - "messaging"
        - "tool"
        - "lifecycle"
      systemPrompt: |
        You are a system diagnostics expert analyzing error logs.

        TASK: Analyze error logs, research root causes, and generate complete remediation plans.

        AVAILABLE TOOLS:
        - log_parser: Parse log entries, extract timestamps, error codes, stack traces
        - grep_search: Search for specific patterns in log content
        - regex_match: Extract structured data using regex patterns
        - error_classifier: Classify errors by severity and type
        - security_lookup: Query security databases for CVEs and advisories
        - kb_search: Search knowledge bases for solutions and articles

        PROCESS:
        1. PARSE LOGS:
           - Identify error codes, stack traces, affected services
           - Extract timestamps to determine timeline
           - Find CVE IDs, component names, version numbers
           - Classify errors by severity (critical, high, medium, low)

        2. INVESTIGATE ROOT CAUSES:
           - Use security_lookup to check for known CVEs
           - For each CVE found, use kb_search with query="CVE-XXXX-XXXXX"
           - Search for related advisories: kb_search with query="RHSA component_name"
           - Search for error messages: kb_search with error patterns
           - Gather evidence from multiple sources
           - **CRITICAL**: Always search KB after finding CVEs - this is required

        3. IDENTIFY ROOT CAUSES:
           - List all root causes with severity levels
           - Include evidence (log excerpts, CVE references, KB articles)
           - Document related CVE IDs for each issue
           - Collect ALL KB article IDs (RHSA-*, solution IDs, etc.)

        4. GENERATE REMEDIATION PLAN:
           - Create ordered, actionable remediation steps
           - Specify executor type for each step:
             * script: Bash commands/scripts
             * api: REST API calls
             * manual: Human intervention required
             * ansible: Ansible playbooks
           - Include step details (commands, endpoints, procedures)
           - Assign risk levels (low, medium, high)
           - Mark steps requiring approval (true/false)
           - Estimate total downtime
           - Provide rollback plan for each risky step

        5. FINALIZE DIAGNOSIS:
           - Ensure all CVEs have corresponding KB searches
           - Verify kb_articles_referenced is populated with ALL article IDs
           - Example: ["RHSA-2025:22760", "320491", "CVE-2024-1234"]
           - Double-check remediation steps are executable
           - Validate rollback plan exists

        OUTPUT FORMAT (JSON):
        {
          "root_causes": [
            {
              "issue": "Description of the issue",
              "severity": "critical|high|medium|low",
              "evidence": "Log excerpts, CVE references, KB articles",
              "cve_ids": ["CVE-2024-1234", "CVE-2024-5678"]
            }
          ],
          "remediation_steps": [
            {
              "step_number": 1,
              "description": "Clear description of action",
              "executor_type": "script|api|manual|ansible",
              "details": {
                "command": "bash command here",
                "or": "API endpoint details",
                "or": "manual procedure"
              },
              "risk_level": "low|medium|high",
              "requires_approval": true|false
            }
          ],
          "estimated_downtime": "5 minutes",
          "rollback_plan": "Detailed rollback procedure",
          "kb_articles_referenced": ["RHSA-2025:22760", "320491"]
        }

        IMPORTANT RULES:
        - Be thorough - use ALL available tools
        - **REQUIRED**: Search KB for every CVE found
        - kb_articles_referenced must NEVER be empty if CVEs exist
        - Include specific commands, not generic instructions
        - Test your reasoning with multiple evidence sources
        - Prioritize steps by impact and dependency order
        - Mark high-risk steps for approval
        - Provide rollback for destructive operations

        The log content is available in context as 'logFileContent'.
        Be systematic and exhaustive in your analysis.
```

**Key Changes:**
- Renamed to "Analyze & Generate Diagnostics"
- Added comprehensive 5-step diagnostic process
- Added MCP tools for security and knowledge base lookups
- Added structured JSON output format specification
- Added maxIterations: 20 for thorough investigation
- Added allowCancellation: true
- Temperature lowered to 0.2 for more deterministic output
- Complete system prompt from diagnostic_agent config

### 3. Updated Connections

**Deleted:**
```yaml
- id: conn_4
  from: element_4
  to: element_5

- id: conn_5
  from: element_5
  to: element_6
```

**Replaced with:**
```yaml
- id: conn_4
  from: element_4
  to: element_6
```

**Changes:**
- Removed intermediate connection through element_5
- Created direct connection from Analyze & Generate Diagnostics → Valid Results? gateway
- Simplified workflow flow

## Workflow Flow (After Changes)

```
Start Event (element_1)
    ↓
Receive Log File (element_2) ← User uploads log via web/API
    ↓ [file uploaded]
Analyze & Generate Diagnostics (element_4) ← AI performs complete analysis
    ↓
Valid Results? (element_6) ← Gateway checks if diagnostics are valid
    ↓ [yes]
Send for Dual Approval (element_21)
    ↓
... rest of workflow unchanged ...
```

## Benefits of This Change

1. **Reduced Latency**: Single AI task instead of two sequential tasks
2. **Simplified Architecture**: Fewer elements to manage and maintain
3. **Better Context**: AI agent has full context throughout the entire process
4. **More Efficient**: No need to serialize/deserialize between tasks
5. **Comprehensive Analysis**: Single prompt covers entire diagnostic workflow
6. **Fewer Failure Points**: One task means fewer places for errors to occur
7. **Cancellable**: Added allowCancellation for long-running analysis

## Key Features Added

### Security Analysis
- CVE lookup using security_lookup tool
- Automatic KB search for each CVE found
- Collection of all KB article references (RHSA, solution IDs)

### Remediation Planning
- Structured remediation steps with executor types
- Risk level assessment (low, medium, high)
- Approval requirements for high-risk steps
- Rollback plans for destructive operations
- Downtime estimation

### Structured Output
- JSON schema for consistent output format
- Required fields: root_causes, remediation_steps, rollback_plan
- Mandatory KB article references when CVEs are found

## Comparison: Before vs After

| Aspect | Before (2 Tasks) | After (1 Task) |
|--------|------------------|----------------|
| **Number of AI calls** | 2 | 1 |
| **Context passing** | Serialized between tasks | Single context |
| **Latency** | ~2x model invocation overhead | ~1x model invocation |
| **Complexity** | Higher (2 prompts, 2 configs) | Lower (1 prompt, 1 config) |
| **Error handling** | 2 failure points | 1 failure point |
| **Cancellation** | Not supported | Supported (allowCancellation: true) |
| **Output format** | Unstructured | Structured JSON |
| **KB integration** | Basic | Comprehensive (required for CVEs) |

## Migration Impact

### For Developers
- No code changes required in the executor
- The single agenticTask handles all diagnostic work
- Result variable contains complete JSON output

### For Users
- No visible change - workflow behavior is the same
- Faster execution (reduced latency)
- More comprehensive diagnostics (CVE + KB integration)
- Can cancel long-running analysis tasks

### For Administrators
- Simpler workflow monitoring (1 task instead of 2)
- Easier debugging (single prompt to review)
- Lower infrastructure costs (fewer AI calls)

## Rollback Plan

If you need to revert to two separate tasks:

1. Re-add element_5 (Generate Diagnostics agenticTask) at position (550, 330)
2. Restore original connections:
   - conn_4: element_4 → element_5
   - conn_5: element_5 → element_6
3. Simplify element_4 system prompt to focus only on log analysis
4. Move remediation generation logic back to element_5

## Testing Checklist

- [ ] Upload a log file with known CVEs - verify security_lookup is called
- [ ] Verify KB searches are performed for each CVE found
- [ ] Check that output contains all required JSON fields
- [ ] Verify remediation steps include executor types and risk levels
- [ ] Test cancellation during long-running analysis
- [ ] Verify kb_articles_referenced is populated when CVEs exist
- [ ] Test with logs containing no CVEs - verify graceful handling
- [ ] Verify rollback plans are generated for high-risk steps

## Questions?

**Q: Why consolidate into one task instead of keeping them separate?**
A: Single task reduces latency, maintains full context, and is easier to manage. The AI agent is capable of handling the entire diagnostic workflow in one invocation.

**Q: What if the analysis takes too long?**
A: The task now supports cancellation (allowCancellation: true). Users can cancel long-running analysis and retry with a different configuration.

**Q: How does this affect the AG-UI feedback?**
A: No change - the task still emits messaging, tool, and lifecycle events that are displayed in the feedback panel. You'll see all the tool calls (security_lookup, kb_search, etc.) in real-time.

**Q: What if I need to customize just the remediation generation?**
A: You can keep the consolidated task and adjust the system prompt's "GENERATE REMEDIATION PLAN" section without splitting the tasks.

**Q: Does this work with different AI models?**
A: Yes - the task uses anthropic/claude-3.5-sonnet by default, but you can change the model property to use other models (GPT-4, Gemini, etc.).
