# Boundary Events Implementation Plan

## Summary

Boundary events have been added to the UI palette. The next step is implementing the behavior where they attach to tasks instead of being placed freely on the canvas.

---

## Current Status ✅

### Completed:
1. ✅ **UI Palette** - Added "Boundary Events" section with 4 types
2. ✅ **Visual Icons** - Lightning bolt, clock, arrow, triangle icons
3. ✅ **Documentation** - Complete BOUNDARY-EVENTS.md guide
4. ✅ **Color Coding** - Red (error), Orange (timer), Purple (escalation), Blue (signal)

### Boundary Event Types in Palette:
- `errorBoundaryEvent` - Catches exceptions (red, lightning bolt)
- `timerBoundaryEvent` - Handles timeouts (orange, clock)
- `escalationBoundaryEvent` - Escalates without stopping (purple, arrow)
- `signalBoundaryEvent` - External signals (blue, triangle)

---

## Implementation Plan

### Phase 1: Frontend (app.js) - Attachment Behavior

#### 1.1 Add Helper Method - Check if Boundary Event
```javascript
isBoundaryEventType(type) {
    const boundaryTypes = [
        'errorBoundaryEvent',
        'timerBoundaryEvent',
        'escalationBoundaryEvent',
        'signalBoundaryEvent'
    ];
    return boundaryTypes.includes(type);
}
```

#### 1.2 Modify setupPalette() - Lines 113-128
```javascript
setupPalette() {
    const paletteItems = document.querySelectorAll('.palette-item');
    paletteItems.forEach(item => {
        item.addEventListener('click', () => {
            const type = item.getAttribute('data-type');
            if (type === 'sequenceFlow') {
                this.enterConnectionMode();
            } else if (type === 'pool') {
                this.addPool();
            } else if (this.isBoundaryEventType(type)) {
                // NEW: Enter boundary event attachment mode
                this.enterBoundaryEventMode(type);
            } else {
                this.addElement(type, 400, 300);
            }
        });
    });
}
```

#### 1.3 Add enterBoundaryEventMode() Method
```javascript
enterBoundaryEventMode(type) {
    this.boundaryEventMode = true;
    this.boundaryEventType = type;
    this.canvas.style.cursor = 'crosshair';

    // Visual feedback
    console.log(`🎯 Click on a task to attach ${type}`);

    // Show helper message
    const message = document.createElement('div');
    message.id = 'boundaryEventHint';
    message.style.cssText = `
        position: fixed;
        top: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: #9b59b6;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        z-index: 1000;
        font-size: 14px;
    `;
    message.textContent = `Click on a task to attach ${this.getDefaultName(type)}`;
    document.body.appendChild(message);
}
```

#### 1.4 Modify addElement() - Add attachedToRef Support
```javascript
addElement(type, x, y, poolId = null, laneId = null, attachedToRef = null) {
    const id = this.generateId();
    const element = {
        id,
        type,
        name: this.getDefaultName(type),
        x,
        y,
        poolId,
        laneId,
        attachedToRef,  // NEW: For boundary events
        properties: {},
        // ... rest
    };

    // NEW: If it's a boundary event, add specific properties
    if (this.isBoundaryEventType(type)) {
        element.properties.cancelActivity = true;  // Interrupting by default
        if (type === 'timerBoundaryEvent') {
            element.properties.timerDuration = 'PT30S';  // Default 30 seconds
        }
        if (type === 'errorBoundaryEvent') {
            element.properties.errorCode = '';  // Catch all errors
        }
    }

    this.elements.push(element);
    this.renderElement(element);
    this.saveState();
    return element;
}
```

#### 1.5 Add Click Handler for Task Selection
```javascript
// In setupEventListeners(), add to canvas click:
this.canvas.addEventListener('click', (e) => {
    // NEW: Handle boundary event attachment
    if (this.boundaryEventMode) {
        const target = e.target.closest('[data-id]');
        if (target && this.isTask Element(target)) {
            const taskId = target.getAttribute('data-id');
            this.attachBoundaryEvent(taskId);
        } else {
            // Clicked outside task - cancel mode
            this.exitBoundaryEventMode();
        }
        return;
    }

    // ... existing click handling
});
```

#### 1.6 Add attachBoundaryEvent() Method
```javascript
attachBoundaryEvent(taskId) {
    const task = this.elements.find(e => e.id === taskId);
    if (!task) return;

    // Calculate position on task boundary
    const position = this.calculateBoundaryPosition(task, this.boundaryEventType);

    // Create boundary event attached to task
    const boundaryEvent = this.addElement(
        this.boundaryEventType,
        position.x,
        position.y,
        task.poolId,
        task.laneId,
        taskId  // attachedToRef
    );

    console.log(`✅ Attached ${this.boundaryEventType} to task ${task.name}`);

    this.exitBoundaryEventMode();
    this.selectElement(boundaryEvent);
}
```

