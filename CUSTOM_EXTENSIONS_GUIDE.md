# BPMN Custom Task Type Extensions Guide

## Can You Extend BPMN?

**YES!** BPMN 2.0 was designed to be extensible. While it defines standard task types (User Task, Service Task, etc.), you can create custom task types for domain-specific needs.

## Why Create Custom Task Types?

1. **Domain-Specific Modeling** - Represent specialized activities unique to your industry
2. **Emerging Technologies** - Model new technology patterns (AI agents, blockchain, IoT)
3. **Organizational Standards** - Enforce company-specific process patterns
4. **Better Communication** - Use familiar terminology for your team
5. **Tool Integration** - Integrate with custom execution engines

## BPMN Extension Mechanisms

### 1. Extension Elements
Standard BPMN way to add custom metadata:
```xml
<bpmn:task id="task1" name="AI Analysis">
  <bpmn:extensionElements>
    <custom:agentType>nlp-classifier</custom:agentType>
    <custom:model>gpt-4</custom:model>
  </bpmn:extensionElements>
</bpmn:task>
```

### 2. Custom Task Types (What We've Built)
Creating visually distinct task types with custom icons:
- Easier to recognize in diagrams
- Self-documenting workflows
- Better user experience

## Agentic Task: A Custom Extension

### What is an Agentic Task?

**Definition:** A task performed by an autonomous AI agent that can:
- Make decisions independently
- Learn from interactions
- Adapt behavior over time
- Interact with multiple systems

