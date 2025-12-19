# How to Import the Approval Workflow

## Steps to Import

1. **Open the BPMN Modeler**
   - Open `index.html` in your web browser

2. **Import the YAML File**
   - Click the "Import YAML" button in the top toolbar
   - Select the `approval-workflow.yaml` file
   - The workflow will be automatically loaded onto the canvas

3. **View the Workflow**
   - You should see a pool with two lanes:
     - **Main Process Lane** (top): Contains the main workflow tasks
     - **Approval Lane** (bottom): Contains approval tasks and decision gateways

## Workflow Description

This approval workflow demonstrates a multi-stage approval process with the following flow:

### Main Process Lane:
1. **Start Process** → Initiates the workflow
2. **Submit Request** → User submits an initial request
3. **Process Data** → After approval, data is processed
4. **Generate Report** → After validation, a report is generated
5. **Publish Results** → After final approval, results are published
6. **End Process** → Workflow completes successfully

### Approval Lane:
1. **Review Request** → Manager reviews the submitted request
   - **Approved?** gateway → If rejected, goes to "Handle Rejection"

2. **Validate Processing** → Validates the processed data
   - **Valid?** gateway → If invalid, goes to "Handle Rejection"

3. **Final Approval** → Final approval of the generated report
   - **Final OK?** gateway → If rejected, goes to "Handle Rejection"

4. **Handle Rejection** → Processes any rejection from the three approval stages
   - **Rejected** end event → Process ends due to rejection

### Cross-Lane Interactions:
- Each main task sends a request to the approval lane
- Approval decisions route back to the main lane or to rejection handling
- All three approval stages can trigger rejection handling

## Editing the Workflow

Once imported, you can:

1. **Move Elements**: Click and drag any element to reposition it
2. **Edit Properties**: Click on any element to edit its name and documentation in the right panel
3. **Add New Elements**: Use the left palette to add new tasks, events, or gateways
4. **Create Connections**: Click "Sequence Flow" in the palette, then click connection points to link elements
5. **Delete Elements**: Select an element and click "Delete Selected" or press the Delete key
6. **Zoom**: Use the zoom controls to adjust your view

## Re-exporting

After making changes:

1. Click "Export YAML" button
2. Copy to clipboard or download the updated YAML file
3. The file will contain all your modifications

## Workflow Pattern Uses

This pattern is useful for:
- Purchase order approvals
- Document review workflows
- Multi-stage authorization processes
- Quality control workflows
- Any process requiring validation at multiple stages
