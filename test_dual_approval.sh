#!/bin/bash

# Test Dual Approval Workflow
# This script triggers a fresh workflow execution with both email and manual approval paths

echo "🚀 Starting dual approval workflow test..."
echo ""

# Trigger the workflow
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "'"$(cat workflows/ai-log-analysis-dual-approval-workflow.yaml | sed 's/"/\\"/g')"'",
    "context": {
      "logFileName": "test-error.log",
      "logFileContent": "ERROR: Connection timeout\nERROR: Memory leak detected\nWARNING: Disk space low",
      "logFileUrl": "s3://devops-logs/test-error.log",
      "issueCount": "3",
      "severityLevel": "High",
      "diagnosticSteps": "1. Check network connectivity\n2. Restart service\n3. Clear disk space"
    }
  }' | jq '.'

echo ""
echo "✅ Workflow started!"
echo ""
echo "Expected behavior:"
echo "  1. Both email and manual approval paths will start in parallel"
echo "  2. You will see a manual approval popup in the UI"
echo "  3. You will receive an email with approve/deny links"
echo "  4. When you approve via EITHER path:"
echo "     - The OTHER path should be automatically cancelled"
echo "     - The popup should close (if you approved via email)"
echo "     - The workflow should continue"
echo ""
echo "Watch the backend logs to see the cancellation events!"
