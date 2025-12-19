# BPMN Timer Events Guide

## Overview

Your BPMN workflow executor now supports **Timer Events** for monitoring tasks, creating delays, and handling timeouts!

## Timer Event Types

### 1. **Timer Intermediate Catch Event** ⏱️
**Purpose:** Wait for a specific duration or until a specific date/time before continuing the workflow.

**Use Cases:**
- Delay execution (wait 30 minutes before sending reminder)
- Schedule actions (wait until 9 AM to start processing)
- Cooling-off periods (wait 24 hours before finalizing)
- Batch job scheduling

**Properties:**
- **Timer Type:** `duration`, `date`, or `cycle`
- **Duration:** ISO 8601 format (e.g., `PT5M`, `PT1H`, `P1D`)
- **Date/Time:** ISO 8601 timestamp (e.g., `2024-12-25T10:00:00Z`)
- **Cycle:** Repeating timer (e.g., `R3/PT10M` = repeat 3 times every 10 min)

**Example Workflow:**
```
[Start] → [Create Order] → [Wait Timer: PT2H] → [Send Confirmation] → [End]
                           (Wait 2 hours)
```

---

### 2. **Boundary Timer Event** ⏰
**Purpose:** Monitor a task and trigger an alternative path if the task takes too long (timeout/SLA violation).

**Use Cases:**
- SLA monitoring (escalate if approval takes > 24 hours)
- Timeout handling (cancel payment if no response in 5 minutes)
- Automatic escalation (notify manager if task not completed)
- Deadline enforcement

**Properties:**
- **Timer Type:** `duration` or `date`
- **Duration (Timeout):** How long to wait (e.g., `PT30M`)
- **Date/Time (Deadline):** Absolute deadline (e.g., `2024-12-31T23:59:59Z`)
- **Cancel Activity:** `true` = interrupt task, `false` = continue task
- **Attached To:** ID of the task being monitored

**Example Workflow:**
```
[Start] → [User Task: Review Document] → [End]
                ↓
          [Boundary Timer: PT24H]
                ↓
          [Send Escalation Email]
```

---

## ISO 8601 Duration Format

### Duration Examples

| Format | Meaning |
|--------|---------|
| `PT30S` | 30 seconds |
| `PT5M` | 5 minutes |
| `PT1H` | 1 hour |
| `PT2H30M` | 2 hours 30 minutes |
| `P1D` | 1 day |
| `P1DT12H` | 1 day 12 hours |
| `P7D` | 7 days (1 week) |

### Date/Time Examples

| Format | Meaning |
|--------|---------|
| `2024-12-25T10:00:00Z` | UTC time |
| `2024-12-25T10:00:00-05:00` | EST time |
| `2025-01-01T00:00:00Z` | New Year midnight UTC |

### Cycle Examples (Advanced)

| Format | Meaning |
|--------|---------|
| `R3/PT10M` | Repeat 3 times, every 10 minutes |
| `R/P1D` | Repeat indefinitely, every day |
| `R5/PT1H` | Repeat 5 times, every hour |

---

## How to Use Timer Events

### Step 1: Add Timer Event from Palette

1. **Open** `index.html` in your browser
2. **Look** for the "Events" section in the left palette
3. **Click** on one of the new timer events:
   - **Timer** (intermediate catch event - standalone timer)
   - **Boundary Timer** (attached to tasks for monitoring)

### Step 2: Configure Timer Properties

1. **Click** on the timer event in the canvas
2. **Properties panel** appears on the right
3. **Configure** timer settings:

#### For Timer Intermediate Catch Event:
```yaml
Name: Wait 30 Minutes
Timer Type: duration
Duration: PT30M
```

#### For Boundary Timer Event:
```yaml
Name: Escalation Timeout
Timer Type: duration
Duration (Timeout): PT2H
Cancel Activity: true
Attached To: element_5
```

### Step 3: Connect to Workflow

#### Intermediate Timer (Standalone):
```
[Task A] → [Timer: Wait 10 min] → [Task B]
```

#### Boundary Timer (Attached to Task):
```
[Task A] ──→ [Task B]  (normal path)
   ↓
[Timeout Timer]
   ↓
[Escalation Task]  (timeout path)
```

---

## Real-World Examples

### Example 1: Order Processing with Delay

**Scenario:** After creating an order, wait 1 hour before sending confirmation to allow for cancellations.

```yaml
- id: element_1
  type: startEvent
  name: Order Created

- id: element_2
  type: serviceTask
  name: Create Order

- id: element_3
  type: timerIntermediateCatchEvent
  name: Wait 1 Hour
  properties:
    timerType: duration
    timerDuration: PT1H

- id: element_4
  type: sendTask
  name: Send Confirmation Email

connections:
  - from: element_1, to: element_2
  - from: element_2, to: element_3
  - from: element_3, to: element_4
```

