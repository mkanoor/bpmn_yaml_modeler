#!/usr/bin/env python3
"""
Analyze Log File using BPMN Workflow

This script executes the log analysis workflow with a custom log file.

Usage:
    python analyze_log.py <path_to_log_file>

Example:
    python analyze_log.py /var/log/application.log
    python analyze_log.py ~/logs/error.log
"""

import requests
import sys
import os

def analyze_log_file(log_file_path):
    """Execute log analysis workflow with custom log file"""

    print("=" * 60)
    print("  Log Analysis Workflow")
    print("=" * 60)
    print()

    # Check if log file exists
    if not os.path.exists(log_file_path):
        print(f"❌ Error: Log file not found: {log_file_path}")
        sys.exit(1)

    print(f"📄 Reading log file: {log_file_path}")

    # Read the log file
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
            log_content = f.read()
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        sys.exit(1)

    log_size = len(log_content)
    log_lines = log_content.count('\n') + 1
    log_name = os.path.basename(log_file_path)

    print(f"   Size: {log_size:,} bytes")
    print(f"   Lines: {log_lines:,}")
    print()

    # Read the workflow YAML
    workflow_path = 'log-analysis-ansible-workflow.yaml'
    if not os.path.exists(workflow_path):
        print(f"❌ Error: Workflow file not found: {workflow_path}")
        print(f"   Make sure you're running this from the project root directory")
        sys.exit(1)

    print(f"📋 Loading workflow: {workflow_path}")

    try:
        with open(workflow_path, 'r') as f:
            workflow_yaml = f.read()
    except Exception as e:
        print(f"❌ Error reading workflow file: {e}")
        sys.exit(1)

    print()

    # Prepare execution request
    payload = {
        "yaml": workflow_yaml,
        "context": {
            "logFileContent": log_content,
            "logFileName": log_name
        }
    }

    print("🚀 Starting workflow execution...")
    print()

    # Execute workflow
    try:
        response = requests.post(
            'http://localhost:8000/workflows/execute',
            json=payload,
            timeout=10
        )
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend server")
        print("   Make sure the backend is running:")
        print("   cd backend && python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error executing workflow: {e}")
        sys.exit(1)

    if response.status_code == 200:
        result = response.json()
        print("=" * 60)
        print("✅ Workflow Started Successfully!")
        print("=" * 60)
        print()
        print(f"Instance ID: {result.get('instance_id')}")
        print(f"Status: {result.get('status')}")
        print()
        print("📧 What happens next:")
        print()
        print("1. AI analyzes your log file")
        print("   └─ Identifies errors, issues, and root causes")
        print()
        print("2. You receive an email with:")
        print("   ├─ Analysis summary and findings")
        print("   ├─ AI confidence score")
        print("   └─ Approve/Deny buttons")
        print()
        print("3. Click Approve in the email")
        print("   └─ AI generates Ansible playbook")
        print()
        print("4. You receive a second email with:")
        print("   ├─ Generated Ansible YAML")
        print("   ├─ Deployment instructions")
        print("   └─ Remediation steps")
        print()
        print("=" * 60)
        print()
        print("📬 Check your email inbox!")
        print()

    else:
        print("=" * 60)
        print("❌ Workflow Execution Failed")
        print("=" * 60)
        print()
        print(f"Status Code: {response.status_code}")
        print(f"Error: {response.text}")
        print()
        sys.exit(1)


def main():
    """Main entry point"""

    if len(sys.argv) != 2:
        print("Usage: python analyze_log.py <path_to_log_file>")
        print()
        print("Examples:")
        print("  python analyze_log.py /var/log/application.log")
        print("  python analyze_log.py ~/logs/error.log")
        print("  python analyze_log.py ./test.log")
        print()
        sys.exit(1)

    log_file = sys.argv[1]
    analyze_log_file(log_file)


if __name__ == '__main__':
    main()