#### 1.7 Add calculateBoundaryPosition() Method
```javascript
calculateBoundaryPosition(task, boundaryType) {
    // Position boundary events on task border
    // Error - bottom left
    // Timer - top right
    // Escalation - top left
    // Signal - bottom right

    const positions = {
        errorBoundaryEvent: { offsetX: -15, offsetY: 35 },
        timerBoundaryEvent: { offsetX: 85, offsetY: -15 },
        escalationBoundaryEvent: { offsetX: -15, offsetY: -15 },
        signalBoundaryEvent: { offsetX: 85, offsetY: 35 }
    };

    const offset = positions[boundaryType] || { offsetX: 0, offsetY: 0 };

    return {
        x: task.x + offset.offsetX,
        y: task.y + offset.offsetY
    };
}
```

#### 1.8 Add exitBoundaryEventMode() Method
```javascript
exitBoundaryEventMode() {
    this.boundaryEventMode = false;
    this.boundaryEventType = null;
    this.canvas.style.cursor = 'default';

    // Remove hint message
    const hint = document.getElementById('boundaryEventHint');
    if (hint) hint.remove();
}
```

#### 1.9 Add isTaskElement() Helper
```javascript
isTaskElement(element) {
    const el = this.elements.find(e => e.id === element.getAttribute('data-id'));
    if (!el) return false;

    const taskTypes = [
        'task', 'userTask', 'serviceTask', 'scriptTask',
        'sendTask', 'receiveTask', 'manualTask',
        'businessRuleTask', 'agenticTask', 'subProcess', 'callActivity'
    ];

    return taskTypes.includes(el.type);
}
```

#### 1.10 Update getDefaultName() - Add Boundary Names
```javascript
getDefaultName(type) {
    const names = {
        // ... existing names
        errorBoundaryEvent: 'Catch Error',
        timerBoundaryEvent: '30s Timeout',
        escalationBoundaryEvent: 'Escalate',
        signalBoundaryEvent: 'Catch Signal'
    };
    return names[type] || type;
}
```

---

### Phase 2: Frontend (app.js) - Rendering

#### 2.1 Update renderElement() - Render Boundary Events
```javascript
renderElement(element) {
    // ... existing rendering logic

    if (this.isBoundaryEventType(element.type)) {
        this.renderBoundaryEvent(element);
        return;
    }

    // ... rest of rendering
}
```

#### 2.2 Add renderBoundaryEvent() Method
```javascript
renderBoundaryEvent(element) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'bpmn-element bpmn-boundary-event');
    g.setAttribute('data-id', element.id);
    g.setAttribute('transform', `translate(${element.x}, ${element.y})`);

    // Dashed outer circle
    const outerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    outerCircle.setAttribute('cx', 0);
    outerCircle.setAttribute('cy', 0);
    outerCircle.setAttribute('r', 12);
    outerCircle.setAttribute('fill', 'white');
    outerCircle.setAttribute('stroke', this.getBoundaryEventColor(element.type));
    outerCircle.setAttribute('stroke-width', 2);
    outerCircle.setAttribute('stroke-dasharray', '3,2');
    g.appendChild(outerCircle);

    // Inner circle
    const innerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    innerCircle.setAttribute('cx', 0);
    innerCircle.setAttribute('cy', 0);
    innerCircle.setAttribute('r', 9);
    innerCircle.setAttribute('fill', 'none');
    innerCircle.setAttribute('stroke', this.getBoundaryEventColor(element.type));
    innerCircle.setAttribute('stroke-width', 1.5);
    g.appendChild(innerCircle);

    // Icon
    const icon = this.createBoundaryEventIcon(element.type);
    g.appendChild(icon);

    // Name label
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', 0);
    text.setAttribute('y', 25);
    text.setAttribute('class', 'element-text');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-size', 10);
    text.textContent = element.name;
    g.appendChild(text);

    this.elementsLayer.appendChild(g);
    this.makeElementDraggable(g, element);
    this.makeElementSelectable(g, element);
}
```

#### 2.3 Add getBoundaryEventColor() Helper
```javascript
getBoundaryEventColor(type) {
    const colors = {
        errorBoundaryEvent: '#e74c3c',
        timerBoundaryEvent: '#f39c12',
        escalationBoundaryEvent: '#9b59b6',
        signalBoundaryEvent: '#3498db'
    };
    return colors[type] || '#000';
}
```

