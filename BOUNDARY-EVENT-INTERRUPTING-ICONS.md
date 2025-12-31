# Boundary Events - Interrupting vs Non-Interrupting Icons

## Overview

The palette now has **separate items** for interrupting and non-interrupting boundary events, with distinct visual icons that follow BPMN 2.0 specification.

## Feature Description

### Two Palette Sections

**1. Boundary Events (Interrupting)** - Solid borders
- When these events trigger, they **stop/cancel** the task
- Visual: Solid circle borders
- Label: (I) suffix

**2. Boundary Events (Non-Interrupting)** - Dashed borders
- When these events trigger, the task **continues running**
- Visual: Dashed circle borders
- Label: (NI) suffix

## Visual Distinction

### Interrupting Events (Solid Borders)
```
  ┌─────────┐
  │    ●    │  Solid outer circle
  │   ●●●   │  Solid inner circle
  │  ●●●●●  │
  │   ⚡️    │  Icon in center
  │         │
  └─────────┘
```

**Meaning**: Event **stops** the task when triggered

### Non-Interrupting Events (Dashed Borders)
```
  ┌─────────┐
  │  ┈ ┈ ┈  │  Dashed outer circle
  │ ┈     ┈ │  Dashed inner circle
  │┈       ┈│
  │   ⚡️    │  Icon in center
  │ ┈     ┈ │
  │  ┈ ┈ ┈  │
  └─────────┘
```

**Meaning**: Event triggers but task **continues** running

## Available Boundary Events

### Error Boundary Event
**Interrupting (I)**:
- Solid red borders
- Catches errors and **stops** the task
- Use case: Handle exceptions, failover to error path

**Non-Interrupting (NI)**:
- Dashed red borders
- Catches errors but task **continues**
- Use case: Log errors, notify admin, but keep processing

### Timer Boundary Event
**Interrupting (I)**:
- Solid orange borders
- Timeout **stops** the task
- Use case: SLA violations, deadlines, task must complete in time

**Non-Interrupting (NI)**:
- Dashed orange borders
- Timeout triggers but task **continues**
- Use case: Send reminder, escalate, but let task finish

### Escalation Boundary Event
**Interrupting (I)**:
- Solid purple borders
- Escalation **stops** the task
- Use case: Escalate to manager and cancel current approval

**Non-Interrupting (NI)**:
- Dashed purple borders
- Escalation triggers but task **continues**
- Use case: Notify supervisor, but let employee keep working

### Signal Boundary Event
**Interrupting (I)**:
- Solid blue borders
- Signal **stops** the task
- Use case: Cancel order on external signal

**Non-Interrupting (NI)**:
- Dashed blue borders
- Signal received but task **continues**
- Use case: Receive notification, log it, continue processing

## Usage Flow

### 1. Select from Palette
**Interrupting Events** (top section):
- Click Error (I), Timer (I), Escalate (I), or Signal (I)
- Helper message shows: "Click on a task to attach... (Interrupting)"
- Purple background color

**Non-Interrupting Events** (bottom section):
- Click Error (NI), Timer (NI), Escalate (NI), or Signal (NI)
- Helper message shows: "Click on a task to attach... (Non-Interrupting)"
- Teal/green background color

### 2. Attach to Task
- Click on any task element
- Boundary event appears on task border
- Visual matches palette selection (solid or dashed)

### 3. Verify in Properties
- Click the boundary event
- Properties panel shows "Interrupting" checkbox
- Checked = Interrupting (solid borders)
- Unchecked = Non-Interrupting (dashed borders)

## Implementation Details

### HTML Changes

**File**: `index.html`

**Added Two Sections**:
```html
<!-- Interrupting (Solid Borders) -->
<div class="palette-section">
    <h4>Boundary Events (Interrupting)</h4>
    <div class="palette-item" data-type="errorBoundaryEvent" data-interrupting="true">
        <svg>
            <circle stroke-dasharray="" /> <!-- Solid -->
        </svg>
        <span>Error (I)</span>
    </div>
    <!-- ... more interrupting events -->
</div>

<!-- Non-Interrupting (Dashed Borders) -->
<div class="palette-section">
    <h4>Boundary Events (Non-Interrupting)</h4>
    <div class="palette-item" data-type="errorBoundaryEvent" data-interrupting="false">
        <svg>
            <circle stroke-dasharray="3,2" /> <!-- Dashed -->
        </svg>
        <span>Error (NI)</span>
    </div>
    <!-- ... more non-interrupting events -->
</div>
```

### JavaScript Changes

**File**: `app.js`

**1. Palette Setup** (line 115-137):
```javascript
setupPalette() {
    paletteItems.forEach(item => {
        const type = item.getAttribute('data-type');
        const interrupting = item.getAttribute('data-interrupting');

        const isInterrupting = interrupting === 'true' || interrupting === null;
        this.enterBoundaryEventMode(type, isInterrupting);
    });
}
```

**2. Boundary Event Mode** (line 228-255):
```javascript
enterBoundaryEventMode(type, isInterrupting = true) {
    this.boundaryEventType = type;
    this.boundaryEventInterrupting = isInterrupting;

    const interruptingText = isInterrupting ? 'Interrupting' : 'Non-Interrupting';
    message.textContent = `Click on a task to attach ${type} (${interruptingText})`;
    message.style.background = isInterrupting ? '#9b59b6' : '#16a085'; // Purple vs Teal
}
```

**3. Attach Event** (line 290-318):
```javascript
attachBoundaryEvent(taskId) {
    const boundaryEvent = this.addElement(...);

    // Set interrupting property
    boundaryEvent.properties.cancelActivity = this.boundaryEventInterrupting;
}
```

