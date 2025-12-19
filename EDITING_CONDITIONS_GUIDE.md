# How to Edit Gateway Conditions

## Quick Answer

To change the conditional value (like changing `sum > 10` to `sum > 20`):

### Method 1: In the UI (Easy!)

1. **Click** on the arrow/line coming out of the gateway
2. **Properties panel** appears on the right
3. **Edit** the "Condition" field
4. **Change** `${sum} > 10` to `${sum} > 20`
5. **Done!** Export YAML to save changes

### Method 2: In the YAML File (Direct)

1. **Open** `add-numbers-conditional-workflow.yaml` in text editor
2. **Find** the connection (around line 127):
   ```yaml
   - id: conn_3
     type: sequenceFlow
     name: "sum > 10"
     from: element_3
     to: element_4
     properties:
       condition: "${sum} > 10"  ← Change this value
   ```
3. **Change** to:
   ```yaml
   condition: "${sum} > 20"
   ```
4. **Save** file
5. **Import** updated YAML into UI

---

## UI Instructions (Detailed)

### Step 1: Select the Connection

**Visual:**
```
    ╱───────╲
   ╱ Gateway ╲
   ╲         ╱
    ╲───┬───╱
        │
        │ ← Click this arrow line!
        ▼
    ┌─────┐
    │Task │
    └─────┘
```

**How to:**
1. **Look** for the arrow/line leaving the gateway
2. **Click** directly on the line (not the gateway itself)
3. Line should **highlight** when selected
4. **Properties panel** on the right updates

### Step 2: Edit the Condition Field

**Properties Panel Shows:**
```
┌─────────────────────────────┐
│ Connection Properties       │
├─────────────────────────────┤
│ ID: conn_3                  │
│ (read-only, greyed out)     │
├─────────────────────────────┤
│ Name (Label): sum > 10      │ ← Display name
│                             │
├─────────────────────────────┤
│ Condition: ${sum} > 10      │ ← EDIT HERE!
│                             │
└─────────────────────────────┘
```

**What to Change:**
- **Condition field:** This is the actual logic evaluated
- **Name field:** Optional label shown on diagram

**Example Changes:**

```
Original:  ${sum} > 10
Change to: ${sum} > 20

Original:  ${sum} > 10
Change to: ${sum} >= 15

Original:  ${sum} > 10
Change to: ${sum} > 5 and ${sum} <= 100
```

### Step 3: Export Updated Workflow

1. **Click** "Export YAML" button
2. **Save** or download the updated workflow
3. **Import** it back if needed

---

## Common Condition Edits

### Change Threshold Value

**From:**
```yaml
condition: "${sum} > 10"
```

**To:**
```yaml
condition: "${sum} > 20"    # Now checks if sum > 20
condition: "${sum} > 5"     # Lower threshold
condition: "${sum} > 100"   # Higher threshold
```

### Change Operator

**From:**
```yaml
condition: "${sum} > 10"    # Greater than
```

**To:**
```yaml
condition: "${sum} >= 10"   # Greater than or equal
condition: "${sum} < 10"    # Less than
condition: "${sum} <= 10"   # Less than or equal
condition: "${sum} == 10"   # Exactly equal
condition: "${sum} != 10"   # Not equal
```

### Add Multiple Conditions

**From:**
```yaml
condition: "${sum} > 10"
```

**To:**
```yaml
condition: "${sum} > 10 and ${sum} < 100"  # Range check
condition: "${sum} > 10 or ${urgent}"      # Either condition
condition: "${sum} > 10 and ${approved}"   # Both must be true
```

### Change Variable

**From:**
```yaml
condition: "${sum} > 10"
```

**To:**
```yaml
condition: "${total} > 10"        # Different variable
condition: "${result} > 10"       # Check different result
condition: "${amount} > 10"       # Different context key
```

---

## YAML File Editing

### Finding the Right Connection

**Structure:**
```yaml
connections:
  # Success path
  - id: conn_3
    type: sequenceFlow
    name: "sum > 10"           # Label shown on diagram
    from: element_3            # From gateway
    to: element_4              # To success task
    properties:
      condition: "${sum} > 10" # ← EDIT THIS
      documentation: "..."

  # Failure path (default)
  - id: conn_6
    type: sequenceFlow
    name: "sum <= 10"
    from: element_3
    to: element_7
    properties:
      condition: ""            # Empty = default
```

### Making Changes

**1. Identify the connection:**
- Look at `from:` and `to:` fields
- Match to your workflow diagram
- Find the one leaving the gateway (`from: element_3`)

**2. Edit the condition:**
```yaml
# Before
properties:
  condition: "${sum} > 10"

# After
properties:
  condition: "${sum} > 20"
```

**3. Optionally update name:**
```yaml
# Before
name: "sum > 10"

# After
name: "sum > 20"  # Update label to match
```

**4. Save and reload:**
- Save YAML file
- Import into UI
- Execute to test

---

## Examples: Different Thresholds

### Example 1: Higher Threshold (sum > 50)

**YAML:**
```yaml
- id: conn_3
  name: "sum > 50"
  from: element_3
  to: element_4
  properties:
    condition: "${sum} > 50"
```

