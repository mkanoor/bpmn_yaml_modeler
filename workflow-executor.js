// Workflow Executor - Sends workflows to backend for execution

class WorkflowExecutor {
    constructor(backendUrl = 'http://localhost:8000') {
        this.backendUrl = backendUrl;
        this.currentLogFile = null;
    }

    showExecutionModal() {
        const modal = document.getElementById('executeModal');
        if (modal) {
            modal.classList.add('active');

            // Set default context
            const contextInput = document.getElementById('contextInput');
            if (contextInput && !contextInput.value) {
                contextInput.value = JSON.stringify({
                    requester: {
                        email: 'user@example.com',
                        name: 'Test User'
                    }
                }, null, 2);
            }
        }
    }

    hideExecutionModal() {
        const modal = document.getElementById('executeModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    async executeCurrentWorkflow(context = {}) {
        try {
            // Get current workflow YAML
            const yaml = this.getCurrentWorkflowYAML();

            if (!yaml) {
                alert('No workflow to execute. Please create a workflow first.');
                return;
            }

            // Read log file if uploaded
            let logFileContent = null;
            let logFileName = null;

            if (this.currentLogFile) {
                logFileContent = await this.readFileAsText(this.currentLogFile);
                logFileName = this.currentLogFile.name;
            }

            // Add log file to context
            if (logFileContent) {
                context.logFileContent = logFileContent;
                context.logFileName = logFileName;
                context.logFileUrl = `local://${logFileName}`;
            }

            // Send to backend
            const response = await fetch(`${this.backendUrl}/workflows/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    yaml: yaml,
                    context: context
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to execute workflow');
            }

            const result = await response.json();

            console.log('✅ Workflow execution started:', result);

            // Show success notification
            if (aguiClient) {
                aguiClient.showNotification(
                    'Workflow Execution Started',
                    `Instance ID: ${result.instance_id}`,
                    'success'
                );
            } else {
                alert(`Workflow execution started!\nInstance ID: ${result.instance_id}\n\nConnect to WebSocket to see real-time updates.`);
            }

            return result;

        } catch (error) {
            console.error('❌ Error executing workflow:', error);

            if (aguiClient) {
                aguiClient.showNotification(
                    'Execution Error',
                    error.message,
                    'error'
                );
            } else {
                alert(`Error executing workflow:\n${error.message}`);
            }

            throw error;
        }
    }

    async readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    getCurrentWorkflowYAML() {
        // Access the modeler instance (from app.js)
        if (typeof modeler === 'undefined') {
            console.error('Modeler not found');
            return null;
        }

        // Generate YAML from current state
        const data = {
            process: {
                id: 'process_1',
                name: 'BPMN Process',
                pools: modeler.pools.map(pool => ({
                    id: pool.id,
                    name: pool.name,
                    x: pool.x,
                    y: pool.y,
                    width: pool.width,
                    height: pool.height,
                    lanes: pool.lanes
                })),
                elements: modeler.elements.map(element => {
                    const exported = {
                        id: element.id,
                        type: element.type,
                        name: element.name,
                        x: element.x,
                        y: element.y,
                        poolId: element.poolId,
                        laneId: element.laneId,
                        properties: element.properties
                    };

                    if (element.type === 'subProcess') {
                        exported.expanded = element.expanded;
                        exported.width = element.width;
                        exported.height = element.height;
                        if (element.childElements && element.childElements.length > 0) {
                            exported.childElements = element.childElements;
                        }
                        if (element.childConnections && element.childConnections.length > 0) {
                            exported.childConnections = element.childConnections;
                        }
                    }

                    return exported;
                }),
                connections: modeler.connections.map(connection => ({
                    id: connection.id,
                    type: connection.type,
                    name: connection.name,
                    from: connection.from,
                    to: connection.to,
                    properties: connection.properties || {}
                }))
            }
        };

        return jsyaml.dump(data, { indent: 2 });
    }


    async checkHealth() {
        try {
            const response = await fetch(`${this.backendUrl}/health`);
            const data = await response.json();
            return data.status === 'healthy';
        } catch (error) {
            console.error('Backend health check failed:', error);
            return false;
        }
    }

    async listActiveWorkflows() {
        try {
            const response = await fetch(`${this.backendUrl}/workflows/active`);
            const data = await response.json();
            return data.workflows;
        } catch (error) {
            console.error('Error listing workflows:', error);
            return [];
        }
    }
}

// Create global executor instance
const workflowExecutor = new WorkflowExecutor();

// Add execute button handler when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const executeBtn = document.getElementById('executeBtn');
    const executeModal = document.getElementById('executeModal');
    const startExecutionBtn = document.getElementById('startExecutionBtn');
    const cancelExecutionBtn = document.getElementById('cancelExecutionBtn');
    const logFileInput = document.getElementById('logFileInput');

    // Execute button - shows modal
    if (executeBtn) {
        executeBtn.addEventListener('click', async () => {
            // Check if backend is running
            const isHealthy = await workflowExecutor.checkHealth();

            if (!isHealthy) {
                const startBackend = confirm(
                    'Backend server is not running!\n\n' +
                    'To execute workflows, you need to start the backend:\n' +
                    '1. cd backend\n' +
                    '2. pip install -r requirements.txt\n' +
                    '3. python main.py\n\n' +
                    'Click OK to continue anyway (will fail), or Cancel to abort.'
                );

                if (!startBackend) {
                    return;
                }
            }

            // Show execution modal
            workflowExecutor.showExecutionModal();
        });
    }

    // Log file input handler
    if (logFileInput) {
        logFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                workflowExecutor.currentLogFile = file;
                console.log('Log file selected:', file.name);
            }
        });
    }

    // Start execution button
    if (startExecutionBtn) {
        startExecutionBtn.addEventListener('click', async () => {
            // Get context from textarea
            const contextInput = document.getElementById('contextInput');
            let context = {};

            try {
                context = JSON.parse(contextInput.value || '{}');
            } catch (error) {
                alert('Invalid JSON in context variables. Please check your input.');
                return;
            }

            // Hide modal
            workflowExecutor.hideExecutionModal();

            // Execute workflow
            await workflowExecutor.executeCurrentWorkflow(context);
        });
    }

    // Cancel button
    if (cancelExecutionBtn) {
        cancelExecutionBtn.addEventListener('click', () => {
            workflowExecutor.hideExecutionModal();
        });
    }

    // Modal close buttons
    if (executeModal) {
        const closeBtn = executeModal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                workflowExecutor.hideExecutionModal();
            });
        }
    }

    // Check backend health on startup
    setTimeout(async () => {
        const isHealthy = await workflowExecutor.checkHealth();
        console.log(isHealthy ? '✅ Backend is running' : '⚠️ Backend is not running');
    }, 1000);
});
