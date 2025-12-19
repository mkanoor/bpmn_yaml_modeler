# BPMN Subprocess Guide: Collapsed vs Expanded

## Can Subprocesses Be Viewed on the Same Screen?

**YES!** BPMN supports two display modes for subprocesses:

1. **Collapsed Subprocess** - Compact box with [+] symbol
2. **Expanded Subprocess** - Shows internal flow directly on canvas

This modeler supports BOTH modes with easy toggle functionality!

## Understanding BPMN Subprocesses

### What is a Subprocess?

A subprocess is a **process within a process** - a way to:
- **Decompose** complex processes into manageable pieces
- **Organize** related activities together
- **Reuse** common process patterns
- **Hide** complexity while maintaining detail
- **Improve readability** of large diagrams

### Collapsed vs Expanded

| Feature | Collapsed | Expanded |
|---------|-----------|----------|
| **Display** | Single box with [+] | Full internal flow visible |
| **Size** | Fixed (100x60px) | Variable (default 300x200px) |
| **Children** | Hidden | Visible on same canvas |
| **Use Case** | High-level view | Detailed documentation |
| **Symbol** | **+** at bottom | **−** at bottom |

## Visual Comparison

### Collapsed Subprocess
```
┌──────────────────┐
│                  │
│  Payment Process │  ← Compact representation
│                  │
│        +         │  ← Plus symbol
└──────────────────┘
```

### Expanded Subprocess
```
┌─────────────────────────────────────────────────┐
│ Payment Process                        −        │  ← Minus symbol
│                                                  │
│   ○ → [Authorize] → <Approved?> → [Capture]    │  ← Internal flow
│                          │                       │     visible
│                          ↓                       │
│                    [Notify Failure]              │
│                                                  │
└─────────────────────────────────────────────────┘
```

## How to Use in the Modeler

### Method 1: Click the +/− Button
1. Add a Sub-Process from the palette
2. Click the **+** symbol at the bottom
3. Subprocess expands showing internal flow
4. Click **−** to collapse again

### Method 2: Use Properties Panel
1. Select the subprocess
2. In Properties Panel, find "Display" section
3. Check **"Expanded (show internal flow)"**
4. Uncheck to collapse

### Default Behavior
When first expanded, a subprocess automatically contains:
- Start Event (left side)
- End Event (right side)
- You can add more elements by modifying the YAML

## YAML Structure for Subprocesses

### Collapsed Subprocess
```yaml
- id: subprocess_1
  type: subProcess
  name: Payment Processing
  x: 400
  y: 200
  expanded: false  # Collapsed
  properties:
    documentation: "Handle payment operations"
```

### Expanded Subprocess
```yaml
- id: subprocess_1
  type: subProcess
  name: Payment Processing
  x: 400
  y: 200
  expanded: true   # Expanded!
  width: 400       # Expanded size
  height: 200
  properties:
    documentation: "Handle payment operations"

  # Child elements (relative to subprocess center)
  childElements:
    - id: child_start
      type: startEvent
      name: Start
      x: -150  # Relative position
      y: 0
      properties: {}

    - id: child_task
      type: serviceTask
      name: Authorize Payment
      x: -50
      y: 0
      properties:
        implementation: "External"
        topic: "payment-auth"

    - id: child_end
      type: endEvent
      name: End
      x: 100
      y: 0
      properties: {}

  # Connections between child elements
  childConnections:
    - id: child_conn_1
      type: sequenceFlow
      from: child_start
      to: child_task

    - id: child_conn_2
      type: sequenceFlow
      from: child_task
      to: child_end
```

## Coordinate System for Child Elements

Child elements use **relative coordinates** from the subprocess center:

```
Subprocess Center (0, 0)
    │
    ├─ (-100, 0)  ← Left side
    ├─ (+100, 0)  ← Right side
    ├─ (0, -50)   ← Top
    └─ (0, +50)   ← Bottom
```

**Example Layout:**
- Start Event: x=-150 (far left)
- Task 1: x=-50 (left of center)
- Gateway: x=50 (right of center)
- Task 2: x=100, y=-40 (upper right)
- End Event: x=150 (far right)

## Creating Complex Subprocess Flows

### Example: Payment with Retry Logic
```yaml
childElements:
  - id: start
    type: startEvent
    x: -180
    y: 0

  - id: authorize
    type: serviceTask
    name: Authorize Card
    x: -100
    y: 0

  - id: check
    type: exclusiveGateway
    name: Success?
    x: 0
    y: 0

  - id: capture
    type: serviceTask
    name: Capture Payment
    x: 80
    y: -40

  - id: retry
    type: task
    name: Retry Logic
    x: 0
    y: 60

  - id: fail
    type: endEvent
    name: Failed
    x: 180
    y: 60

  - id: success
    type: endEvent
    name: Success
    x: 180
    y: -40

childConnections:
  - from: start
    to: authorize

  - from: authorize
    to: check

  - from: check
    to: capture
    name: "yes"

  - from: check
    to: retry
    name: "no"

  - from: retry
    to: authorize  # Loop back!

  - from: capture
    to: success

  # After max retries
  - from: retry
    to: fail
    name: "max retries"
```

