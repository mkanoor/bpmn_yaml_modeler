# BPMN Gateway Conditionals Guide

## Overview

Gateways in BPMN are decision points that control the flow of your workflow based on **conditions**. Your BPMN executor supports powerful conditional logic using context variables and expressions.

---

## How BPMN Gateway Conditionals Work

### 1. Context Variables

Throughout workflow execution, tasks store results in the **context** (a key-value store):

```python
context = {
    'sum': 12,
    'num1': 7,
    'num2': 5,
    'approved': True,
    'confidence': 0.92
}
```

### 2. Sequence Flow Conditions

Each outgoing flow from a gateway can have a **condition** that determines if it should be taken:

```yaml
connections:
  - id: conn_1
    from: gateway_1
    to: task_success
    name: "sum > 10"
    properties:
      condition: "${sum} > 10"
```

### 3. Condition Evaluation

The `GatewayEvaluator` (backend/gateway_evaluator.py) evaluates conditions:

**Evaluation Process:**
1. Extract condition from sequence flow `name` or `properties.condition`
2. Resolve variables from context: `${sum}` → `12`
3. Evaluate expression: `12 > 10` → `True`
4. Take the first matching path (exclusive gateway)

---

## Gateway Types

### 1. Exclusive Gateway (XOR) - One Path Only

**Symbol:** Diamond with "×" inside

**Behavior:**
- Evaluates conditions **in order**
- Takes **first matching** path
- Exactly **one path** is taken
- If no condition matches, raises error (always provide default)

**Use When:**
- Mutually exclusive outcomes
- Either/or decisions
- Single choice scenarios

**Example:**
```yaml
# Gateway
- id: gateway_check_amount
  type: exclusiveGateway
  name: Amount Check

# Connections
- from: gateway_check_amount
  to: task_vip_processing
  name: "amount > 1000"
  properties:
    condition: "${amount} > 1000"

- from: gateway_check_amount
  to: task_standard_processing
  name: "default"
  properties:
    condition: ""  # Empty = default path
```

**Result:** If amount = 1500 → VIP processing; If amount = 500 → Standard processing

---

### 2. Parallel Gateway (AND) - All Paths

**Symbol:** Diamond with "+" inside

**Behavior:**
- Takes **all outgoing paths** simultaneously
- No condition evaluation (conditions ignored)
- All paths execute in parallel

**Use When:**
- Multiple tasks must happen concurrently
- Fan-out/fan-in patterns
- Parallel processing

**Example:**
```yaml
- id: gateway_parallel_split
  type: parallelGateway
  name: Process in Parallel

# All these paths execute simultaneously
- from: gateway_parallel_split
  to: task_send_email

- from: gateway_parallel_split
  to: task_update_database

- from: gateway_parallel_split
  to: task_log_event
```

---

### 3. Inclusive Gateway (OR) - One or More Paths

**Symbol:** Diamond with "○" inside

**Behavior:**
- Evaluates **all conditions**
- Takes **all matching** paths
- At least **one path** must match

**Use When:**
- Multiple non-exclusive outcomes
- Optional parallel paths
- Multiple conditions can be true

**Example:**
```yaml
- id: gateway_notify
  type: inclusiveGateway
  name: Determine Notifications

# Multiple paths can be taken
- from: gateway_notify
  to: task_email
  properties:
    condition: "${notifyEmail} == True"

- from: gateway_notify
  to: task_sms
  properties:
    condition: "${notifySMS} == True"

- from: gateway_notify
  to: task_slack
  properties:
    condition: "${notifySlack} == True"
```

**Result:** If `notifyEmail=True` and `notifySMS=True` → Both email and SMS sent

---

## Condition Syntax

### Variable Reference Syntax

**Format:** `${variableName}`

```yaml
# In connections
properties:
  condition: "${sum} > 10"
  condition: "${approved} == True"
  condition: "${confidence} >= 0.8"
```

### Supported Condition Types

#### 1. Comparison Operators

```yaml
# Greater than
condition: "${age} > 18"
condition: "${amount} > 1000"

# Greater than or equal
condition: "${confidence} >= 0.8"
condition: "${score} >= 90"

# Less than
condition: "${count} < 5"
condition: "${temperature} < 100"

# Less than or equal
condition: "${attempts} <= 3"

# Equal
condition: "${status} == 'approved'"
condition: "${count} == 10"

# Not equal
condition: "${result} != 'error'"
condition: "${type} != 'spam'"
```