**Result:** Order created → Wait 1 hour → Send confirmation

---

### Example 2: User Task with SLA Timeout

**Scenario:** User must approve within 24 hours, or escalate to manager.

```yaml
- id: element_5
  type: userTask
  name: Approve Budget Request
  properties:
    assignee: john@company.com
    priority: High

- id: element_6
  type: boundaryTimerEvent
  name: 24 Hour SLA
  properties:
    timerType: duration
    timerDuration: PT24H
    cancelActivity: false  # Keep task open even after timeout
    attachedTo: element_5

- id: element_7
  type: sendTask
  name: Escalate to Manager
  properties:
    to: manager@company.com
    subject: SLA Violation - Budget Approval Pending

connections:
  - from: element_5, to: element_8  # Normal approval path
  - from: element_6, to: element_7  # Timeout escalation path
```

**Result:**
- **If approved within 24h:** Continue normally
- **If > 24h:** Send escalation email (user task stays open)

---

### Example 3: Multi-Stage Reminder System

**Scenario:** Send reminders at 1 day, 3 days, and 7 days after registration.

```yaml
- id: element_10
  type: startEvent
  name: User Registered

- id: element_11
  type: timerIntermediateCatchEvent
  name: Wait 1 Day
  properties:
    timerType: duration
    timerDuration: P1D

- id: element_12
  type: sendTask
  name: Send First Reminder

- id: element_13
  type: timerIntermediateCatchEvent
  name: Wait 2 More Days
  properties:
    timerType: duration
    timerDuration: P2D

- id: element_14
  type: sendTask
  name: Send Second Reminder

connections:
  - from: element_10, to: element_11
  - from: element_11, to: element_12
  - from: element_12, to: element_13
  - from: element_13, to: element_14
```

**Result:** Day 1: First reminder → Day 3: Second reminder → Day 7: Final reminder

---

### Example 4: Payment Processing with Timeout

**Scenario:** Wait for payment confirmation, timeout after 5 minutes.

```yaml
- id: element_20
  type: receiveTask
  name: Wait for Payment Confirmation
  properties:
    messageRef: paymentConfirmed

- id: element_21
  type: boundaryTimerEvent
  name: Payment Timeout
  properties:
    timerType: duration
    timerDuration: PT5M
    cancelActivity: true  # Cancel waiting if timeout
    attachedTo: element_20

- id: element_22
  type: serviceTask
  name: Cancel Order

- id: element_23
  type: serviceTask
  name: Process Payment

connections:
  - from: element_20, to: element_23  # Payment received
  - from: element_21, to: element_22  # Timeout occurred
```

**Result:**
- **Payment received < 5 min:** Process payment
- **No payment after 5 min:** Cancel order

---

## Backend Implementation

### Timer Executors

Two executor classes handle timer events:

#### 1. TimerIntermediateCatchEventExecutor
```python
# Location: backend/task_executors.py:671-770

# Supports:
- Duration timers (PT5M, PT1H, P1D)
- Date/time timers (2024-12-25T10:00:00Z)
- Cycle timers (R3/PT10M)

# Behavior:
- Parses ISO 8601 duration format
- Calculates wait time
- Sleeps for duration (capped at 10 seconds for demo)
- Stores completion timestamp in context
```

#### 2. BoundaryTimerEventExecutor
```python
# Location: backend/task_executors.py:773-818

# Supports:
- Timeout monitoring
- Deadline enforcement
- Cancel activity option

# Behavior:
- Monitors attached task
- Triggers after timeout duration
- Can interrupt or continue task
- Stores timeout event in context
```

### Duration Parsing

```python
def parse_duration(self, duration_str: str) -> float:
    """
    PT5M  → 300 seconds
    PT1H  → 3600 seconds
    P1D   → 86400 seconds
    PT2H30M → 9000 seconds
    """
    # Uses regex to extract days, hours, minutes, seconds
    # Returns total seconds as float
```

### Production Considerations

**Current Implementation (Demo):**
- Wait times capped at 10 seconds for quick testing
- Simple sleep-based delays
- No persistent timer storage

**Production Enhancement Needed:**
```python
# Use actual datetime for scheduling
# Store timer state in database
# Use message queue (Redis/RabbitMQ) for reliability
# Support timer cancellation
# Handle server restarts gracefully
```

---

## Testing Timer Events

### Quick Test 1: Simple Delay

1. **Create workflow:**
   - Start Event
   - Timer Intermediate Catch Event (PT30S)
   - End Event

2. **Configure timer:**
   ```
   Name: Wait 30 Seconds
   Timer Type: duration
   Duration: PT30S
   ```

