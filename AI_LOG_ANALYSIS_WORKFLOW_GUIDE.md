# AI-Powered Log Analysis & Remediation Workflow

## Overview

This BPMN workflow demonstrates a complete AI-driven DevOps process that:
1. **Receives** log files from users
2. **Analyzes** logs using AI agents with MCP tools
3. **Generates** diagnostic steps automatically
4. **Requires human approval** before proceeding
5. **Creates** Ansible playbooks for remediation
6. **Executes** infrastructure changes

## Workflow Architecture

### Three-Lane Design

```
┌─────────────────────────────────────────────────────────┐
│ User Interaction Lane                                   │
│  Upload → Receive → Store → ┌─ Approve ─┐ → Notify     │
└────────────────────────────┼────────────┼──────────────┘
                             │            │
┌────────────────────────────┼────────────┼──────────────┐
│ AI Analysis & Generation   │            │              │
│  Analyze → Generate → ──────┘  Generate Playbook       │
│  (MCP)    Diagnostics          Validate                │
└─────────────────────────────────────────┼──────────────┘
                                          │
┌─────────────────────────────────────────┼──────────────┐
│ Execution & Deployment                  │              │
│  Store Playbook → Execute → Notify → End               │
└────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Agentic Task: Log Analysis with MCP Tools

**Purpose:** Analyze uploaded log files using AI with MCP tool capabilities

**Properties:**
```yaml
agentType: "log-analyzer"
model: "claude-3-opus"
capabilities:
  - log-parsing
  - pattern-recognition
  - root-cause-analysis
  - mcp-tool-usage

mcpTools:
  - filesystem-read      # Read log files
  - grep-search         # Search for patterns
  - regex-match         # Pattern matching
  - log-parser          # Parse structured logs
  - error-classifier    # Classify errors
```

**What It Does:**
- Uses MCP filesystem tools to read uploaded logs
- Searches for error patterns and anomalies
- Identifies root causes using pattern recognition
- Classifies issues by severity
- Extracts relevant context

**System Prompt:**
```
You are an expert DevOps engineer analyzing system logs.
Use MCP tools to:
1. Read and parse log files
2. Search for error patterns
3. Identify root causes
4. Classify issue severity
5. Generate diagnostic steps
```

### 2. Agentic Task: Generate Diagnostic Steps

**Purpose:** Convert analysis findings into actionable diagnostic steps

**Properties:**
```yaml
agentType: "diagnostic-generator"
model: "gpt-4"
capabilities:
  - step-generation
  - prioritization
  - validation

outputFormat: "json"
prioritizeBySeverity: "true"
estimateImpact: "true"
```

**Output Example:**
```json
{
  "diagnosticSteps": [
    {
      "step": 1,
      "action": "Check disk space on /var partition",
      "severity": "high",
      "estimatedImpact": "critical",
      "command": "df -h /var",
      "expectedOutcome": "Available space > 20%"
    },
    {
      "step": 2,
      "action": "Restart nginx service",
      "severity": "medium",
      "estimatedImpact": "moderate",
      "command": "systemctl restart nginx",
      "expectedOutcome": "Service active"
    }
  ],
  "rootCause": "Disk space exhaustion in /var/log",
  "confidence": 0.92
}
```

### 3. User Task: Review & Approve Diagnostics

**Purpose:** Human-in-the-loop approval before automated remediation

**Form Fields:**
- **Diagnostic Steps** - List of proposed actions
- **Severity Level** - Impact assessment
- **Estimated Impact** - Predicted changes
- **Approval Decision** - Approve/Reject
- **Comments** - Human feedback

**Why This Matters:**
- Prevents automated actions on critical systems
- Allows domain expertise to validate AI decisions
- Provides audit trail for compliance
- Enables continuous learning from feedback

### 4. Agentic Task: Generate Ansible Playbook

**Purpose:** Create production-ready Ansible playbook from approved diagnostics

**Properties:**
```yaml
agentType: "playbook-generator"
model: "claude-3-sonnet"
capabilities:
  - ansible-generation
  - yaml-formatting
  - best-practices
  - idempotency-check

mcpTools:
  - ansible-validator
  - yaml-linter
  - security-checker

