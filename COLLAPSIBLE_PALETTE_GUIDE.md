# Collapsible Palette Sections Guide

The left palette now has **collapsible sections** to help you organize and navigate BPMN elements more efficiently!

## Features

### 🎯 Collapsible Sections
All palette sections can be collapsed/expanded by clicking on their headers:

- **Events** - Start, End, Intermediate, Timer, Boundary Timer
- **Activities** - Tasks, User Tasks, Service Tasks, etc.
- **Custom Tasks** - Agentic Task
- **Gateways** - Exclusive, Parallel, Inclusive
- **Swimlanes** - Pools and Lanes
- **Connections** - Sequence Flow

### 💾 State Persistence
Your collapsed/expanded preferences are **automatically saved**:
- Saved to browser localStorage
- Persists across browser sessions
- Each section remembers its state independently

### ✨ Visual Indicators
- **▼ Arrow Down** - Section is expanded (items visible)
- **▶ Arrow Right** - Section is collapsed (items hidden)
- **Hover Effect** - Header highlights when you hover over it

## How to Use

### Collapse a Section
1. **Click on the section header** (e.g., "EVENTS", "ACTIVITIES")
2. Arrow rotates to the right **▶**
3. Items slide up and hide
4. State is automatically saved

### Expand a Section
1. **Click on the collapsed section header**
2. Arrow rotates down **▼**
3. Items slide down and appear
4. State is automatically saved

### Quick Tips
- **Collapse unused sections** to reduce clutter
- **Keep frequently used sections expanded** for quick access
- **Use during workflow creation** to focus on relevant elements
- **Collapse all but one** to maximize visibility of specific element types

## Use Cases

### 1. Focus on Specific Elements
Working only with tasks and gateways?
```
✅ ACTIVITIES (expanded)
✅ GATEWAYS (expanded)
❌ Events (collapsed)
❌ Custom Tasks (collapsed)
❌ Swimlanes (collapsed)
❌ Connections (collapsed)
```

### 2. Simple Workflows
Creating basic start → task → end flows?
```
✅ EVENTS (expanded)
✅ ACTIVITIES (expanded)
✅ CONNECTIONS (expanded)
❌ Gateways (collapsed)
❌ Custom Tasks (collapsed)
❌ Swimlanes (collapsed)
```

### 3. Advanced Workflows
Building complex process with AI and timers?
```
✅ EVENTS (expanded) - For timer events
✅ CUSTOM TASKS (expanded) - For agentic tasks
✅ GATEWAYS (expanded) - For decision logic
❌ Swimlanes (collapsed)
```

### 4. Clean Workspace
Want minimal distractions?
```
Collapse all sections except the one you're currently using
Quick expand when you need something else
```

## Visual Design

### Collapsed State
```
┌─────────────────────────┐
│ EVENTS               ▶  │  ← Click to expand
├─────────────────────────┤
│ ACTIVITIES           ▶  │
├─────────────────────────┤
│ GATEWAYS             ▼  │  ← Expanded
│  ◇ Exclusive            │
│  ◇ Parallel             │
│  ◇ Inclusive            │
└─────────────────────────┘
```

### Expanded State
```
┌─────────────────────────┐
│ EVENTS               ▼  │  ← Click to collapse
│  ○ Start                │
│  ⦿ End                  │
│  ⦿ Intermediate         │
│  ⏱ Timer                │
│  ⏱ Boundary Timer       │
├─────────────────────────┤
│ ACTIVITIES           ▶  │  ← Collapsed
└─────────────────────────┘
```

## Animation

Sections use smooth CSS transitions:
- **Slide Down** - Items expand with fade-in effect
- **Slide Up** - Items collapse with fade-out effect
- **Arrow Rotation** - 90° rotation animation
- **Duration** - 300ms for smooth experience

## Technical Details

### CSS Classes
```css
.palette-section           /* Section container */
.palette-section.collapsed /* Collapsed state */
.palette-section-items     /* Items container (animated) */
```