#### 2.4 Add createBoundaryEventIcon() Helper
```javascript
createBoundaryEventIcon(type) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    const color = this.getBoundaryEventColor(type);

    if (type === 'errorBoundaryEvent') {
        // Lightning bolt
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 2 -7 L -3 0 L 0 0 L -2 7 L 3 0 L 0 0 Z');
        path.setAttribute('fill', color);
        g.appendChild(path);
    } else if (type === 'timerBoundaryEvent') {
        // Clock
        const clockCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        clockCircle.setAttribute('r', 6);
        clockCircle.setAttribute('fill', 'none');
        clockCircle.setAttribute('stroke', color);
        clockCircle.setAttribute('stroke-width', 1.5);
        g.appendChild(clockCircle);

        const hourHand = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        hourHand.setAttribute('x1', 0);
        hourHand.setAttribute('y1', 0);
        hourHand.setAttribute('x2', 0);
        hourHand.setAttribute('y2', -4);
        hourHand.setAttribute('stroke', color);
        hourHand.setAttribute('stroke-width', 1.5);
        g.appendChild(hourHand);

        const minuteHand = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        minuteHand.setAttribute('x1', 0);
        minuteHand.setAttribute('y1', 0);
        minuteHand.setAttribute('x2', 3);
        minuteHand.setAttribute('y2', 0);
        minuteHand.setAttribute('stroke', color);
        minuteHand.setAttribute('stroke-width', 1.5);
        g.appendChild(minuteHand);
    } else if (type === 'escalationBoundaryEvent') {
        // Up arrow
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 0 -5 L -4 1 L -1.5 1 L -1.5 5 L 1.5 5 L 1.5 1 L 4 1 Z');
        path.setAttribute('fill', color);
        g.appendChild(path);
    } else if (type === 'signalBoundaryEvent') {
        // Triangle
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 0 -5 L 5 4 L -5 4 Z');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', 1.5);
        g.appendChild(path);
    }

    return g;
}
```

---

### Phase 3: Properties Panel

#### 3.1 Update showProperties() - Display attachedToRef
```javascript
showProperties(element) {
    // ... existing properties

    // NEW: For boundary events, show attached task
    if (element.attachedToRef) {
        const attachedTask = this.elements.find(e => e.id === element.attachedToRef);
        const taskName = attachedTask ? attachedTask.name : element.attachedToRef;

        html += `
            <div class="property-group">
                <label>Attached To:</label>
                <div style="padding: 0.5rem; background: #f0f0f0; border-radius: 4px;">
                    📎 ${taskName}
                </div>
            </div>
        `;
    }

    // NEW: Timer duration for timer boundary events
    if (element.type === 'timerBoundaryEvent') {
        html += `
            <div class="property-group">
                <label for="prop-timerDuration">Timer Duration (ISO 8601):</label>
                <input type="text" id="prop-timerDuration"
                       value="${element.properties.timerDuration || 'PT30S'}"
                       placeholder="PT30S">
                <small>Examples: PT30S (30s), PT5M (5min), PT1H (1hr)</small>
            </div>
        `;
    }

    // NEW: Error code for error boundary events
    if (element.type === 'errorBoundaryEvent') {
        html += `
            <div class="property-group">
                <label for="prop-errorCode">Error Code (empty = catch all):</label>
                <input type="text" id="prop-errorCode"
                       value="${element.properties.errorCode || ''}"
                       placeholder="Leave empty to catch all errors">
                <small>Examples: ValidationError, TimeoutError, or empty</small>
            </div>
        `;
    }

    // NEW: Cancel activity checkbox for all boundary events
    if (this.isBoundaryEventType(element.type)) {
        const cancelActivity = element.properties.cancelActivity !== false;  // Default true
        html += `
            <div class="property-group">
                <label>
                    <input type="checkbox" id="prop-cancelActivity"
                           ${cancelActivity ? 'checked' : ''}>
                    Interrupting (cancel task on trigger)
                </label>
                <small>Unchecked = non-interrupting (task continues)</small>
            </div>
        `;
    }
}
```

---

### Phase 4: Backend Implementation

#### 4.1 Add Boundary Event Types to models.py
```python
# In Element model
class Element(BaseModel):
    id: str
    type: str
    name: str
    x: float
    y: float
    poolId: Optional[str] = None
    laneId: Optional[str] = None
    attachedToRef: Optional[str] = None  # NEW: For boundary events
    properties: Dict[str, Any] = {}
```

