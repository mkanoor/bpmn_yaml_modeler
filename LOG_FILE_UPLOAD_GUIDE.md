# Local Log File Upload Guide

## New Feature: Upload Log Files from Your Disk

You can now upload log files directly from your local machine instead of needing S3 buckets!

## How to Use

### 1. Start the Backend

```bash
./start-backend.sh
```

Or:
```bash
cd backend
python main.py
```

### 2. Open the Frontend

```bash
open index.html
```

### 3. Import the AI Log Analysis Workflow

1. Click **"Import YAML"**
2. Select `ai-log-analysis-workflow.yaml`
3. The workflow will appear on the canvas

### 4. Execute with Local Log File

1. Click **"▶ Execute Workflow"** button
2. A modal dialog will appear with two sections:

   **Upload Log File:**
   - Click the file input area
   - Browse to select a log file from your disk
   - Example: Select `sample-error.log` from the project directory

   **Context Variables:**
   - Edit the JSON to add any additional context
   - The log file will be automatically added to context
   - Default context:
     ```json
     {
       "requester": {
         "email": "user@example.com",
         "name": "Test User"
       }
     }
     ```

3. Click **"Start Execution"**

### 5. Watch the Analysis

The workflow will:
1. Read your log file content
2. Pass it to the agentic task
3. Analyze the log file for errors, warnings, and critical messages
4. Show tool usage notifications (filesystem-read, grep-search, log-parser)
5. Generate diagnostic findings
6. Display an approval form with the analysis results

## What Happens Behind the Scenes

### Frontend (JavaScript)

```javascript
// Read the log file
const logFileContent = await readFileAsText(file);

// Add to context
context.logFileContent = logFileContent;  // Full file content
context.logFileName = file.name;          // "sample-error.log"
context.logFileUrl = `local://${file.name}`;  // Local identifier
```

### Backend (Python)

```python
# AgenticTaskExecutor receives context with log content
log_content = context.get('logFileContent', '')
log_file_name = context.get('logFileName', 'unknown.log')

# Analyze the log content
errors = log_content.lower().count('error')
warnings = log_content.lower().count('warning')
critical = log_content.lower().count('critical')

# Generate findings
findings = [
    f'Found {errors} errors, {warnings} warnings, {critical} critical',
    'Analysis of log patterns complete',
    ...
]

# Check for specific issues
if 'disk' in log_content.lower():
    findings.append('Potential disk space issue detected')
if 'memory' in log_content.lower():
    findings.append('Potential memory issue detected')
```

## Testing with Sample Log File

A sample log file is included: `sample-error.log`

This file contains:
- ✅ 8 ERROR messages
- ✅ 6 WARNING messages
- ✅ 2 CRITICAL messages
- ✅ Various issues: cache connection, database timeout, memory, disk space

### Expected Analysis Results

When you upload `sample-error.log`, the agent will detect:

1. **Error Count:** "Found 8 errors, 6 warnings, 2 critical messages"
2. **Connection Issues:** "Potential connection/timeout issue detected"
3. **Memory Issues:** "Potential memory issue detected"
4. **Disk Issues:** "Potential disk space issue detected"

## Context Variables Explained

After uploading a log file, your context will automatically include:

```json
{
  "logFileContent": "2024-12-19 10:23:45 [INFO] Application started...",
  "logFileName": "sample-error.log",
  "logFileUrl": "local://sample-error.log",
  "requester": {
    "email": "user@example.com",
    "name": "Test User"
  }
}
```

You can reference these in your workflow:
- `${logFileName}` - The filename
- `${logFileUrl}` - Local path identifier
- Use `logFileContent` in agentic tasks for analysis

## Visual Feedback

During execution you'll see:

1. **Tool Usage Notifications** (top right):
   ```
   🔧 filesystem-read
      path: sample-error.log
      encoding: utf-8

   🔧 grep-search
      pattern: ERROR|FATAL|CRITICAL
      content_preview: 2024-12-19 10:23:45 [INFO]...

   🔧 log-parser
      format: detect
      file: sample-error.log
   ```

2. **Analysis Results** in approval form:
   - Found errors, warnings, critical counts
   - Detected issues (disk, memory, connection)
   - Recommended actions

## Advantages Over S3

### Before (S3 Required):
```json
{
  "logFileUrl": "s3://devops-logs/nginx-error.log"
}
```
- ❌ Needs S3 bucket setup
- ❌ Needs AWS credentials
- ❌ File must be uploaded first
- ❌ Costs money for storage

### Now (Local Upload):
```json
{
  "logFileContent": "...",
  "logFileName": "nginx-error.log",
  "logFileUrl": "local://nginx-error.log"
}
```
- ✅ No cloud setup needed
- ✅ Works offline
- ✅ Instant - no upload delay
- ✅ Free - no storage costs
- ✅ Perfect for development/testing

## Supported File Types

The file input accepts:
- `.log` files (standard log files)
- `.txt` files (text logs)
- Any text file (uses wildcard `*`)

## File Size Limits

**Browser Limits:**
- Files are read into memory
- Practical limit: ~10-50 MB for smooth performance
- Very large files (>100 MB) may slow down the browser

**Recommendations:**
- For testing: Use files < 10 MB
- For production: Consider chunking large files
- Tail logs before uploading: `tail -n 10000 huge.log > sample.log`

## Creating Test Log Files

### Generate a Simple Error Log

```bash
cat > test-error.log << 'EOF'
2024-12-19 12:00:00 [ERROR] Database connection failed
2024-12-19 12:00:01 [ERROR] Retry attempt 1 failed
2024-12-19 12:00:05 [CRITICAL] Service unavailable
2024-12-19 12:00:10 [WARNING] Falling back to cache
2024-12-19 12:00:15 [INFO] Service recovered
EOF
```

### Extract Real Application Logs

```bash
# Last 100 lines of nginx error log
tail -n 100 /var/log/nginx/error.log > nginx-sample.log