### LocalStorage Keys
Each section state is stored individually:
```
palette-section-Events: "true" | "false"
palette-section-Activities: "true" | "false"
palette-section-Gateways: "true" | "false"
palette-section-Swimlanes: "true" | "false"
palette-section-Connections: "true" | "false"
palette-section-Custom Tasks: "true" | "false"
```

### JavaScript Methods
```javascript
setupCollapsibleSections()  // Initialize all collapsible sections
// Called automatically on page load
```

## Keyboard Accessibility

While we recommend using the mouse/touchpad, you can navigate with keyboard:
1. **Tab** - Navigate to section headers
2. **Enter/Space** - Toggle collapse/expand
3. **Tab** - Continue to palette items when expanded

## Browser Compatibility

Collapsible sections work in all modern browsers:
- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ Opera

## Customization

### Change Animation Speed
Edit `styles.css`:
```css
.palette-section-items {
    transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
    /* Change 0.3s to your preferred duration */
}
```

### Change Arrow Icon
Edit `styles.css`:
```css
.palette-section h4::after {
    content: '▼';  /* Change to: '⌄' or '⯆' or '▾' */
}
```

### Auto-Collapse All on Load
Add to `app.js` in `setupCollapsibleSections()`:
```javascript
// Auto-collapse all sections by default
sections.forEach(section => {
    if (!localStorage.getItem(`palette-section-${sectionName}`)) {
        section.classList.add('collapsed');
    }
});
```

## Troubleshooting

### Sections Won't Collapse
1. **Hard refresh**: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. **Check console**: F12 → Console for JavaScript errors
3. **Clear cache**: Browser settings → Clear cache

### State Not Persisting
1. **Check localStorage**: F12 → Application → LocalStorage
2. **Privacy mode**: Won't save in incognito/private browsing
3. **Clear and retry**: `localStorage.clear()` in console

### Animation Glitchy
1. **Disable animations**: Use browser dev tools to check CSS
2. **Check max-height**: May need adjustment for many items
3. **GPU acceleration**: Some browsers may need `-webkit-transform: translateZ(0)`

## Best Practices

### ✅ Do
- Collapse sections you rarely use
- Keep 2-3 most-used sections expanded
- Use collapse/expand to reduce scrolling
- Organize by workflow complexity

### ❌ Don't
- Don't collapse all sections (hard to find elements)
- Don't leave all expanded if you have limited screen space
- Don't forget you can quickly expand when needed

## Examples

### Example 1: Simple Process Creation
```
1. Start with all sections expanded
2. Identify which elements you need
3. Collapse unused sections
4. Focus on creating your workflow
5. Expand temporarily when you need something specific
```

### Example 2: Large Screen Setup
```
- Keep all sections expanded
- Plenty of space for all elements
- Quick access to everything
```

### Example 3: Laptop/Small Screen
```
- Collapse most sections
- Expand only what you're currently using
- Maximize canvas space
- Quick toggle as needed
```

## Future Enhancements

Planned improvements:
- [ ] **Collapse All** button
- [ ] **Expand All** button
- [ ] **Keyboard shortcuts** (Alt+1, Alt+2, etc.)
- [ ] **Section reordering** (drag to rearrange)
- [ ] **Custom sections** (create your own groups)
- [ ] **Recent items** section (auto-populated)

## Summary

✨ **Click headers** to collapse/expand  
💾 **Auto-save** state across sessions  
🎯 **Organize** your workspace efficiently  
⚡ **Smooth animations** for better UX  
🎨 **Theme-aware** arrows and hover effects  

**Enjoy a cleaner, more organized palette!** 🎉

## Quick Reference

| Action | Result |
|--------|--------|
| Click section header | Toggle collapse/expand |
| ▼ Arrow down | Section is expanded |
| ▶ Arrow right | Section is collapsed |
| Hover header | Highlight and color change |
| Collapsed state | Saves automatically |

Happy organizing! 📋
