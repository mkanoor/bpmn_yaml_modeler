# BPMN Task Properties Configuration Guide

## Overview

In BPMN, task properties define how a task behaves when executed. Properties are essential for:
- **Execution logic** - How the process engine executes the task
- **Assignment** - Who performs the task
- **Integration** - How the task connects to external systems
- **Behavior** - Task-specific configuration

## How Properties Work in BPMN

### BPMN XML Standard
In standard BPMN 2.0 XML, properties are defined using extension elements:

```xml
<bpmn:serviceTask id="task1" name="Call API">
  <bpmn:extensionElements>
    <camunda:properties>
      <camunda:property name="endpoint" value="https://api.example.com" />
      <camunda:property name="method" value="POST" />
    </camunda:properties>
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

### In This Modeler
We use a YAML-based approach that's easier to read and edit:

```yaml
elements:
  - id: task1
    type: serviceTask
    name: Call API
    properties:
      implementation: "External"
      topic: "api-calls"
      endpoint: "https://api.example.com"
      method: "POST"
```

## Three Levels of Properties

### 1. Basic Properties
Available for ALL elements:
- **ID** - Unique identifier
- **Name** - Display name
- **Type** - Element type
- **Documentation** - Description

### 2. Task-Specific Properties
Predefined properties based on task type:

#### User Task
| Property | Description | Example |
|----------|-------------|---------|
| `assignee` | User assigned to the task | `john.doe@company.com` |
| `candidateGroups` | Groups that can claim the task | `managers, approvers` |
| `priority` | Task priority | `High`, `Medium`, `Low` |
| `dueDate` | When the task is due | `2024-12-31T23:59:59Z` |

#### Service Task
| Property | Description | Example |
|----------|-------------|---------|
| `implementation` | How the service is called | `Java Class`, `External` |
| `class` | Java class name | `com.example.MyDelegate` |
| `expression` | Expression to evaluate | `${myBean.execute()}` |
| `resultVariable` | Variable to store result | `apiResponse` |
| `topic` | External task topic | `payment-processing` |

#### Script Task
| Property | Description | Example |
|----------|-------------|---------|
| `scriptFormat` | Scripting language | `JavaScript`, `Python` |
| `script` | Actual script code | `return a + b;` |
| `resultVariable` | Variable to store result | `calculationResult` |

#### Send Task
| Property | Description | Example |
|----------|-------------|---------|
| `messageType` | Type of message | `Email`, `SMS`, `Webhook` |
| `to` | Recipient | `customer@example.com` |
| `subject` | Message subject | `Order Confirmation` |
| `messageBody` | Message content | Template or text |

#### Receive Task
| Property | Description | Example |
|----------|-------------|---------|
| `messageRef` | Message reference | `paymentConfirmation` |
| `timeout` | Max wait time (ms) | `30000` |
| `correlationKey` | Message correlation | `${orderId}` |

#### Business Rule Task
| Property | Description | Example |
|----------|-------------|---------|
| `decisionRef` | Decision table reference | `discountRules` |
| `resultVariable` | Variable for result | `discount` |
| `decisionTable` | Path to DMN file | `rules/discount.dmn` |

#### Agentic Task (Custom)
| Property | Description | Example |
|----------|-------------|---------|
| `agentType` | Type of AI agent | `nlp-classifier` |
| `model` | AI model to use | `gpt-4`, `claude-3-opus` |
| `capabilities` | Agent abilities | `intent-detection` |
| `confidenceThreshold` | Minimum confidence | `0.85` |
| `maxRetries` | Max retry attempts | `3` |
| `learningEnabled` | Enable learning | `true` |

#### Call Activity
| Property | Description | Example |
|----------|-------------|---------|
| `calledElement` | Process to call | `approval-subprocess` |
| `calledElementBinding` | Version binding | `latest`, `deployment` |
| `inheritVariables` | Pass variables | `true` |
| `async` | Run asynchronously | `false` |

### 3. Custom Properties
Any additional key-value pairs you define:

```yaml
properties:
  # Task-specific
  implementation: "External"
  topic: "payment-processing"

  # Custom properties
  custom:
    retryStrategy: "exponential"
    maxAttempts: "5"
    notifyOnFailure: "true"
    customerId: "${customer.id}"
