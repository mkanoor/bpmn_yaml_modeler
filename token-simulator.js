// Token Flow Simulator - Simulates token animation without executing workflow

class TokenSimulator {
    constructor(aguiClient, modeler) {
        this.aguiClient = aguiClient;
        this.modeler = modeler;
        this.isSimulating = false;
        this.isPaused = false;
        this.simulationSpeed = 1.0; // 1.0 = normal, 2.0 = 2x speed, 0.5 = half speed
        this.currentElement = null;
        this.simulationTimeout = null;

        // Configurable delays (in milliseconds at 1x speed)
        this.delays = {
            taskExecution: 2000,      // How long a task "executes"
            tokenMovement: 800,       // Token animation duration (matches moveToken)
            gatewayEvaluation: 500,   // How long gateway takes to decide
            parallelForkDelay: 200    // Delay between creating parallel tokens
        };
    }

    async startSimulation() {
        if (this.isSimulating) {
            console.log('⚠️ Simulation already running');
            return;
        }

        console.log('');
        console.log('🎬 ═══════════════════════════════════════════════════════');
        console.log('🎬 STARTING TOKEN FLOW SIMULATION');
        console.log('🎬 Speed: ' + this.simulationSpeed + 'x');
        console.log('🎬 ═══════════════════════════════════════════════════════');
        console.log('');

        this.isSimulating = true;
        this.isPaused = false;

        // Clear any existing execution state
        this.aguiClient.clearAllHighlights();

        // Find start event
        const startEvent = this.modeler.elements.find(e => e.type === 'startEvent');
        if (!startEvent) {
            console.error('❌ No start event found in workflow');
            this.stopSimulation();
            return;
        }

        // Start simulation from start event
        await this.simulateElement(startEvent.id);
    }

    stopSimulation() {
        console.log('');
        console.log('🛑 SIMULATION STOPPED');
        console.log('');

        this.isSimulating = false;
        this.isPaused = false;
        if (this.simulationTimeout) {
            clearTimeout(this.simulationTimeout);
            this.simulationTimeout = null;
        }
    }

    pauseSimulation() {
        this.isPaused = true;
        console.log('⏸️ Simulation paused');
    }

    resumeSimulation() {
        this.isPaused = false;
        console.log('▶️ Simulation resumed');
    }

    setSpeed(speed) {
        this.simulationSpeed = speed;
        console.log(`⚡ Simulation speed set to ${speed}x`);
    }

    async simulateElement(elementId) {
        if (!this.isSimulating) return;

        // Wait if paused
        while (this.isPaused && this.isSimulating) {
            await this.sleep(100);
        }

        if (!this.isSimulating) return;

        const element = this.modeler.elements.find(e => e.id === elementId);
        if (!element) {
            console.warn(`⚠️ Element ${elementId} not found`);
            return;
        }

        this.currentElement = elementId;

        console.log(`📍 Simulating: ${element.type} "${element.name}" (${elementId})`);

        // Highlight element (triggers token creation)
        this.aguiClient.highlightElement(elementId);

        // Simulate element execution based on type
        switch (element.type) {
            case 'startEvent':
                await this.simulateStartEvent(element);
                break;

            case 'endEvent':
                await this.simulateEndEvent(element);
                break;

            case 'task':
            case 'scriptTask':
            case 'userTask':
            case 'serviceTask':
            case 'sendTask':
            case 'receiveTask':
            case 'callActivity':
                await this.simulateTask(element);
                break;

            case 'exclusiveGateway':
                await this.simulateExclusiveGateway(element);
                break;

            case 'parallelGateway':
                await this.simulateParallelGateway(element);
                break;

            case 'inclusiveGateway':
                await this.simulateInclusiveGateway(element);
                break;

            default:
                console.warn(`⚠️ Unknown element type: ${element.type}`);
                await this.simulateTask(element); // Treat as generic task
        }
    }

    async simulateStartEvent(element) {
        console.log('🟢 Start event - beginning workflow');
        await this.sleep(500); // Brief pause at start

        // Mark complete and move to next
        this.aguiClient.markElementComplete(element.id);
        await this.sleep(this.delays.tokenMovement);

        await this.moveToNextElements(element.id);
    }

    async simulateEndEvent(element) {
        console.log('🏁 End event - workflow complete');
        await this.sleep(500);

        this.aguiClient.markElementComplete(element.id);

        // Check if there are other active paths (for parallel flows)
        // If not, stop simulation
        await this.sleep(1000);

        console.log('✅ Simulation completed successfully');
        this.stopSimulation();
    }

    async simulateTask(element) {
        const taskDelay = this.getScaledDelay(this.delays.taskExecution);
        console.log(`⚙️ Executing task "${element.name}" (${(taskDelay / 1000).toFixed(1)}s)`);

        await this.sleep(taskDelay);

        this.aguiClient.markElementComplete(element.id);
        await this.sleep(this.delays.tokenMovement);

        await this.moveToNextElements(element.id);
    }

