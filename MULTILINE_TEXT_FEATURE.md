# Multiline Text for Task Names

## Problem Solved

Task names and gateway labels that are too long now automatically wrap to multiple lines instead of overflowing outside the element boundaries.

## What Changed

### Before
```
┌─────────────────────────────┐
│ Extract Playbook Results for Dis... │  ← Text cut off!
└─────────────────────────────┘
```

### After
```
┌─────────────────────────────┐
│ Extract Playbook Results    │
│ for Display                 │  ← Wrapped to multiple lines!
└─────────────────────────────┘
```

## Features

### Automatic Text Wrapping
- **Word-based wrapping**: Breaks at word boundaries, not mid-word
- **Smart sizing**: Calculates optimal wrap based on element width
- **Centered text**: Multi-line text stays centered in tasks
- **Proper spacing**: Line height of 1.2x font size for readability

### Applies To

✅ **All Task Types**:
- `task`
- `userTask`
- `serviceTask`
- `scriptTask`
- `sendTask`
- `receiveTask`
- `manualTask`
- `businessRuleTask`
- `agenticTask`
- `subProcess`
- `callActivity`

✅ **All Gateway Types**:
- `exclusiveGateway`
- `parallelGateway`
- `inclusiveGateway`

### Text Sizing

| Element Type | Max Width | Font Size | Notes |
|--------------|-----------|-----------|-------|
| Normal Tasks | 80px | 11px | Centered, 2-3 lines typical |
| Expanded SubProcess | width - 20px | 13px | Left-aligned, bold |
| Gateways | 120px | 11px | Below diamond, centered |

## Examples

### Example 1: Long Task Name

**Task Name**: "Generate Ansible Playbook Based on Analysis"

**Renders as**:
```
┌─────────────────────┐
│  Generate Ansible   │
│  Playbook Based on  │
│     Analysis        │
└─────────────────────┘
```

### Example 2: Very Long Task Name

**Task Name**: "Send Analysis Report for Approval via Email"

**Renders as**:
```
┌─────────────────────┐
│   Send Analysis     │
│  Report for Approval│
│    via Email        │
└─────────────────────┘
```

### Example 3: Gateway Label

**Gateway Name**: "Approved?"

**Renders as**:
```
    ◇
   Approved?
```

**Gateway Name**: "Analysis Validation Successful?"

**Renders as**:
```
      ◇
   Analysis
  Validation
  Successful?
```

## How It Works

### Text Wrapping Algorithm

```javascript
wrapText(text, maxWidth, fontSize) {
    // 1. Split text into words
    const words = text.split(' ');

    // 2. Calculate characters per line
    const charsPerLine = maxWidth / (fontSize * 0.6);

    // 3. Build lines by adding words
    // 4. Break to new line when length exceeds limit
    // 5. Return array of lines
}
```

### Multiline Rendering

```javascript
createMultilineText(parentGroup, text, x, y, maxWidth, options) {
    // 1. Wrap text into lines
    const lines = wrapText(text, maxWidth, fontSize);

    // 2. Calculate total height
    const totalHeight = lines.length * lineHeight;

    // 3. Center vertically
    const startY = y - (totalHeight / 2) + (lineHeight / 2);

    // 4. Create SVG <text> element for each line
    lines.forEach((line, index) => {
        // Create text at startY + (index * lineHeight)
    });
}
```

## Usage in Workflows

### Long Task Names Work Perfectly

```yaml
elements:
  - id: element_1
    type: agenticTask
    name: Generate Comprehensive Ansible Playbook Based on Log Analysis
    # ↑ This long name will wrap to 4-5 lines automatically
```

### Gateway Labels Too

```yaml
elements:
  - id: element_2
    type: exclusiveGateway
    name: Did the Analysis Pass Validation Checks?
    # ↑ Wraps nicely below the diamond
```

## Testing

### Test with Log Analysis Workflow

Import `log-analysis-ansible-workflow.yaml` to see:

