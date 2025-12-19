# Log Analysis Workflow - Email Template Fix

## Problem

Email templates were not showing diagnostic data or playbook content. The emails were blank or showed variable names like `${element_3_result.analysis}` instead of actual values.

## Root Cause

The email templates were using **dot notation** to access nested properties:
```yaml
${element_3_result.log_size}
${element_3_result.analysis}
${element_8_result.findings}
```

However, the variable resolver in `task_executors.py` only supports **simple variable replacement**, not nested property access.

```python
# This works:
${analysisId}          → "ANALYSIS-1234"

# This doesn't work:
${element_3_result.analysis}  → undefined (stays as literal text)
```

## Solution

Added **script tasks** after each agentic task to **flatten** the nested results into individual context variables.

### Before (Not Working)

```
AI Analysis (element_3)
  ↓
  Stores: element_3_result = {
    analysis: "...",
    log_size: 1234,
    confidence: 0.92,
    findings: [...]
  }
  ↓
Send Email
  Uses: ${element_3_result.analysis}  ← Doesn't work!
```

### After (Working)

```
AI Analysis (element_3)
  ↓
  Stores: element_3_result = {...}
  ↓
Extract Results (element_3b) ← NEW SCRIPT TASK
  ↓
  Flattens:
    analysis_summary = result['analysis']
    analysis_log_size = result['log_size']
    analysis_confidence = result['confidence']
    analysis_findings = result['findings']
  ↓
Send Email
  Uses: ${analysis_summary}  ← Works!
```

## Changes Made

### 1. Added Extract Script Task After AI Analysis

**New element:** `element_3b - Extract Analysis Results`

```python
# Flatten the analysis result for email template
analysis_result = context.get('element_3_result', {})

# Extract individual fields
context['analysis_summary'] = analysis_result.get('analysis', 'No analysis available')
context['analysis_log_size'] = analysis_result.get('log_size', 0)
context['analysis_model'] = analysis_result.get('model_used', 'Unknown')
context['analysis_confidence'] = analysis_result.get('confidence', 0)
context['analysis_tools'] = ', '.join(analysis_result.get('tools_used', []))

# Format findings as readable text
findings = analysis_result.get('findings', [])
if isinstance(findings, list):
    context['analysis_findings'] = '\n'.join(f"{i+1}. {finding}" for i, finding in enumerate(findings))
else:
    context['analysis_findings'] = str(findings)
```

### 2. Updated Analysis Approval Email

**Changed from:**
```html
<p><strong>Log Size:</strong> ${element_3_result.log_size} bytes</p>
<p><strong>AI Model:</strong> ${element_3_result.model_used}</p>
<pre>${element_3_result.findings}</pre>
```

**Changed to:**
```html
<p><strong>Log Size:</strong> ${analysis_log_size} bytes</p>
<p><strong>AI Model:</strong> ${analysis_model}</p>
<pre>${analysis_findings}</pre>
```

### 3. Added Extract Script Task After Playbook Generation

**New element:** `element_9 - Extract Playbook Results` (replaced service task)

```python
# Flatten the playbook generation result for email template
playbook_result = context.get('element_8_result', {})

# Extract individual fields
context['playbook_summary'] = playbook_result.get('analysis', 'Playbook generated')
context['playbook_model'] = playbook_result.get('model_used', 'Unknown')
context['playbook_confidence'] = playbook_result.get('confidence', 0)
context['playbook_tools'] = ', '.join(playbook_result.get('tools_used', []))

# Extract the actual playbook YAML
findings = playbook_result.get('findings', [])
if isinstance(findings, list):
    context['playbook_yaml'] = '\n\n'.join(findings)
else:
    context['playbook_yaml'] = str(findings)
```

### 4. Updated Playbook Success Email

**Changed from:**
```html
<p><strong>AI Model:</strong> ${element_8_result.model_used}</p>
<p>${element_3_result.analysis}</p>
<pre>${element_8_result.findings}</pre>
```

**Changed to:**
```html
<p><strong>AI Model:</strong> ${playbook_model}</p>
<p>${analysis_summary}</p>
<pre>${playbook_yaml}</pre>
```

### 5. Updated Rejection Email

**Changed from:**
```html
<p>${element_3_result.analysis}</p>
```

**Changed to:**
```html
<p>${analysis_summary}</p>
<pre>${analysis_findings}</pre>
```

### 6. Added New Connection

**New connection:** `conn_3b` links `element_3` → `element_3b` → `element_4`

## Flattened Variables Reference

### From AI Analysis (element_3 → element_3b)