#### 4.2 Implement Error Boundary in workflow_engine.py
```python
async def execute_task(self, task: Element):
    """Execute a task with error boundary event support"""

    # Find any error boundary events attached to this task
    error_boundaries = [
        e for e in self.workflow.process.elements
        if e.type == 'errorBoundaryEvent' and e.attachedToRef == task.id
    ]

    try:
        # Execute the task
        executor = self.task_executors.get_executor(task.type)
        async for progress in executor.execute(task, self.context):
            await self.agui_server.send_progress(progress)

        # Task completed successfully
        await self.send_event('element.completed', task.id)

    except Exception as e:
        logger.error(f"Task {task.name} failed: {e}")

        # Check if any boundary event catches this error
        for boundary in error_boundaries:
            error_code = boundary.properties.get('errorCode', '')
            cancel_activity = boundary.properties.get('cancelActivity', True)

            # Empty error code catches all errors
            # Otherwise check if exception type matches
            if not error_code or type(e).__name__ == error_code:
                logger.info(f"Error caught by boundary event: {boundary.name}")

                # Send boundary event triggered
                await self.send_event('boundary.triggered', boundary.id, {
                    'errorType': type(e).__name__,
                    'errorMessage': str(e)
                })

                # Follow boundary event's outgoing flow
                await self.execute_from_element(boundary.id)
                return  # Error handled, don't propagate

        # No boundary caught the error - re-raise
        raise
```

#### 4.3 Implement Timer Boundary
```python
async def execute_task_with_timer(self, task: Element):
    """Execute task with timer boundary event support"""

    # Find timer boundaries attached to this task
    timer_boundaries = [
        e for e in self.workflow.process.elements
        if e.type == 'timerBoundaryEvent' and e.attachedToRef == task.id
    ]

    if not timer_boundaries:
        # No timers, execute normally
        await self.execute_task(task)
        return

    # Create task future
    task_future = asyncio.create_task(self.execute_task(task))

    # Create timer futures
    timer_futures = []
    for boundary in timer_boundaries:
        duration_str = boundary.properties.get('timerDuration', 'PT30S')
        duration_seconds = parse_iso8601_duration(duration_str)
        timer_future = asyncio.create_task(asyncio.sleep(duration_seconds))
        timer_futures.append((timer_future, boundary))

    # Wait for first to complete
    all_futures = [task_future] + [t[0] for t in timer_futures]
    done, pending = await asyncio.wait(all_futures, return_when=asyncio.FIRST_COMPLETED)

    # Check what completed
    if task_future in done:
        # Task completed before timeout
        for timer_future, _ in timer_futures:
            timer_future.cancel()
        return

    # Timer expired
    for timer_future, boundary in timer_futures:
        if timer_future in done:
            cancel_activity = boundary.properties.get('cancelActivity', True)

            if cancel_activity:
                # Cancel the task
                task_future.cancel()
                logger.info(f"Task {task.name} cancelled by timer {boundary.name}")

            # Trigger boundary event
            await self.send_event('boundary.triggered', boundary.id, {
                'reason': 'timeout'
            })

            # Follow boundary flow
            await self.execute_from_element(boundary.id)
            break
```

---

## Testing Plan

### Test 1: Error Boundary Event
```yaml
- id: risky_task
  type: scriptTask
  script: x = 1 / 0  # Will fail

- id: error_boundary
  type: errorBoundaryEvent
  attachedToRef: risky_task
  properties:
    errorCode: ""

connections:
  - from: error_boundary
    to: error_handler
```

**Expected**: Error caught, flow goes to error_handler

### Test 2: Timer Boundary Event
```yaml
- id: slow_task
  type: scriptTask
  script: time.sleep(60)

- id: timeout_boundary
  type: timerBoundaryEvent
  attachedToRef: slow_task
  properties:
    timerDuration: "PT5S"  # 5 seconds

connections:
  - from: timeout_boundary
    to: timeout_handler
```

**Expected**: After 5s, timeout triggers, task cancelled

---

## Summary

This implementation provides:
- ✅ Click-to-attach UI for boundary events
- ✅ Visual positioning on task borders
- ✅ Properties panel for configuration
- ✅ Backend error catching (try-catch equivalent)
- ✅ Backend timer/timeout handling
- ✅ BPMN standard compliant

**Next Steps:**
1. Implement frontend attachment behavior
2. Implement backend error catching
3. Implement backend timer support
4. Update deadlock example to use error boundaries
