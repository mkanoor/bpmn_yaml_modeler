# Gateway Conditional Fix - Both Paths Issue Resolved

## Problem

The "Add Numbers" workflow was taking **BOTH paths** from the exclusive gateway, instead of just one path based on the condition.

**Expected Behavior:**
- If `sum > 10` → Take SUCCESS path only
- If `sum <= 10` → Take FAILURE (default) path only

**Actual Behavior:**
- Both SUCCESS and FAILURE paths were executing

---

## Root Cause

**Issue in `gateway_evaluator.py` (line 47):**

```python
# OLD CODE (WRONG)
condition = flow.name or flow.properties.get('condition', '')
```

**Problem:**
- Used `flow.name` as a fallback for condition
- The YAML had `name: "sum <= 10"` on the default path
- Since name was non-empty, it was treated as a condition expression
- Tried to evaluate `"sum <= 10"` as code, which failed or behaved unexpectedly

---

## The Fix

### 1. Fixed Gateway Evaluator (backend/gateway_evaluator.py)

**Exclusive Gateway (lines 45-65):**

**Before:**
```python
for flow in outgoing_flows:
    condition = flow.name or flow.properties.get('condition', '')  # ❌ Wrong

    if not condition or condition == '':
        # Take default path
```

**After:**
```python
for flow in outgoing_flows:
    condition = flow.properties.get('condition', '')  # ✅ Correct

    if condition == '':
        logger.info(f"Taking default path: {flow.id} (name: {flow.name})")
        # Take default path
        return [self.workflow.get_element_by_id(flow.to)]

    # Evaluate condition
    if self.evaluate_condition(condition, context):
        logger.info(f"Condition matched: {condition} (flow: {flow.id})")
        return [self.workflow.get_element_by_id(flow.to)]
```

**Changes:**
- ✅ Only uses `properties.condition`, not `name`
- ✅ Explicit `condition == ''` check for default path
- ✅ Returns immediately after finding match (XOR behavior)
- ✅ Better logging for debugging

---

**Inclusive Gateway (lines 104-117):**

**Before:**
```python
condition = flow.name or flow.properties.get('condition', '')  # ❌ Wrong
```

**After:**
```python
condition = flow.properties.get('condition', '')  # ✅ Correct

if condition == '' or self.evaluate_condition(condition, context):
    # Take this path
```

---

### 2. Updated YAML File

**Changed default path name (line 181):**

**Before:**
```yaml
- id: conn_6
  name: "sum <= 10"  # ❌ Confusing
  properties:
    condition: ""
```

**After:**
```yaml
- id: conn_6
  name: "default"  # ✅ Clear
  properties:
    condition: ""
```

**Why:**
- Makes it clear this is the default path
- Prevents confusion between `name` and `condition`
- `name` is just a label, `condition` is the logic

---

## How It Works Now

### Evaluation Order

**Gateway gets outgoing flows in this order:**
```yaml
1. conn_3: condition="${sum} > 10"  (SUCCESS path)
2. conn_6: condition=""             (DEFAULT path)
```

**Evaluation Logic:**

```python
# Flow 1: conn_3
condition = "${sum} > 10"
if condition == '':  # False
    # Skip
if evaluate_condition("${sum} > 10", context):  # Check sum
    if sum > 10:  # True for sum=12
        return SUCCESS_PATH  # ✅ Take this path, stop here
    else:  # False for sum=8
        # Continue to next flow

# Flow 2: conn_6
condition = ""
if condition == '':  # True
    return DEFAULT_PATH  # ✅ Take this path
```

**Result:**
- **Exactly ONE** path is taken
- First matching path wins
- Default path is fallback

---

## Test Cases

### Test 1: Sum > 10 (Success Path)

**Input:**
```yaml
script: |
  num1 = 7
  num2 = 5
  sum = 12
```

**Execution:**
```
1. Evaluate conn_3: "${sum} > 10"
   → 12 > 10 = True
   → Take SUCCESS path
   → STOP (XOR gateway)

2. conn_6 never evaluated
```

**Backend Logs:**
```
INFO: Added 7 + 5 = 12
INFO: Evaluating gateway: Sum > 10?
INFO: Condition matched: ${sum} > 10 (flow: conn_3)
INFO: Path to: Process Valid Sum
✅ Success path only
```

---

### Test 2: Sum <= 10 (Default Path)

**Input:**
```yaml
script: |
  num1 = 3
  num2 = 5
  sum = 8
```

**Execution:**
```
1. Evaluate conn_3: "${sum} > 10"
   → 8 > 10 = False
   → Continue to next flow

2. Evaluate conn_6: condition=""
   → Empty = default
   → Take FAILURE path
   → STOP
```

**Backend Logs:**
```
INFO: Added 3 + 5 = 8
INFO: Evaluating gateway: Sum > 10?
INFO: Taking default path: conn_6 (name: default)
INFO: Path to: Send Failure Notification
✅ Failure path only
```

---

## YAML Best Practices

### ✅ Correct Pattern