**Visual Marker:** Robot icon in indigo color (#6366f1)

### Why Agentic Task Isn't in Standard BPMN

BPMN 2.0 was released in 2011, before the AI agent revolution. Standard task types don't capture:
- **Autonomous decision-making** capabilities
- **Learning and adaptation** over time
- **Multi-modal interactions** (text, vision, code)
- **Reasoning and planning** abilities
- **Self-improvement** mechanisms

### Agentic Task vs Standard BPMN Tasks

| Feature | Service Task | Script Task | **Agentic Task** |
|---------|-------------|-------------|------------------|
| Decision Making | Rule-based | Programmatic | **Autonomous AI** |
| Learning | No | No | **Yes - continuous** |
| Adaptability | Fixed logic | Static code | **Dynamic behavior** |
| Context Awareness | Limited | Limited | **Full context understanding** |
| Error Handling | Predefined | Coded | **Self-correcting** |
| Complexity | Simple APIs | Simple scripts | **Complex reasoning** |

## Creating Your Own Custom Task Types

### Step 1: Define the Task Type

Identify what makes your task type unique:
- What capability does it represent?
- How is it different from existing types?
- What visual marker would communicate its purpose?

**Examples:**
- `blockchainTask` - Smart contract execution
- `iotTask` - IoT device interactions
- `quantumTask` - Quantum computing operations
- `bioTask` - Biological process automation
- `xrTask` - Extended reality interactions

### Step 2: Design the Visual Marker

Create an SVG icon that:
- Fits in the top-left corner of a task rectangle
- Uses a distinctive color
- Is recognizable at small sizes
- Follows BPMN visual conventions

**Color Recommendations:**
- AI/Agentic: Indigo (#6366f1)
- Blockchain: Orange (#f97316)
- IoT: Green (#10b981)
- Quantum: Purple (#a855f7)
- Security: Red (#ef4444)

### Step 3: Add to the UI

#### HTML Palette (`index.html`):
```html
<div class="palette-item" data-type="myCustomTask">
    <svg width="40" height="40">
        <rect x="5" y="10" width="30" height="20" rx="5"
              fill="white" stroke="#000" stroke-width="2"/>
        <!-- Your custom icon here -->
    </svg>
    <span>My Custom Task</span>
</div>
```

#### JavaScript Rendering (`app.js`):

1. **Add to getDefaultName:**
```javascript
myCustomTask: 'My Custom Task'
```

2. **Add to case statement:**
```javascript
case 'myCustomTask':
```

3. **Add icon rendering:**
```javascript
} else if (element.type === 'myCustomTask') {
    // Draw your custom icon
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    // ... icon attributes
    g.appendChild(icon);
}
```

4. **Add to connection points check:**
```javascript
|| element.type === 'myCustomTask'
```

5. **Add to properties dropdown:**
```javascript
{ value: 'myCustomTask', label: 'My Custom Task' }
```

## Real-World Custom Task Type Examples

### 1. Blockchain Task
**Purpose:** Execute smart contract operations
**Icon:** Chain link or cryptocurrency symbol
**Properties:**
- `contractAddress`
- `network` (Ethereum, Polygon, etc.)
- `gasLimit`
- `function`

### 2. IoT Task
**Purpose:** Interact with IoT devices
**Icon:** Connected devices or sensor
**Properties:**
- `deviceId`
- `protocol` (MQTT, CoAP, etc.)
- `command`
- `expectedResponse`

### 3. Quantum Task
**Purpose:** Quantum computing operations
**Icon:** Quantum circuit or atom
**Properties:**
- `quantumCircuit`
- `qubits`
- `provider` (IBM Q, AWS Braket)
- `shots`

### 4. Agentic Task (Already Implemented!)
**Purpose:** AI agent execution
**Icon:** Robot with antenna
**Properties:**
- `agentType` (e.g., "nlp-classifier", "decision-maker")
- `model` (e.g., "gpt-4", "claude-3")
- `capabilities` (array of agent abilities)
- `learningEnabled` (boolean)

## Agentic Task Properties

### Standard Properties
All tasks have these:
- `id` - Unique identifier
- `name` - Display name
- `documentation` - Description

### Agentic-Specific Properties
Extended properties for AI agents:

```yaml
properties:
  # Agent Configuration
  agentType: "nlp-classifier"
  model: "gpt-4"

  # Capabilities
  capabilities:
    - "intent-detection"
    - "sentiment-analysis"
    - "entity-extraction"

  # Learning & Adaptation
  learningEnabled: true
  feedbackLoop: "reinforcement"

  # Performance
  confidenceThreshold: 0.85
  maxRetries: 3
  timeout: 30000

  # Context
  contextWindow: 8192
  memoryType: "long-term"
```

## Use Cases for Agentic Tasks

### 1. Customer Support
```
Receive Request → [Agentic: Analyze Intent] → [Agentic: Generate Response]
  → [Agentic: Validate Quality] → Send Response
```

### 2. Document Processing
```
Upload Document → [Agentic: Extract Information] → [Agentic: Classify Document]
  → [Agentic: Validate Data] → Store in Database
```

### 3. Code Review
```
Code Commit → [Agentic: Analyze Code] → [Agentic: Security Scan]
  → [Agentic: Suggest Improvements] → Notify Developer
```

### 4. Data Analysis
```
Receive Dataset → [Agentic: Explore Data] → [Agentic: Generate Insights]
  → [Agentic: Create Visualization] → Share Report
```

### 5. Content Moderation
```
User Post → [Agentic: Content Analysis] → [Agentic: Policy Check]
  → Decision Gateway → Publish/Reject
```

## Integration with BPMN Engines

### How Execution Engines Handle Custom Tasks

1. **Extension Recognition**
```javascript
if (task.type === 'agenticTask') {
    const agent = agentFactory.create(task.properties.agentType);
    await agent.execute(task.properties);
}
```

2. **Custom Executors**
```javascript
class AgenticTaskExecutor {
    async execute(task) {
        const agent = new AIAgent(task.properties.model);
        const result = await agent.process(task.input);
        return result;
    }
}
```

3. **Service Registration**
```javascript
processEngine.registerTaskType('agenticTask', AgenticTaskExecutor);
```

## Best Practices

### DO:
✅ Use standard BPMN types when possible
✅ Create custom types for genuinely unique capabilities
✅ Document custom types thoroughly
✅ Use distinctive visual markers
✅ Follow BPMN naming conventions (camelCase + "Task")
✅ Include execution semantics in documentation

### DON'T:
❌ Create custom types for minor variations
❌ Use confusing or ambiguous names
❌ Ignore visual consistency
❌ Forget to document properties
❌ Make icons too complex
❌ Break BPMN execution semantics

## YAML Export Format

Custom task types export like standard tasks:

```yaml
elements:
  - id: agent_1
    type: agenticTask        # Custom type
    name: Analyze Customer Request
    x: 300
    y: 200
    properties:
      agentType: "nlp-classifier"
      model: "gpt-4"
      capabilities:
        - "intent-detection"
        - "sentiment-analysis"
      documentation: "AI agent analyzes customer request"
```

## Interoperability Considerations

### Will Other Tools Understand Your Custom Types?

**Probably Not.** Custom extensions are tool-specific. However:

1. **Graceful Degradation:** Other tools may render as generic tasks
2. **Extension Metadata:** BPMN XML can preserve custom properties
3. **Documentation:** Good docs help manual translation
4. **Standard Mapping:** You can map custom types to standard ones for export

### Making Custom Types More Portable

```yaml
# Include both custom and standard type mapping
type: agenticTask
standardType: serviceTask  # Fallback for other tools
extension:
  customType: agenticTask
  namespace: "http://yourcompany.com/bpmn"
```

## Future of BPMN and AI

As AI agents become mainstream, we may see:
- **BPMN 3.0** with native AI task types
- **AI-BPMN Extension Spec** standardizing agentic tasks
- **Industry Standards** for AI workflow modeling
- **Tool Support** for agent orchestration

Until then, custom extensions like Agentic Task fill the gap!

## Example Workflow

Import `agentic-workflow-example.yaml` to see:
- 5 different Agentic Tasks in action
- AI-powered customer support workflow
- Integration with standard BPMN tasks
- Properties showing agent capabilities

## Summary

| Aspect | Details |
|--------|---------|
| **Can you extend BPMN?** | Yes! BPMN 2.0 is designed for extensions |
| **How?** | Custom task types with unique visual markers |
| **Why?** | Model domain-specific or emerging technology patterns |
| **Agentic Task** | Custom type for autonomous AI agents |
| **Visual Marker** | Robot icon in indigo color |
| **Use Cases** | Customer support, document processing, code review, data analysis |
| **Portability** | Tool-specific, but can export with metadata |
| **Best Practice** | Use standard types when possible, extend when necessary |

## Getting Started

1. **Add Agentic Tasks:** Click "Agentic Task" in the Custom Tasks palette section
2. **Configure Properties:** Set agentType, model, and capabilities
3. **Connect in Workflow:** Wire to other tasks like any BPMN element
4. **Export to YAML:** Save your agentic workflows
5. **Implement Execution:** Build executors for your process engine

Welcome to the future of process automation with AI agents! 🤖
