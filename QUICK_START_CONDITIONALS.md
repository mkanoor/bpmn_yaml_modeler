# Quick Start: Gateway Conditionals

## TL;DR - 30 Second Guide

### How It Works:
1. **Tasks** store data in `context`: `context['sum'] = 12`
2. **Gateways** check conditions on outgoing flows
3. **Conditions** use `${variable}` syntax: `"${sum} > 10"`
4. **First match** wins (exclusive gateway)

---

## Your Workflow: Add Numbers

**File:** `add-numbers-conditional-workflow.yaml`

### Visual Flow:
```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────────────────┐
│ Add Two Numbers     │  Script: sum = num1 + num2
│ (Script Task)       │  Stores: context['sum'] = 12
└──────────┬──────────┘
           │
           ▼
       ╱───────╲
      ╱  Sum >  ╲
     │   10?    │  Exclusive Gateway
      ╲         ╱
       ╲───┬───╱
           │
    ┌──────┴──────┐
    │             │
 YES│             │NO (default)
    │             │
    ▼             ▼
┌─────────┐   ┌─────────┐
│ Process │   │ Failure │
│ Valid   │   │ Notify  │
│ Sum     │   └────┬────┘
└────┬────┘        │
     │             ▼
     ▼          ┌─────────┐
┌─────────┐    │  FAIL   │
│ Success │    │  END    │
│ Notify  │    └─────────┘
└────┬────┘
     │
     ▼
┌─────────┐
│ SUCCESS │
│  END    │
└─────────┘
```

---

## Test Cases

### Test 1: Success (7 + 5 = 12 > 10)
```
Input:  number1=7, number2=5
Sum:    12
Check:  12 > 10 ✅
Path:   SUCCESS → Process → Notify → End
```

### Test 2: Failure (3 + 5 = 8 ≤ 10)
```
Input:  number1=3, number2=5
Sum:    8
Check:  8 > 10 ❌
Path:   FAILURE → Notify → Failed End
```

### Test 3: Edge (5 + 5 = 10 ≤ 10)
```
Input:  number1=5, number2=5
Sum:    10
Check:  10 > 10 ❌ (10 is NOT greater than 10)
Path:   FAILURE → Notify → Failed End
```

---

## Key Code Snippets

### Script Task (Stores Data)
```python
# In element_2 script:
num1 = context.get('number1', 7)
num2 = context.get('number2', 5)
result = num1 + num2
context['sum'] = result  # ← Available to gateway
```

### Gateway Condition (Reads Data)
```yaml
# Success path connection:
- id: conn_3
  from: element_3  # Gateway
  to: element_4    # Process Valid Sum
  name: "sum > 10"
  properties:
    condition: "${sum} > 10"  # ← Reads context['sum']
```

### Default Path (Fallback)
```yaml
# Failure path connection:
- id: conn_6
  from: element_3
  to: element_7
  name: "sum <= 10"
  properties:
    condition: ""  # ← Empty = default (if no other matches)
```

---

## How to Run

### Step 1: Import
1. Open `index.html`
2. Click "Import YAML"
3. Select `add-numbers-conditional-workflow.yaml`

### Step 2: Execute
1. Click "▶ Execute Workflow"
2. Watch the flow on canvas
3. Check backend logs

### Step 3: Observe
**Backend logs show:**
```
INFO: Executing script task: Add Two Numbers
INFO: Added 7 + 5 = 12
INFO: Evaluating gateway: Sum > 10?
INFO: Condition matched: ${sum} > 10
INFO: Path to: Process Valid Sum
```

---

## Condition Syntax Cheat Sheet

### Numbers
```yaml
"${sum} > 10"         # Greater than
"${sum} >= 10"        # Greater or equal
"${sum} < 10"         # Less than
"${sum} <= 10"        # Less or equal
"${sum} == 10"        # Equal
"${sum} != 10"        # Not equal
```

### Strings
```yaml
"${status} == 'approved'"
"${country} == 'USA'"
"${type} != 'spam'"
```

### Boolean
```yaml
"${approved}"                    # Check if true
"not ${rejected}"                # Check if false
"${active} and ${verified}"      # Both must be true
"${isAdmin} or ${isModerator}"   # Either is true
```

### Complex
```yaml
"${age} >= 18 and ${hasLicense}"
"${amount} > 1000 or ${vipMember}"
"${score} >= 90 and ${attempts} <= 3"
```

### Default (Always Matches)
```yaml
""  # Empty condition
```

---

## Common Patterns

### Pattern 1: Value Threshold
```yaml
# Check if value meets minimum
condition: "${orderTotal} >= 100"
```

### Pattern 2: Range Check
```yaml
# Check if value is in range
condition: "${age} >= 18 and ${age} < 65"
```

### Pattern 3: Multi-Criteria
```yaml
# Multiple conditions must be true
condition: "${approved} and ${confidence} >= 0.8 and not ${flagged}"
```

### Pattern 4: Tier Selection
```yaml
# Connection 1: Premium tier
condition: "${amount} > 10000"

# Connection 2: Standard tier
condition: "${amount} > 100"

# Connection 3: Default (reject)
condition: ""
```

---

## Troubleshooting

### Issue: Wrong Path Taken

**Check:**
1. Is variable in context? → Check task stores it
2. Is condition syntax correct? → Use `${variable}`
3. Is value what you expect? → Check backend logs

**Debug:**
```
INFO: Context: {'sum': 12, 'num1': 7, 'num2': 5}
INFO: Evaluating condition: ${sum} > 10
INFO: Condition result: True
```

### Issue: "No path matched" Error

**Fix:** Add default path
```yaml
# Always include this:
- from: gateway
  to: fallback_task
  properties:
    condition: ""  # Default
```

### Issue: Condition Not Working

**Common Mistakes:**
```yaml
# ❌ Wrong
condition: "sum > 10"              # Missing ${}
condition: "${status} == approved" # Missing quotes for string

# ✅ Correct
condition: "${sum} > 10"
condition: "${status} == 'approved'"
```

---

## Modify Your Workflow

### Change the Threshold
```yaml
# Make it require sum > 20
properties:
  condition: "${sum} > 20"
```

### Change Default Numbers
```yaml
script: |
  num1 = context.get('number1', 15)  # Default 15
  num2 = context.get('number2', 10)  # Default 10
  # Sum = 25 > 10 → Success
```

### Add Third Path
```yaml
# Add "Very High" path for sum > 50
- id: element_9
  type: task
  name: Process Very High Sum

# Add connection BEFORE other conditions
- from: element_3
  to: element_9
  name: "sum > 50"
  properties:
    condition: "${sum} > 50"

# Existing conditions follow
```

---

## Next Steps

1. **Import the workflow** → See it in action
2. **Modify conditions** → Change threshold values
3. **Add more paths** → Create tiered processing
4. **Use different operators** → Try `>=`, `<`, `!=`
5. **Combine conditions** → Use `and`, `or`, `not`

**Read full guide:** `GATEWAY_CONDITIONALS_GUIDE.md`

---

## Summary

✅ **Created:** Workflow with conditional gateway
✅ **Function:** Add numbers, route based on sum
✅ **Condition:** `${sum} > 10`
✅ **Success:** sum > 10 → Process → Success
✅ **Failure:** sum ≤ 10 → Notify → Failed

**It's ready to use!** 🚀