    async simulateExclusiveGateway(element) {
        const outgoing = this.modeler.connections.filter(c => c.from === element.id);

        console.log(`◆ Exclusive gateway "${element.name}" - evaluating ${outgoing.length} paths`);

        await this.sleep(this.getScaledDelay(this.delays.gatewayEvaluation));

        // Choose a random path (or first path with condition)
        const chosenPath = this.chooseGatewayPath(element, outgoing);

        if (chosenPath) {
            console.log(`  → Chose path: "${chosenPath.name || 'unnamed'}" to ${chosenPath.to}`);

            // Simulate gateway.path_taken event
            this.aguiClient.highlightPath(chosenPath.id, element.id);

            this.aguiClient.markElementComplete(element.id);
            await this.sleep(this.delays.tokenMovement);

            // Continue on chosen path
            await this.simulateElement(chosenPath.to);
        } else {
            console.error('❌ No valid path found from exclusive gateway');
            this.stopSimulation();
        }
    }

    async simulateParallelGateway(element) {
        const incoming = this.modeler.connections.filter(c => c.to === element.id);
        const outgoing = this.modeler.connections.filter(c => c.from === element.id);

        if (incoming.length > 1) {
            // This is a JOIN
            console.log(`⬥ Parallel gateway JOIN "${element.name}" - synchronizing ${incoming.length} paths`);
            // Token merging is handled automatically by aguiClient
            // Just mark complete and continue
            await this.sleep(this.getScaledDelay(500));
            this.aguiClient.markElementComplete(element.id);
            await this.sleep(this.delays.tokenMovement);

            if (outgoing.length > 0) {
                await this.simulateElement(outgoing[0].to);
            }
        } else {
            // This is a FORK
            console.log(`⬥ Parallel gateway FORK "${element.name}" - creating ${outgoing.length} parallel paths`);

            await this.sleep(this.getScaledDelay(this.delays.gatewayEvaluation));

            this.aguiClient.markElementComplete(element.id);
            await this.sleep(this.delays.tokenMovement);

            // Execute all paths in parallel (using Promise.all for true parallelism)
            const pathPromises = outgoing.map((conn, index) => {
                return this.sleep(index * this.getScaledDelay(this.delays.parallelForkDelay))
                    .then(() => this.simulateElement(conn.to));
            });

            await Promise.all(pathPromises);
        }
    }

    async simulateInclusiveGateway(element) {
        const outgoing = this.modeler.connections.filter(c => c.from === element.id);

        console.log(`◇ Inclusive gateway "${element.name}" - evaluating ${outgoing.length} paths`);

        await this.sleep(this.getScaledDelay(this.delays.gatewayEvaluation));

        // For simulation, randomly choose 1 or more paths
        const chosenPaths = this.chooseInclusivePaths(element, outgoing);

        console.log(`  → Activated ${chosenPaths.length} path(s)`);

        this.aguiClient.markElementComplete(element.id);
        await this.sleep(this.delays.tokenMovement);

        // Execute chosen paths in parallel
        const pathPromises = chosenPaths.map((conn, index) => {
            return this.sleep(index * this.getScaledDelay(this.delays.parallelForkDelay))
                .then(() => this.simulateElement(conn.to));
        });

        await Promise.all(pathPromises);
    }

    async moveToNextElements(elementId) {
        const outgoing = this.modeler.connections.filter(c => c.from === elementId);

        if (outgoing.length === 0) {
            // No outgoing connections - workflow might be complete
            return;
        } else if (outgoing.length === 1) {
            // Single path
            await this.simulateElement(outgoing[0].to);
        } else {
            // Multiple paths - should be handled by gateway
            console.warn(`⚠️ Element ${elementId} has ${outgoing.length} outgoing connections but is not a gateway`);
            // Default: take first path
            await this.simulateElement(outgoing[0].to);
        }
    }

    chooseGatewayPath(gateway, outgoingConnections) {
        // For simulation, we can:
        // 1. Choose first path with condition = true
        // 2. Choose first path if no conditions
        // 3. Random choice

        // Look for default path (no condition or empty condition)
        const defaultPath = outgoingConnections.find(c =>
            !c.properties || !c.properties.condition || c.properties.condition === ''
        );

        // If there's a default, use it, otherwise use first path
        return defaultPath || outgoingConnections[0];
    }

    chooseInclusivePaths(gateway, outgoingConnections) {
        // For inclusive gateway simulation, randomly activate 1 to N paths
        // At least one path must be chosen

        const numPaths = Math.max(1, Math.floor(Math.random() * outgoingConnections.length) + 1);

        // Shuffle and take first N
        const shuffled = [...outgoingConnections].sort(() => Math.random() - 0.5);
        return shuffled.slice(0, numPaths);
    }