```yaml
# Gateway
- id: gateway_1
  type: exclusiveGateway

# Connections (conditional BEFORE default)
connections:
  # Conditional path - FIRST
  - id: conn_success
    name: "amount > 1000"  # Label for diagram
    from: gateway_1
    to: task_vip
    properties:
      condition: "${amount} > 1000"  # Actual logic

  # Default path - LAST
  - id: conn_default
    name: "default"        # Label for diagram
    from: gateway_1
    to: task_standard
    properties:
      condition: ""        # Empty = default
```

**Key Points:**
1. ✅ Conditional paths first
2. ✅ Default path last (empty condition)
3. ✅ Use `properties.condition` for logic
4. ✅ Use `name` for display label only

---

### ❌ Wrong Patterns

**Don't use name as condition:**
```yaml
# ❌ WRONG
- id: conn_bad
  name: "${sum} > 10"     # Name is just a label!
  properties:
    condition: ""          # Empty won't work
```

**Don't put default first:**
```yaml
# ❌ WRONG ORDER
connections:
  - condition: ""          # Default path first
  - condition: "${x} > 5"  # Never reached!
```

**Don't omit properties:**
```yaml
# ❌ INCOMPLETE
- id: conn_incomplete
  name: "some condition"
  # Missing properties.condition!
```

---

## Summary of Changes

### Files Modified

**1. backend/gateway_evaluator.py**
- Line 48: Changed to use only `properties.condition`
- Line 51-52: Explicit empty condition check
- Line 60: Better logging
- Line 108: Same fix for inclusive gateway

**2. add-numbers-conditional-workflow.yaml**
- Line 181: Changed name from "sum <= 10" to "default"

---

### What's Fixed

✅ **Exclusive Gateway:**
- Only ONE path taken
- Conditions evaluated in order
- First match wins
- Default path is fallback

✅ **Inclusive Gateway:**
- Multiple paths can be taken
- Only if conditions match
- Empty condition = always taken

✅ **YAML Structure:**
- Clear separation of `name` vs `condition`
- Default path clearly labeled
- Proper ordering (conditional before default)

---

## How to Create Proper Conditional Workflows

### Step 1: Define Gateway

```yaml
- id: my_gateway
  type: exclusiveGateway
  name: Check Amount
```

### Step 2: Add Conditional Paths (Order Matters!)

```yaml
connections:
  # Path 1: High value (check FIRST)
  - id: conn_high
    name: "amount > 10000"
    from: my_gateway
    to: task_vip_processing
    properties:
      condition: "${amount} > 10000"

  # Path 2: Medium value (check SECOND)
  - id: conn_medium
    name: "amount > 1000"
    from: my_gateway
    to: task_standard_processing
    properties:
      condition: "${amount} > 1000"

  # Path 3: Default (check LAST)
  - id: conn_default
    name: "default"
    from: my_gateway
    to: task_reject
    properties:
      condition: ""  # Empty = default
```

### Step 3: Test

**Test Case 1: amount = 15000**
```
Evaluate: 15000 > 10000 → True → VIP path ✅
Stop (XOR gateway)
```

**Test Case 2: amount = 5000**
```
Evaluate: 5000 > 10000 → False
Evaluate: 5000 > 1000 → True → Standard path ✅
Stop (XOR gateway)
```

**Test Case 3: amount = 500**
```
Evaluate: 500 > 10000 → False
Evaluate: 500 > 1000 → False
Evaluate: "" (empty) → True → Default path ✅
Stop (XOR gateway)
```

---

## Verification

### Check Your Workflow Works Correctly

1. **Import** `add-numbers-conditional-workflow.yaml`
2. **Execute** with defaults (7 + 5 = 12)
3. **Check logs:**
   ```
   INFO: Condition matched: ${sum} > 10 (flow: conn_3)
   ✅ Only one path taken
   ```
4. **Modify** script to use 3 + 5 = 8
5. **Execute** again
6. **Check logs:**
   ```
   INFO: Taking default path: conn_6 (name: default)
   ✅ Only one path taken
   ```

---

## Troubleshooting

### Problem: Both Paths Still Executing

**Check:**
1. ✅ Is `properties.condition` set (not just `name`)?
2. ✅ Is default path **last** in connections list?
3. ✅ Is default path condition empty: `condition: ""`?

**Debug:**
```python
# Check backend logs
INFO: Evaluating gateway: ...
INFO: Condition matched: ... (flow: ...)
# Should only see ONE path taken
```

### Problem: No Paths Taken

**Check:**
1. ✅ Is there a default path with empty condition?
2. ✅ Are conditions syntactically correct?
3. ✅ Do variables exist in context?

---

## Final Result

✅ **Gateway now works correctly:**
- ONE path for exclusive gateway
- Conditions evaluated in order
- Default path as fallback
- Clear logging for debugging

✅ **YAML template ready:**
- Easy to edit conditions
- Clear structure
- Proper defaults

✅ **UI supports editing:**
- Click connections to edit
- Change condition values
- Add new paths

**Your workflow is now ready to use!** 🎉
