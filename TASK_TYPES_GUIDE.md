# BPMN Task Types Guide

## Overview

BPMN defines several specialized task types, each representing a different kind of work. Each task type has a unique visual marker (icon) in the top-left corner of the task rectangle.

## Task Types and Their Uses

### 1. Task (Generic)
**Visual:** Plain rectangle with rounded corners
**Purpose:** Generic work unit with no specific type
**Use When:** The nature of the work doesn't fit other categories
**Example:** "Archive Records", "Process Application"

---

### 2. User Task
**Visual:** Person icon (head + shoulders)
**Purpose:** Work performed by a human user through a user interface
**Use When:**
- Filling out forms
- Making manual decisions
- Reviewing information
- Approving requests

**Example:** "Fill Registration Form", "Review Document", "Approve Purchase Order"

**Typical Implementation:** Task shows up in a user's task list/inbox

---

### 3. Service Task
**Visual:** Gear/cog icon
**Purpose:** Automated work performed by a software service
**Use When:**
- Calling web services/APIs
- Invoking external systems
- Automated system operations
- Database operations

**Example:** "Call Payment Gateway API", "Update CRM", "Send to Message Queue"

**Typical Implementation:** Executed by process engine automatically, no human intervention

---

### 4. Script Task
**Visual:** Document/scroll icon
**Purpose:** Execute a script or code snippet
**Use When:**
- Running JavaScript, Python, or other scripts
- Performing calculations
- Data transformations
- Simple automation logic

**Example:** "Calculate Tax", "Format Data", "Generate Random Number"

**Typical Implementation:** Script code is embedded in the task definition

---

### 5. Send Task
**Visual:** Filled envelope icon
**Purpose:** Send a message to an external participant
**Use When:**
- Sending emails
- Sending notifications
- Publishing messages to queues
- Triggering external processes

**Example:** "Send Confirmation Email", "Notify Customer", "Publish Event"

**Typical Implementation:** One-way message sending, doesn't wait for response

---

### 6. Receive Task
**Visual:** Empty envelope icon
**Purpose:** Wait to receive a message from an external participant
**Use When:**
- Waiting for customer response
- Receiving callbacks
- Listening for events
- Awaiting external signals

**Example:** "Wait for Payment Confirmation", "Receive Customer Feedback", "Await Approval Email"

**Typical Implementation:** Process pauses until message is received

---

### 7. Manual Task
**Visual:** Hand icon
**Purpose:** Physical work done outside the system
**Use When:**
- Physical tasks not tracked by the system
- Work that happens offline
- Non-digital activities

**Example:** "Package Items", "File Physical Documents", "Conduct Physical Inspection"

**Typical Implementation:** Process engine may pause, but doesn't track the actual work

---

### 8. Business Rule Task
**Visual:** Table/grid icon
**Purpose:** Execute business rules using a business rules engine
**Use When:**
- Applying complex business logic
- Decision tables
- Rule-based decisions
- Policy enforcement

**Example:** "Determine Discount Tier", "Validate Eligibility", "Apply Pricing Rules"

**Typical Implementation:** Integrates with DMN (Decision Model and Notation) engines

---

### 9. Sub-Process
**Visual:** Rectangle with "+" symbol at bottom
**Purpose:** A process within a process, expandable
**Use When:**
- Grouping related activities
- Creating reusable process fragments
- Managing complexity through decomposition

**Example:** "Onboarding Process", "Approval Workflow", "Error Handling"

**Typical Implementation:** Can be collapsed/expanded, contains its own flow

---

### 10. Call Activity
**Visual:** Thick border (stroke-width: 4)
**Purpose:** Invoke an external, reusable process
**Use When:**
- Calling the same process from multiple places
- Process reusability
- Invoking standardized subprocesses

**Example:** "Credit Check", "Standard Approval", "Notification Service"

**Typical Implementation:** References a separate process definition

---

## Visual Reference

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │ 👤          │     │ ⚙️          │
│    Task     │     │ User Task   │     │Service Task │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 📜          │     │ ✉️ (filled) │     │ ✉️ (empty)  │
│ Script Task │     │  Send Task  │     │Receive Task │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ✋          │     │ 📊          │     │             │
│Manual Task  │     │Business Rule│     │ Sub-Process │
│             │     │    Task     │     │      +      │
└─────────────┘     └─────────────┘     └─────────────┘

┏━━━━━━━━━━━━━┓
┃             ┃  ← Thick border
┃Call Activity┃
┃             ┃
┗━━━━━━━━━━━━━┛
```

## Common Patterns

### User + Service Task Pattern
```
User Task (Fill Form) → Service Task (Validate Data) → Service Task (Save to DB)
```
Human input followed by automated processing

### Send + Receive Task Pattern
```
Send Task (Request Approval) → Receive Task (Wait for Response)
```
Asynchronous communication pattern

### Service + Business Rule Pattern
```
Service Task (Fetch Data) → Business Rule Task (Apply Rules) → Service Task (Update System)
```
Data-driven decision making

### Multiple Call Activities
```
Task A → [Call: Process X] → Task B → [Call: Process X] → Task C
```
Reusing the same subprocess multiple times

## How to Use in the BPMN Modeler

### Adding Task Types:

1. **From Palette:** Click the desired task type in the Activities section
2. **Change Type:**
   - Select an existing task
   - Use the "Task Type" dropdown in the Properties panel
   - The visual marker updates automatically

### In YAML:

```yaml
elements:
  - id: task_1
    type: userTask        # Specify the task type
    name: Review Document
    x: 200
    y: 150
    properties:
      documentation: "User reviews the document for accuracy"
```

### Example Workflow:

Import `task-types-example.yaml` to see all task types in action!

## Best Practices

1. **Use Specific Types:** Don't use generic "Task" when a specific type applies
2. **Be Consistent:** Use the same task type for similar activities across processes
3. **Document Well:** Each task type should have clear documentation
4. **Consider Implementation:** Choose task types based on how they'll be executed
5. **User vs Manual:**
   - User Task: System-tracked human work
   - Manual Task: Offline work the system doesn't track

## Technical Implementation Notes

When implementing BPMN processes:

- **User Tasks** → Assigned to users, appear in task lists
- **Service Tasks** → Implemented as Java classes, REST calls, etc.
- **Script Tasks** → Contain embedded script code
- **Send/Receive Tasks** → Integrate with messaging systems
- **Business Rule Tasks** → Connect to rules engines (Drools, DMN)
- **Call Activities** → Reference external process definitions

## Summary

| Task Type | Icon | Automation | Human Involved | System Tracked |
|-----------|------|------------|----------------|----------------|
| Task | None | Either | Either | Yes |
| User Task | 👤 | No | Yes | Yes |
| Service Task | ⚙️ | Yes | No | Yes |
| Script Task | 📜 | Yes | No | Yes |
| Send Task | ✉️ (filled) | Yes | No | Yes |
| Receive Task | ✉️ (empty) | Yes | No | Yes |
| Manual Task | ✋ | No | Yes | No |
| Business Rule Task | 📊 | Yes | No | Yes |
| Sub-Process | + | Either | Either | Yes |
| Call Activity | Thick border | Either | Either | Yes |

Choose the right task type to make your BPMN diagrams clear and executable!