    getScaledDelay(baseDelay) {
        return baseDelay / this.simulationSpeed;
    }

    sleep(ms) {
        return new Promise(resolve => {
            this.simulationTimeout = setTimeout(resolve, ms);
        });
    }
}

// Create global simulator instance (will be initialized when modeler is ready)
let tokenSimulator;

// Initialize simulator when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for modeler and aguiClient to be initialized
    setTimeout(() => {
        if (typeof modeler !== 'undefined' && typeof aguiClient !== 'undefined') {
            tokenSimulator = new TokenSimulator(aguiClient, modeler);
            console.log('✅ Token simulator initialized');
            setupSimulationUI();
        } else {
            console.warn('⚠️ Modeler or AG-UI client not available for simulator');
        }
    }, 1000);
});

// Setup simulation UI controls
function setupSimulationUI() {
    const simulateBtn = document.getElementById('simulateBtn');
    const simulateModal = document.getElementById('simulateModal');
    const startSimulationBtn = document.getElementById('startSimulationBtn');
    const cancelSimulationBtn = document.getElementById('cancelSimulationBtn');
    const simulationSpeedSelect = document.getElementById('simulationSpeed');

    // Toolbar controls
    const toolbarControls = document.getElementById('simulationToolbarControls');
    const pauseToolbarBtn = document.getElementById('pauseSimToolbarBtn');
    const resumeToolbarBtn = document.getElementById('resumeSimToolbarBtn');
    const stopToolbarBtn = document.getElementById('stopSimToolbarBtn');
    const speedToolbarSelect = document.getElementById('simSpeedToolbar');

    // Open simulation modal
    if (simulateBtn) {
        simulateBtn.addEventListener('click', () => {
            simulateModal.classList.add('active');
        });
    }

    // Close modal buttons
    if (cancelSimulationBtn) {
        cancelSimulationBtn.addEventListener('click', () => {
            simulateModal.classList.remove('active');
        });
    }

    const closeBtn = simulateModal.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            simulateModal.classList.remove('active');
        });
    }

    // Start simulation
    if (startSimulationBtn) {
        startSimulationBtn.addEventListener('click', async () => {
            // Get selected speed
            const speed = parseFloat(simulationSpeedSelect.value);
            tokenSimulator.setSpeed(speed);

            // Sync toolbar speed selector
            if (speedToolbarSelect) {
                speedToolbarSelect.value = simulationSpeedSelect.value;
            }

            // Close modal
            simulateModal.classList.remove('active');

            // Show toolbar controls, hide simulate button
            if (toolbarControls) {
                toolbarControls.style.display = 'inline-flex';
                toolbarControls.style.alignItems = 'center';
            }
            if (simulateBtn) {
                simulateBtn.style.display = 'none';
            }

            // Start simulation
            await tokenSimulator.startSimulation();

            // When simulation completes, reset UI
            if (toolbarControls) {
                toolbarControls.style.display = 'none';
            }
            if (simulateBtn) {
                simulateBtn.style.display = 'inline-block';
            }
            if (pauseToolbarBtn) {
                pauseToolbarBtn.style.display = 'inline-block';
            }
            if (resumeToolbarBtn) {
                resumeToolbarBtn.style.display = 'none';
            }
        });
    }

    // Toolbar pause button
    if (pauseToolbarBtn) {
        pauseToolbarBtn.addEventListener('click', () => {
            tokenSimulator.pauseSimulation();
            pauseToolbarBtn.style.display = 'none';
            resumeToolbarBtn.style.display = 'inline-block';
        });
    }

    // Toolbar resume button
    if (resumeToolbarBtn) {
        resumeToolbarBtn.addEventListener('click', () => {
            tokenSimulator.resumeSimulation();
            resumeToolbarBtn.style.display = 'none';
            pauseToolbarBtn.style.display = 'inline-block';
        });
    }

    // Toolbar stop button
    if (stopToolbarBtn) {
        stopToolbarBtn.addEventListener('click', () => {
            tokenSimulator.stopSimulation();

            // Hide toolbar controls, show simulate button
            if (toolbarControls) {
                toolbarControls.style.display = 'none';
            }
            if (simulateBtn) {
                simulateBtn.style.display = 'inline-block';
            }
            if (pauseToolbarBtn) {
                pauseToolbarBtn.style.display = 'inline-block';
            }
            if (resumeToolbarBtn) {
                resumeToolbarBtn.style.display = 'none';
            }
        });
    }

    // Toolbar speed selector
    if (speedToolbarSelect) {
        speedToolbarSelect.addEventListener('change', (e) => {
            const speed = parseFloat(e.target.value);
            if (tokenSimulator) {
                tokenSimulator.setSpeed(speed);
            }
        });
    }
}
