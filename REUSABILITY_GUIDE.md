# BPMN Reusability Guide: Call Activities vs Swim Lanes

## Understanding Reusability in BPMN

### Two Different Concepts:

1. **Swim Lanes (Pools & Lanes)** - Organizational Structure
   - Represent different participants, roles, or departments
   - Show WHO performs activities
   - Do NOT represent reusable logic
   - Example: "Approval Lane" vs "Main Process Lane" shows different roles

2. **Call Activities (Reusable Subprocesses)** - Functional Reusability
   - Represent the SAME logic being invoked multiple times
   - Enable process reuse and modularity
   - Visually indicated by thick borders
   - Example: The same "Approval Subprocess" called at different stages

## Why Your Original Request Needs Call Activities

You wanted "the same approval method to be called repeatedly" - this is **functional reusability**, which requires:

- **Call Activities** (thick-bordered rectangles) that reference a shared subprocess
- NOT swim lanes, which only show organizational separation

## The Reusable Approval Pattern

### File: `reusable-approval-workflow.yaml`

This workflow demonstrates TRUE reusability:

```
Main Process:
  Start → Prepare Request → [Level 1 Approval] → Update Records
    → [Level 2 Approval] → Process Payment → [Final Approval]
    → Complete Transaction → End

Each [Call Activity] invokes THE SAME approval subprocess:
  Start Approval → Review & Approve → Approved?
    ├─ Yes → Approved (End)
    └─ No → Notify Rejection → Rejected (End)
```

### Key Features:

1. **Three Call Activities** (thick borders):
   - Level 1 Approval
   - Level 2 Approval
   - Final Approval

2. **One Reusable Subprocess** called by all three:
   - Defined once in the `subProcesses` section
   - Contains: Start → Review → Decision Gateway → End (Approved/Rejected)
   - Referenced by `calledElement: approval_subprocess`

3. **Benefits**:
   - Define approval logic ONCE
   - Call it THREE times
   - Change the subprocess logic, all three calls automatically updated
   - Reduces redundancy and maintenance

## Comparison: First Example vs Reusable Example

### First Example (`approval-workflow.yaml`) - WRONG for Reusability
```
Main Lane:          Submit → Process → Generate → Publish
                      ↓         ↓         ↓
Approval Lane:    Review → Validate → Final Review
```
**Problem:** Three DIFFERENT approval tasks, not reusable logic

### Reusable Example (`reusable-approval-workflow.yaml`) - CORRECT
```
Main Lane:  Prepare → [Call: Approval] → Update → [Call: Approval]
            → Payment → [Call: Approval] → Complete

Approval Subprocess (called 3 times):
  Start → Review & Approve → Decision → End
```
**Benefit:** ONE subprocess definition, THREE invocations

## How Call Activities Work

### In BPMN Notation:
- **Regular Task**: Thin border (stroke-width: 2)
- **Sub-Process**: Thin border with "+" symbol
- **Call Activity**: THICK border (stroke-width: 4) - indicates it calls an external process

### In the YAML:

```yaml
elements:
  - id: element_3
    type: callActivity              # Type is callActivity
    name: Level 1 Approval
    properties:
      calledElement: approval_subprocess  # References the subprocess

subProcesses:
  - id: approval_subprocess         # Defined once
    name: Approval Subprocess
    elements: [...]                 # Contains the actual logic
```

## When to Use Each Pattern

### Use Swim Lanes When:
- Showing different organizational roles
- Illustrating handoffs between departments
- Modeling collaboration between teams
- Example: Customer, Support Team, Manager lanes

### Use Call Activities When:
- The SAME logic is invoked multiple times
- You want to abstract and reuse process fragments
- Creating libraries of reusable processes
- Example: Credit check, approval logic, notification service

### Use Both Together:
You can combine them! For example:
```
Main Process Pool:
  Lane 1 (Requester): Submit → [Call: Approval] → Process
  Lane 2 (Manager):   Monitor → [Call: Approval] → Review

Approval Subprocess (shared):
  Check Rules → Validate → Decide → Notify
```

## Importing and Editing

### To Import the Reusable Workflow:

1. Open `index.html` in your browser
2. Click "Import YAML"
3. Select `reusable-approval-workflow.yaml`
4. Observe:
   - Three **thick-bordered** Call Activities in the main lane
   - Each references the same approval subprocess
   - A visual representation of the subprocess below

### Editing Call Activities:

1. **Click on a Call Activity** (thick border)
2. **Edit Properties**:
   - `name`: Display name (e.g., "Level 1 Approval")
   - `calledElement`: Which subprocess it calls
   - `documentation`: Describe the context

3. **The subprocess itself** can be:
   - Defined in the `subProcesses` section
   - Stored as a separate process definition
   - Managed in a process repository

### Visual Differences You'll See:

| Element Type | Visual Indicator | Purpose |
|-------------|------------------|---------|
| Task | Thin border | Single unit of work |
| Sub-Process | Thin border + [+] | Expandable subprocess |
| Call Activity | **Thick border** | **Calls reusable logic** |

## Real-World Examples

### Purchase Order System:
```
Main Flow:
  Create PO → [Call: Approval] → Send to Vendor → Receive Goods
    → [Call: Approval] → Process Payment → [Call: Approval] → Close PO

Reusable Approval Subprocess:
  Assign Approver → Review → Decision → Notify
```

### Document Management:
```
Main Flow:
  Draft Document → [Call: Review] → Revise → [Call: Review]
    → Finalize → [Call: Review] → Publish

Reusable Review Subprocess:
  Assign Reviewer → Collect Feedback → Approve/Reject → Archive
```

## Technical Implementation

In a real BPMN execution engine:

1. **Call Activity** triggers the subprocess
2. **Process Instance** is created for the subprocess
3. **Data is passed** between caller and subprocess
4. **Control returns** to the Call Activity when subprocess completes
5. **Main process continues** based on subprocess outcome

## Benefits of This Pattern

1. **Maintainability**: Change approval logic in ONE place
2. **Consistency**: Same approval rules applied everywhere
3. **Testing**: Test the subprocess independently
4. **Reusability**: Use across multiple processes
5. **Governance**: Centralize compliance logic

## Summary

- **Swim Lanes** = WHO (organizational structure)
- **Call Activities** = WHAT (reusable functional logic)
- For "calling the same approval repeatedly", use **Call Activities**
- The thick border visually indicates "this calls something else"
- Define subprocess once, invoke it many times

Import `reusable-approval-workflow.yaml` to see this in action!