**Behavior:**
- Input: 7 + 5 = 12 → **FAIL** (12 ≤ 50)
- Input: 30 + 25 = 55 → **SUCCESS** (55 > 50)

### Example 2: Range Check (10 < sum < 100)

**YAML:**
```yaml
# Success path: sum in valid range
- id: conn_3
  name: "10 < sum < 100"
  from: element_3
  to: element_4
  properties:
    condition: "${sum} > 10 and ${sum} < 100"

# Failure path: out of range
- id: conn_6
  name: "out of range"
  from: element_3
  to: element_7
  properties:
    condition: ""  # Default
```

**Behavior:**
- 7 + 5 = 12 → **SUCCESS** (10 < 12 < 100)
- 50 + 60 = 110 → **FAIL** (110 ≥ 100)

### Example 3: Exact Value Check

**YAML:**
```yaml
- id: conn_3
  name: "sum == 12"
  from: element_3
  to: element_4
  properties:
    condition: "${sum} == 12"
```

**Behavior:**
- 7 + 5 = 12 → **SUCCESS** (exactly 12)
- 6 + 6 = 12 → **SUCCESS** (exactly 12)
- 10 + 5 = 15 → **FAIL** (not 12)

### Example 4: Not Equal

**YAML:**
```yaml
- id: conn_3
  name: "sum != 0"
  from: element_3
  to: element_4
  properties:
    condition: "${sum} != 0"
```

**Behavior:**
- Any non-zero sum → **SUCCESS**
- 0 + 0 = 0 → **FAIL**

---

## Testing Your Changes

### Method 1: Change Script Defaults

**In YAML, edit the script task:**
```yaml
- id: element_2
  type: scriptTask
  name: Add Two Numbers
  properties:
    script: |
      num1 = context.get('number1', 30)  # Changed from 7
      num2 = context.get('number2', 25)  # Changed from 5
      # Sum = 55, condition: ${sum} > 10 → SUCCESS
```

### Method 2: Test Different Thresholds

**Create multiple test cases:**

**Test 1: Threshold 20**
```yaml
condition: "${sum} > 20"
script: num1 = 15, num2 = 10  # Sum = 25 → SUCCESS
```

**Test 2: Threshold 50**
```yaml
condition: "${sum} > 50"
script: num1 = 30, num2 = 25  # Sum = 55 → SUCCESS
```

**Test 3: Threshold 100**
```yaml
condition: "${sum} > 100"
script: num1 = 60, num2 = 50  # Sum = 110 → SUCCESS
```

---

## Troubleshooting

### Problem: Condition Not Working

**Check:**
1. ✅ Syntax correct? `${variableName} operator value`
2. ✅ Variable exists? Script stores `context['sum']`
3. ✅ Quotes for strings? `${status} == 'approved'`
4. ✅ Connection selected? Click the arrow, not gateway

**Debug:**
```yaml
# ❌ Wrong
condition: "sum > 10"           # Missing ${}
condition: "${sum} > ten"       # 'ten' is string, not number
condition: "${status} == approved"  # Missing quotes

# ✅ Correct
condition: "${sum} > 10"
condition: "${sum} > 10"
condition: "${status} == 'approved'"
```

### Problem: Can't Select Connection

**Solution:**
1. **Zoom in** if connections are small
2. **Click directly** on the line (not endpoint)
3. **Look** for highlight when selected
4. **Check** properties panel updates

### Problem: Changes Not Saved

**Solution:**
1. **Export YAML** after editing in UI
2. **Save** the YAML file
3. **Re-import** to verify changes persist

---

## Quick Reference

### Changing Just the Number

**Find this in YAML:**
```yaml
condition: "${sum} > 10"
              ↑       ↑
           variable  number
```

**Change the number:**
```yaml
condition: "${sum} > 5"    # Lower
condition: "${sum} > 20"   # Higher
condition: "${sum} > 100"  # Much higher
```

### Changing the Operator

**Operators:**
```
>   Greater than
>=  Greater than or equal
<   Less than
<=  Less than or equal
==  Equal
!=  Not equal
```

**Examples:**
```yaml
condition: "${sum} > 10"   # More than 10
condition: "${sum} >= 10"  # 10 or more
condition: "${sum} < 10"   # Less than 10
condition: "${sum} <= 10"  # 10 or less
condition: "${sum} == 10"  # Exactly 10
condition: "${sum} != 10"  # Not 10
```

---

## Summary

### To Change Condition Value:

**Option 1: UI (Recommended)**
1. Click connection arrow
2. Edit "Condition" field in properties
3. Change value (e.g., 10 → 20)
4. Export YAML

**Option 2: YAML File**
1. Open YAML in editor
2. Find connection with `from: element_3`
3. Edit `condition: "${sum} > 10"`
4. Change 10 to your value
5. Save and import

### Common Changes:

```yaml
# Original
condition: "${sum} > 10"

# Higher threshold
condition: "${sum} > 20"

# Lower threshold
condition: "${sum} > 5"

# Different operator
condition: "${sum} >= 10"

# Range check
condition: "${sum} > 10 and ${sum} < 100"
```

**You can now easily modify any gateway condition!** 🎉
