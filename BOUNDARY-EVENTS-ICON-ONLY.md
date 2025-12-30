# Boundary Events - Icon-Only Display

## Change Summary

Boundary events now display **icon-only** without text labels for a cleaner visual appearance.

## Before vs After

### Before (with text labels):
```
┌─────────────────────┐
│                     │
│    User Task        │    🟠
│                     │   30s Timeout  ← Text clutters the diagram
└─────────────────────┘
```

### After (icon-only):
```
┌─────────────────────┐
│                     │
│    User Task        │    🟠  ← Clean icon only
│                     │
└─────────────────────┘
```

## Visual Design

### Boundary Event Icons

Each boundary event type has a distinctive **colored icon**:

| Type | Color | Icon | Description |
|------|-------|------|-------------|
| **Error Boundary** | 🔴 Red (#e74c3c) | ⚡ Lightning bolt | Catches exceptions |
| **Timer Boundary** | 🟠 Orange (#f39c12) | ⏰ Clock | Handles timeouts |
| **Escalation Boundary** | 🟣 Purple (#9b59b6) | ⬆️ Up arrow | Non-interrupting escalation |
| **Signal Boundary** | 🔵 Blue (#3498db) | 🔺 Triangle | Catches external signals |

### Visual Structure

Each boundary event is rendered as:
- **Dashed outer circle** (radius: 15px, stroke-width: 2px, color-coded)
- **Solid inner circle** (radius: 12px, stroke-width: 1.5px, color-coded)
- **Icon** (centered, color-coded)
- **No text label** (for clean appearance)

### Connection Points

Boundary events have **4 connection points** at the circle edge:
- Right (x: 15, y: 0)
- Left (x: -15, y: 0)
- Top (x: 0, y: -15)
- Bottom (x: 0, y: 15)

These are sized to match the 15px radius of the boundary event circle.

## How to View Details

To see the boundary event's name and properties:

1. **Click on the boundary event icon**
2. Properties panel shows:
   - Name (e.g., "30s Timeout", "Catch Error")
   - Type (errorBoundaryEvent, timerBoundaryEvent, etc.)
   - Attached To (which task it monitors)
   - Type-specific properties:
     - **Timer**: Duration (PT30S, PT5M, etc.)
     - **Error**: Error Code (empty = catch all)
     - **All**: Interrupting checkbox

## Benefits

### 1. Cleaner Diagrams
- No overlapping text
- Task names remain readable
- Professional BPMN appearance

### 2. Visual Recognition
- Color-coded icons are instantly recognizable
- Red = error, Orange = timeout, Purple = escalation, Blue = signal
- Standard BPMN symbology

### 3. Space Efficiency
- Boundary events take minimal space
- Can attach multiple boundaries to same task
- Diagrams scale better

### 4. Standard Compliance
- Matches professional BPMN tools (Camunda Modeler, Signavio, etc.)
- Icon-based representation is industry standard
- Click for details is expected UX pattern

## Code Changes

### File: `app.js`

**Line 680-686**: Removed text label from boundary events
```javascript
case 'errorBoundaryEvent':
case 'timerBoundaryEvent':
case 'escalationBoundaryEvent':
case 'signalBoundaryEvent':
    // ... render circles and icon ...

    // No text label - boundary events are icon-only for clean appearance
    // Click the boundary event to see its name and properties in the panel
    break;
```

**Line 644-645**: Removed text label from legacy boundaryTimerEvent
```javascript
// No text label - boundary events are icon-only
break;
```

**Line 1109-1120**: Adjusted connection points for boundary events
```javascript
getConnectionPoints(element) {
    if (element.type.includes('Event')) {
        // Boundary events are smaller (r=15), regular events are larger (r=20)
        const isBoundaryEvent = this.isBoundaryEventType(element.type);
        const radius = isBoundaryEvent ? 15 : 20;

        points.push({ x: radius, y: 0 }); // right
        points.push({ x: -radius, y: 0 }); // left
        // ...
    }
}
```

## Usage Example

### Attaching Multiple Boundary Events

You can now attach multiple boundary events to the same task without visual clutter:

```
┌─────────────────────┐
│                     │  🟠 Timer (top-right)
│    API Call Task    │  🔴 Error (bottom-right)
│                     │  🔵 Signal (bottom-left)
└─────────────────────┘
```

Each icon is clearly visible and clickable!

### Standard Positions

Boundary events attach to tasks at these positions:
- **Error** → Bottom-left (offsetX: -45, offsetY: 25)
- **Timer** → Top-right (offsetX: 45, offsetY: -25)
- **Escalation** → Top-left (offsetX: -45, offsetY: -25)
- **Signal** → Bottom-right (offsetX: 45, offsetY: 25)

This prevents overlapping when multiple boundaries are attached.

## Testing

1. **Hard reload** the browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Attach a boundary event to a task
3. **Expected**: Small colored icon appears (no text label)
4. Click the icon
5. **Expected**: Properties panel shows boundary event details
6. Attach multiple boundaries to same task
7. **Expected**: All icons visible and clickable

## Comparison with BPMN Tools

This matches the behavior of professional BPMN modelers:

- **Camunda Modeler**: Icon-only boundary events ✅
- **Signavio**: Icon-only boundary events ✅
- **Bizagi**: Icon-only boundary events ✅
- **bpmn.io**: Icon-only boundary events ✅

Your modeler now follows industry best practices!
