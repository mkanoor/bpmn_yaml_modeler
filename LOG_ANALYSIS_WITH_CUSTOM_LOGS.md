# Using Custom Log Files with Log Analysis Workflow

## Overview

The log analysis workflow now supports **both sample data and custom log files**:

- **Default:** Uses built-in sample logs (database errors, memory issues, etc.)
- **Custom:** Provide your own log file content via execution context

## Method 1: Via API (Recommended)

### Execute with Custom Log Content

```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "... workflow YAML ...",
    "context": {
      "logFileContent": "2024-01-15 ERROR [App] Something failed\n2024-01-15 CRITICAL [DB] Connection lost",
      "logFileName": "my-app.log"
    }
  }'
```

### Execute with Log File from Disk

```bash
# Read log file and pass content
LOG_CONTENT=$(cat /path/to/your/logfile.log)

curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "yaml": $(cat log-analysis-ansible-workflow.yaml | jq -Rs .),
  "context": {
    "logFileContent": $(echo "$LOG_CONTENT" | jq -Rs .),
    "logFileName": "production.log"
  }
}
EOF
```

## Method 2: Via UI (Simple)

### Option A: Use Sample Data (Default)

1. Import workflow
2. Click Execute
3. Uses built-in sample logs automatically

### Option B: Modify Workflow YAML Before Import

1. Open `log-analysis-ansible-workflow.yaml`
2. Find the "Prepare Log Analysis" script task
3. Replace the sample log content:

```yaml
script: |
  # Read your actual log file
  with open('/path/to/your/logfile.log', 'r') as f:
      context['logFileContent'] = f.read()
  context['logFileName'] = 'production.log'
  context['logSource'] = 'file'

  # Generate analysis ID
  context['analysisId'] = f"ANALYSIS-{random.randint(1000, 9999)}"
  # ... rest of script
```

4. Import and execute

## Method 3: Python Script to Execute Workflow

Create a script to execute the workflow with your log file:

```python
#!/usr/bin/env python3
"""
Execute log analysis workflow with custom log file
"""
import requests
import yaml
import sys

def analyze_log_file(log_file_path):
    """Analyze a log file using the BPMN workflow"""

    # Read the log file
    with open(log_file_path, 'r') as f:
        log_content = f.read()

    # Read the workflow YAML
    with open('log-analysis-ansible-workflow.yaml', 'r') as f:
        workflow_yaml = f.read()

    # Prepare execution request
    payload = {
        "yaml": workflow_yaml,
        "context": {
            "logFileContent": log_content,
            "logFileName": log_file_path.split('/')[-1]
        }
    }

    # Execute workflow
    response = requests.post(
        'http://localhost:8000/workflows/execute',
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Workflow started!")
        print(f"Instance ID: {result.get('instance_id')}")
        print(f"\n📧 Check your email for:")
        print(f"  1. Analysis report with Approve/Deny buttons")
        print(f"  2. Ansible playbook (after approval)")
    else:
        print(f"❌ Error: {response.text}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyze_log.py <path_to_log_file>")
        sys.exit(1)

    log_file = sys.argv[1]
    analyze_log_file(log_file)
```

**Usage:**
```bash
python analyze_log.py /var/log/application.log
```

## How It Works

### Workflow Logic

```python
# In Prepare Log Analysis script task:

if 'logFileContent' not in context or not context['logFileContent']:
    # No custom log provided - use sample data
    context['logFileContent'] = '''...sample logs...'''
    context['logSource'] = 'sample'
else:
    # Custom log provided - use it!
    context['logFileName'] = context.get('logFileName', 'uploaded.log')
    context['logSource'] = 'uploaded'
```

### Automatic Severity Detection

The workflow automatically determines severity based on log content:

```python
if 'critical' in log_content or 'fatal' in log_content:
    severity = 'CRITICAL'
elif 'error' in log_content:
    severity = 'HIGH'
elif 'warning' in log_content:
    severity = 'MEDIUM'
else:
    severity = 'LOW'
```

## Examples

### Example 1: Nginx Error Log

```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "...",
    "context": {
      "logFileContent": "2024/01/15 10:23:45 [error] 1234#0: *567 connect() failed (111: Connection refused)\n2024/01/15 10:24:12 [crit] 1234#0: *568 SSL_do_handshake() failed",
      "logFileName": "nginx-error.log"
    }
  }'
```

### Example 2: Application Log with Stack Trace

```bash
LOG_CONTENT=$(cat app.log)

curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"yaml\": $(cat log-analysis-ansible-workflow.yaml | jq -Rs .),
    \"context\": {
      \"logFileContent\": $(echo "$LOG_CONTENT" | jq -Rs .),
      \"logFileName\": \"app.log\"
    }
  }"
```