3. **Execute workflow:**
   - Click "▶ Execute Workflow"
   - Watch backend logs
   - Timer will wait 2 seconds (demo mode)

4. **Expected output:**
   ```
   Timer started: Wait 30 Seconds
   Timer will wait for 30.0 seconds (duration: PT30S)
   Timer completed: waited 2 seconds
   ```

### Quick Test 2: Boundary Timer on User Task

1. **Create workflow:**
   - Start Event
   - User Task (Approve Request)
   - Boundary Timer Event attached to User Task
   - Send Task (Escalation)
   - End Event

2. **Configure boundary timer:**
   ```
   Name: 2 Hour Timeout
   Timer Type: duration
   Duration (Timeout): PT2H
   Cancel Activity: false
   Attached To: <user_task_id>
   ```

3. **Execute workflow:**
   - User task appears with approval form
   - Boundary timer monitors in parallel
   - After 2 seconds (demo), timeout triggers
   - Escalation email sent

4. **Expected behavior:**
   - User task stays open (Cancel Activity = false)
   - Escalation path executes
   - Both paths can complete

---

## Timer Event Properties Reference

### Common Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `name` | string | Timer name/label | "Wait 30 Minutes" |
| `timerType` | enum | Timer type | "duration", "date", "cycle" |

### Duration Timer Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `timerDuration` | string | ISO 8601 duration | "PT5M", "PT1H", "P1D" |

### Date Timer Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `timerDate` | string | ISO 8601 timestamp | "2024-12-25T10:00:00Z" |

### Cycle Timer Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `timerCycle` | string | Repeat expression | "R3/PT10M" |

### Boundary Timer Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `cancelActivity` | boolean | Interrupt task on timeout | true, false |
| `attachedTo` | string | Task element ID | "element_5" |

---

## Best Practices

### 1. **Use Descriptive Names**
```
✅ Good: "Wait 24 Hours for Cooling-Off Period"
❌ Bad: "Timer 1"
```

### 2. **Choose Appropriate Timer Type**
- **Delay/Wait:** Use Timer Intermediate Catch Event
- **Timeout/SLA:** Use Boundary Timer Event
- **Scheduled Start:** Use Timer Start Event (future enhancement)

### 3. **Set Realistic Timeouts**
```
✅ Good: PT30M for payment confirmation
❌ Bad: PT5S for user approval
```

### 4. **Document Timer Behavior**
```yaml
properties:
  documentation: |
    This timer enforces a 24-hour SLA for manager approval.
    If not approved within 24 hours, the request is automatically escalated.
```

### 5. **Handle Timeout Paths**
Always provide a clear path from boundary timer events:
```
[Task] → [Success Path]
   ↓
[Timeout] → [Escalation/Cancellation Path]
```

### 6. **Test with Short Durations First**
```
Development: PT30S (30 seconds)
Testing: PT5M (5 minutes)
Production: PT24H (24 hours)
```

---

## Troubleshooting

### Timer Not Waiting Long Enough

**Problem:** Timer completes immediately

**Solution:**
- Check timer type is set to "duration"
- Verify duration format (must be ISO 8601)
- Example: `PT5M` not `5M`

### Boundary Timer Not Triggering

**Problem:** Timeout doesn't fire

**Solution:**
- Verify "Attached To" property has correct task ID
- Check timer is connected in workflow
- Ensure task is actually running

### Duration Format Errors

**Problem:** `Invalid duration format`

**Solution:** Use correct ISO 8601 format:
```
✅ PT5M (5 minutes)
✅ PT1H (1 hour)
✅ P1D (1 day)
❌ 5M (missing PT)
❌ 1 hour (not ISO 8601)
```

### Timer Waiting Too Long in Demo

**Problem:** Timer waits full duration in development

**Solution:**
- Current implementation caps wait at 10 seconds
- If you see longer waits, check backend logs
- Modify `actual_wait` cap in task_executors.py

---

## What's Next?

### Future Enhancements

1. **Timer Start Events** - Start workflows at scheduled times
2. **Persistent Timers** - Survive server restarts
3. **Timer Cancellation** - Cancel active timers dynamically
4. **Cron Expression Support** - Full cron scheduling
5. **Timer Event History** - Track all timer activations
6. **Real-Time Timer Display** - Show countdown in UI

---

## Summary

✅ **Added:** 2 new timer event types
✅ **Supports:** Duration, date/time, and cycle timers
✅ **Backend:** Full executor implementation with ISO 8601 parsing
✅ **Frontend:** Palette items, rendering, and properties panel
✅ **Use Cases:** Delays, timeouts, SLA monitoring, scheduling

**You can now:**
- Add wait/delay steps to workflows
- Monitor task execution with timeouts
- Enforce SLAs and deadlines
- Schedule workflow actions

**Try it now:** Add a timer event to your workflow and see it in action! 🚀