#### 2. Boolean Conditions

```yaml
# Check if true
condition: "${approved}"
condition: "${isValid}"

# Check if false
condition: "not ${approved}"
condition: "${rejected}"
```

#### 3. Logical Operators

```yaml
# AND
condition: "${age} > 18 and ${hasLicense} == True"
condition: "${score} >= 90 and ${attempts} <= 3"

# OR
condition: "${isAdmin} or ${isModerator}"
condition: "${amount} > 1000 or ${vipMember}"

# NOT
condition: "not ${banned}"
condition: "${enabled} and not ${suspended}"

# Complex
condition: "${age} >= 18 and (${hasPermit} or ${isResident})"
```

#### 4. String Conditions

```yaml
# String equality
condition: "${status} == 'approved'"
condition: "${country} == 'USA'"

# String in list (advanced)
condition: "${role} in ['admin', 'moderator']"

# Contains (using Python 'in')
condition: "'error' in ${message}"
```

#### 5. Arithmetic in Conditions

```yaml
# Calculate then compare
condition: "${price} * ${quantity} > 1000"
condition: "${total} - ${discount} < 100"

# Percentage
condition: "${correct} / ${total} >= 0.8"
```

#### 6. Default Path (No Condition)

```yaml
# Empty condition = default path (taken if no other matches)
condition: ""

# Or omit properties entirely
name: "default"
```

---

## Real-World Examples

### Example 1: Age Verification

```yaml
elements:
  - id: task_1
    type: userTask
    name: Enter Age

  - id: gateway_1
    type: exclusiveGateway
    name: Age Check

  - id: task_adult
    type: task
    name: Adult Content

  - id: task_minor
    type: task
    name: Minor Content

connections:
  - from: gateway_1
    to: task_adult
    name: "age >= 18"
    properties:
      condition: "${age} >= 18"

  - from: gateway_1
    to: task_minor
    name: "default"
    properties:
      condition: ""
```

---

### Example 2: Approval Confidence Check

```yaml
elements:
  - id: task_analyze
    type: agenticTask
    name: Analyze Document
    properties:
      # Stores result with confidence score

  - id: gateway_confidence
    type: exclusiveGateway
    name: Confidence Check

  - id: task_auto_approve
    type: task
    name: Auto Approve

  - id: task_human_review
    type: userTask
    name: Human Review Required

connections:
  - from: gateway_confidence
    to: task_auto_approve
    name: "High Confidence"
    properties:
      condition: "${confidence} >= 0.9"

  - from: gateway_confidence
    to: task_human_review
    name: "Low Confidence"
    properties:
      condition: ""  # Default
```

---

### Example 3: Multi-Notification (Inclusive Gateway)

```yaml
elements:
  - id: gateway_notify
    type: inclusiveGateway
    name: Send Notifications

  - id: task_email
    type: sendTask
    name: Email Notification

  - id: task_sms
    type: sendTask
    name: SMS Notification

  - id: task_push
    type: sendTask
    name: Push Notification

connections:
  # Can take multiple paths
  - from: gateway_notify
    to: task_email
    properties:
      condition: "${preferences.email} == True"

  - from: gateway_notify
    to: task_sms
    properties:
      condition: "${preferences.sms} == True and ${urgent}"

  - from: gateway_notify
    to: task_push
    properties:
      condition: "${preferences.push} == True"
```

---

### Example 4: Order Processing

```yaml
elements:
  - id: gateway_order_value
    type: exclusiveGateway
    name: Order Value Check

connections:
  - from: gateway_order_value
    to: task_vip_processing
    name: "Premium Order"
    properties:
      condition: "${orderTotal} > 10000"

  - from: gateway_order_value
    to: task_standard_processing
    name: "Standard Order"
    properties:
      condition: "${orderTotal} >= 100 and ${orderTotal} <= 10000"

  - from: gateway_order_value
    to: task_reject_order
    name: "Minimum Not Met"
    properties:
      condition: ""  # Default: < 100
```

---

## Your Example Workflow: Add Numbers with Conditional

### Workflow Description

**File:** `add-numbers-conditional-workflow.yaml`

**Flow:**
1. **Start** → Workflow begins
2. **Add Two Numbers (Script Task)** → Adds `number1 + number2`, stores `sum` in context
3. **Exclusive Gateway** → Checks if `sum > 10`
   - **YES (sum > 10)** → Process Valid Sum → Send Success Notification → Success End
   - **NO (sum <= 10)** → Send Failure Notification → Failed End

