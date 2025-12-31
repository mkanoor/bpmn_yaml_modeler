# Complete Testing Guide - All Visualization Fixes

## Quick Test Checklist

After implementing all detach fixes, test these scenarios to verify everything works:

### ✅ Test 1: Token Flow Display
1. Load a workflow
2. Click "Execute Workflow"
3. **Expected**: Colored tokens animate through the workflow
4. **Console**: Should show token creation logs
5. **Visual**: Tokens should be clearly visible (10px radius, solid colors)

### ✅ Test 2: Token Cleanup on Re-execution
1. Execute workflow → Tokens appear
2. Click "Execute Workflow" again
3. **Expected**: Old tokens cleared, new tokens appear
4. **Console**: Should show "🧹 Clearing previous execution state"
5. **Visual**: Should see exactly the right number of tokens (no duplicates)

### ✅ Test 3: Token Cleanup on New Workflow
1. Execute workflow → Tokens appear
2. Load a new workflow (File → Open)
3. **Expected**: Tokens cleared from previous workflow
4. **Console**: Should show "🧹 Removed tokensLayer"
5. **Visual**: Canvas should be clean (no leftover tokens)

### ✅ Test 4: Tokens During Canvas Pan
1. Execute workflow → Tokens appear
2. Shift+drag to pan canvas
3. **Expected**: Tokens move with canvas automatically
4. **Visual**: Tokens stay anchored to their elements

### ✅ Test 5: Tokens During Pool Drag
1. Execute workflow → Tokens appear
2. Drag a pool header (swimlane label)
3. **Expected**: Tokens move with pool and elements
4. **Console**: Should show "✅ Restored tokensLayer with N tokens"
5. **Visual**: Tokens stay on their elements (not left behind)

### ✅ Test 6: Tokens During Zoom
1. Execute workflow → Tokens appear
2. Zoom in/out using mouse wheel or zoom buttons
3. **Expected**: Tokens scale with zoom
4. **Visual**: Tokens stay anchored to elements at all zoom levels

### ✅ Test 7: Tokens During Reset View
1. Execute workflow → Tokens appear
2. Pan and zoom to change view
3. Click "Reset View" button
4. **Expected**: Tokens return to correct positions
5. **Visual**: Tokens anchored to elements after reset

### ✅ Test 8: Completion Marks During Pool Drag
1. Execute workflow → Checkmarks (✓) appear on completed tasks
2. Drag pool header
3. **Expected**: Checkmarks move with tasks
4. **Console**: Should show "Restoring N marks for element"
5. **Visual**: Checkmarks stay on top-right of tasks

### ✅ Test 9: Skip Marks During Pool Drag
1. Execute workflow with exclusive gateway → Skip marks (⊘) on untaken paths
2. Drag pool header
3. **Expected**: Skip marks move with elements
4. **Visual**: Skip marks stay on their elements

### ✅ Test 10: Path Indicators During Pool Drag
1. Execute workflow with gateway split → Checkmarks (✓) and X marks (⊘) on flows
2. Drag pool header
3. **Expected**: Path indicators move with connections
4. **Console**: Should show "Restoring N path indicators"
5. **Visual**: Indicators stay at midpoint of their connection lines

### ✅ Test 11: Multiple Rapid Drags
1. Execute workflow → All visualizations appear
2. Drag pool rapidly back and forth 10+ times
3. **Expected**: No duplicates, no disappearing visualizations
4. **Visual**: Everything stays in sync

### ✅ Test 12: Element Type Change
1. Execute workflow → Visualizations appear
2. Select a task
3. Change type in properties panel (e.g., Task → Script Task)
4. **Expected**: Visualizations preserved during re-render
5. **Console**: Should show detach/restore logs

## Console Output Reference

### Good Console Output (Everything Working):

```
🚀 Workflow started: instance_123
🧹 Clearing previous execution state (tokens, highlights, checkmarks)
🔵 All tokens removed and tokensLayer cleared

🔵 Creating token for element_1 (Start)
   Position: (200, 150)
   Token ID: token-0

🔵 Moving token token-0 from element_1 to element_2
   From: (200, 150) To: (350, 150)

🔄 rerenderElements() called
   Current zoom: 1
   Current pan: {x: 0, y: 0}
   ✅ Restored tokensLayer with 3 tokens
   Restoring runtime state for 5 elements
   Restoring 2 marks for element element_2
      - completion-mark at (20, -20)
   Restoring 2 path indicators
```

### Bad Console Output (Issues):

```
🔄 rerenderElements() called
   (No token restoration message) ← Tokens lost!
   Restoring runtime state for 5 elements
```

Or:

```
❌ Element NOT found in DOM: element_2 ← Element missing!
```

Or:

```
🔵 Creating token for element_1 (Start)
🔵 Creating token for element_1 (Start) ← Duplicate! Cleanup failed
```