```

## Configuring Properties in the UI

### Step 1: Select an Element
Click on any task, event, or gateway on the canvas

### Step 2: View Properties Panel
The right panel shows three sections:

#### Basic Properties
- **ID**: Auto-generated, can be edited
- **Name**: Display name on the canvas
- **Type**: Element type (can be changed via dropdown)
- **Documentation**: Description field

#### Task-Specific Properties (if applicable)
Predefined fields based on task type:
- Dropdowns for select fields
- Text inputs for strings
- Number inputs for numeric values
- Checkboxes for booleans
- Textareas for longer content

#### Custom Properties
- Click **"+ Add Custom Property"**
- Enter **Property Name** (left field)
- Enter **Value** (right field)
- Click **×** to remove a property

### Step 3: Edit Properties
All changes save automatically as you type!

### Step 4: Export
Click **"Export YAML"** to see/save your configuration

## Property Configuration Examples

### Example 1: User Task with Assignment
```yaml
- id: reviewTask
  type: userTask
  name: Review Application
  properties:
    assignee: "manager@company.com"
    candidateGroups: "reviewers, managers"
    priority: "High"
    dueDate: "P3D"  # 3 days from start
    documentation: "Manager reviews the application for completeness"
```

**UI Configuration:**
1. Click on the task
2. Set "Task Type" to "User Task"
3. Fill in "Assignee": `manager@company.com`
4. Fill in "Candidate Groups": `reviewers, managers`
5. Select "Priority": `High`
6. Set "Due Date": `P3D`

### Example 2: Service Task calling API
```yaml
- id: callPaymentAPI
  type: serviceTask
  name: Process Payment
  properties:
    implementation: "External"
    topic: "payment-processing"
    resultVariable: "paymentResult"
    documentation: "Calls external payment gateway"
    custom:
      endpoint: "https://api.stripe.com/v1/charges"
      apiKey: "${env.STRIPE_API_KEY}"
      timeout: "5000"
```

**UI Configuration:**
1. Select task
2. Set "Task Type" to "Service Task"
3. Select "Implementation": `External`
4. Set "External Task Topic": `payment-processing`
5. Set "Result Variable": `paymentResult`
6. Click "+ Add Custom Property"
   - Property: `endpoint`, Value: `https://api.stripe.com/v1/charges`
7. Add more custom properties as needed

### Example 3: Agentic Task with AI Configuration
```yaml
- id: analyzeIntent
  type: agenticTask
  name: Analyze Customer Intent
  properties:
    agentType: "nlp-classifier"
    model: "gpt-4"
    capabilities: "intent-detection, sentiment-analysis, entity-extraction"
    confidenceThreshold: 0.85
    maxRetries: 3
    learningEnabled: true
    documentation: "AI agent analyzes customer request"
    custom:
      temperature: "0.3"
      maxTokens: "1000"
      contextWindow: "8192"
```

**UI Configuration:**
1. Add Agentic Task from palette
2. In properties:
   - Agent Type: `nlp-classifier`
   - AI Model: `gpt-4` (dropdown)
   - Capabilities: `intent-detection, sentiment-analysis`
   - Confidence Threshold: `0.85`
   - Max Retries: `3`
   - Learning Enabled: ✓ (checked)
3. Custom Properties:
   - `temperature`: `0.3`
   - `maxTokens`: `1000`
   - `contextWindow`: `8192`

### Example 4: Script Task with Calculation
```yaml
- id: calculateDiscount
  type: scriptTask
  name: Calculate Discount
  properties:
    scriptFormat: "JavaScript"
    script: |
      var discount = 0;
      if (orderTotal > 1000) discount = 0.15;
      else if (orderTotal > 500) discount = 0.10;
      else discount = 0.05;
      discount;
    resultVariable: "discountRate"
    documentation: "Calculates discount based on order total"
```

**UI Configuration:**
1. Select Script Task
2. Script Format: `JavaScript`
3. Script: Paste multi-line script
4. Result Variable: `discountRate`

## Property Expressions

Many BPMN engines support expressions in property values:

### Variable References
```yaml
assignee: "${requester.manager}"
to: "${customer.email}"
amount: "${order.total}"
```

### Calculations
```yaml
dueDate: "${now().plusDays(3)}"
priority: "${order.value > 10000 ? 'High' : 'Normal'}"
```

### Spring EL (Common in Camunda/Flowable)
```yaml
class: "${myDelegate}"
expression: "${customerService.notify(execution)}"
```

## Best Practices

### DO:
✅ Use task-specific properties when available
✅ Add documentation to explain purpose
✅ Use expressions for dynamic values
✅ Group related custom properties with prefixes
✅ Validate property values before deployment
✅ Use meaningful property names

### DON'T:
❌ Hardcode sensitive data (use variables/expressions)
❌ Use generic property names like "prop1", "value"
❌ Leave required properties empty
❌ Duplicate information across properties
❌ Mix different naming conventions

## Property Naming Conventions

### Recommended Formats:
- **camelCase**: `maxRetries`, `apiEndpoint` (recommended)
- **snake_case**: `max_retries`, `api_endpoint`
- **kebab-case**: `max-retries`, `api-endpoint`

**Choose one and be consistent!**

### Prefixing Custom Properties:
```yaml
custom:
  http.endpoint: "https://api.example.com"
  http.method: "POST"
  http.timeout: "5000"

  retry.maxAttempts: "3"
  retry.backoff: "exponential"

  notify.onSuccess: "true"
  notify.recipients: "team@company.com"
```

## Integration with Process Engines

### Camunda Platform
```yaml
properties:
  implementation: "External"
  topic: "my-topic"
  custom:
    camunda.asyncBefore: "true"
    camunda.retryTimeCycle: "R3/PT5M"
```

### Flowable
```yaml
properties:
  class: "com.example.MyDelegate"
  custom:
    flowable.async: "true"
    flowable.exclusive: "false"
```

### Custom Engine
You can define any properties your custom engine understands:

```yaml
properties:
  custom:
    myEngine.executor: "threadPool"
    myEngine.queue: "high-priority"
    myEngine.timeout: "30000"
```

## Property Validation

When implementing a process engine, validate properties:

```javascript
function validateUserTask(task) {
    if (!task.properties.assignee && !task.properties.candidateGroups) {
        throw new Error('User task must have assignee or candidate groups');
    }

    if (task.properties.priority) {
        const valid = ['Low', 'Medium', 'High', 'Critical'];
        if (!valid.includes(task.properties.priority)) {
            throw new Error('Invalid priority value');
        }
    }
}
```

## Exporting Properties

### YAML Export
Click "Export YAML" to get all properties in YAML format:

```yaml
process:
  elements:
    - id: task1
      type: serviceTask
      name: My Task
      properties:
        implementation: "External"
        topic: "my-topic"
        custom:
          customProp: "customValue"
```

### Using in Process Engines
Parse the YAML and map properties to your engine's format:

```javascript
const element = yaml.load(yamlContent);
const task = element.properties;

// Map to Camunda format
const camundaTask = {
    id: element.id,
    name: element.name,
    type: element.type,
    'camunda:topic': task.topic,
    'camunda:asyncBefore': task.custom['asyncBefore']
};
```

## Summary

| Property Type | When to Use | Where Defined | Example |
|--------------|-------------|---------------|---------|
| **Basic** | Always | Built-in | `id`, `name`, `type` |
| **Task-Specific** | Standard BPMN behavior | Template | `assignee`, `class`, `script` |
| **Custom** | Domain-specific needs | User-defined | `apiKey`, `retryPolicy` |

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│  BPMN PROPERTY CONFIGURATION            │
├─────────────────────────────────────────┤
│  1. Select Element on Canvas            │
│  2. View Properties Panel (right side)  │
│  3. Edit Fields:                         │
│     • Basic Properties (always)          │
│     • Task-Specific (by type)            │
│     • Custom (click "+ Add")             │
│  4. Changes Save Automatically           │
│  5. Export YAML to see result           │
└─────────────────────────────────────────┘
```

Configure your tasks with precision to build executable process workflows! 🎯