### Key Components

#### Script Task (Add Numbers)
```yaml
- id: element_2
  type: scriptTask
  name: Add Two Numbers
  properties:
    scriptFormat: "Python"
    script: |
      num1 = context.get('number1', 7)  # Default: 7
      num2 = context.get('number2', 5)  # Default: 5
      result = num1 + num2
      context['sum'] = result           # Store in context
```

**What it does:**
- Gets `number1` and `number2` from context (or uses defaults)
- Calculates sum
- Stores `sum`, `num1`, `num2` in context for gateway

#### Exclusive Gateway (Decision)
```yaml
- id: element_3
  type: exclusiveGateway
  name: Sum > 10?
```

**What it does:**
- Evaluates outgoing flow conditions
- Takes first matching path

#### Success Path (sum > 10)
```yaml
- id: conn_3
  name: "sum > 10"
  from: element_3
  to: element_4
  properties:
    condition: "${sum} > 10"
```

**When taken:** If sum is 11, 12, 15, 100, etc.

#### Failure Path (sum <= 10) - Default
```yaml
- id: conn_6
  name: "sum <= 10"
  from: element_3
  to: element_7
  properties:
    condition: ""  # Empty = default
```

**When taken:** If sum is 10, 9, 5, 0, etc.

---

## Testing the Workflow

### Test Case 1: Success (sum > 10)

**Input:**
```python
context['number1'] = 7
context['number2'] = 5
```

**Expected:**
- Sum = 12
- Condition `${sum} > 10` → True
- Path: Success → Process Valid Sum → Success Notification → End

**Backend logs:**
```
INFO: Added 7 + 5 = 12
INFO: Evaluating gateway: Sum > 10?
INFO: Condition matched: ${sum} > 10
INFO: Taking path to: Process Valid Sum
```

---

### Test Case 2: Failure (sum <= 10)

**Input:**
```python
context['number1'] = 3
context['number2'] = 5
```

**Expected:**
- Sum = 8
- Condition `${sum} > 10` → False
- Default path taken
- Path: Failure → Failure Notification → End

**Backend logs:**
```
INFO: Added 3 + 5 = 8
INFO: Evaluating gateway: Sum > 10?
INFO: Taking default path: conn_6
INFO: Path to: Send Failure Notification
```

---

### Test Case 3: Edge Case (sum = 10)

**Input:**
```python
context['number1'] = 5
context['number2'] = 5
```

**Expected:**
- Sum = 10
- Condition `${sum} > 10` → False (10 is NOT greater than 10)
- Default path taken
- Path: Failure

---

## How to Use This Workflow

### Option 1: Import and Execute

1. **Open** `index.html` in browser
2. **Click** "Import YAML"
3. **Select** `add-numbers-conditional-workflow.yaml`
4. **Click** "▶ Execute Workflow"
5. **Watch** the execution flow

### Option 2: Customize Input Numbers

Edit the workflow file to change default numbers:

```yaml
script: |
  num1 = context.get('number1', 15)  # Changed from 7
  num2 = context.get('number2', 8)   # Changed from 5
  # Sum will be 23, which is > 10
```

### Option 3: Provide Input via Context

If you enhance the start event to accept input:

```python
# Before execution
context['number1'] = 20
context['number2'] = 30
# Sum = 50 → Success path
```

---

## Advanced Conditional Patterns

### Pattern 1: Multi-Level Decision Tree

```yaml
# First Gateway: Check Category
- id: gateway_1
  type: exclusiveGateway
  name: Category?

# If category = 'premium'
- from: gateway_1
  to: gateway_2
  condition: "${category} == 'premium'"

# Second Gateway: Check Amount
- id: gateway_2
  type: exclusiveGateway
  name: Amount?

- from: gateway_2
  to: task_vip
  condition: "${amount} > 10000"

- from: gateway_2
  to: task_standard_premium
  condition: ""
```

---

### Pattern 2: Conditional with Multiple Criteria

```yaml
# Complex condition combining multiple factors
connections:
  - from: gateway_approval
    to: task_auto_approve
    properties:
      condition: "${amount} < 1000 and ${confidence} >= 0.9 and ${riskScore} < 0.3"

  - from: gateway_approval
    to: task_manager_review
    properties:
      condition: "${amount} >= 1000 or ${riskScore} >= 0.5"

  - from: gateway_approval
    to: task_reject
    properties:
      condition: ""  # Everything else
```