### Example 3: Multi-File Analysis

For multiple log files, concatenate them:

```bash
LOG_CONTENT=$(cat /var/log/app/*.log)

curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"yaml\": $(cat log-analysis-ansible-workflow.yaml | jq -Rs .),
    \"context\": {
      \"logFileContent\": $(echo "$LOG_CONTENT" | jq -Rs .),
      \"logFileName\": \"combined-logs.log\"
    }
  }"
```

## Context Variables You Can Provide

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `logFileContent` | No | Sample logs | The actual log file content to analyze |
| `logFileName` | No | `application.log` or `uploaded.log` | Name of the log file |
| `severity` | No | Auto-detected | Override severity (CRITICAL, HIGH, MEDIUM, LOW) |

## Email Indicators

The analysis email will show whether sample or custom logs were used:

**With Sample Logs:**
```
Analysis ID: ANALYSIS-1234
Log File: application.log
Source: sample
```

**With Custom Logs:**
```
Analysis ID: ANALYSIS-5678
Log File: production.log
Source: uploaded
```

## Testing

### Test with Sample Data (No Setup Needed)

```bash
# Just import and execute in UI
# Uses built-in sample logs automatically
```

### Test with Custom Log

```bash
# Create test log
cat > test.log <<EOF
2024-01-15 10:00:00 ERROR Database connection failed
2024-01-15 10:00:05 CRITICAL Out of memory
2024-01-15 10:00:10 WARNING Slow query detected
EOF

# Execute workflow
python analyze_log.py test.log

# Check your email!
```

## Production Use

### Option 1: File Upload Endpoint (Future Enhancement)

```python
# Add to backend/main.py
@app.post("/workflows/analyze-log")
async def analyze_log_endpoint(file: UploadFile = File(...)):
    """Upload log file and analyze"""
    content = await file.read()
    log_content = content.decode('utf-8')

    # Load workflow YAML
    with open('log-analysis-ansible-workflow.yaml') as f:
        workflow_yaml = f.read()

    # Execute with context
    # ... execute workflow with logFileContent = log_content
```

### Option 2: S3/Cloud Storage Integration

```python
# In Prepare Log Analysis script task
import boto3

# Read from S3
s3_url = context.get('logFileUrl')  # e.g., s3://bucket/logs/app.log
if s3_url:
    s3 = boto3.client('s3')
    bucket = s3_url.split('/')[2]
    key = '/'.join(s3_url.split('/')[3:])

    response = s3.get_object(Bucket=bucket, Key=key)
    context['logFileContent'] = response['Body'].read().decode('utf-8')
    context['logFileName'] = key.split('/')[-1]
```

### Option 3: API Integration

```python
# Trigger from external system
import requests

# Your monitoring system detects an issue
# Automatically triggers log analysis

response = requests.post('http://bpmn-server:8000/workflows/execute', json={
    'yaml': workflow_yaml,
    'context': {
        'logFileContent': fetch_recent_logs(),
        'logFileName': 'incident-logs.txt',
        'severity': 'CRITICAL'
    }
})
```

## Limitations

### Log File Size

- **Current limit:** Python string size (typically ~100MB)
- **Recommended:** Keep logs under 10MB for better AI analysis
- **For large files:** Pre-filter or split into chunks

### Log Format

- Works with any text-based log format
- AI analysis handles various formats automatically
- Structured logs (JSON) work well
- Unstructured logs also supported

## Troubleshooting

### Issue: Workflow uses sample data instead of my file

**Check:**
1. Verify `logFileContent` is in execution context
2. Check that content is not empty string
3. Ensure content is a string, not binary

### Issue: Log content truncated

**Solution:** Split large logs:
```python
# Take last 10,000 lines
with open('huge.log') as f:
    lines = f.readlines()
    context['logFileContent'] = ''.join(lines[-10000:])
```

### Issue: Special characters in logs

**Solution:** Ensure proper encoding:
```python
with open('logfile.log', 'r', encoding='utf-8', errors='replace') as f:
    context['logFileContent'] = f.read()
```

## Summary

**Default Behavior:**
- No setup needed
- Uses sample logs automatically
- Good for testing workflow functionality

**Custom Logs:**
- Provide `logFileContent` in execution context
- Use API, script, or modify workflow YAML
- Production-ready for real log analysis

**Best Practice:**
- Start with sample data to test the workflow
- Move to custom logs for real analysis
- Use API/script for automated integration

🚀 **Ready to analyze your logs?** Start with the sample data, then provide your own!
