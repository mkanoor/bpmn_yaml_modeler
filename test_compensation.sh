#!/bin/bash

echo "========================================"
echo "Testing Compensation Workflow"
echo "========================================"
echo ""

echo "1. Testing SUCCESS scenario (payment succeeds, no compensation):"
echo "----------------------------------------------------------------"
python backend/main.py \
  workflows/compensation-rollback-example.yaml \
  context-examples/compensation-success-context.json 2>&1 | \
  grep -E "Book|Payment|Confirmation|COMPENSAT|✅|❌|🔄|💳|🛫|🏨|📧"

echo ""
echo ""
echo "2. Testing FAILURE scenario (payment fails, triggers compensation):"
echo "--------------------------------------------------------------------"
python backend/main.py \
  workflows/compensation-rollback-example.yaml \
  context-examples/compensation-failure-context.json 2>&1 | \
  grep -E "Book|Payment|Error|COMPENSAT|✅|❌|🔄|💳|🛫|🏨|📧|Cancell"

echo ""
echo "========================================"
echo "Test Complete"
echo "========================================"
