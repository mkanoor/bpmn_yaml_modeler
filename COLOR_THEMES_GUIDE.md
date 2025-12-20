# Color Themes Guide

The BPMN Modeler now supports **6 beautiful color themes** to customize your workspace!

## Available Themes

### 🔵 Blue (Default)
- **Primary Color**: Classic Blue (#3498db)
- **Header**: Dark Blue-Gray (#2c3e50)
- **Best For**: Professional, standard BPMN diagrams

### 🟠 Orange
- **Primary Color**: Warm Orange (#e67e22)
- **Header**: Deep Orange (#d35400)
- **Best For**: Creative, energetic workflows

### 🟢 Green
- **Primary Color**: Emerald Green (#27ae60)
- **Header**: Teal (#16a085)
- **Best For**: Environmental, nature-focused processes

### 🟣 Lavender
- **Primary Color**: Purple (#9b59b6)
- **Header**: Deep Purple (#7d3c98)
- **Best For**: Elegant, sophisticated diagrams

### 🔷 Teal
- **Primary Color**: Turquoise (#16a085)
- **Header**: Deep Teal (#0e6655)
- **Best For**: Modern, calm workspace

### 🌸 Pink
- **Primary Color**: Bright Pink (#e91e63)
- **Header**: Deep Pink (#ad1457)
- **Best For**: Vibrant, eye-catching workflows

## How to Change Themes

### Method 1: Theme Selector (Recommended)
1. Look for the **"Theme"** dropdown in the header (top-right area)
2. Click the dropdown
3. Select your preferred theme
4. Theme changes immediately!

### Method 2: Browser Console
```javascript
// Get the modeler instance
modeler.setTheme('orange');  // Options: blue, orange, green, lavender, teal, pink
```

## Theme Persistence

Your theme choice is **automatically saved** in browser localStorage!

- Theme persists across browser sessions
- Each browser/device remembers its own theme
- No server-side storage needed

## What Changes with Themes?

When you switch themes, the following elements update their colors:

### Header & Buttons
✅ **Header Background** - Main header bar color  
✅ **Primary Buttons** - Export, Import, Execute buttons  
✅ **Button Hover States** - Darker shade on hover  

### BPMN Elements
✅ **Element Stroke** - Border color of tasks, events, gateways  
✅ **Selection Glow** - Highlight color when element is selected  
✅ **Connection Points** - Small circles that appear on hover  
✅ **Active Element** - Pulsing glow during execution  

### Connections
✅ **Selected Connection** - Color when connection is selected  
✅ **Active Flow** - Color during workflow execution  

### Modals & Forms
✅ **Modal Headers** - Header background in dialogs  
✅ **Approve/Reject Buttons** - Action button colors  

### Consistent Elements
The following remain **consistent across all themes** for clarity:

- ⚠️ **Danger/Error States** - Always red for warnings/errors
- ✅ **Success States** - Always green for completed tasks
- ⚡ **Warning States** - Always orange for warnings

## Examples

### Blue Theme (Default)
```
Header: Dark Blue-Gray
Buttons: Classic Blue
Elements: Blue stroke
Selection: Blue glow
```

### Orange Theme
```
Header: Deep Orange
Buttons: Warm Orange
Elements: Orange stroke
Selection: Orange glow
```

### Green Theme
```
Header: Teal
Buttons: Emerald Green
Elements: Teal stroke
Selection: Green glow
```

### Lavender Theme
```
Header: Deep Purple
Buttons: Purple
Elements: Purple stroke
Selection: Purple glow
```

## Technical Details

### CSS Variables
Themes use CSS custom properties (variables) for easy customization:

```css
:root {
    --primary-color: #3498db;
    --primary-dark: #2980b9;
    --header-bg: #2c3e50;
    --selection-glow: #3498db;
    --connection-point: #3498db;
    /* ... more variables */
}
```

### Theme Switching
Themes are applied via `data-theme` attribute on `<html>`:

```html
<!-- Blue (default) -->
<html>

<!-- Orange -->
<html data-theme="orange">

<!-- Green -->
<html data-theme="green">
```

### LocalStorage Key
Theme preference is stored under:
```
Key: bpmn-modeler-theme
Value: blue | orange | green | lavender | teal | pink
```

## Customizing Themes

Want to create your own theme? Here's how:

### 1. Add CSS Theme Definition
Edit `styles.css` and add a new theme:

```css
/* Custom Theme */
[data-theme="custom"] {
    --primary-color: #your-color;
    --primary-dark: #your-dark-color;
    --header-bg: #your-header-color;
    --accent-color: #your-accent;
    --selection-glow: #your-glow;
    --connection-point: #your-point-color;
}
```

### 2. Add Theme to Dropdown
Edit `index.html`:

```html
<select id="themeSelect">
    <option value="blue">Blue</option>
    <!-- ... other themes ... -->
    <option value="custom">My Custom Theme</option>
</select>
```

### 3. Apply Your Theme
```javascript
modeler.setTheme('custom');
```

## Color Accessibility

All themes are designed with accessibility in mind:

- ✅ Sufficient contrast ratios for text
- ✅ Distinct colors for different states
- ✅ Color-blind friendly where possible
- ✅ Consistent visual hierarchy

## Browser Compatibility

Theme switching works in all modern browsers:

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

## Tips & Tricks

### Tip 1: Match Your Brand
Choose a theme that matches your company's brand colors:
- Blue: Professional services
- Orange: Creative agencies
- Green: Environmental/sustainability
- Purple: Luxury/premium brands

### Tip 2: Reduce Eye Strain
If working long hours:
- **Teal**: Easy on the eyes
- **Green**: Calming effect
- **Lavender**: Soft and soothing

### Tip 3: Presentation Mode
For screenshots or presentations:
- **Blue**: Most professional
- **Orange**: Most vibrant
- **Pink**: Most eye-catching

### Tip 4: Team Coordination
Set the same theme across your team for consistent screenshots and documentation.

### Tip 5: Quick Switch
Use browser console for rapid testing:
```javascript
['blue', 'orange', 'green', 'lavender', 'teal', 'pink'].forEach((theme, i) => {
    setTimeout(() => modeler.setTheme(theme), i * 1000);
});
```

## Troubleshooting

### Theme Not Changing?
1. **Hard refresh**: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. **Clear cache**: Browser settings → Clear cache
3. **Check console**: F12 → Console for errors

### Theme Not Persisting?
1. **Check localStorage**: F12 → Application → LocalStorage
2. **Privacy mode**: Themes won't save in incognito/private mode
3. **Clear localStorage**: `localStorage.removeItem('bpmn-modeler-theme')`

### Colors Look Wrong?
1. **Browser zoom**: Reset zoom to 100%
2. **Night mode**: Disable browser night/dark mode
3. **Color calibration**: Check monitor color settings

## Future Enhancements

Planned theme features:

- [ ] **Dark Mode** - Full dark theme support
- [ ] **High Contrast** - Accessibility mode
- [ ] **Custom Colors** - Color picker for each element
- [ ] **Theme Import/Export** - Share custom themes
- [ ] **Auto Theme** - Match system preferences
- [ ] **Gradient Themes** - Multi-color gradients

## Summary

🎨 **6 Beautiful Themes**: Blue, Orange, Green, Lavender, Teal, Pink  
💾 **Auto-Save**: Remembers your choice  
⚡ **Instant Switch**: Changes apply immediately  
🎯 **Consistent**: Professional look across all themes  
🌈 **Customizable**: Create your own themes  

**Try them all and find your favorite!** 🎉

## Quick Reference

| Theme | Hex Color | Use Case |
|-------|-----------|----------|
| 🔵 Blue | #3498db | Professional, standard |
| 🟠 Orange | #e67e22 | Creative, energetic |
| 🟢 Green | #27ae60 | Environmental, calm |
| 🟣 Lavender | #9b59b6 | Elegant, sophisticated |
| 🔷 Teal | #16a085 | Modern, soothing |
| 🌸 Pink | #e91e63 | Vibrant, bold |

Happy theming! 🎨
