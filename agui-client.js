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

        // Track cancellable and cancelled tasks
        this.cancellableTasks = new Set();
        this.cancelledTasks = new Set();

        // Token animation
        this.tokens = new Map(); // elementId -> array of token SVG elements (for parallel flows)
        this.tokenCounter = 0;
        this.tokenJoinWaiting = new Map(); // elementId -> { expected: N, arrived: [{token, timestamp}], timeoutId: timer }
        this.tokenColors = [
            { fill: '#3498db', stroke: '#2980b9', shadow: 'rgba(52, 152, 219, 0.8)', name: 'blue' },
            { fill: '#e74c3c', stroke: '#c0392b', shadow: 'rgba(231, 76, 60, 0.8)', name: 'red' },
            { fill: '#2ecc71', stroke: '#27ae60', shadow: 'rgba(46, 204, 113, 0.8)', name: 'green' },
            { fill: '#f39c12', stroke: '#e67e22', shadow: 'rgba(243, 156, 18, 0.8)', name: 'orange' },
            { fill: '#9b59b6', stroke: '#8e44ad', shadow: 'rgba(155, 89, 182, 0.8)', name: 'purple' },
            { fill: '#1abc9c', stroke: '#16a085', shadow: 'rgba(26, 188, 156, 0.8)', name: 'teal' },
            { fill: '#e91e63', stroke: '#c2185b', shadow: 'rgba(233, 30, 99, 0.8)', name: 'pink' },
            { fill: '#ff9800', stroke: '#f57c00', shadow: 'rgba(255, 152, 0, 0.8)', name: 'amber' }
        ];
        this.deadlockTimeout = 30000; // 30 seconds - if join doesn't complete, it's a deadlock

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

            case 'task.cancellable':
                this.handleTaskCancellable(message);
                break;

            case 'task.cancelling':
                this.handleTaskCancelling(message);
                break;

            case 'task.cancel.failed':
                this.handleTaskCancelFailed(message);
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

            case 'text.message.chunk':
                this.handleTextMessageChunk(message);
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

            case 'messages.snapshot':
                this.handleMessagesSnapshot(message);
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

        // Clear any existing tokens and highlights from previous execution
        console.log('🧹 Clearing previous execution state (tokens, highlights, checkmarks)');
        this.clearAllHighlights();

        // Build notification message with optional file name
        let notificationMsg = message.workflowName;
        if (message.workflowFile) {
            notificationMsg += `\nFile: ${message.workflowFile}`;
        }
        notificationMsg += '\nInstance: ' + message.instanceId.substring(0, 8) + '...';

        this.showNotification('Workflow Started', notificationMsg, 'info');

        // Update header with workflow info
        this.updateWorkflowHeader(message);
    }

    updateWorkflowHeader(message) {
        // Find or create workflow info display in header
        let workflowInfo = document.getElementById('workflow-info');
        if (!workflowInfo) {
            const toolbar = document.querySelector('.toolbar');
            if (toolbar) {
                workflowInfo = document.createElement('div');
                workflowInfo.id = 'workflow-info';
                workflowInfo.style.cssText = `
                    margin-left: 1rem;
                    padding: 0.5rem 1rem;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 4px;
                    font-size: 0.85rem;
                    color: white;
                    max-width: 400px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                `;
                toolbar.appendChild(workflowInfo);
            }
        }

        if (workflowInfo) {
            let displayText = message.workflowName;
            if (message.workflowFile) {
                // Show just the filename, not full path
                const fileName = message.workflowFile.split('/').pop();
                displayText = `📄 ${fileName}`;
            }
            workflowInfo.textContent = displayText;
            workflowInfo.title = `Workflow: ${message.workflowName}\n${message.workflowFile ? 'File: ' + message.workflowFile + '\n' : ''}Instance: ${message.instanceId}`;
        }
    }

    handleWorkflowCompleted(message) {
        console.log('✅ Workflow completed:', message.outcome);

        const outcomeEmoji = message.outcome === 'success' ? '✅' : '❌';
        const outcomeClass = message.outcome === 'success' ? 'success' : 'error';

        // Wait 2 seconds before marking skipped paths to allow tokens to finish animating
        setTimeout(() => {
            // After workflow completes, mark any elements on not-taken paths as skipped
            this.markNotTakenPathsAsSkipped();

            // Mark end events with outcome color
            this.markEndEventsWithOutcome(message.outcome);
        }, 2000); // Delay to allow final token animations to complete

        this.showNotification(
            `Workflow ${message.outcome}`,
            `Completed in ${message.duration.toFixed(2)}s - Click "Clear Execution" to reset`,
            outcomeClass
        );

        // Don't auto-clear - preserve final state for review
        // User can manually clear using the "Clear Execution" button
    }

    markEndEventsWithOutcome(outcome) {
        console.log(`🎯 Marking end events with outcome: ${outcome}`);

        // Find all end events that were COMPLETED (not just all end events)
        const allElements = document.querySelectorAll('.bpmn-element[data-id]');

        let endEventCount = 0;
        allElements.forEach(element => {
            // Check if this is an end event by looking for the thick border circle
            // End events have a circle with stroke-width="4" and class="bpmn-event"
            const circle = element.querySelector('circle.bpmn-event[stroke-width="4"]');

            if (circle) {
                const elementId = element.getAttribute('data-id');

                // Only color this end event if it was actually completed (reached)
                if (element.classList.contains('completed')) {
                    endEventCount++;
                    console.log(`  Found COMPLETED end event: ${elementId}`);

                    // Remove any existing outcome classes
                    circle.classList.remove('outcome-success', 'outcome-failure');

                    // Add outcome class based on result
                    if (outcome === 'success') {
                        circle.classList.add('outcome-success');
                        console.log(`  ✅ Added success class to ${elementId}`);
                    } else {
                        circle.classList.add('outcome-failure');
                        console.log(`  ❌ Added failure class to ${elementId}`);
                    }
                } else {
                    console.log(`  Skipping end event ${elementId} (not completed)`);
                }
            }
        });

        console.log(`🎯 Marked ${endEventCount} completed end event(s)`);
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
            // Track visited elements to prevent infinite loops
            const visited = new Set();

            notTakenFlowIds.forEach(flowId => {
                const connection = modeler.connections.find(c => c.id === flowId);
                if (connection) {
                    console.log(`  Connection ${flowId}: from ${connection.from} to ${connection.to}`);
                    // Recursively mark all elements starting from the target
                    this.markElementAndDownstreamAsSkippedUsingModel(connection.to, visited);
                }
            });
        } else {
            console.warn('⚠️ Modeler not available, falling back to DOM-based marking');
            notTakenFlows.forEach(flow => {
                this.markPathElementsAsSkipped(flow);
            });
        }
    }

    markElementAndDownstreamAsSkippedUsingModel(elementId, visited = new Set()) {
        // Prevent infinite loops from circular connections
        if (visited.has(elementId)) {
            console.log(`  ⚠️ Already visited ${elementId}, skipping to prevent loop`);
            return;
        }

        console.log(`  📍 Marking element ${elementId} as skipped`);

        // Add to visited set
        visited.add(elementId);

        // Mark this element as skipped
        this.markElementSkipped(elementId);

        // Find all outgoing connections from this element using the model
        if (typeof modeler !== 'undefined' && modeler.connections) {
            const outgoingConnections = modeler.connections.filter(c => c.from === elementId);

            console.log(`    Found ${outgoingConnections.length} outgoing connections from ${elementId}`);

            outgoingConnections.forEach(conn => {
                console.log(`    Following connection ${conn.id} to ${conn.to}`);
                // Recursively mark downstream elements (pass visited set)
                this.markElementAndDownstreamAsSkippedUsingModel(conn.to, visited);
            });
        }
    }

    // ===== TOKEN ANIMATION =====

    createToken(elementId, offsetIndex = 0, colorIndex = 0) {
        console.log(`    🔵 createToken called: elementId=${elementId}, offsetIndex=${offsetIndex}, colorIndex=${colorIndex}`);
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (!element) {
            console.warn(`    ❌ createToken: Element ${elementId} not found in DOM`);
            return null;
        }

        // DEBUG: Log element classes
        console.log(`    🔍 Element classes: "${element.getAttribute('class')}"`);
        console.log(`    🔍 Has subprocess-child-element class: ${element.classList.contains('subprocess-child-element')}`);

        // Get element position from its transform attribute
        const transform = element.getAttribute('transform');
        let x = 0, y = 0;
        if (transform) {
            const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
            if (match) {
                x = parseFloat(match[1]);
                y = parseFloat(match[2]);
            }
        }

        console.log(`    🔍 Initial position from transform: (${x}, ${y})`);

        // Check if this is a subprocess child element (has relative coordinates)
        // If so, add the parent subprocess position to get absolute coordinates
        if (element.classList.contains('subprocess-child-element')) {
            console.log(`    🔍 IS a subprocess child element - looking for parent...`);

            // Find the parent subprocess element
            // DOM structure: <g class="bpmn-element" transform="..."> <g> <g class="subprocess-children"> <g class="subprocess-child-element">
            // We need to go from subprocess-children -> parent <g> -> parent <g class="bpmn-element">
            const subprocessChildrenGroup = element.closest('.subprocess-children');
            console.log(`    🔍 subprocessChildrenGroup found: ${subprocessChildrenGroup !== null}`);

            if (subprocessChildrenGroup) {
                const shapeGroup = subprocessChildrenGroup.parentElement;  // The <g> from createShape()
                console.log(`    🔍 shapeGroup (first parent) found: ${shapeGroup !== null}`);
                console.log(`    🔍 shapeGroup id: ${shapeGroup?.getAttribute('data-id')}`);

                if (shapeGroup) {
                    // Go up one more level to get the bpmn-element group with the transform
                    const subprocessGroup = shapeGroup.parentElement;
                    console.log(`    🔍 subprocessGroup (second parent - bpmn-element) found: ${subprocessGroup !== null}`);
                    console.log(`    🔍 subprocessGroup class: "${subprocessGroup?.getAttribute('class')}"`);
                    console.log(`    🔍 subprocessGroup id: ${subprocessGroup?.getAttribute('data-id')}`);

                    const parentTransform = subprocessGroup?.getAttribute('transform');
                    console.log(`    🔍 Parent transform: "${parentTransform}"`);

                    if (parentTransform) {
                        const parentMatch = parentTransform.match(/translate\(([^,]+),\s*([^)]+)\)/);
                        if (parentMatch) {
                            const parentX = parseFloat(parentMatch[1]);
                            const parentY = parseFloat(parentMatch[2]);
                            console.log(`    📍 Child element detected - parent subprocess at (${parentX}, ${parentY})`);
                            console.log(`    📍 Adding parent position: (${x}, ${y}) + (${parentX}, ${parentY})`);
                            x += parentX;
                            y += parentY;
                            console.log(`    📍 New absolute position: (${x}, ${y})`);
                        } else {
                            console.warn(`    ❌ Parent transform doesn't match expected pattern`);
                        }
                    } else {
                        console.warn(`    ❌ Parent has no transform attribute`);
                    }
                } else {
                    console.warn(`    ❌ subprocessChildrenGroup has no parent element`);
                }
            } else {
                console.warn(`    ❌ Could not find .subprocess-children parent group`);
            }
        } else {
            console.log(`    🔍 NOT a subprocess child element - using position as-is`);
        }

        // Apply offset for multiple tokens (spread them out)
        const offset = offsetIndex * 12; // 12px spacing between tokens
        x += offset;

        console.log(`    🔍 Final token position (with offset): (${x}, ${y})`);
        console.log(`    🔍 Creating token at this position...`);

        // Get color for this token
        const color = this.tokenColors[colorIndex % this.tokenColors.length];

        // Create token as a group with transform (so it moves with canvas zoom/pan)
        const tokenId = `token-${this.tokenCounter++}`;
        const tokenGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        tokenGroup.setAttribute('id', tokenId);
        tokenGroup.setAttribute('class', 'bpmn-token-group');
        tokenGroup.setAttribute('transform', `translate(${x}, ${y})`);
        tokenGroup.setAttribute('data-element-id', elementId); // Track which element this token belongs to

        // Create token circle (at 0,0 within the group)
        const token = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        token.setAttribute('class', 'bpmn-token');
        token.setAttribute('data-token-color', color.name);
        token.setAttribute('cx', 0);
        token.setAttribute('cy', 0);
        token.setAttribute('r', '10'); // Increased from 8 to 10 for better visibility
        token.setAttribute('fill', color.fill);
        token.setAttribute('stroke', color.stroke);
        token.setAttribute('stroke-width', '3'); // Increased from 2 to 3 for better visibility
        token.setAttribute('opacity', '1'); // Full opacity for better visibility

        // Add glow effect with stronger shadow
        token.style.filter = `drop-shadow(0 0 8px ${color.shadow})`;

        // Append circle to token group
        tokenGroup.appendChild(token);

        // Add to tokens layer (or create if doesn't exist)
        let tokensLayer = document.getElementById('tokensLayer');
        if (!tokensLayer) {
            // IMPORTANT: Append to mainGroup, not root SVG, so tokens zoom/pan with canvas
            const mainGroup = document.getElementById('mainGroup');
            if (mainGroup) {
                tokensLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                tokensLayer.setAttribute('id', 'tokensLayer');
                tokensLayer.setAttribute('style', 'pointer-events: none;'); // Tokens don't block mouse events
                mainGroup.appendChild(tokensLayer); // Append as LAST child of mainGroup (renders on top)
                console.log(`    ✅ Created tokensLayer and appended to mainGroup (will render on top of all elements)`);
            } else {
                console.error(`    ❌ mainGroup not found - cannot create tokensLayer!`);
            }
        }

        if (tokensLayer) {
            tokensLayer.appendChild(tokenGroup); // Append the group (which contains the circle)
            console.log(`    ✅ Token group appended to tokensLayer`);

            // Verify tokensLayer is inside mainGroup (critical for zoom/pan to work)
            const parent = tokensLayer.parentElement;
            if (parent && parent.id === 'mainGroup') {
                console.log(`    ✅ tokensLayer correctly inside mainGroup (will transform with canvas)`);
            } else {
                console.error(`    ❌ WARNING: tokensLayer parent is "${parent?.id}" not "mainGroup" - tokens won't pan/zoom correctly!`);
            }
        } else {
            console.warn(`    ❌ tokensLayer not found - token NOT added to DOM!`);
        }

        // Store token GROUP in array for this element
        if (!this.tokens.has(elementId)) {
            this.tokens.set(elementId, []);
        }
        this.tokens.get(elementId).push(tokenGroup); // Store the group, not just the circle

        const colorEmoji = this.getColorEmoji(color.name);
        console.log(`    ${colorEmoji} ${color.name.toUpperCase()} token created at element: ${elementId} (${this.tokens.get(elementId).length} total)`);
        console.log(`    Token position: transform=${tokenGroup.getAttribute('transform')}, r=${token.getAttribute('r')}`);
        console.log(`    Token visible in DOM:`, tokenGroup.parentElement !== null);
        return tokenGroup; // Return the group instead of just the circle
    }

    getColorEmoji(colorName) {
        const emojiMap = {
            'blue': '🔵',
            'red': '🔴',
            'green': '🟢',
            'orange': '🟠',
            'purple': '🟣',
            'teal': '🔵',
            'pink': '🩷',
            'amber': '🟡'
        };
        return emojiMap[colorName] || '⚪';
    }

    moveToken(fromElementId, toElementId, specificToken = null, onComplete = null) {
        const fromElement = document.querySelector(`[data-id="${fromElementId}"]`);
        const toElement = document.querySelector(`[data-id="${toElementId}"]`);

        if (!fromElement || !toElement) {
            console.warn(`Cannot move token: element not found (from: ${fromElementId}, to: ${toElementId})`);
            if (onComplete) onComplete();
            return;
        }

        // Get positions
        const fromPos = this.getElementPosition(fromElement);
        const toPos = this.getElementPosition(toElement);

        console.log(`🔵 moveToken: from ${fromElementId} at (${fromPos.x}, ${fromPos.y}) to ${toElementId} at (${toPos.x}, ${toPos.y})`);

        // Get token to move
        let token = specificToken;
        if (!token) {
            const tokensAtElement = this.tokens.get(fromElementId);
            if (!tokensAtElement || tokensAtElement.length === 0) {
                console.log(`    ⚠️ No token found at ${fromElementId}, creating new token`);
                token = this.createToken(fromElementId);
            } else {
                console.log(`    ✅ Found existing token at ${fromElementId} (${tokensAtElement.length} total)`);
                // Take the first token from the array
                token = tokensAtElement[0];
            }
        } else {
            console.log(`    ✅ Using specific token provided`);
        }

        if (!token) {
            console.warn(`    ❌ Failed to get or create token for ${fromElementId}`);
            if (onComplete) onComplete();
            return;
        }

        console.log(`🔵 Animating token movement from ${fromElementId} to ${toElementId}`);

        // Animate token movement
        const duration = 800; // ms
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Easing function (ease-in-out)
            const eased = progress < 0.5
                ? 2 * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;

            // Interpolate position
            const x = fromPos.x + (toPos.x - fromPos.x) * eased;
            const y = fromPos.y + (toPos.y - fromPos.y) * eased;

            // Update token group's transform instead of cx/cy
            token.setAttribute('transform', `translate(${x}, ${y})`);
            // Also update data attribute so we can track position
            token.setAttribute('data-element-id', toElementId);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                // Animation complete - update token association
                // Remove from source
                const fromTokens = this.tokens.get(fromElementId);
                if (fromTokens) {
                    const index = fromTokens.indexOf(token);
                    if (index > -1) {
                        fromTokens.splice(index, 1);
                    }
                    if (fromTokens.length === 0) {
                        this.tokens.delete(fromElementId);
                    }
                }

                // Add to destination
                if (!this.tokens.has(toElementId)) {
                    this.tokens.set(toElementId, []);
                }
                this.tokens.get(toElementId).push(token);

                console.log(`🔵 Token arrived at ${toElementId}`);
                if (onComplete) onComplete();
            }
        };

        requestAnimationFrame(animate);
    }

    removeToken(elementId, specificToken = null) {
        const tokensAtElement = this.tokens.get(elementId);
        if (!tokensAtElement || tokensAtElement.length === 0) return;

        if (specificToken) {
            // Remove specific token
            const index = tokensAtElement.indexOf(specificToken);
            if (index > -1) {
                tokensAtElement.splice(index, 1);
                specificToken.style.transition = 'opacity 0.3s';
                specificToken.setAttribute('opacity', '0');
                setTimeout(() => {
                    specificToken.remove();
                    console.log(`🔵 Token removed from ${elementId} (${tokensAtElement.length} remaining)`);
                }, 300);
            }
            if (tokensAtElement.length === 0) {
                this.tokens.delete(elementId);
            }
        } else {
            // Remove all tokens at this element
            tokensAtElement.forEach(token => {
                token.style.transition = 'opacity 0.3s';
                token.setAttribute('opacity', '0');
                setTimeout(() => {
                    token.remove();
                }, 300);
            });
            this.tokens.delete(elementId);
            console.log(`🔵 All tokens removed from ${elementId}`);
        }
    }

    removeAllTokens() {
        this.tokens.forEach((tokensArray, elementId) => {
            tokensArray.forEach(token => {
                token.remove();
            });
        });
        this.tokens.clear();

        // Also remove the tokensLayer container itself so it's recreated fresh on next execution
        const tokensLayer = document.getElementById('tokensLayer');
        if (tokensLayer) {
            tokensLayer.remove();
            console.log('🔵 All tokens removed and tokensLayer cleared');
        } else {
            console.log('🔵 All tokens removed');
        }
    }

    getElementPosition(element) {
        const transform = element.getAttribute('transform');
        let x = 0, y = 0;
        if (transform) {
            const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
            if (match) {
                x = parseFloat(match[1]);
                y = parseFloat(match[2]);
            }
        }

        // Check if this is a subprocess child element (has relative coordinates)
        if (element.classList.contains('subprocess-child-element')) {
            // DOM structure: <g class="bpmn-element" transform="..."> <g> <g class="subprocess-children"> <g class="subprocess-child-element">
            // We need to go from subprocess-children -> parent <g> -> parent <g class="bpmn-element">
            const subprocessChildrenGroup = element.closest('.subprocess-children');
            if (subprocessChildrenGroup) {
                const shapeGroup = subprocessChildrenGroup.parentElement;  // The <g> from createShape()
                if (shapeGroup) {
                    // Go up one more level to get the bpmn-element group with the transform
                    const subprocessGroup = shapeGroup.parentElement;
                    if (subprocessGroup) {
                        const parentTransform = subprocessGroup.getAttribute('transform');
                        if (parentTransform) {
                            const parentMatch = parentTransform.match(/translate\(([^,]+),\s*([^)]+)\)/);
                            if (parentMatch) {
                                x += parseFloat(parentMatch[1]);
                                y += parseFloat(parentMatch[2]);
                            }
                        }
                    }
                }
            }
        }

        return { x, y };
    }

    // ===== ELEMENT HIGHLIGHTING =====

    highlightElement(elementId) {
        console.log(`🔵 highlightElement called for: ${elementId}`);

        // Remove previous highlights
        document.querySelectorAll('.bpmn-element.active').forEach(el => {
            el.classList.remove('active');
        });

        // Highlight current element
        const element = document.querySelector(`[data-id="${elementId}"]`);
        if (element) {
            console.log(`  ✅ Found element in DOM: ${elementId}`);
            element.classList.add('active');

            // Scroll into view
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            // Element not found in DOM - likely a subprocess internal element
            console.log(`  ℹ️ Element ${elementId} not in DOM (likely subprocess internal element - skipping token)`);
            return; // Don't try to create token for elements that aren't rendered
        }

        // Only create token at START events - other elements receive tokens via moveToken()
        // Check if this element's type indicates it's a start event
        const isStartEvent = element.querySelector('circle[stroke-width="2"]') !== null &&
                            !element.querySelector('circle[stroke-width="4"]'); // Not an end event

        const tokensAtElement = this.tokens.get(elementId);
        if (!tokensAtElement || tokensAtElement.length === 0) {
            // Only create tokens for start events (workflow entry points)
            // Other elements will receive tokens via moveToken() from previous elements
            if (isStartEvent) {
                console.log(`  🎯 Creating token for START event ${elementId} (no existing tokens)`);
                const token = this.createToken(elementId);
                if (token) {
                    console.log(`  ✅ Token created successfully`);
                } else {
                    console.warn(`  ❌ Token creation FAILED`);
                }
            } else {
                console.log(`  ℹ️ No tokens yet at ${elementId}, but not a start event - will receive token from previous element`);
            }
        } else {
            console.log(`  ℹ️ Element already has ${tokensAtElement.length} token(s), not creating new one`);
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

            // Find next element(s) and move token
            this.moveTokenToNextElements(elementId);
        } else {
            // Element not in DOM (subprocess internal element)
            console.log(`  ℹ️ Element ${elementId} not in DOM (subprocess internal - skipping completion mark)`);
            // Still try to move tokens in case this is a valid element
            this.moveTokenToNextElements(elementId);
        }

        // Remove cancel button from feedback panel since task has completed
        this.removeCancelButton(elementId);

        // Mark task as no longer cancellable
        this.cancellableTasks.delete(elementId);
    }

    isCompensationTask(element) {
        /**
         * Check if an element is a compensation task.
         * Compensation tasks are identified by:
         * 1. Having an incoming flow from a compensation boundary event
         * 2. Typically in a compensation/rollback swimlane
         * 3. No outgoing flows (they are terminal within the compensation flow)
         */
        if (!element || !modeler || !modeler.connections) {
            return false;
        }

        // Find incoming connections
        const incomingConnections = modeler.connections.filter(c => c.to === element.id);

        // Check if any incoming connection is from a compensation boundary event
        for (const conn of incomingConnections) {
            const sourceElement = modeler.elements.find(e => e.id === conn.from);
            if (sourceElement && sourceElement.type === 'compensationBoundaryEvent') {
                return true;
            }
        }

        return false;
    }

    moveTokenToNextElements(elementId) {
        // Find outgoing connections from this element
        if (typeof modeler !== 'undefined' && modeler.connections) {
            let outgoingConnections = modeler.connections.filter(c => c.from === elementId);

            // If no connections found, check Event Sub-Process child connections
            if (outgoingConnections.length === 0) {
                console.log(`🔍 No main connections found for ${elementId}, checking Event Sub-Processes`);
                // Search all Event Sub-Processes for this element
                const eventSubProcesses = modeler.elements.filter(e =>
                    e.type === 'eventSubProcess' && e.childConnections
                );
                console.log(`🔍 Found ${eventSubProcesses.length} Event Sub-Process(es) with childConnections`);
                for (const subprocess of eventSubProcesses) {
                    console.log(`  📋 ESP "${subprocess.name}" has ${subprocess.childConnections.length} child connections`);
                    console.log(`  📋 Child connections:`, subprocess.childConnections.map(c => `${c.from} -> ${c.to}`));
                    const childConnections = subprocess.childConnections.filter(c => c.from === elementId);
                    console.log(`  📋 Filtered childConnections for ${elementId}:`, childConnections);
                    if (childConnections.length > 0) {
                        outgoingConnections = childConnections;
                        console.log(`🔵 Found ${childConnections.length} child connections in Event Sub-Process for ${elementId}`);
                        break;
                    }
                }
                if (outgoingConnections.length === 0) {
                    console.log(`❌ No childConnections found for ${elementId} in any Event Sub-Process`);
                }
            }

            if (outgoingConnections.length === 0) {
                // No outgoing connections
                // Check if this is a compensation task - if so, keep the token visible
                const element = modeler.elements.find(e => e.id === elementId);
                const isCompensationTask = element && this.isCompensationTask(element);

                if (isCompensationTask) {
                    console.log(`🔄 Compensation task ${elementId} completed - keeping token visible`);
                    // Keep token visible on completed compensation task
                    // Don't remove it - this shows the compensation was executed
                } else {
                    // End event or other terminal element - remove token
                    this.removeToken(elementId);
                }
            } else if (outgoingConnections.length === 1) {
                // Single path - move token to next element
                const nextElementId = outgoingConnections[0].to;

                // Check if next element is a parallel gateway join
                const nextElement = modeler.elements.find(e => e.id === nextElementId);
                if (nextElement && nextElement.type === 'parallelGateway') {
                    const incomingToNext = modeler.connections.filter(c => c.to === nextElementId);
                    if (incomingToNext.length > 1) {
                        // This is a join - handle synchronization
                        this.handleParallelGatewayJoin(elementId, nextElementId, outgoingConnections[0]);
                        return;
                    }
                }

                // Normal move
                this.moveToken(elementId, nextElementId);
            } else {
                // Multiple paths - check if this is a parallel gateway
                const element = modeler.elements.find(e => e.id === elementId);

                if (element && element.type === 'parallelGateway') {
                    // Check if this is a join or fork by counting incoming connections
                    const incomingConnections = modeler.connections.filter(c => c.to === elementId);

                    if (incomingConnections.length > 1) {
                        // This is a JOIN - tokens should have already merged
                        // Just move the merged token forward
                        this.moveToken(elementId, outgoingConnections[0].to);
                    } else {
                        // This is a FORK - create multiple tokens with different colors
                        console.log(`🔵 Parallel gateway FORK ${elementId} - creating ${outgoingConnections.length} tokens`);

                        const tokensAtElement = this.tokens.get(elementId);
                        if (tokensAtElement && tokensAtElement.length > 0) {
                            // Take one token and clone it for each outgoing path
                            const sourceToken = tokensAtElement[0];

                            outgoingConnections.forEach((conn, index) => {
                                if (index === 0) {
                                    // Keep the original token blue (color index 0)
                                    this.moveToken(elementId, conn.to, sourceToken);
                                } else {
                                    // Create new tokens with different colors for each parallel path
                                    const newToken = this.createToken(elementId, index, index);
                                    if (newToken) {
                                        this.moveToken(elementId, conn.to, newToken);
                                    }
                                }
                            });
                        }
                    }
                } else {
                    // Exclusive or inclusive gateway - will be handled by gateway.path_taken event
                    console.log(`🔵 Gateway ${elementId} has ${outgoingConnections.length} outgoing paths - waiting for gateway decision`);
                }
            }
        }
    }

    handleParallelGatewayJoin(fromElementId, joinGatewayId, connection) {
        // Initialize join tracking if not exists
        if (!this.tokenJoinWaiting.has(joinGatewayId)) {
            const incomingConnections = modeler.connections.filter(c => c.to === joinGatewayId);
            this.tokenJoinWaiting.set(joinGatewayId, {
                expected: incomingConnections.length,
                arrived: [],
                startTime: Date.now(),
                timeoutId: null
            });

            // Start deadlock detection timer
            const joinInfo = this.tokenJoinWaiting.get(joinGatewayId);
            joinInfo.timeoutId = setTimeout(() => {
                this.detectDeadlock(joinGatewayId);
            }, this.deadlockTimeout);
        }

        const joinInfo = this.tokenJoinWaiting.get(joinGatewayId);
        const arrivalIndex = joinInfo.arrived.length + 1;

        console.log(`🔵 Token arriving at parallel gateway JOIN: ${joinGatewayId} from ${fromElementId} (arrival #${arrivalIndex})`);

        // Move token to the join gateway
        this.moveToken(fromElementId, joinGatewayId, null, () => {
            // After token arrives, record it with timestamp
            const tokensAtJoin = this.tokens.get(joinGatewayId);
            if (tokensAtJoin && tokensAtJoin.length > 0) {
                const arrivedToken = tokensAtJoin[tokensAtJoin.length - 1]; // The most recently arrived
                const colorName = arrivedToken.getAttribute('data-token-color');
                const emoji = this.getColorEmoji(colorName);

                joinInfo.arrived.push({
                    token: arrivedToken,
                    timestamp: Date.now(),
                    color: colorName,
                    from: fromElementId
                });

                console.log(`${emoji} ${colorName.toUpperCase()} token arrived at JOIN (${joinInfo.arrived.length}/${joinInfo.expected})`);
            }

            // Check if all incoming tokens have arrived
            this.checkParallelGatewayJoinComplete(joinGatewayId);
        });
    }

    checkParallelGatewayJoinComplete(joinGatewayId) {
        if (typeof modeler !== 'undefined' && modeler.connections) {
            const joinInfo = this.tokenJoinWaiting.get(joinGatewayId);
            if (!joinInfo) return;

            const tokensAtJoin = this.tokens.get(joinGatewayId);
            const tokenCount = tokensAtJoin ? tokensAtJoin.length : 0;

            console.log(`🔵 Parallel gateway JOIN ${joinGatewayId}: ${tokenCount}/${joinInfo.expected} tokens arrived`);

            if (tokenCount >= joinInfo.expected) {
                // All tokens have arrived - show arrival order and merge
                console.log(`✅ All tokens arrived at JOIN ${joinGatewayId} - merging`);
                console.log('📊 Arrival order:');
                joinInfo.arrived.forEach((arrival, index) => {
                    const emoji = this.getColorEmoji(arrival.color);
                    console.log(`  ${index + 1}. ${emoji} ${arrival.color.toUpperCase()} token (from ${arrival.from})`);
                });

                // Keep the first-arrived token, remove the rest
                const firstToken = joinInfo.arrived[0].token;
                const firstColor = joinInfo.arrived[0].color;
                const firstEmoji = this.getColorEmoji(firstColor);

                console.log(`🏆 Keeping ${firstEmoji} ${firstColor.toUpperCase()} token (arrived first), merging others`);

                // Remove all tokens except the first one
                tokensAtJoin.forEach(token => {
                    if (token !== firstToken) {
                        token.style.transition = 'opacity 0.3s';
                        token.setAttribute('opacity', '0');
                        setTimeout(() => {
                            token.remove();
                            const index = tokensAtJoin.indexOf(token);
                            if (index > -1) {
                                tokensAtJoin.splice(index, 1);
                            }
                        }, 300);
                    }
                });

                // Clear deadlock timer
                if (joinInfo.timeoutId) {
                    clearTimeout(joinInfo.timeoutId);
                }

                // Clear join tracking
                this.tokenJoinWaiting.delete(joinGatewayId);

                // The join gateway will complete and trigger moveTokenToNextElements
            }
        }
    }

    detectDeadlock(joinGatewayId) {
        const joinInfo = this.tokenJoinWaiting.get(joinGatewayId);
        if (!joinInfo) return;

        const waitTime = Date.now() - joinInfo.startTime;
        const arrivedCount = joinInfo.arrived.length;
        const expectedCount = joinInfo.expected;
        const missingCount = expectedCount - arrivedCount;

        console.error('');
        console.error('🚨 ═══════════════════════════════════════════════════════');
        console.error('🚨 DEADLOCK DETECTED!');
        console.error('🚨 ═══════════════════════════════════════════════════════');
        console.error(`Gateway: ${joinGatewayId}`);
        console.error(`Wait time: ${(waitTime / 1000).toFixed(1)}s`);
        console.error(`Tokens arrived: ${arrivedCount}/${expectedCount}`);
        console.error(`Missing tokens: ${missingCount}`);
        console.error('');

        if (arrivedCount > 0) {
            console.error('✅ Tokens that arrived:');
            joinInfo.arrived.forEach((arrival, index) => {
                const emoji = this.getColorEmoji(arrival.color);
                const timeSinceArrival = Date.now() - arrival.timestamp;
                console.error(`  ${index + 1}. ${emoji} ${arrival.color.toUpperCase()} token (from ${arrival.from}) - arrived ${(timeSinceArrival / 1000).toFixed(1)}s ago`);
            });
        }

        console.error('');
        console.error('❌ Missing token paths (never arrived):');
        const incomingConnections = modeler.connections.filter(c => c.to === joinGatewayId);
        const arrivedFromIds = new Set(joinInfo.arrived.map(a => a.from));
        incomingConnections.forEach(conn => {
            if (!arrivedFromIds.has(conn.from)) {
                console.error(`  ⚠️  Path from ${conn.from} - token never arrived`);
            }
        });

        console.error('');
        console.error('💡 Possible causes:');
        console.error('  • One or more parallel paths threw an exception');
        console.error('  • A path diverted to error handling and never reached join');
        console.error('  • A path contains an infinite loop or is still running');
        console.error('  • Incorrect workflow design - unbalanced fork/join');
        console.error('🚨 ═══════════════════════════════════════════════════════');
        console.error('');

        // Mark gateway as deadlocked visually
        this.markGatewayAsDeadlocked(joinGatewayId, joinInfo);

        // Show notification
        this.showNotification(
            '⚠️ Deadlock Detected',
            `Gateway ${joinGatewayId} is waiting for ${missingCount} more token(s) but they will never arrive. Check console for details.`,
            'error'
        );
    }

    markGatewayAsDeadlocked(joinGatewayId, joinInfo) {
        const gateway = document.querySelector(`[data-id="${joinGatewayId}"]`);
        if (!gateway) return;

        // Add deadlock class
        gateway.classList.add('deadlocked');

        // Add pulsing red border
        const diamond = gateway.querySelector('rect');
        if (diamond) {
            diamond.setAttribute('stroke', '#e74c3c');
            diamond.setAttribute('stroke-width', '4');
            diamond.style.animation = 'deadlockPulse 1s ease-in-out infinite';
        }

        // Add warning icon
        const warningIcon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        warningIcon.setAttribute('class', 'deadlock-warning');
        warningIcon.setAttribute('x', '0');
        warningIcon.setAttribute('y', '-30');
        warningIcon.setAttribute('font-size', '24');
        warningIcon.setAttribute('fill', '#e74c3c');
        warningIcon.setAttribute('text-anchor', 'middle');
        warningIcon.textContent = '⚠️';
        gateway.appendChild(warningIcon);

        // Add status text
        const statusText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        statusText.setAttribute('class', 'deadlock-status');
        statusText.setAttribute('x', '0');
        statusText.setAttribute('y', '40');
        statusText.setAttribute('font-size', '10');
        statusText.setAttribute('fill', '#e74c3c');
        statusText.setAttribute('text-anchor', 'middle');
        statusText.setAttribute('font-weight', 'bold');
        statusText.textContent = `DEADLOCK (${joinInfo.arrived.length}/${joinInfo.expected})`;
        gateway.appendChild(statusText);

        console.log(`🚨 Gateway ${joinGatewayId} marked as DEADLOCKED`);
    }

    removeCancelButton(elementId) {
        const panel = document.getElementById(`feedback-panel-${elementId}`);
        if (panel) {
            const contentDiv = panel.querySelector('.feedback-content');
            if (contentDiv) {
                const cancelBtn = contentDiv.querySelector('.cancel-task-btn');
                if (cancelBtn) {
                    console.log(`🗑️ Removing cancel button for completed task: ${elementId}`);
                    cancelBtn.remove();
                }
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
        console.log('🚫🚫🚫 handleTaskCancelled called 🚫🚫🚫');
        console.log('   Message:', JSON.stringify(message, null, 2));
        console.log('   Element ID:', message.elementId);
        console.log('   Element ID type:', typeof message.elementId);
        console.log('   Reason:', message.reason);

        // Find and close the approval modal for this task
        const selector = `.approval-modal[data-task-id="${message.elementId}"]`;
        console.log('   Looking for modal with selector:', selector);

        // Get all modals and log their task IDs
        const allModals = document.querySelectorAll('.approval-modal');
        console.log('   All modals in DOM:', allModals.length);
        allModals.forEach((m, i) => {
            console.log(`     Modal ${i}: data-task-id="${m.getAttribute('data-task-id')}"`);
        });

        const modal = document.querySelector(selector);
        console.log('   Modal found:', modal ? 'YES' : 'NO');

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
            console.log('   Trying to find modal another way...');

            // Try to find by checking each modal's task ID
            let foundModal = null;
            allModals.forEach(m => {
                const taskId = m.getAttribute('data-task-id');
                console.log(`   Comparing "${taskId}" === "${message.elementId}": ${taskId === message.elementId}`);
                if (taskId === message.elementId) {
                    foundModal = m;
                }
            });

            if (foundModal) {
                console.log('✅ Found modal via iteration!');
                foundModal.style.opacity = '0';
                foundModal.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => foundModal.remove(), 300);

                this.showNotification(
                    'Approval Cancelled',
                    message.reason || 'Another approval path completed first',
                    'info'
                );
            } else {
                console.log('❌ Still could not find modal');
            }
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

            // Move token along the chosen path
            if (typeof modeler !== 'undefined' && modeler.connections) {
                const connection = modeler.connections.find(c => c.id === flowId);
                if (connection) {
                    console.log(`🔵 Gateway chose path: ${flowId} from ${connection.from} to ${connection.to}`);
                    this.moveToken(connection.from, connection.to);
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

        // Reset end event colors to default by removing outcome classes
        document.querySelectorAll('.bpmn-element[data-id]').forEach(element => {
            const circle = element.querySelector('circle.bpmn-event[stroke-width="4"]');
            if (circle) {
                // Remove outcome classes to reset to default CSS colors
                circle.classList.remove('outcome-success', 'outcome-failure');
            }
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

        // Remove all tokens
        this.removeAllTokens();

        // Clear all feedback panels
        document.querySelectorAll('.task-feedback-panel').forEach(panel => panel.remove());

        // Clear all feedback icons
        document.querySelectorAll('.feedback-icon').forEach(icon => icon.remove());

        // Clear workflow info from header
        const workflowInfo = document.getElementById('workflow-info');
        if (workflowInfo) {
            workflowInfo.remove();
        }

        // Request backend to clear history (AG-UI checkpointing)
        this.send({
            type: 'clear.history',
            timestamp: new Date().toISOString()
        });
        console.log('🗑️ Requested backend to clear history');
    }

    // AG-UI Streaming Feedback Handlers

    handleTextMessageStart(message) {
        console.log('📝 Text message start:', message.elementId, message.messageId);
        console.log('   Full message:', JSON.stringify(message, null, 2));
        console.log('');
        console.log('═══════════════════════════════════════════════════════');
        console.log('📝 LLM TEXT MESSAGE START');
        console.log('═══════════════════════════════════════════════════════');
        console.log('Element ID:', message.elementId);
        console.log('Message ID:', message.messageId);
        console.log('Thread ID:', message.threadId);
        console.log('Role:', message.role);
        console.log('═══════════════════════════════════════════════════════');
        console.log('');

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        console.log('   Panel found:', panel ? 'YES' : 'NO', panel?.id);

        // Create a new event item in the timeline
        const eventItem = document.createElement('div');
        eventItem.className = 'feedback-event-item';
        eventItem.setAttribute('data-message-id', message.messageId);

        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'event-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        eventItem.appendChild(timestamp);

        // Add event header
        const header = document.createElement('div');
        header.className = 'event-header';
        header.innerHTML = '<span class="event-icon">💬</span><span class="event-title">LLM Response</span>';
        eventItem.appendChild(header);

        // Add message container (for streaming content)
        const messageContainer = document.createElement('div');
        messageContainer.className = 'feedback-message streaming';
        messageContainer.setAttribute('data-message-id', message.messageId);
        messageContainer.innerHTML = '<span class="typing-indicator">●●●</span>';
        eventItem.appendChild(messageContainer);

        panel.appendChild(eventItem);
        console.log('   Event item appended to panel. Panel children count:', panel.children.length);
        console.log('   Event item HTML:', eventItem.outerHTML.substring(0, 200));
        console.log(`   Panel scrollHeight: ${panel.scrollHeight}px, clientHeight: ${panel.clientHeight}px`);
        console.log(`   Event item offsetHeight: ${eventItem.offsetHeight}px`);

        this.showFeedbackIcon(message.elementId);

        // Auto-scroll to bottom
        panel.scrollTop = panel.scrollHeight;
    }

    handleTextMessageContent(message) {
        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const messageContainer = panel.querySelector(`.feedback-message[data-message-id="${message.messageId}"]`);

        if (messageContainer) {
            // Remove typing indicator if present
            const typingIndicator = messageContainer.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Append delta (new chunk) - streaming text
            if (message.delta) {
                const previousLength = messageContainer.textContent.length;
                messageContainer.textContent += message.delta;
                const newLength = messageContainer.textContent.length;

                // Log EVERY delta to see the full LLM response
                console.log('───────────────────────────────────────────────────────');
                console.log('📝 LLM TEXT MESSAGE CONTENT (Delta - STREAMING)');
                console.log('───────────────────────────────────────────────────────');
                console.log('Element ID:', message.elementId);
                console.log('Message ID:', message.messageId);
                console.log('Delta length:', message.delta.length);
                console.log('Delta text:', message.delta);
                console.log('Total accumulated length:', previousLength, '→', newLength);
                console.log('Accumulated text so far (first 500 chars):');
                console.log(messageContainer.textContent.substring(0, 500));
                console.log('───────────────────────────────────────────────────────');
                console.log('');
            } else if (message.content) {
                // Backend sent entire message at once (NOT streaming)
                messageContainer.textContent = message.content;
                console.log('');
                console.log('═══════════════════════════════════════════════════════');
                console.log('📝 LLM TEXT MESSAGE CONTENT (Full - NOT STREAMING!)');
                console.log('═══════════════════════════════════════════════════════');
                console.log('⚠️  WARNING: Backend sent entire message at once');
                console.log('⚠️  This means streaming is NOT enabled on the backend');
                console.log('Element ID:', message.elementId);
                console.log('Message ID:', message.messageId);
                console.log('Content length:', message.content.length);
                console.log('Full content:');
                console.log(message.content);
                console.log('═══════════════════════════════════════════════════════');
                console.log('');
            } else {
                console.warn('⚠️ Message has neither delta nor content!', message);
            }

            // Auto-scroll to bottom as content arrives
            panel.scrollTop = panel.scrollHeight;
        } else {
            console.warn(`⚠️ Message container NOT found for messageId: ${message.messageId}`);
            console.log(`   Panel children count: ${panel.children.length}`);
            console.log(`   Looking for: .feedback-message[data-message-id="${message.messageId}"]`);
        }
    }

    handleTextMessageEnd(message) {
        console.log('✅ Text message complete:', message.elementId, message.messageId);
        console.log('');
        console.log('═══════════════════════════════════════════════════════');
        console.log('✅ LLM TEXT MESSAGE END');
        console.log('═══════════════════════════════════════════════════════');
        console.log('Element ID:', message.elementId);
        console.log('Message ID:', message.messageId);
        console.log('Thread ID:', message.threadId);
        console.log('═══════════════════════════════════════════════════════');
        console.log('');

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const messageContainer = panel.querySelector(`.feedback-message[data-message-id="${message.messageId}"]`);

        if (messageContainer) {
            // Remove typing indicator
            const typingIndicator = messageContainer.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Mark as complete and remove streaming class
            messageContainer.classList.remove('streaming');
            messageContainer.classList.add('complete');
        }
    }

    handleTextMessageChunk(message) {
        console.log('');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('📦 TEXT MESSAGE CHUNK (SENTENCE)');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('Element ID:', message.elementId);
        console.log('Message ID:', message.messageId);
        console.log('Role:', message.role);
        console.log('Content length:', message.content.length);
        console.log('Content:', message.content);
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('');

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Count current sentences (look for feedback-message elements, not all event items)
        const currentSentenceCount = panel.querySelectorAll('.feedback-message').length + 1;

        // Create a new event item for this sentence
        const eventItem = document.createElement('div');
        eventItem.className = 'feedback-event-item';
        eventItem.setAttribute('data-message-id', message.messageId);

        // Add sentence number and timestamp (use message timestamp if available, otherwise current time)
        const timestamp = document.createElement('div');
        timestamp.className = 'event-timestamp';
        const timestampStr = message.timestamp
            ? new Date(message.timestamp).toLocaleTimeString()
            : new Date().toLocaleTimeString();
        timestamp.innerHTML = `<span class="sentence-number">#${currentSentenceCount}</span> ${timestampStr}`;
        eventItem.appendChild(timestamp);

        // Add event header
        const header = document.createElement('div');
        header.className = 'event-header';
        header.innerHTML = '<span class="event-icon">💬</span><span class="event-title">LLM Response</span>';
        eventItem.appendChild(header);

        // Add message container with the complete sentence
        const messageContainer = document.createElement('div');
        messageContainer.className = 'feedback-message complete';
        messageContainer.setAttribute('data-message-id', message.messageId);
        messageContainer.textContent = message.content;
        eventItem.appendChild(messageContainer);

        panel.appendChild(eventItem);

        // Update counter in header
        this.updateFeedbackCounter(message.elementId);

        this.showFeedbackIcon(message.elementId);

        // Auto-scroll to bottom
        panel.scrollTop = panel.scrollHeight;
    }

    updateFeedbackCounter(elementId) {
        const counterElement = document.getElementById(`feedback-count-${elementId}`);
        if (counterElement) {
            const panel = this.getOrCreateFeedbackPanel(elementId);
            const totalItems = panel.querySelectorAll('.feedback-event-item').length;
            counterElement.textContent = `${totalItems} item${totalItems !== 1 ? 's' : ''}`;

            // Check if panel is scrollable and add indicator
            this.updateScrollIndicator(panel);
        }
    }

    updateScrollIndicator(panel) {
        // Check if content is scrollable (has overflow)
        const isScrollable = panel.scrollHeight > panel.clientHeight;
        const isScrolledToBottom = Math.abs(panel.scrollHeight - panel.clientHeight - panel.scrollTop) < 5;

        if (isScrollable && !isScrolledToBottom) {
            panel.classList.add('has-more-content');
        } else {
            panel.classList.remove('has-more-content');
        }
    }

    handleTaskThinking(message) {
        console.log('🤔 Task thinking:', message.elementId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Create a separate event item for thinking
        const eventItem = document.createElement('div');
        eventItem.className = 'feedback-event-item thinking-event';

        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'event-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        eventItem.appendChild(timestamp);

        // Add thinking content
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'feedback-thinking';
        thinkingDiv.innerHTML = `
            <span class="thinking-icon">🤔</span>
            <span class="thinking-text">${message.message || 'Thinking...'}</span>
        `;
        eventItem.appendChild(thinkingDiv);

        panel.appendChild(eventItem);

        // Update counter
        this.updateFeedbackCounter(message.elementId);

        this.showFeedbackIcon(message.elementId);

        // Auto-scroll to bottom
        panel.scrollTop = panel.scrollHeight;
    }

    handleTaskToolStart(message) {
        console.log('🔧 Tool start:', message.elementId, message.toolName);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Create a separate event item for tool execution
        const eventItem = document.createElement('div');
        eventItem.className = 'feedback-event-item tool-event';
        eventItem.setAttribute('data-tool', message.toolName);

        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'event-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        eventItem.appendChild(timestamp);

        // Add tool content
        const toolDiv = document.createElement('div');
        toolDiv.className = 'feedback-tool';
        toolDiv.innerHTML = `
            <span class="tool-icon">🔧</span>
            <span class="tool-name">${message.toolName}</span>
            <span class="tool-status running">Running...</span>
        `;
        eventItem.appendChild(toolDiv);

        panel.appendChild(eventItem);

        // Update counter
        this.updateFeedbackCounter(message.elementId);

        this.showFeedbackIcon(message.elementId);

        // Auto-scroll to bottom
        panel.scrollTop = panel.scrollHeight;
    }

    handleTaskToolEnd(message) {
        console.log('✅ Tool complete:', message.elementId, message.toolName);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);
        const eventItem = panel.querySelector(`.feedback-event-item[data-tool="${message.toolName}"]`);

        if (eventItem) {
            const statusSpan = eventItem.querySelector('.tool-status');
            if (statusSpan) {
                statusSpan.textContent = '✓ Complete';
                statusSpan.classList.remove('running');
                statusSpan.classList.add('complete');
            }
        }
    }

    handleMessagesSnapshot(message) {
        console.log('');
        console.log('═══════════════════════════════════════════════════════');
        console.log('📼 MESSAGES SNAPSHOT (REPLAY)');
        console.log('═══════════════════════════════════════════════════════');
        console.log('Element ID:', message.elementId);
        console.log('Thread ID:', message.threadId);
        console.log('Messages:', message.messages?.length || 0);
        console.log('Thinking events:', message.thinking?.length || 0);
        console.log('Tool events:', message.tools?.length || 0);
        console.log('');

        // Log all messages in detail
        if (message.messages && message.messages.length > 0) {
            console.log('──────────────────────────────────────────────────────');
            console.log('ALL LLM MESSAGES:');
            console.log('──────────────────────────────────────────────────────');
            message.messages.forEach((msg, index) => {
                console.log('');
                console.log(`Message ${index + 1}/${message.messages.length}:`);
                console.log('  ID:', msg.id);
                console.log('  Role:', msg.role);
                console.log('  Timestamp:', msg.timestamp);
                console.log('  Cancelled:', msg.cancelled || false);
                console.log('  Content length:', msg.content?.length || 0);
                console.log('  Content:');
                console.log(msg.content);
                console.log('');
            });
            console.log('──────────────────────────────────────────────────────');
        }
        console.log('═══════════════════════════════════════════════════════');
        console.log('');

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Clear existing content for replay
        panel.innerHTML = '';

        // Collect all events with timestamps for chronological ordering
        const allEvents = [];

        // Add thinking events
        if (message.thinking && message.thinking.length > 0) {
            message.thinking.forEach(thinking => {
                allEvents.push({
                    type: 'thinking',
                    timestamp: new Date(thinking.timestamp),
                    data: thinking
                });
            });
        }

        // Add tool events (split into start and end)
        if (message.tools && message.tools.length > 0) {
            message.tools.forEach(tool => {
                allEvents.push({
                    type: 'tool.start',
                    timestamp: new Date(tool.startTime),
                    data: tool
                });
                if (tool.endTime) {
                    allEvents.push({
                        type: 'tool.end',
                        timestamp: new Date(tool.endTime),
                        data: tool
                    });
                }
            });
        }

        // Add message events
        if (message.messages && message.messages.length > 0) {
            message.messages.forEach(msg => {
                allEvents.push({
                    type: 'message',
                    timestamp: new Date(msg.timestamp),
                    data: msg
                });
            });
        }

        // Sort events chronologically
        allEvents.sort((a, b) => a.timestamp - b.timestamp);

        console.log(`📼 Replaying ${allEvents.length} events in chronological order`);

        // Render events in order
        allEvents.forEach((event, index) => {
            const eventItem = document.createElement('div');
            eventItem.className = 'feedback-event-item';

            // Add timestamp
            const timestamp = document.createElement('div');
            timestamp.className = 'event-timestamp';
            timestamp.textContent = event.timestamp.toLocaleTimeString();
            eventItem.appendChild(timestamp);

            if (event.type === 'thinking') {
                // Thinking event
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'feedback-thinking';
                thinkingDiv.innerHTML = `
                    <span class="thinking-icon">🤔</span>
                    <span class="thinking-text">${event.data.message}</span>
                `;
                eventItem.appendChild(thinkingDiv);

            } else if (event.type === 'tool.start') {
                // Tool start event
                eventItem.setAttribute('data-tool', event.data.name);
                const toolDiv = document.createElement('div');
                toolDiv.className = 'feedback-tool';
                toolDiv.innerHTML = `
                    <span class="tool-icon">🔧</span>
                    <span class="tool-name">${event.data.name}</span>
                    <span class="tool-status running">Running...</span>
                `;
                eventItem.appendChild(toolDiv);

            } else if (event.type === 'tool.end') {
                // Tool end event
                eventItem.setAttribute('data-tool', event.data.name);
                const toolDiv = document.createElement('div');
                toolDiv.className = 'feedback-tool';
                toolDiv.innerHTML = `
                    <span class="tool-icon">🔧</span>
                    <span class="tool-name">${event.data.name}</span>
                    <span class="tool-status complete">✓ Complete</span>
                `;
                eventItem.appendChild(toolDiv);

            } else if (event.type === 'message') {
                // LLM message event
                eventItem.setAttribute('data-message-id', event.data.id);

                const header = document.createElement('div');
                header.className = 'event-header';
                header.innerHTML = '<span class="event-icon">💬</span><span class="event-title">LLM Response</span>';
                eventItem.appendChild(header);

                const messageContainer = document.createElement('div');
                messageContainer.className = event.data.cancelled ? 'feedback-message cancelled' : 'feedback-message complete';
                messageContainer.setAttribute('data-message-id', event.data.id);
                messageContainer.textContent = event.data.content;

                // Add cancellation notice if message was cancelled
                if (event.data.cancelled) {
                    const cancelNotice = document.createElement('div');
                    cancelNotice.className = 'message-cancelled-notice';
                    cancelNotice.innerHTML = `⚠️ (Partial response - task cancelled: ${event.data.cancellationReason || 'User cancelled'})`;
                    messageContainer.appendChild(cancelNotice);
                }

                eventItem.appendChild(messageContainer);
            }

            panel.appendChild(eventItem);
        });

        // Check if any messages were cancelled and show overall notice
        const cancelledMessages = message.messages ? message.messages.filter(m => m.cancelled) : [];
        if (cancelledMessages.length > 0) {
            const overallNotice = document.createElement('div');
            overallNotice.className = 'replay-cancellation-notice';
            overallNotice.innerHTML = `
                <span class="cancel-icon">⚠️</span>
                <strong>This task was cancelled during execution</strong>
                <div class="cancel-reason">${cancelledMessages[0].cancellationReason || 'User cancelled'}</div>
            `;
            panel.appendChild(overallNotice);
        }

        this.showFeedbackIcon(message.elementId);

        // Ensure cancel button is removed for replayed (completed) tasks
        this.removeCancelButton(message.elementId);
        this.cancellableTasks.delete(message.elementId);

        console.log('📼 Replay complete - panel populated with history in chronological order');
    }

    getOrCreateFeedbackPanel(elementId) {
        console.log(`🔍 getOrCreateFeedbackPanel called for elementId: ${elementId}`);
        let panel = document.getElementById(`feedback-panel-${elementId}`);

        if (!panel) {
            console.log(`   Creating NEW panel for ${elementId}`);
            panel = document.createElement('div');
            panel.id = `feedback-panel-${elementId}`;
            panel.className = 'task-feedback-panel';
            panel.innerHTML = `
                <div class="feedback-header">
                    <span class="feedback-title">Task Activity</span>
                    <span class="feedback-count" id="feedback-count-${elementId}">0 items</span>
                    <button class="feedback-close" onclick="this.closest('.task-feedback-panel').style.display='none'">×</button>
                </div>
                <div class="feedback-content"></div>
            `;

            // Position panel in a fixed, visible location (top-right corner)
            // This avoids issues with canvas zoom/pan affecting positioning
            panel.style.position = 'fixed';
            panel.style.right = '20px';
            panel.style.top = '100px';
            panel.style.display = 'none';  // Hidden by default - only show when user clicks bubble
            console.log(`   Positioned panel at fixed location: right: 20px, top: 100px`);
            console.log(`   Panel hidden by default - user must click bubble to show`);

            // Make panel draggable
            this.makePanelDraggable(panel);

            // Add scroll listener to update scroll indicator
            const contentDiv = panel.querySelector('.feedback-content');
            if (contentDiv) {
                contentDiv.addEventListener('scroll', () => {
                    this.updateScrollIndicator(contentDiv);
                });
            }

            document.body.appendChild(panel);
            console.log(`   Panel appended to body`);
            console.log(`   Panel dimensions: ${panel.offsetWidth}x${panel.offsetHeight}`);
        } else {
            console.log(`   Panel already exists for ${elementId}`);
        }

        const contentDiv = panel.querySelector('.feedback-content');
        console.log(`   Returning .feedback-content div, has ${contentDiv?.children.length || 0} children`);
        return contentDiv || panel;
    }

    makePanelDraggable(panel) {
        const header = panel.querySelector('.feedback-header');
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;

        header.style.cursor = 'move';

        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('feedback-close')) return; // Don't drag when clicking close button

            isDragging = true;
            initialX = e.clientX - panel.offsetLeft;
            initialY = e.clientY - panel.offsetTop;

            // Remove right/top positioning and use left/top for dragging
            const rect = panel.getBoundingClientRect();
            panel.style.left = `${rect.left}px`;
            panel.style.top = `${rect.top}px`;
            panel.style.right = 'auto';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            e.preventDefault();
            currentX = e.clientX - initialX;
            currentY = e.clientY - initialY;

            panel.style.left = `${currentX}px`;
            panel.style.top = `${currentY}px`;
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
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
                const wasHidden = panel.style.display === 'none';
                panel.style.display = wasHidden ? 'block' : 'none';
                console.log(`💬 Feedback bubble clicked for ${elementId}`);
                console.log(`   Panel is now: ${wasHidden ? 'VISIBLE' : 'HIDDEN'}`);

                if (wasHidden) {
                    const contentDiv = panel.querySelector('.feedback-content');
                    console.log(`   Panel has ${contentDiv?.children.length || 0} event items`);

                    // If panel is empty, request replay from server
                    if (contentDiv && contentDiv.children.length === 0) {
                        console.log(`   Panel is empty - requesting replay from server`);
                        this.requestReplay(elementId);
                    }
                }
            }
        });

        element.appendChild(icon);
        console.log(`💬 Feedback icon added to element ${elementId} - CLICK IT to show panel`);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, message not sent:', message);
        }
    }

    requestReplay(elementId) {
        console.log(`📼 Requesting replay for element: ${elementId}`);
        this.send({
            type: 'replay.request',
            elementId: elementId,
            timestamp: new Date().toISOString()
        });
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

    // ===== CANCELLATION SUPPORT =====

    handleTaskCancellable(message) {
        console.log('✅ Task is cancellable:', message.elementId);
        this.cancellableTasks.add(message.elementId);

        // Add cancel button to feedback panel
        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Check if cancel button already exists
        if (panel.querySelector('.cancel-task-btn')) {
            return;
        }

        // Create cancel button
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'cancel-task-btn';
        cancelBtn.innerHTML = '🛑 Cancel Task';
        cancelBtn.title = 'Stop this task execution';

        cancelBtn.addEventListener('click', () => {
            this.cancelTask(message.elementId);
        });

        // Insert at the beginning of the panel
        panel.insertBefore(cancelBtn, panel.firstChild);
    }

    cancelTask(elementId, reason = 'User cancelled') {
        if (!this.cancellableTasks.has(elementId)) {
            console.warn(`Task ${elementId} is not cancellable`);
            return;
        }

        console.log('🛑 Sending cancel request for task:', elementId);

        // Disable the cancel button immediately
        const panel = this.getOrCreateFeedbackPanel(elementId);
        const cancelBtn = panel.querySelector('.cancel-task-btn');
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = '⏳ Cancelling...';
        }

        // Send cancel request
        this.send({
            type: 'task.cancel.request',
            elementId: elementId,
            reason: reason,
            timestamp: new Date().toISOString()
        });

        this.cancelledTasks.add(elementId);
    }

    handleTaskCancelling(message) {
        console.log('⏳ Task cancelling:', message.elementId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Update cancel button
        const cancelBtn = panel.querySelector('.cancel-task-btn');
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = '⏳ Cancelling...';
            cancelBtn.classList.add('cancelling');
        }

        // Add cancelling notice
        const notice = document.createElement('div');
        notice.className = 'cancelling-notice';
        notice.innerHTML = `<span class="cancel-icon">⏳</span> ${message.message || 'Stopping task gracefully...'}`;
        panel.insertBefore(notice, panel.firstChild);
    }

    handleTaskCancelled(message) {
        console.log('🚫 Task cancelled:', message.elementId);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Remove cancel button
        const cancelBtn = panel.querySelector('.cancel-task-btn');
        if (cancelBtn) {
            cancelBtn.remove();
        }

        // Remove cancelling notice
        const cancellingNotice = panel.querySelector('.cancelling-notice');
        if (cancellingNotice) {
            cancellingNotice.remove();
        }

        // Add cancellation complete notice
        const notice = document.createElement('div');
        notice.className = 'cancellation-notice';
        notice.innerHTML = `
            <span class="cancel-icon">⚠️</span>
            <strong>Task cancelled by user</strong>
            <div class="cancel-reason">${message.reason || 'User requested cancellation'}</div>
        `;

        // Add partial result if available
        if (message.partialResult) {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'partial-result';
            resultDiv.innerHTML = `
                <strong>Partial Result:</strong><br>
                ${JSON.stringify(message.partialResult, null, 2)}
            `;
            notice.appendChild(resultDiv);
        }

        panel.appendChild(notice);

        // Mark task as no longer cancellable
        this.cancellableTasks.delete(message.elementId);
    }

    handleTaskCancelFailed(message) {
        console.warn('❌ Task cancellation failed:', message.elementId, message.error);

        const panel = this.getOrCreateFeedbackPanel(message.elementId);

        // Re-enable cancel button if it exists
        const cancelBtn = panel.querySelector('.cancel-task-btn');
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.textContent = '🛑 Cancel Task';
            cancelBtn.classList.remove('cancelling');
        }

        // Show error message
        const errorNotice = document.createElement('div');
        errorNotice.className = 'cancel-error-notice';
        errorNotice.innerHTML = `
            <span class="cancel-icon">❌</span>
            <strong>Cannot cancel task</strong>
            <div class="cancel-error">${message.error}</div>
        `;

        panel.appendChild(errorNotice);

        // Auto-remove error after 5 seconds
        setTimeout(() => {
            errorNotice.remove();
        }, 5000);
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