# Last hour of application logs
grep "2024-12-19 1[0-1]:" /var/log/app.log > app-sample.log

# Only errors and warnings
grep -E "ERROR|WARNING|CRITICAL" /var/log/app.log > errors-only.log
```

## Troubleshooting

### "No file selected" error

**Solution:** Make sure to click the file input and select a file before clicking "Start Execution"

### File content not appearing in analysis

**Solution:**
1. Check browser console for errors
2. Verify the file is a text file (not binary)
3. Try a smaller file first

### Analysis shows "0 errors" for a file with errors

**Solution:**
- The analysis is case-insensitive
- Make sure your log uses standard keywords: ERROR, WARNING, CRITICAL
- Check the file actually uploaded (look at tool notifications)

### Modal doesn't appear when clicking Execute

**Solution:**
1. Check browser console for JavaScript errors
2. Refresh the page
3. Make sure `workflow-executor.js` is loaded

## Example Workflow

Here's a complete example:

1. **Create a test log:**
   ```bash
   echo "2024-12-19 12:00:00 [ERROR] Test error" > my-test.log
   echo "2024-12-19 12:00:01 [WARNING] Test warning" >> my-test.log
   ```

2. **Import workflow:**
   - Click "Import YAML"
   - Select `ai-log-analysis-workflow.yaml`

3. **Execute:**
   - Click "▶ Execute Workflow"
   - Upload `my-test.log`
   - Click "Start Execution"

4. **Observe:**
   - Watch elements light up
   - See tool usage notifications
   - View analysis in approval form
   - Approve or reject the diagnostics

## Integration with Your Workflows

### In Your YAML Workflow

```yaml
- id: analyze_task
  type: agenticTask
  name: Analyze Logs
  properties:
    agentType: "log-analyzer"
    model: "claude-3-opus"
    custom:
      mcpTools:
        - "filesystem-read"
        - "grep-search"
        - "log-parser"
      systemPrompt: |
        Analyze the log file content provided in the context.
        Look for errors, warnings, and critical issues.
        Generate diagnostic recommendations.
```

The agentic task will automatically receive:
- `context['logFileContent']` - Full file text
- `context['logFileName']` - Filename
- `context['logFileUrl']` - Local path

### Accessing in Context

In gateway conditions:
```yaml
connections:
  - from: gateway_1
    to: error_handling
    name: "${element_4_result.findings.length > 0}"
```

In send tasks:
```yaml
properties:
  to: "${requester.email}"
  subject: "Analysis of ${logFileName}"
  messageBody: |
    Analysis complete for ${logFileName}
    Findings: ${element_4_result.findings}
```

## Summary

✅ **No S3 needed** - Upload directly from disk
✅ **Works offline** - No cloud dependencies
✅ **Instant feedback** - See analysis in real-time
✅ **Visual notifications** - Watch tool usage
✅ **Simple interface** - Just click and upload
✅ **Sample included** - `sample-error.log` ready to test

**Start analyzing your logs locally in seconds!** 🚀