1. **"Prepare Log Analysis"** - Short name, single line
2. **"AI Log Analysis"** - Medium name, single line
3. **"Extract Analysis Results"** - Wraps to 2 lines
4. **"Send Analysis Report for Approval"** - Wraps to 3 lines
5. **"Wait for Approval Decision"** - Wraps to 2-3 lines
6. **"Generate Ansible Playbook"** - Wraps to 2 lines
7. **"Extract Playbook Results"** - Wraps to 2 lines
8. **"Send Playbook Report"** - Medium name, single line

### Visual Test

1. **Create a new task**
2. **Name it**: "This is a very long task name that should wrap to multiple lines automatically"
3. **See**: Text wraps nicely within the task box
4. **Zoom in/out**: Text scales properly with zoom

## Benefits

### ✅ No More Cut-Off Text
Task names are fully visible regardless of length.

### ✅ Improved Readability
Multi-line text is easier to read than truncated text.

### ✅ Professional Appearance
Workflows look polished and well-formatted.

### ✅ Automatic Behavior
No configuration needed - works automatically.

### ✅ Smart Wrapping
Breaks at word boundaries, not mid-word.

## Limitations

### Current Limitations

1. **Approximation**: Character width is approximated (fontSize * 0.6)
   - Works well for most fonts
   - May be slightly off for very wide/narrow fonts

2. **No Hyphenation**: Long single words may overflow
   - Example: "Supercalifragilisticexpialidocious" won't break
   - Solution: Use shorter words or abbreviations

3. **Static After Render**: Text doesn't dynamically reflow on resize
   - Wrapping is calculated at render time
   - Re-import or reload to recalculate

### Workarounds

**For very long single words**:
```yaml
# Bad: Won't wrap well
name: "SuperLongWordThatCantBreak"

# Good: Will wrap nicely
name: "Super Long Word That Can Break"
```

**For extremely long names**:
```yaml
# Consider using shorter, clearer names
name: "Generate Ansible Playbook"  # Clear and concise
# Instead of:
name: "Generate Comprehensive Production-Ready Ansible Playbook Based on AI Analysis Results"
```

## Technical Details

### SVG Text Elements

Each line is rendered as a separate `<text>` element:

```xml
<g transform="translate(100, 100)">
  <rect x="-50" y="-30" width="100" height="60" />
  <text x="0" y="-10">Extract Playbook</text>
  <text x="0" y="5">Results for</text>
  <text x="0" y="20">Display</text>
</g>
```

### Line Height Calculation

```javascript
const fontSize = 11;
const lineHeight = fontSize * 1.2;  // 13.2px
// Provides comfortable spacing between lines
```

### Vertical Centering

```javascript
const totalHeight = lines.length * lineHeight;
const startY = y - (totalHeight / 2) + (lineHeight / 2);
// Centers the block of text vertically
```

## Browser Compatibility

✅ **All modern browsers** fully support SVG text rendering:
- Chrome/Edge
- Firefox
- Safari
- Opera

## Future Enhancements

Potential improvements:

- [ ] **Ellipsis for overflow**: Add "..." for text that's too long
- [ ] **Tooltip on hover**: Show full text in tooltip
- [ ] **Dynamic reflow**: Recalculate on zoom/resize
- [ ] **Custom line breaks**: Support `\n` in task names
- [ ] **Hyphenation**: Break long words with hyphens
- [ ] **Font measurement**: Use actual SVG text measurement for accuracy
- [ ] **Configurable max lines**: Limit to N lines with ellipsis

## Summary

**Task names now automatically wrap to multiple lines!**

✅ **No more overflow** - Text stays inside elements
✅ **Automatic** - Works without configuration
✅ **Smart** - Breaks at word boundaries
✅ **Readable** - Proper spacing and centering
✅ **Works everywhere** - All tasks and gateways

**Perfect for workflows with descriptive task names like the log analysis workflow!** 🎉

Try it now:
1. Refresh your browser
2. Import any workflow
3. Long task names automatically wrap!