**4. Render Event** (line 658-696):
```javascript
case 'errorBoundaryEvent':
    const isInterrupting = element.properties?.cancelActivity !== false;

    // Outer circle
    const beOuterCircle = ...;
    if (!isInterrupting) {
        beOuterCircle.setAttribute('stroke-dasharray', '3,2'); // Dashed
    }

    // Inner circle
    const beInnerCircle = ...;
    if (!isInterrupting) {
        beInnerCircle.setAttribute('stroke-dasharray', '2,1.5'); // Dashed
    }
```

## BPMN 2.0 Specification Compliance

This implementation follows **BPMN 2.0 specification**:

### Standard Visual Notation
- ✅ **Interrupting**: Solid circle borders
- ✅ **Non-Interrupting**: Dashed circle borders
- ✅ **Color-coded** by type (Error=Red, Timer=Orange, etc.)
- ✅ **Icon inside** shows event type

### Standard Behavior
- ✅ **cancelActivity = true**: Interrupting (stops task)
- ✅ **cancelActivity = false**: Non-Interrupting (task continues)

### Standard Positioning
- ✅ Attached to task boundary
- ✅ Different positions for different types:
  - Error: bottom-left
  - Timer: top-right
  - Escalation: top-left
  - Signal: bottom-right

## Use Cases

### Example 1: Payment Processing with Timeout

**Interrupting Timer** (30 seconds):
- If payment not completed in 30s → **Cancel** transaction
- Flow goes to timeout error handler
- User sees "Transaction cancelled"

**Non-Interrupting Timer** (20 seconds):
- At 20s → Send reminder to user
- Payment processing **continues**
- User sees "Please complete payment" but can still pay

### Example 2: Approval Task with Escalation

**Interrupting Escalation**:
- Manager doesn't respond in 2 days → **Cancel** their approval
- Flow goes to senior manager
- Original manager can no longer approve

**Non-Interrupting Escalation**:
- Manager doesn't respond in 1 day → Notify senior manager
- Original manager's approval **still valid**
- Both can approve in parallel

### Example 3: Data Processing with Error Handling

**Interrupting Error**:
- Data validation fails → **Stop** processing
- Flow goes to error handler
- Record marked as failed

**Non-Interrupting Error**:
- Data validation fails → Log warning
- Processing **continues** with defaults
- Record processed with warnings

## Console Output

### Interrupting Event Attached:
```
🎯 Boundary Event Mode: Click on a task to attach timerBoundaryEvent (Interrupting)
✅ Attached timerBoundaryEvent (Interrupting) to task Approve Request
```

### Non-Interrupting Event Attached:
```
🎯 Boundary Event Mode: Click on a task to attach timerBoundaryEvent (Non-Interrupting)
✅ Attached timerBoundaryEvent (Non-Interrupting) to task Approve Request
```

## Helper Message Colors

**Interrupting** (default):
- Background: Purple `#9b59b6`
- Indicates: Event will stop the task

**Non-Interrupting**:
- Background: Teal/Green `#16a085`
- Indicates: Event won't stop the task

## Testing

### Test 1: Visual Distinction
1. Add interrupting timer to a task
2. Add non-interrupting timer to another task
3. **Expected**:
   - Interrupting has solid borders
   - Non-interrupting has dashed borders

### Test 2: Property Persistence
1. Add non-interrupting error event
2. Click the event → Check properties panel
3. **Expected**: "Interrupting" checkbox is unchecked
4. Save/load workflow
5. **Expected**: Still non-interrupting after reload

### Test 3: Helper Message
1. Click "Timer (I)" in palette
2. **Expected**: Purple message "Click on task... (Interrupting)"
3. Click "Timer (NI)" in palette
4. **Expected**: Teal message "Click on task... (Non-Interrupting)"

## Properties Panel

When you click a boundary event, the properties panel shows:

```
┌─────────────────────────────────────┐
│ ┌────┐  Timer Boundary Event        │
│ │ ⏰  │  30s Timeout                 │
│ └────┘                               │
├─────────────────────────────────────┤
│ ID: element_5                        │
│ Name: 30s Timeout                    │
│ Timer Duration: PT30S                │
│                                      │
│ ☑ Interrupting (cancel task on      │
│   trigger)                           │
│                                      │
│ Unchecked = non-interrupting (task  │
│ continues after boundary event       │
│ triggers)                            │
└─────────────────────────────────────┘
```

Checking/unchecking the box changes the visual from solid to dashed borders.

## Summary

### What Was Added
✅ **Two palette sections**: Interrupting and Non-Interrupting
✅ **8 new palette items**: 4 types × 2 variants
✅ **Visual distinction**: Solid vs dashed borders
✅ **Color-coded helper messages**: Purple (interrupting) vs Teal (non-interrupting)
✅ **Automatic property setting**: `cancelActivity` based on selection
✅ **Dynamic rendering**: Borders update based on property

### Benefits
✅ **BPMN 2.0 compliant**: Follows standard notation
✅ **Clear visual distinction**: Immediately see interrupting vs non-interrupting
✅ **Intuitive labels**: (I) and (NI) suffixes
✅ **Separate palette sections**: Organized by behavior
✅ **Helpful tooltips**: Explain the difference
✅ **Color-coded feedback**: Visual confirmation of selection

### Files Modified
- `index.html`: Added two boundary event sections with 8 items
- `app.js`: Updated palette, mode, attachment, and rendering logic

Users can now easily choose and distinguish between interrupting and non-interrupting boundary events! 🎯