playbookStandard: "ansible-2.16"
includeRollback: "true"
validationLevel: "strict"
```

**Generated Playbook Example:**
```yaml
---
- name: Remediate disk space issues
  hosts: affected_servers
  become: yes

  pre_tasks:
    - name: Check current disk space
      shell: df -h /var
      register: disk_before
      changed_when: false

    - name: Verify we have space to proceed
      assert:
        that: disk_before.stdout | regex_search('[0-9]+%') | int < 95
        fail_msg: "Disk critically full - manual intervention required"

  tasks:
    - name: Clean old log files
      find:
        paths: /var/log
        age: 30d
        recurse: yes
      register: old_logs

    - name: Archive old logs
      archive:
        path: "{{ item.path }}"
        dest: "/backup/logs/{{ item.path | basename }}.gz"
        remove: yes
      loop: "{{ old_logs.files }}"
      when: old_logs.files | length > 0

    - name: Restart affected services
      systemd:
        name: nginx
        state: restarted
      register: service_restart

  post_tasks:
    - name: Verify disk space improved
      shell: df -h /var
      register: disk_after
      changed_when: false

    - name: Send metrics
      uri:
        url: "https://metrics.company.com/api/remediation"
        method: POST
        body_format: json
        body:
          before: "{{ disk_before.stdout }}"
          after: "{{ disk_after.stdout }}"
          playbook: "disk-cleanup"

  rescue:
    - name: Rollback on failure
      # Restore from backup if needed
      debug:
        msg: "Playbook failed - manual review required"
```

## Workflow Steps Detailed

### Phase 1: Log Upload & Storage
1. **User Uploads Log** (Start Event)
   - Web UI or API endpoint
   - Supports common log formats

2. **Receive Log File** (Receive Task)
   - Validates file format
   - Checks file size limits
   - Timeout: 5 minutes

3. **Store in S3** (Service Task)
   - Uploads to secure S3 bucket
   - Applies encryption (AES256)
   - Sets 30-day retention
   - Returns S3 URL for processing

### Phase 2: AI Analysis
4. **Analyze Logs with MCP** (Agentic Task)
   - AI agent reads log file from S3
   - Uses MCP tools for file operations
   - Searches for error patterns
   - Identifies anomalies
   - Determines root cause

5. **Generate Diagnostics** (Agentic Task)
   - Converts findings to steps
   - Prioritizes by severity
   - Estimates impact
   - Formats as JSON
   - Calculates confidence score

6. **Valid Results?** (Gateway)
   - **Yes** (confidence ≥ 0.8) → Continue to approval
   - **No** (confidence < 0.8) → Escalate to manual review

### Phase 3: Human Approval
7. **Review & Approve Diagnostics** (User Task)
   - Assigned to log uploader + DevOps team
   - High priority
   - 2-hour SLA
   - Shows diagnostic steps, severity, impact
   - Human makes approve/reject decision

8. **Approved?** (Gateway)
   - **Approved** → Generate Ansible playbook
   - **Rejected** → Notify user and end

### Phase 4: Playbook Generation
9. **Generate Ansible Playbook** (Agentic Task)
   - Creates playbook from approved steps
   - Follows Ansible best practices
   - Includes pre-flight checks
   - Adds error handling
   - Implements rollback logic
   - Uses MCP tools for validation

10. **Validate Syntax** (Script Task)
    - Runs ansible-lint
    - Validates YAML syntax
    - Checks security issues
    - Returns validation results

11. **Valid Playbook?** (Gateway)
    - **Valid** → Store and execute
    - **Invalid** → Attempt to fix and regenerate (max 2 attempts)

### Phase 5: Execution
12. **Store Playbook** (Service Task)
    - Commits to Git repository
    - Versions the playbook
    - Tags with metadata

13. **Execute on Target Systems** (Manual Task)
    - DevOps team runs playbook
    - Monitors execution
    - Verifies results

14. **Send Success Notification** (Send Task)
    - Emails stakeholders
    - Includes summary and results
    - Links to playbook in Git

15. **Workflow Complete** (End Event)

## Error Handling Paths

### Path 1: Invalid AI Diagnostics
```
Generate Diagnostics → Valid? (No) → Manual Analysis Required → Escalated
```
When AI confidence is too low, a senior SRE reviews manually.

### Path 2: User Rejection
```
Review & Approve → Approved? (No) → Notify Rejection → Rejected by Human
```
User can reject diagnostics with comments for feedback loop.

### Path 3: Playbook Validation Failure
```
Validate Syntax → Valid? (No) → Fix & Regenerate → (retry) → Generate Playbook
```
Attempts to auto-fix validation errors up to 2 times.

## MCP Tool Integration

### Available MCP Tools

**For Log Analysis:**
- `filesystem-read` - Read log files from storage
- `grep-search` - Search for specific patterns
- `regex-match` - Advanced pattern matching
- `log-parser` - Parse structured logs (JSON, syslog, etc.)
- `error-classifier` - Classify error types and severity

**For Playbook Generation:**
- `ansible-validator` - Validate playbook syntax
- `yaml-linter` - Check YAML formatting
- `security-checker` - Scan for security issues

### How AI Agents Use MCP Tools

**Example Agent Interaction:**
```python
# AI Agent's internal process (conceptual)

# 1. Read the log file
log_content = mcp_tool('filesystem-read', {
    'path': log_file_url,
    'encoding': 'utf-8'
})

# 2. Search for errors
errors = mcp_tool('grep-search', {
    'content': log_content,
    'pattern': r'ERROR|FATAL|CRITICAL',
    'context_lines': 5
})

