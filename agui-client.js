// AG-UI Client - Connects to backend WebSocket for real-time workflow updates

class AGUIClient {
    constructor(url = 'ws://localhost:8000/ws') {
        this.url = url;
        this.ws = null;
        this.handlers = {};
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 5000;

        this.connect();
    }

    connect() {
        console.log('Connecting to AG-UI server:', this.url);

        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('✅ Connected to AG-UI server');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);

                // Send ping to keep alive
                this.startPingInterval();
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };

            this.ws.onclose = () => {
                console.log('Disconnected from AG-UI server');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.stopPingInterval();

                // Attempt reconnection
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting in ${this.reconnectDelay / 1000}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                    setTimeout(() => this.connect(), this.reconnectDelay);
                } else {
                    console.error('Max reconnection attempts reached');
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
        }
    }

    startPingInterval() {
        this.pingInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, 30000); // Ping every 30 seconds
    }

    stopPingInterval() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.className = connected ? 'connected' : 'disconnected';
            indicator.textContent = connected ? '● Connected' : '● Disconnected';
        }
    }

    handleMessage(message) {
        const { type } = message;
        console.log('📨 Received:', type, message);

        // Special logging for cancellation messages
        if (type === 'task.cancelled') {
            console.log('🚫🚫🚫 TASK CANCELLED MESSAGE RECEIVED 🚫🚫🚫');
            console.log('   Element ID:', message.elementId);
            console.log('   Reason:', message.reason);
        }

        // Route to appropriate handler
        switch(type) {
            case 'workflow.started':
                this.handleWorkflowStarted(message);
                break;

            case 'workflow.completed':
                this.handleWorkflowCompleted(message);
                break;

            case 'element.activated':
                this.highlightElement(message.elementId);
                break;

            case 'element.completed':
                this.markElementComplete(message.elementId);
                break;

            case 'task.progress':
                this.updateTaskProgress(message.elementId, message.progress, message.status, message.message);
                break;

            case 'agent.tool_use':
                this.showAgentToolUse(message.elementId, message.tool, message.arguments);
                break;

            case 'userTask.created':
                this.showApprovalForm(message.taskInstance);
                break;

            case 'gateway.evaluating':
                this.highlightElement(message.elementId);
                break;

            case 'gateway.path_taken':
                this.highlightPath(message.flowId, message.elementId);
                break;

            case 'task.error':
                this.showErrorOnElement(message.elementId, message.error);
                break;

            case 'task.cancelled':
                this.handleTaskCancelled(message);
                break;

            case 'text.message.start':
                this.handleTextMessageStart(message);
                break;

            case 'text.message.content':
                this.handleTextMessageContent(message);
                break;

            case 'text.message.end':
                this.handleTextMessageEnd(message);
                break;

            case 'task.thinking':
                this.handleTaskThinking(message);
                break;

            case 'task.tool.start':
                this.handleTaskToolStart(message);
                break;

            case 'task.tool.end':
                this.handleTaskToolEnd(message);
                break;

            case 'pong':
                // Ping response
                break;

            default:
                console.log('Unknown message type:', type);
        }

        // Call custom handlers
        if (this.handlers[type]) {
            this.handlers[type].forEach(handler => handler(message));
        }
    }

    handleWorkflowStarted(message) {
        console.log('🚀 Workflow started:', message.instanceId);
        this.showNotification('Workflow Started', `${message.workflowName} is now executing`, 'info');
    }

    handleWorkflowCompleted(message) {
        console.log('✅ Workflow completed:', message.outcome);

        const outcomeEmoji = message.outcome === 'success' ? '✅' : '❌';
        const outcomeClass = message.outcome === 'success' ? 'success' : 'error';

        // After workflow completes, mark any elements on not-taken paths as skipped
        this.markNotTakenPathsAsSkipped();

        this.showNotification(
            `Workflow ${message.outcome}`,
            `Completed in ${message.duration.toFixed(2)}s - Click "Clear Execution" to reset`,
            outcomeClass
        );

        // Don't auto-clear - preserve final state for review
        // User can manually clear using the "Clear Execution" button
    }

    markNotTakenPathsAsSkipped() {
        console.log('🔍 Marking not-taken paths as skipped...');

        // Find all connections marked as not-taken and get their IDs
        const notTakenFlows = document.querySelectorAll('.bpmn-connection.path-not-taken');
        const notTakenFlowIds = [];

        notTakenFlows.forEach(flow => {
            const flowId = flow.getAttribute('data-id');
            if (flowId) {
                notTakenFlowIds.push(flowId);
                console.log(`  Found not-taken flow: ${flowId}`);
            }
        });

        // Access the modeler's connection data to find target elements
        if (typeof modeler !== 'undefined' && modeler.connections) {
            notTakenFlowIds.forEach(flowId => {
                const connection = modeler.connections.find(c => c.id === flowId);
                if (connection) {
                    console.log(`  Connection ${flowId}: from ${connection.from} to ${connection.to}`);
                    // Recursively mark all elements starting from the target
                    this.markElementAndDownstreamAsSkippedUsingModel(connection.to);
                }
            });
        } else {
            console.warn('⚠️ Modeler not available, falling back to DOM-based marking');
            notTakenFlows.forEach(flow => {
                this.markPathElementsAsSkipped(flow);
            });
        }
    }

    markElementAndDownstreamAsSkippedUsingModel(elementId) {
        console.log(`  📍 Marking element ${elementId} as skipped`);

        // Mark this element as skipped
        this.markElementSkipped(elementId);

        // Find all outgoing connections from this element using the model
        if (typeof modeler !== 'undefined' && modeler.connections) {
            const outgoingConnections = modeler.connections.filter(c => c.from === elementId);

            console.log(`    Found ${outgoingConnections.length} outgoing connections from ${elementId}`);

            outgoingConnections.forEach(conn => {
                console.log(`    Following connection ${conn.id} to ${conn.to}`);
                // Recursively mark downstream elements
                this.markElementAndDownstreamAsSkippedUsingModel(conn.to);
            });
        }
    }

    highlightElement(elementId) {
        // Remove previous highlights
        document.querySelectorAll('.bpmn-element.active').forEach(el => {
            el.classList.remove('active');
        });

        // Highlight current element
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.classList.add('active');

            // Scroll into view
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    markElementComplete(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            // Don't override if already marked as skipped
            if (element.classList.contains('skipped')) {
                console.log(`Element ${elementId} is skipped, not marking as completed`);
                return;
            }

            element.classList.remove('active');
            element.classList.add('completed');

            // Add green checkmark (task was executed and completed)
            const existingCheckmark = element.querySelector('.completion-mark');
            if (!existingCheckmark) {
                const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                checkmark.setAttribute('class', 'completion-mark');
                checkmark.setAttribute('x', '20');
                checkmark.setAttribute('y', '-20');
                checkmark.setAttribute('font-size', '20');
                checkmark.setAttribute('fill', '#27ae60'); // Green - task executed
                checkmark.textContent = '✓';
                element.appendChild(checkmark);
            }
        }
    }

    markElementSkipped(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (!element) {
            console.warn(`    ⚠️ Element ${elementId} not found in DOM`);
            return;
        }

        // Don't override if already marked as completed (task was actually executed)
        if (element.classList.contains('completed')) {
            console.log(`    ✅ Element ${elementId} is completed, not marking as skipped`);
            return;
        }

        // Check if already skipped
        if (element.classList.contains('skipped')) {
            console.log(`    ⊘ Element ${elementId} already marked as skipped`);
            return;
        }

        console.log(`    ⊘ Marking element ${elementId} as SKIPPED`);

        element.classList.remove('active');
        element.classList.add('skipped');

        // Add orange/yellow skip indicator (task was not executed)
        const existingMark = element.querySelector('.skip-mark');
        if (!existingMark) {
            const skipMark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            skipMark.setAttribute('class', 'skip-mark');
            skipMark.setAttribute('x', '20');
            skipMark.setAttribute('y', '-20');
            skipMark.setAttribute('font-size', '20');
            skipMark.setAttribute('fill', '#f39c12'); // Orange - task skipped
            skipMark.textContent = '⊘'; // Circle with slash
            element.appendChild(skipMark);
        }
    }

    updateTaskProgress(elementId, progress, status, message) {
        console.log(`Progress ${elementId}: ${(progress * 100).toFixed(0)}% - ${message}`);

        // Update or create progress bar
        let progressContainer = document.getElementById(`progress-${elementId}`);

        if (!progressContainer) {
            const element = document.querySelector(`[data-id="${elementId}"]`);
            if (element) {
                // Create progress overlay
                progressContainer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                progressContainer.setAttribute('id', `progress-${elementId}`);
                progressContainer.setAttribute('class', 'progress-overlay');

                // Progress bar background
                const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                bgRect.setAttribute('x', '-50');
                bgRect.setAttribute('y', '35');
                bgRect.setAttribute('width', '100');
                bgRect.setAttribute('height', '4');
                bgRect.setAttribute('fill', '#ecf0f1');
                bgRect.setAttribute('rx', '2');
                progressContainer.appendChild(bgRect);

                // Progress bar fill
                const fillRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                fillRect.setAttribute('id', `progress-fill-${elementId}`);
                fillRect.setAttribute('x', '-50');
                fillRect.setAttribute('y', '35');
                fillRect.setAttribute('width', '0');
                fillRect.setAttribute('height', '4');
                fillRect.setAttribute('fill', '#3498db');
                fillRect.setAttribute('rx', '2');
                progressContainer.appendChild(fillRect);

                element.appendChild(progressContainer);
            }
        }

        // Update progress fill
        const fillRect = document.getElementById(`progress-fill-${elementId}`);
        if (fillRect) {
            fillRect.setAttribute('width', `${progress * 100}`);
        }

        // Show tooltip with message
        this.showTooltip(elementId, message);

        // Remove progress bar when complete
        if (progress >= 1.0) {
            setTimeout(() => {
                if (progressContainer) {
                    progressContainer.remove();
                }
            }, 1000);
        }
    }

    showAgentToolUse(elementId, tool, args) {
        console.log(`🤖 Agent using tool: ${tool}`, args);

        // Create floating notification
        const notification = document.createElement('div');
        notification.className = 'tool-use-notification';
        notification.innerHTML = `
            <div class="tool-icon">🔧</div>
            <div class="tool-info">
                <div class="tool-name">${tool}</div>
                <div class="tool-args">${JSON.stringify(args).substring(0, 50)}...</div>
            </div>
        `;

        // Position near element
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            const rect = element.getBoundingClientRect();
            notification.style.position = 'fixed';
            notification.style.left = `${rect.right + 10}px`;
            notification.style.top = `${rect.top}px`;
        } else {
            notification.style.position = 'fixed';
            notification.style.top = '80px';
            notification.style.right = '20px';
        }

        document.body.appendChild(notification);

        // Fade out and remove
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    showApprovalForm(taskInstance) {
        console.log('📋 Showing approval form for:', taskInstance.taskName);

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'approval-modal active';
        modal.setAttribute('data-task-id', taskInstance.taskId);
        modal.innerHTML = `
            <div class="modal-backdrop"></div>
            <div class="modal-content approval-form">
                <div class="modal-header">
                    <h2>${taskInstance.taskName}</h2>
                    <button class="close-btn" onclick="this.closest('.approval-modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="task-details">
                        <p><strong>Assignee:</strong> ${taskInstance.assignee || 'N/A'}</p>
                        <p><strong>Priority:</strong> ${taskInstance.priority}</p>
                        ${taskInstance.dueDate ? `<p><strong>Due:</strong> ${taskInstance.dueDate}</p>` : ''}
                    </div>

                    <div class="form-data">
                        <h3>Data for Review:</h3>
                        <pre>${JSON.stringify(taskInstance.data, null, 2)}</pre>
                    </div>

                    <div class="form-group">
                        <label for="approval-comments-${taskInstance.taskId}">Comments:</label>
                        <textarea
                            id="approval-comments-${taskInstance.taskId}"
                            placeholder="Enter your comments..."
                            rows="4"
                        ></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn approve-btn" onclick="aguiClient.approveTask('${taskInstance.taskId}')">
                        ✓ Approve
                    </button>
                    <button class="btn reject-btn" onclick="aguiClient.rejectTask('${taskInstance.taskId}')">
                        ✗ Reject
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    handleTaskCancelled(message) {
        console.log('🚫 handleTaskCancelled called');
        console.log('   Element ID:', message.elementId);
        console.log('   Reason:', message.reason);

        // Find and close the approval modal for this task
        const selector = `.approval-modal[data-task-id="${message.elementId}"]`;
        console.log('   Looking for modal with selector:', selector);

        const modal = document.querySelector(selector);
        console.log('   Modal found:', modal);

        if (modal) {
            console.log('✅ CLOSING modal for task:', message.elementId);

            // Add fade-out animation
            modal.style.opacity = '0';
            modal.style.transition = 'opacity 0.3s ease-out';

            setTimeout(() => {
                modal.remove();
                console.log('✅ Modal removed from DOM');
            }, 300);

            // Show notification explaining why it was cancelled
            this.showNotification(
                'Approval Cancelled',
                message.reason || 'Another approval path completed first',
                'info'
            );
        } else {
            console.log('❌ Modal NOT found for task:', message.elementId);
            console.log('   All modals in DOM:', document.querySelectorAll('.approval-modal'));
        }

        // Mark element as cancelled/skipped on canvas
        this.markElementCancelled(message.elementId);
    }

    markElementCancelled(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.classList.remove('active');
            element.classList.add('cancelled');

            // Add visual indicator (greyed out)
            if (element.tagName === 'rect' || element.tagName === 'circle' || element.tagName === 'path') {
                element.setAttribute('opacity', '0.4');
                element.setAttribute('stroke-dasharray', '5,5');
            }
        }
    }

    approveTask(taskId) {
        const comments = document.getElementById(`approval-comments-${taskId}`).value;

        this.send({
            type: 'userTask.complete',
            taskId: taskId,
            decision: 'approved',
            comments: comments,
            user: this.getCurrentUser()
        });

        // Close modal
        const modal = document.querySelector('.approval-modal');
        if (modal) modal.remove();

        this.showNotification('Task Approved', 'Your approval has been submitted', 'success');
    }

    rejectTask(taskId) {
        const comments = document.getElementById(`approval-comments-${taskId}`).value;

        this.send({
            type: 'userTask.complete',
            taskId: taskId,
            decision: 'rejected',
            comments: comments,
            user: this.getCurrentUser()
        });

        // Close modal
        const modal = document.querySelector('.approval-modal');
        if (modal) modal.remove();

        this.showNotification('Task Rejected', 'Your rejection has been submitted', 'warning');
    }

    getCurrentUser() {
        // In production, get from authentication
        return 'test-user@example.com';
    }

    highlightPath(flowId, gatewayId) {
        const takenFlow = document.querySelector(`[data-id="${flowId}"]`);

        if (takenFlow) {
            // Highlight the taken path with green
            takenFlow.classList.add('active-flow', 'path-taken');
            takenFlow.setAttribute('stroke', '#27ae60');
            takenFlow.setAttribute('stroke-width', '3');

            // Add checkmark indicator to the taken path
            const flowMidpoint = this.getFlowMidpoint(takenFlow);
            if (flowMidpoint) {
                const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                checkmark.setAttribute('class', 'path-indicator path-taken-indicator');
                checkmark.setAttribute('x', flowMidpoint.x);
                checkmark.setAttribute('y', flowMidpoint.y);
                checkmark.setAttribute('font-size', '24');
                checkmark.setAttribute('fill', '#27ae60');
                checkmark.setAttribute('font-weight', 'bold');
                checkmark.textContent = '✓';

                // Add to connections layer
                const connectionsLayer = document.getElementById('connectionsLayer');
                if (connectionsLayer) {
                    connectionsLayer.appendChild(checkmark);
                }
            }

            // Mark all other outgoing flows from this gateway as NOT taken
            if (gatewayId) {
                const allFlows = document.querySelectorAll(`line[data-id]`);
                allFlows.forEach(flow => {
                    const flowDataId = flow.getAttribute('data-id');

                    // Check if this flow comes from the same gateway
                    if (flowDataId !== flowId && this.isFlowFromGateway(flow, gatewayId)) {
                        // Mark as not taken (gray with X)
                        flow.classList.add('path-not-taken');
                        flow.setAttribute('stroke', '#95a5a6');
                        flow.setAttribute('stroke-dasharray', '5,5');
                        flow.setAttribute('opacity', '0.5');

                        // Add X indicator to not-taken paths
                        const notTakenMidpoint = this.getFlowMidpoint(flow);
                        if (notTakenMidpoint) {
                            const xmark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                            xmark.setAttribute('class', 'path-indicator path-not-taken-indicator');
                            xmark.setAttribute('x', notTakenMidpoint.x);
                            xmark.setAttribute('y', notTakenMidpoint.y);
                            xmark.setAttribute('font-size', '24');
                            xmark.setAttribute('fill', '#95a5a6');
                            xmark.setAttribute('font-weight', 'bold');
                            xmark.textContent = '✗';

                            // Add to connections layer
                            const connectionsLayer = document.getElementById('connectionsLayer');
                            if (connectionsLayer) {
                                connectionsLayer.appendChild(xmark);
                            }
                        }

                        // Note: Elements will be marked as skipped after workflow completes
                        // to avoid race conditions with element.completed messages
                    }
                });
            }
        }
    }

    markPathElementsAsSkipped(flowElement) {
        // Get the target element of this flow
        const x2 = parseFloat(flowElement.getAttribute('x2'));
        const y2 = parseFloat(flowElement.getAttribute('y2'));

        // Find element at the end of this flow
        const allElements = document.querySelectorAll('.bpmn-element[data-id]');
        allElements.forEach(element => {
            const transform = element.getAttribute('transform');
            if (transform) {
                const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
                if (match) {
                    const ex = parseFloat(match[1]);
                    const ey = parseFloat(match[2]);

                    // Check if element is at the end of this flow (within 5px tolerance)
                    const distance = Math.sqrt(Math.pow(x2 - ex, 2) + Math.pow(y2 - ey, 2));
                    if (distance < 5) {
                        const elementId = element.getAttribute('data-id');
                        // Mark this element and recursively mark all downstream elements
                        this.markElementAndDownstreamAsSkipped(elementId);
                    }
                }
            }
        });
    }

    markElementAndDownstreamAsSkipped(elementId) {
        // Mark this element as skipped
        this.markElementSkipped(elementId);

        // Find all outgoing connections from this element
        const allConnections = document.querySelectorAll('.bpmn-connection[data-id]');
        allConnections.forEach(conn => {
            const x1 = parseFloat(conn.getAttribute('x1'));
            const y1 = parseFloat(conn.getAttribute('y1'));

            // Find the element position
            const element = document.querySelector(`[data-id="${elementId}"]`);
            if (element) {
                const transform = element.getAttribute('transform');
                if (transform) {
                    const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
                    if (match) {
                        const ex = parseFloat(match[1]);
                        const ey = parseFloat(match[2]);

                        // Check if this connection starts from this element (within 5px tolerance)
                        const distance = Math.sqrt(Math.pow(x1 - ex, 2) + Math.pow(y1 - ey, 2));
                        if (distance < 5) {
                            // This connection goes out from the skipped element
                            // Recursively mark downstream elements
                            this.markPathElementsAsSkipped(conn);
                        }
                    }
                }
            }
        });
    }

    getFlowMidpoint(flowElement) {
        const x1 = parseFloat(flowElement.getAttribute('x1'));
        const y1 = parseFloat(flowElement.getAttribute('y1'));
        const x2 = parseFloat(flowElement.getAttribute('x2'));
        const y2 = parseFloat(flowElement.getAttribute('y2'));

        if (!isNaN(x1) && !isNaN(y1) && !isNaN(x2) && !isNaN(y2)) {
            return {
                x: (x1 + x2) / 2,
                y: (y1 + y2) / 2
            };
        }
        return null;
    }

    isFlowFromGateway(flowElement, gatewayId) {
        // Get the flow's starting point
        const x1 = parseFloat(flowElement.getAttribute('x1'));
        const y1 = parseFloat(flowElement.getAttribute('y1'));

        // Get the gateway element's position
        const gateway = document.querySelector(`[data-id="${gatewayId}"]`);
        if (gateway) {
            const transform = gateway.getAttribute('transform');
            if (transform) {
                const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
                if (match) {
                    const gx = parseFloat(match[1]);
                    const gy = parseFloat(match[2]);

                    // Check if flow starts near gateway (within 30px tolerance)
                    const distance = Math.sqrt(Math.pow(x1 - gx, 2) + Math.pow(y1 - gy, 2));
                    return distance < 30;
                }
            }
        }
        return false;
    }

    showErrorOnElement(elementId, error) {
        console.error('❌ Error on element:', elementId, error);

        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.classList.add('error');

            // Add error indicator
            const errorMark = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            errorMark.setAttribute('class', 'error-mark');
            errorMark.setAttribute('x', '20');
            errorMark.setAttribute('y', '-20');
            errorMark.setAttribute('font-size', '20');
            errorMark.setAttribute('fill', '#e74c3c');
            errorMark.textContent = '⚠';
            element.appendChild(errorMark);
        }

        this.showNotification('Task Error', error.message, 'error');
    }

    showTooltip(elementId, message) {
        // Simple tooltip implementation
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            element.setAttribute('data-tooltip', message);
        }
    }

    showNotification(title, message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        `;

        const container = document.getElementById('notifications-container') ||
            this.createNotificationsContainer();

        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    createNotificationsContainer() {
        const container = document.createElement('div');
        container.id = 'notifications-container';
        container.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
        return container;
    }

    clearAllHighlights() {
        document.querySelectorAll('.bpmn-element').forEach(el => {
            el.classList.remove('active', 'completed', 'error', 'skipped');
            el.querySelectorAll('.completion-mark, .error-mark, .skip-mark').forEach(mark => mark.remove());
        });

        // Clear connection path indicators
        document.querySelectorAll('.bpmn-connection').forEach(conn => {
            conn.classList.remove('active-flow', 'path-taken', 'path-not-taken');
            conn.removeAttribute('stroke-dasharray');
            conn.setAttribute('stroke', '#2c3e50');
            conn.setAttribute('stroke-width', '2');
            conn.setAttribute('opacity', '1');
        });

        // Remove all path indicators (checkmarks and X marks)
        document.querySelectorAll('.path-indicator').forEach(indicator => indicator.remove());

        // Clear all feedback panels
        document.querySelectorAll('.task-feedback-panel').forEach(panel => panel.remove());
    }

    // AG-UI Streaming Feedback Handlers

    handleTextMessageStart(message) {
        console.log('📝 Text message start:', message.elementId, message.messageId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const messageContainer = document.createElement('div');
        messageContainer.className = 'feedback-message';
        messageContainer.setAttribute('data-message-id', message.messageId);
        messageContainer.innerHTML = '<span class="typing-indicator">●●●</span>';

        panel.appendChild(messageContainer);
        this.showFeedbackIcon(message.elementId);
    }

    handleTextMessageContent(message) {
        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const messageContainer = panel.querySelector(`[data-message-id="${message.messageId}"]`);

        if (messageContainer) {
            // Remove typing indicator if present
            const typingIndicator = messageContainer.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Append delta (new chunk) or replace with full content
            if (message.delta) {
                messageContainer.textContent += message.delta;
            } else {
                messageContainer.textContent = message.content;
            }
        }
    }

    handleTextMessageEnd(message) {
        console.log('✅ Text message complete:', message.elementId, message.messageId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const messageContainer = panel.querySelector(`[data-message-id="${message.messageId}"]`);

        if (messageContainer) {
            // Remove typing indicator
            const typingIndicator = messageContainer.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Mark as complete
            messageContainer.classList.add('complete');
        }
    }

    handleTaskThinking(message) {
        console.log('🤔 Task thinking:', message.elementId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'feedback-thinking';
        thinkingDiv.innerHTML = `
            <span class="thinking-icon">🤔</span>
            <span class="thinking-text">${message.message || 'Thinking...'}</span>
        `;

        panel.appendChild(thinkingDiv);
        this.showFeedbackIcon(message.elementId);

        // Remove thinking indicator after a moment (will be replaced by actual content)
        setTimeout(() => {
            if (thinkingDiv.parentNode) {
                thinkingDiv.remove();
            }
        }, 10000); // Remove after 10s if not replaced
    }

    handleTaskToolStart(message) {
        console.log('🔧 Tool start:', message.elementId, message.toolName);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const toolDiv = document.createElement('div');
        toolDiv.className = 'feedback-tool';
        toolDiv.setAttribute('data-tool', message.toolName);
        toolDiv.innerHTML = `
            <span class="tool-icon">🔧</span>
            <span class="tool-name">${message.toolName}</span>
            <span class="tool-status">Running...</span>
        `;

        panel.appendChild(toolDiv);
        this.showFeedbackIcon(message.elementId);
    }

    handleTaskToolEnd(message) {
        console.log('✅ Tool complete:', message.elementId, message.toolName);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const toolDiv = panel.querySelector(`[data-tool="${message.toolName}"]`);

        if (toolDiv) {
            const statusSpan = toolDiv.querySelector('.tool-status');
            if (statusSpan) {
                statusSpan.textContent = 'Complete';
                statusSpan.classList.add('complete');
            }
        }
    }

    getOrCreateFeedbackPanel(elementId) {
        let panel = document.getElementById(`feedback-panel-${elementId}`);

        if (!panel) {
            panel = document.createElement('div');
            panel.id = `feedback-panel-${elementId}`;
            panel.className = 'task-feedback-panel';
            panel.innerHTML = `
                <div class="feedback-header">
                    <span class="feedback-title">Task Activity</span>
                    <button class="feedback-close" onclick="this.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="feedback-content"></div>
            `;

            // Position near the element
            const element = document.querySelector(`[data-id="${elementId}"]`);
            if (element) {
                const rect = element.getBoundingClientRect();
                panel.style.position = 'fixed';
                panel.style.left = `${rect.right + 20}px`;
                panel.style.top = `${rect.top}px`;
            }

            document.body.appendChild(panel);
        }

        return panel.querySelector('.feedback-content') || panel;
    }

    showFeedbackIcon(elementId) {
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (!element) return;

        // Check if icon already exists
        let icon = element.querySelector('.feedback-icon');
        if (icon) {
            // Pulse the existing icon
            icon.classList.add('pulse');
            setTimeout(() => icon.classList.remove('pulse'), 500);
            return;
        }

        // Create feedback icon
        icon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        icon.setAttribute('class', 'feedback-icon');
        icon.setAttribute('x', '-30');
        icon.setAttribute('y', '-20');
        icon.setAttribute('font-size', '24');
        icon.setAttribute('cursor', 'pointer');
        icon.textContent = '💬';

        // Click to toggle feedback panel
        icon.addEventListener('click', () => {
            const panel = document.getElementById(`feedback-panel-${elementId}`);
            if (panel) {
                panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            }
        });

        element.appendChild(icon);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, message not sent:', message);
        }
    }

    on(messageType, handler) {
        if (!this.handlers[messageType]) {
            this.handlers[messageType] = [];
        }
        this.handlers[messageType].push(handler);
    }

    disconnect() {
        if (this.ws) {
            this.stopPingInterval();
            this.ws.close();
            this.ws = null;
        }
    }
}

// Initialize AG-UI client when DOM is ready
let aguiClient;

document.addEventListener('DOMContentLoaded', () => {
    aguiClient = new AGUIClient();

    // Add connection status indicator to header
    const toolbar = document.querySelector('.toolbar');
    if (toolbar) {
        const statusIndicator = document.createElement('div');
        statusIndicator.id = 'connection-status';
        statusIndicator.className = 'disconnected';
        statusIndicator.textContent = '● Disconnected';
        statusIndicator.style.cssText = 'margin-left: auto; padding: 0.5rem 1rem; font-size: 0.9rem;';
        toolbar.appendChild(statusIndicator);
    }

    // Add Clear Execution button handler
    const clearExecutionBtn = document.getElementById('clearExecutionBtn');
    if (clearExecutionBtn) {
        clearExecutionBtn.addEventListener('click', () => {
            if (aguiClient) {
                aguiClient.clearAllHighlights();
                aguiClient.showNotification('Execution Cleared', 'All execution indicators have been removed', 'info');
            }
        });
    }
});