## When to Use Collapsed vs Expanded

### Use Collapsed When:
✅ Creating high-level overview diagrams
✅ Subprocess details aren't immediately relevant
✅ You want to reduce visual clutter
✅ The subprocess is well-documented elsewhere
✅ Presenting to executives/non-technical stakeholders

### Use Expanded When:
✅ Documenting complete process details
✅ Training new team members
✅ The subprocess is critical to understanding
✅ You want everything visible at once
✅ Creating technical documentation

## Best Practices

### 1. Naming Conventions
```yaml
# Good subprocess names:
name: "Payment Processing"
name: "Customer Notification"
name: "Error Handling"

# Avoid:
name: "Subprocess 1"
name: "Process"
```

### 2. Subprocess Size
- **Default**: 300x200 works for most cases
- **Simple flow** (2-3 elements): 250x150
- **Complex flow** (5+ elements): 400-500 wide
- Keep height reasonable (150-250) to fit in lanes

### 3. Child Element Placement
- Space elements 80-100px apart horizontally
- Use vertical spacing for parallel paths (-40, +40)
- Keep coordinates reasonable (-200 to +200)

### 4. Documentation
Always add documentation to explain:
- Purpose of the subprocess
- Input requirements
- Output produced
- Error handling approach

## Advanced Features

### Multiple Subprocesses in One Process
```yaml
elements:
  - type: startEvent
    x: 100
    y: 200

  - type: subProcess
    name: "Subprocess A"
    x: 250
    y: 200
    expanded: true

  - type: subProcess
    name: "Subprocess B"
    x: 500
    y: 200
    expanded: true

  - type: endEvent
    x: 750
    y: 200
```

### Nested Subprocesses
BPMN allows subprocesses within subprocesses, but for simplicity, this modeler shows:
- Parent subprocess (expanded)
- Child elements (tasks, events, gateways)
- Not multiple levels deep

## Example Workflows

### 1. Simple Expanded Subprocess
```yaml
# See: expanded-subprocess-example.yaml
- Order fulfillment with payment subprocess
- Customer notification subprocess
- Both visible on same screen
```

### 2. Mixed Approach
Use both in the same diagram:
- **Collapsed** for well-understood processes
- **Expanded** for processes needing attention

## Exporting and Sharing

### Exporting
1. Click "Export YAML"
2. Subprocess expansion state is saved
3. Child elements and connections included
4. Share the YAML file with your team

### Importing
1. Click "Import YAML"
2. Subprocesses load in their saved state
3. Expanded subprocesses show internal flow
4. Click +/− to toggle as needed

## Troubleshooting

### Subprocess Not Expanding?
- Check that `expanded: true` in YAML
- Ensure `childElements` array exists
- Verify subprocess has type `subProcess`

### Child Elements Not Showing?
- Check relative coordinates aren't too far
- Ensure subprocess width/height is sufficient
- Verify childConnections reference correct IDs

### Layout Issues?
- Adjust subprocess width/height
- Reposition child elements using x, y coordinates
- Use grid spacing (multiples of 50 or 100)

## Comparison with Other Tools

| Feature | This Modeler | Camunda | bpmn.io |
|---------|--------------|---------|---------|
| Collapsed subprocess | ✅ | ✅ | ✅ |
| Expanded subprocess | ✅ | ✅ | ✅ |
| Same-screen view | ✅ | ✅ | ✅ |
| Click to expand | ✅ | ✅ | Drill-down |
| YAML format | ✅ | ❌ (XML) | ❌ (XML) |

## Quick Reference

```
┌──────────────────────────────────────────┐
│  SUBPROCESS TOGGLE GUIDE                 │
├──────────────────────────────────────────┤
│                                          │
│  Collapsed: [Box with +]                 │
│  • Compact view                          │
│  • Click + to expand                     │
│                                          │
│  Expanded: [Box with internal flow]      │
│  • Shows child elements                  │
│  • Click − to collapse                   │
│                                          │
│  Properties Panel:                       │
│  ☐ Expanded (show internal flow)        │
│                                          │
│  YAML:                                   │
│  expanded: true/false                    │
│  childElements: [...]                    │
│  childConnections: [...]                 │
└──────────────────────────────────────────┘
```

## Summary

**YES**, subprocesses can be viewed on the same screen by:
1. Expanding the subprocess (click +)
2. Internal flow renders directly on canvas
3. Toggle anytime between collapsed/expanded
4. Export/import preserves the state
5. Full BPMN 2.0 compliance

Import `expanded-subprocess-example.yaml` to see it in action! 🎯