# 3. Parse structured entries
parsed_logs = mcp_tool('log-parser', {
    'content': log_content,
    'format': 'json'
})

# 4. Classify errors
classifications = mcp_tool('error-classifier', {
    'errors': errors,
    'context': parsed_logs
})

# 5. Generate diagnostic steps based on findings
diagnostics = generate_steps(classifications)
```

## Configuration Properties

### Critical Properties to Configure

**Log Analyzer Agent:**
```yaml
model: "claude-3-opus"          # Best for complex analysis
contextWindow: "16384"           # Large context for full logs
temperature: "0.3"               # Lower = more focused
confidenceThreshold: 0.8         # Minimum confidence to proceed
```

**Diagnostic Generator:**
```yaml
model: "gpt-4"                   # Good at structured output
temperature: "0.2"               # Very focused for JSON
outputFormat: "json"             # Structured diagnostic steps
```

**Playbook Generator:**
```yaml
model: "claude-3-sonnet"        # Great at code generation
temperature: "0.1"               # Very deterministic
playbookStandard: "ansible-2.16" # Target Ansible version
includeRollback: "true"          # Safety first
validationLevel: "strict"        # No shortcuts
```

## Security Considerations

### 1. **Log File Handling**
- Upload size limits enforced
- Virus scanning before processing
- Encryption at rest (S3)
- Automatic cleanup after 30 days

### 2. **Human Approval Required**
- No automated execution without approval
- Audit trail of all decisions
- Role-based access control

### 3. **Playbook Validation**
- Syntax checking (ansible-lint)
- Security scanning
- No hardcoded credentials
- Dry-run before execution

### 4. **Execution Controls**
- Manual execution step
- Rollback capabilities
- Limited scope (affected hosts only)
- Monitoring and alerting

## Metrics & Observability

Track these metrics:

- **Analysis Time** - Time from upload to diagnostics
- **Approval Time** - Time spent in human review
- **Confidence Scores** - AI confidence over time
- **Approval Rate** - % of diagnostics approved
- **Success Rate** - % of playbooks that execute successfully
- **Time to Remediation** - End-to-end workflow time

## Continuous Improvement

### Learning Loop
1. **Human feedback** (approval/rejection) stored
2. **Execution results** tracked
3. **AI agents** retrained with feedback
4. **Confidence thresholds** adjusted based on accuracy

## Real-World Example

**Scenario:** Web server returning 502 errors

**1. User uploads nginx error.log**
```
2024-03-15 10:23:45 [error] 1234#1234: *1 connect() failed (111: Connection refused)
2024-03-15 10:23:46 [error] 1234#1234: *2 connect() failed (111: Connection refused)
2024-03-15 10:23:47 [crit] 1234#1234: *3 open() "/var/log/nginx/access.log" failed (28: No space left on device)
```

**2. AI Analysis Output:**
```json
{
  "rootCause": "Disk full on /var partition preventing nginx from writing logs",
  "severity": "critical",
  "affectedService": "nginx",
  "diagnosticSteps": [
    "Check disk space: df -h /var",
    "Identify large files: du -sh /var/log/* | sort -rh",
    "Rotate/compress old logs",
    "Restart nginx service"
  ],
  "confidence": 0.94
}
```

**3. Human Reviews and Approves**

**4. Generated Ansible Playbook:**
- Checks disk space
- Archives logs older than 7 days
- Restarts nginx
- Verifies service health

**5. Executed and Resolved**

## Import and Use

### To Import This Workflow:
```bash
1. Open index.html in browser
2. Click "Import YAML"
3. Select "ai-log-analysis-workflow.yaml"
4. View the complete workflow with 3 lanes
```

### To Customize:
1. **Click on Agentic Tasks** to view/edit MCP tool configurations
2. **Adjust confidence thresholds** based on your risk tolerance
3. **Modify approval process** (assignees, priority, SLA)
4. **Add more error handling** paths as needed
5. **Export YAML** when done

## Benefits of This Workflow

✅ **Automated Analysis** - AI reads and understands logs
✅ **MCP Tool Integration** - Leverages powerful file/search capabilities
✅ **Human Oversight** - Critical approval step prevents mistakes
✅ **Code Generation** - Creates production-ready Ansible
✅ **Error Handling** - Multiple safety nets and retry logic
✅ **Audit Trail** - Complete record of decisions and actions
✅ **Scalable** - Handles routine issues automatically
✅ **Learning** - Gets better over time with feedback

## Next Steps

1. **Import the workflow** to visualize it
2. **Configure MCP servers** for tool access
3. **Set up S3 bucket** for log storage
4. **Deploy AI agents** with configured models
5. **Integrate with your systems** (upload endpoint, Ansible Tower, etc.)
6. **Monitor and iterate** based on results

This workflow represents the future of DevOps: AI-assisted, human-approved, automatically remediated! 🚀