## Visual Verification Checklist

### Token Appearance:
- ✅ Clearly visible (10px radius, 3px stroke)
- ✅ Solid colors (no transparency/pulsing)
- ✅ Smooth animation when moving
- ✅ Positioned at element center

### Element Marks:
- ✅ Checkmark (✓) in green at top-right of completed elements
- ✅ Skip mark (⊘) in orange at top-right of skipped elements
- ✅ Error mark (⚠) in red if errors occur
- ✅ Feedback icon (💬) clickable if present

### Path Indicators:
- ✅ Checkmark (✓) in green at midpoint of taken paths
- ✅ X mark (⊘) in red at midpoint of not-taken paths
- ✅ Bold font weight for visibility

### Connection Styling:
- ✅ Active flows highlighted (thicker, colored)
- ✅ Taken paths styled (solid green)
- ✅ Not-taken paths styled (dashed red)

## Hard Reload Instructions

**IMPORTANT**: After code changes, do a hard reload to bypass browser cache:

- **Chrome/Firefox (Windows/Linux)**: `Ctrl + Shift + R`
- **Chrome/Firefox (Mac)**: `Cmd + Shift + R`
- **Safari**: `Cmd + Option + R`

## Debugging Tips

### If tokens don't appear:

1. Check console for token creation logs
2. Verify `tokensLayer` exists: `document.getElementById('tokensLayer')`
3. Check token count: `document.querySelectorAll('.bpmn-token-group').length`
4. Inspect DOM: Look for `<g id="tokensLayer">` inside `mainGroup`

### If tokens appear but don't move:

1. Check if rerenderElements() is being called (console logs)
2. Verify detach/reattach logs appear
3. Check token transforms: `tokenGroup.getAttribute('transform')`
4. Verify pool drag handler is updating token positions

### If marks/indicators don't appear:

1. Check workflow execution completed successfully
2. Verify element state: `element.classList` should have 'completed', 'skipped', etc.
3. Check DOM for mark elements: `element.querySelectorAll('.completion-mark')`
4. Look for path indicators: `document.querySelectorAll('.path-indicator')`

### If visualizations duplicate:

1. Check cleanup is happening (console logs)
2. Verify `removeAllTokens()` is called on workflow start
3. Check for multiple workflow executions
4. Verify tokensLayer is removed on new diagram load

## Performance Testing

### Rapid Pool Drag Test:

1. Execute workflow
2. Drag pool rapidly for 30 seconds
3. **Expected**: Smooth dragging, no lag
4. **Console**: Should see detach/restore logs on each drag
5. **Visual**: No visual artifacts or flickering

### Large Workflow Test:

1. Load workflow with 20+ elements
2. Execute workflow
3. Drag pools, pan, zoom
4. **Expected**: All visualizations move smoothly
5. **Performance**: No noticeable lag (detach is O(1))

## Files to Monitor

### agui-client.js
- Token creation
- Token movement
- Token cleanup

### app.js
- `rerenderElements()` - Detach/reattach logic
- `makePoolDraggable()` - Token position updates during drag
- `newDiagram()` - Cleanup on load

### Console
- Token creation/movement logs
- Detach/restore logs
- Any errors or warnings

## Success Criteria

All tests pass when:

✅ Tokens appear during workflow execution
✅ Tokens are clearly visible and well-sized
✅ Tokens clean up on re-execution and new workflow load
✅ Tokens stay anchored during canvas pan (automatic)
✅ Tokens move with pool during pool drag
✅ Tokens scale correctly during zoom
✅ Completion marks move with elements during pool drag
✅ Path indicators move with connections during pool drag
✅ No duplicates after multiple operations
✅ Console shows proper detach/restore logs
✅ No errors in console

## Common Issues and Solutions

### Issue: "Tokens appear in wrong position"
**Solution**: Verify token groups use transform, not cx/cy attributes

### Issue: "Tokens disappear on re-render"
**Solution**: Check detachedTokensLayer is not null and is being re-attached

### Issue: "Marks recreated instead of preserved"
**Solution**: Verify detachedMarks array stores actual nodes, not data

### Issue: "Path indicators lost during pool drag"
**Solution**: Check detachedPathIndicators are being restored to connectionsLayer

### Issue: "rerenderElements() called too many times"
**Solution**: This is expected during pool drag (once per mouse move). Performance is good due to detach pattern.

## Final Verification

After all tests pass:

1. Execute complex workflow (multiple gateways, pools, tasks)
2. Perform all operations:
   - Canvas pan
   - Pool drag
   - Zoom in/out
   - Reset view
   - Re-execute
   - Load new workflow
3. **Expected**: All visualizations work perfectly in all scenarios
4. **Console**: Clean logs, no errors
5. **Visual**: Professional, polished appearance

🎯 If all these tests pass, the visualization system is fully working!