---

### Pattern 3: Nested Gateways with Fallback

```yaml
# Outer Gateway: Initial Check
- id: gateway_outer
  type: exclusiveGateway

- from: gateway_outer
  to: task_fast_path
  condition: "${urgent} and ${approved}"

- from: gateway_outer
  to: gateway_inner
  condition: "not ${urgent}"

# Inner Gateway: Secondary Check
- id: gateway_inner
  type: exclusiveGateway

- from: gateway_inner
  to: task_normal_processing
  condition: "${approved}"

- from: gateway_inner
  to: task_pending
  condition: ""
```

---

## Troubleshooting

### Problem: Gateway Takes Wrong Path

**Possible Causes:**
1. Condition syntax error
2. Variable not in context
3. Wrong variable type

**Solution:**
```python
# Check backend logs
INFO: Evaluating condition: ${sum} > 10
DEBUG: Context: {'sum': 12, 'num1': 7, 'num2': 5}
INFO: Condition result: True
```

---

### Problem: "No path matched" Error

**Cause:** Exclusive gateway has no default path and no conditions matched

**Solution:** Always provide a default (empty condition):
```yaml
- from: gateway_1
  to: task_default
  name: "default"
  properties:
    condition: ""
```

---

### Problem: Variable Not Found

**Error:** `KeyError: 'variableName'`

**Solution:**
```python
# In script tasks, use .get() with defaults
value = context.get('variableName', default_value)

# Or check existence
if 'variableName' in context:
    value = context['variableName']
```

---

### Problem: Condition Not Evaluating

**Cause:** Missing `${}` syntax or quotes for strings

**Wrong:**
```yaml
condition: "sum > 10"           # 'sum' treated as undefined variable
condition: status == approved   # Missing quotes for string
```

**Correct:**
```yaml
condition: "${sum} > 10"
condition: "${status} == 'approved'"
```

---

## Best Practices

### 1. Always Provide Default Path
```yaml
# ✅ Good: Has default
- from: gateway
  to: success
  condition: "${approved}"

- from: gateway
  to: fallback
  condition: ""  # Default

# ❌ Bad: No default
- from: gateway
  to: success
  condition: "${approved}"
# What if approved is False or missing?
```

---

### 2. Use Clear Condition Names
```yaml
# ✅ Good: Descriptive
name: "High Confidence (>= 0.9)"
condition: "${confidence} >= 0.9"

# ❌ Bad: Unclear
name: "Path 1"
condition: "${x} > 10"
```

---

### 3. Validate Context Variables
```python
# In script tasks, validate before using
if 'sum' not in context:
    context['sum'] = 0

if context['sum'] < 0:
    context['sum'] = 0
```

---

### 4. Document Complex Conditions
```yaml
properties:
  condition: "${age} >= 18 and ${hasLicense} and not ${suspended}"
  documentation: |
    This path is taken when:
    - User is 18 or older
    - User has valid license
    - User is not suspended
```

---

### 5. Order Conditions by Specificity
```yaml
# ✅ Good: Most specific first
- condition: "${amount} > 10000"   # VIP
- condition: "${amount} > 1000"    # Premium
- condition: "${amount} > 100"     # Standard
- condition: ""                     # Default

# ❌ Bad: Default path matches everything first
- condition: ""                     # Default (always matches!)
- condition: "${amount} > 10000"   # Never reached
```

---

## Summary

### How Gateway Conditionals Work:

1. **Tasks store data** in context during execution
2. **Gateways evaluate conditions** on outgoing flows
3. **Conditions reference context** using `${variableName}` syntax
4. **First matching path** is taken (exclusive gateway)
5. **Default path** (empty condition) is fallback

### Supported Features:

✅ Comparison operators (`>`, `<`, `>=`, `<=`, `==`, `!=`)
✅ Boolean logic (`and`, `or`, `not`)
✅ String comparisons
✅ Arithmetic expressions
✅ Default paths
✅ Context variable resolution

### Your Workflow:

✅ **Created:** `add-numbers-conditional-workflow.yaml`
✅ **Function:** Adds two numbers, checks if sum > 10
✅ **Success Path:** sum > 10 → Process → Success
✅ **Failure Path:** sum <= 10 → Notify → Failed

**Try it now!** Import the workflow and watch the conditional logic in action! 🚀