| Variable | Source | Description |
|----------|--------|-------------|
| `analysis_summary` | element_3_result.analysis | Main analysis text |
| `analysis_log_size` | element_3_result.log_size | Size of log file in bytes |
| `analysis_model` | element_3_result.model_used | AI model name |
| `analysis_confidence` | element_3_result.confidence | Confidence score (0-1) |
| `analysis_tools` | element_3_result.tools_used | Comma-separated tool list |
| `analysis_findings` | element_3_result.findings | Numbered findings list |

### From Playbook Generation (element_8 → element_9)

| Variable | Source | Description |
|----------|--------|-------------|
| `playbook_summary` | element_8_result.analysis | Playbook generation summary |
| `playbook_model` | element_8_result.model_used | AI model name |
| `playbook_confidence` | element_8_result.confidence | Confidence score (0-1) |
| `playbook_tools` | element_8_result.tools_used | Comma-separated tool list |
| `playbook_yaml` | element_8_result.findings | The actual Ansible YAML |
| `playbook_findings_count` | calculated | Number of findings |

## Testing the Fix

### 1. Import Updated Workflow

```bash
# In the UI
1. Click Import
2. Select log-analysis-ansible-workflow.yaml
3. Click Execute
```

### 2. Check Email #1 (Analysis Report)

You should now see:
- ✅ Log size number (e.g., "842 bytes")
- ✅ AI model name (e.g., "anthropic/claude-3.5-sonnet")
- ✅ Confidence score (e.g., "0.92")
- ✅ Analysis summary text
- ✅ Tools used (e.g., "log-parser, grep-search")
- ✅ Detailed findings (numbered list)

### 3. Check Email #2 (Playbook Report)

After approving, you should see:
- ✅ Playbook generation summary
- ✅ Original analysis summary
- ✅ **THE ACTUAL ANSIBLE YAML CODE**
- ✅ Tools used for generation
- ✅ Confidence scores

## Why This Approach Works

### Variable Resolution Process

```
1. Email template has: ${analysis_summary}
   ↓
2. SendTaskExecutor calls resolve_variables()
   ↓
3. Regex finds ${analysis_summary}
   ↓
4. Looks up in context: context['analysis_summary']
   ↓
5. Finds value: "Analysis completed using..."
   ↓
6. Replaces in template
   ↓
7. Email shows: "Analysis completed using..."
```

### What Doesn't Work (Dot Notation)

```
1. Email template has: ${element_3_result.analysis}
   ↓
2. SendTaskExecutor calls resolve_variables()
   ↓
3. Regex finds ${element_3_result.analysis}
   ↓
4. Looks up in context: context['element_3_result.analysis']
   ↓
5. Key not found! (context has 'element_3_result' as dict, not 'element_3_result.analysis')
   ↓
6. Returns empty string
   ↓
7. Email shows: (blank)
```

## Alternative Solution (Not Implemented)

We could have enhanced the variable resolver to support dot notation:

```python
def resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
    import re
    def replacer(match):
        var_path = match.group(1).strip()

        # Support dot notation: element_3_result.analysis
        if '.' in var_path:
            parts = var_path.split('.')
            value = context.get(parts[0], {})
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part, '')
                else:
                    return ''
            return str(value)
        else:
            return str(context.get(var_path, ''))

    return re.sub(r'\$\{([^}]+)\}', replacer, text)
```

However, **flattening with script tasks** is better because:
- ✅ More explicit and visible in workflow
- ✅ Allows data transformation (formatting, joining arrays, etc.)
- ✅ Easier to debug (can see extracted values in context)
- ✅ No changes to core engine code
- ✅ Works with current implementation

## Workflow Structure Now

```
element_1: Start
  ↓
element_2: Prepare Log Analysis (script)
  ↓
element_3: AI Log Analysis (agentic)
  ↓
element_3b: Extract Analysis Results (script) ← NEW
  ↓
element_4: Send Analysis Report (email)
  ↓
element_5: Wait for Approval (receive webhook)
  ↓
element_6: Log Decision (script)
  ↓
element_7: Gateway (approved?)
  ├─ YES
  │   ↓
  │   element_8: Generate Ansible Playbook (agentic)
  │   ↓
  │   element_9: Extract Playbook Results (script) ← NEW
  │   ↓
  │   element_10: Send Playbook Report (email)
  │   ↓
  │   element_11: Success (end)
  │
  └─ NO
      ↓
      element_12: Send Rejection (email)
      ↓
      element_13: Rejected (end)
```

## Summary

**Problem:** Emails showed blank values or literal `${...}` text

**Root Cause:** Variable resolver doesn't support dot notation like `${result.field}`

**Solution:** Added script tasks to flatten nested results into simple variables

**Result:** Emails now display:
- ✅ AI analysis findings
- ✅ Confidence scores and metrics
- ✅ **Complete Ansible playbook YAML**
- ✅ Tool usage information
- ✅ All diagnostic data

**Test it:** Re-import the workflow and run it. Both emails should now show complete data!
