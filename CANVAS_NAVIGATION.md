# Canvas Navigation Guide

## New Features Added

The BPMN canvas now supports **pan** (slide left/right/up/down) and **improved zoom** controls!

## How to Navigate

### 🔍 Zoom

**Method 1: Mouse Wheel**
- Scroll up = Zoom in
- Scroll down = Zoom out

**Method 2: Buttons**
- Click `🔍+` = Zoom in
- Click `🔍-` = Zoom out
- Click `↺ Reset` = Reset to 100% zoom and center position
- Click `⛶ Fit` = Automatically zoom to fit all elements

**Method 3: Keyboard (coming soon)**
- Ctrl + = Zoom in
- Ctrl - = Zoom out

### ✋ Pan (Slide/Move Canvas)

**Method 1: Shift + Drag**
1. Hold **Shift** key
2. Click and drag anywhere on canvas
3. Canvas will slide in any direction

**Method 2: Middle Mouse Button**
1. Click and hold **middle mouse button** (wheel button)
2. Drag to pan
3. Release to stop

### ⛶ Fit to View

Click the `⛶ Fit` button to automatically:
- Calculate the bounding box of all elements
- Zoom to show everything
- Center the workflow
- Add padding around edges

Perfect for:
- Wide workflows that extend beyond screen
- After importing a large workflow
- Reviewing the entire process at once

### ↺ Reset View

Click the `↺ Reset` button to:
- Reset zoom to 100% (1:1 scale)
- Reset pan to origin (0, 0)
- Return to default view

## Use Cases

### Wide Workflows

For workflows that are very wide (like the log analysis workflow):

1. **Import workflow** - Elements may be off-screen
2. **Click `⛶ Fit`** - Automatically shows entire workflow
3. **Zoom in** with mouse wheel to see details
4. **Pan** with Shift+Drag to navigate
5. **Click `↺ Reset`** when done to return to normal view

### Detailed Editing

When working on a specific part of a large workflow:

1. **Zoom in** to see element details clearly
2. **Pan** to the section you want to edit
3. Work on that area
4. **Fit to View** to see overall structure
5. Repeat as needed

### Review Mode

To review an entire workflow:

1. **Click `⛶ Fit`** - See everything at once
2. Identify areas of interest
3. **Zoom in** on specific sections
4. **Pan** between sections
5. **Zoom out** to see context

## Visual Indicators

### Cursor Changes
- **Default**: Regular cursor when not interacting
- **Grabbing**: Hand cursor when panning (Shift+Drag)
- **Pointer**: When hovering over elements

### Pan Hint
A small hint text shows in the toolbar:
```
✋ Pan: Shift+Drag
```

Hover over it for full tooltip:
```
Shift+Drag or Middle-Click to Pan
```

## Technical Details

### Transform Order
The canvas applies transformations in this order:
```
translate(panX, panY) → scale(zoom)
```

This means:
1. Canvas is moved (panned) first
2. Then scaled (zoomed)

### Zoom Range
- Minimum: 10% (0.1x)
- Maximum: 300% (3x)
- Default: 100% (1x)

### Pan Range
- Unlimited in all directions
- Pan coordinates stored as `panX` and `panY`

### Fit to View Logic
1. Calculate bounding box of all elements and pools
2. Add 50px padding on all sides
3. Calculate zoom to fit in viewport
4. Cap zoom at 150% maximum
5. Center the content in viewport
6. Apply transform

## Keyboard Shortcuts Summary

| Action | Shortcut |
|--------|----------|
| Zoom In | Mouse Wheel Up or Button |
| Zoom Out | Mouse Wheel Down or Button |
| Pan | Shift + Drag or Middle-Click Drag |
| Reset View | Button |
| Fit to View | Button |
| Undo | Ctrl+Z / Cmd+Z |
| Redo | Ctrl+Y / Cmd+Shift+Z |
| Delete | Delete key |

## Tips & Tricks

### Tip 1: Quick Overview
After importing a workflow, immediately click `⛶ Fit` to see the entire process.

### Tip 2: Precise Editing
1. Fit to view
2. Click on the area you want to edit
3. Zoom in with wheel
4. Pan with Shift+Drag to fine-tune position

### Tip 3: Compare Sections
1. Zoom in on first section
2. Pan to second section
3. Compare without zooming out

### Tip 4: Export Full View
1. Click `⛶ Fit` to show everything
2. Take screenshot or export
3. All elements will be visible

### Tip 5: Navigate Large Workflows
For workflows with 20+ elements:
1. Start with Fit to View
2. Identify the flow path
3. Zoom into start events
4. Follow the path by panning
5. Zoom out at decision points to see branches

## Troubleshooting

### Issue: Elements are off-screen

**Solution:**
```
Click ⛶ Fit button
```

### Issue: Can't see entire workflow

**Solution:**
```
1. Click ⛶ Fit to see everything
2. Or zoom out with mouse wheel
3. Or pan with Shift+Drag to explore
```

### Issue: Zoomed too far in/out

**Solution:**
```
Click ↺ Reset button to return to 100%
```

### Issue: Lost my position

**Solution:**
```
Click ↺ Reset to return to origin
Or click ⛶ Fit to see all elements
```

### Issue: Panning not working

**Check:**
- Are you holding Shift while dragging?
- Or using middle mouse button?
- Cursor should show "grabbing" hand

## Examples

### Example 1: Log Analysis Workflow

The log analysis workflow is very wide (~2600px). To navigate:

```
1. Import log-analysis-ansible-workflow.yaml
2. Click ⛶ Fit
   → Entire workflow visible at ~40% zoom
3. Mouse wheel up to zoom to 100%
4. Shift+Drag to pan right/left between stages
5. See: Prepare → AI Analysis → Email → Approval → Gateway → Playbook Gen
```

### Example 2: Email Approval Workflow

```
1. Import email-approval-test-workflow.yaml
2. Elements extend to ~1700px horizontally
3. Click ⛶ Fit to see full flow
4. Zoom in on gateway to see decision logic
5. Pan to see both approved and denied paths
```

### Example 3: Custom Workflow Creation

```
1. Create elements spanning wide area
2. Periodically click ⛶ Fit to see overall structure
3. Zoom in to 150% for precise connection drawing
4. Pan between distant elements
5. Reset view when done
```

## Browser Compatibility

✅ **Chrome/Edge**: Full support (recommended)
✅ **Firefox**: Full support
✅ **Safari**: Full support
⚠️ **Mobile**: Limited (touch gestures not yet implemented)

## Future Enhancements

Planned features:
- [ ] Touch gestures (pinch to zoom, two-finger pan)
- [ ] Minimap for large workflows
- [ ] Zoom to selection
- [ ] Keyboard shortcuts for zoom/pan
- [ ] Animation for Fit to View
- [ ] Remember zoom/pan per workflow
- [ ] Grid snapping while panning

## Summary

**Pan & Zoom is now fully supported!**

- 🔍 **Zoom**: Mouse wheel, buttons, or fit to view
- ✋ **Pan**: Shift+Drag or middle-click drag
- ⛶ **Fit**: Auto-fit entire workflow in viewport
- ↺ **Reset**: Return to default view

**Perfect for wide workflows like the log analysis workflow!**

Navigate with ease and never lose your elements off-screen again! 🎉
