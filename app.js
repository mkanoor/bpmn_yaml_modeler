// BPMN Modeler Application
class BPMNModeler {
    constructor() {
        this.elements = [];
        this.connections = [];
        this.pools = [];
        this.selectedElement = null;
        this.connectionMode = false;
        this.connectionStart = null;
        this.draggedElement = null;
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        this.isPanning = false;
        this.panStart = { x: 0, y: 0 };
        this.idCounter = 0;

        // Undo/Redo state management
        this.undoStack = [];
        this.redoStack = [];
        this.maxUndoSteps = 50;
        this.isUndoRedoAction = false;

        this.canvas = document.getElementById('canvas');
        this.poolsLayer = document.getElementById('poolsLayer');
        this.connectionsLayer = document.getElementById('connectionsLayer');
        this.elementsLayer = document.getElementById('elementsLayer');
        this.mainGroup = document.getElementById('mainGroup');
        this.propertiesContent = document.getElementById('propertiesContent');

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupPalette();
        this.setupThemeSelector();
        this.loadTheme();
        this.setupCollapsibleSections();
    }

    setupEventListeners() {
        // Toolbar buttons
        document.getElementById('newBtn').addEventListener('click', () => this.newDiagram());
        document.getElementById('saveBtn').addEventListener('click', () => this.exportYAML());
        document.getElementById('loadBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        document.getElementById('fileInput').addEventListener('change', (e) => this.importYAML(e));

        // Canvas controls
        document.getElementById('undoBtn').addEventListener('click', () => this.undo());
        document.getElementById('redoBtn').addEventListener('click', () => this.redo());
        document.getElementById('addPoolBtn').addEventListener('click', () => this.addPool());
        document.getElementById('zoomInBtn').addEventListener('click', () => this.setZoom(this.zoom + 0.1));
        document.getElementById('zoomOutBtn').addEventListener('click', () => this.setZoom(this.zoom - 0.1));
        document.getElementById('resetZoomBtn').addEventListener('click', () => this.resetView());
        document.getElementById('fitToViewBtn').addEventListener('click', () => this.fitToView());
        document.getElementById('deleteBtn').addEventListener('click', () => this.deleteSelected());

        // Canvas events
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));

        // Panning support (Space + drag or Middle mouse button)
        this.canvas.addEventListener('mousedown', (e) => this.handlePanStart(e));
        this.canvas.addEventListener('mousemove', (e) => this.handlePanMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handlePanEnd(e));
        this.canvas.addEventListener('mouseleave', (e) => this.handlePanEnd(e));

        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e), { passive: false });

        // Modal
        const modal = document.getElementById('yamlModal');
        const closeBtn = modal.querySelector('.close');
        closeBtn.addEventListener('click', () => modal.classList.remove('active'));

        document.getElementById('copyYamlBtn').addEventListener('click', () => this.copyYAML());
        document.getElementById('downloadYamlBtn').addEventListener('click', () => this.downloadYAML());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete' && this.selectedElement) {
                this.deleteSelected();
            }

            // Undo: Ctrl+Z (Windows/Linux) or Cmd+Z (Mac)
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.undo();
            }

            // Redo: Ctrl+Y (Windows/Linux) or Cmd+Shift+Z (Mac) or Ctrl+Shift+Z
            if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
                e.preventDefault();
                this.redo();
            }
        });
    }

    setupPalette() {
        const paletteItems = document.querySelectorAll('.palette-item');
        paletteItems.forEach(item => {
            item.addEventListener('click', () => {
                const type = item.getAttribute('data-type');
                if (type === 'sequenceFlow') {
                    this.enterConnectionMode();
                } else if (type === 'pool') {
                    this.addPool();
                } else {
                    // For other elements, we'll add them to the center of the canvas
                    this.addElement(type, 400, 300);
                }
            });
        });
    }

    // Helper function to wrap text into multiple lines
    wrapText(text, maxWidth, fontSize = 12) {
        // Simple word-based text wrapping
        const words = text.split(' ');
        const lines = [];
        let currentLine = '';

        // Approximate characters per line based on width and font size
        const charsPerLine = Math.floor(maxWidth / (fontSize * 0.6));

        words.forEach(word => {
            const testLine = currentLine ? `${currentLine} ${word}` : word;
            if (testLine.length <= charsPerLine) {
                currentLine = testLine;
            } else {
                if (currentLine) {
                    lines.push(currentLine);
                }
                currentLine = word;
            }
        });

        if (currentLine) {
            lines.push(currentLine);
        }

        return lines.length > 0 ? lines : [text];
    }

    // Create multi-line text element
    createMultilineText(parentGroup, text, x, y, maxWidth, options = {}) {
        const fontSize = options.fontSize || 12;
        const textAnchor = options.textAnchor || 'middle';
        const fontWeight = options.fontWeight || 'normal';
        const className = options.className || 'element-text';

        const lines = this.wrapText(text, maxWidth, fontSize);
        const lineHeight = fontSize * 1.2;
        const totalHeight = lines.length * lineHeight;
        const startY = y - (totalHeight / 2) + (lineHeight / 2);

        lines.forEach((line, index) => {
            const textElement = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            textElement.setAttribute('x', x);
            textElement.setAttribute('y', startY + (index * lineHeight));
            textElement.setAttribute('class', className);
            textElement.setAttribute('text-anchor', textAnchor);
            textElement.setAttribute('font-weight', fontWeight);
            textElement.setAttribute('font-size', fontSize);
            textElement.textContent = line;
            parentGroup.appendChild(textElement);
        });

        return lines.length;
    }

    generateId() {
        return `element_${++this.idCounter}`;
    }

    addPool() {
        const id = this.generateId();
        const pool = {
            id,
            type: 'pool',
            name: 'Pool',
            x: 50,
            y: 100 + (this.pools.length * 250),
            width: 800,
            height: 200,
            lanes: []
        };

        // Add default lane
        pool.lanes.push({
            id: this.generateId(),
            name: 'Lane 1',
            height: 200
        });

        this.pools.push(pool);
        this.renderPool(pool);
        this.saveState(); // Save state for undo
    }

    addElement(type, x, y, poolId = null, laneId = null) {
        const id = this.generateId();
        const element = {
            id,
            type,
            name: this.getDefaultName(type),
            x,
            y,
            poolId,
            laneId,
            properties: {},
            expanded: type === 'subProcess' ? false : undefined, // Track collapse state
            childElements: type === 'subProcess' ? [] : undefined, // Nested elements
            childConnections: type === 'subProcess' ? [] : undefined, // Nested connections
            width: type === 'subProcess' ? 300 : undefined, // Expanded width
            height: type === 'subProcess' ? 200 : undefined // Expanded height
        };

        this.elements.push(element);
        this.renderElement(element);
        this.saveState(); // Save state for undo
        return element;
    }

    getDefaultName(type) {
        const names = {
            startEvent: 'Start',
            endEvent: 'End',
            intermediateEvent: 'Intermediate',
            timerIntermediateCatchEvent: 'Wait Timer',
            boundaryTimerEvent: 'Timeout',
            task: 'Task',
            userTask: 'User Task',
            serviceTask: 'Service Task',
            scriptTask: 'Script Task',
            sendTask: 'Send Task',
            receiveTask: 'Receive Task',
            manualTask: 'Manual Task',
            businessRuleTask: 'Business Rule Task',
            agenticTask: 'Agentic Task',
            subProcess: 'Sub-Process',
            callActivity: 'Call Activity',
            exclusiveGateway: 'Exclusive Gateway',
            parallelGateway: 'Parallel Gateway',
            inclusiveGateway: 'Inclusive Gateway'
        };
        return names[type] || type;
    }

    renderPool(pool) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'bpmn-pool');
        g.setAttribute('data-id', pool.id);

        // Pool container
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', pool.x);
        rect.setAttribute('y', pool.y);
        rect.setAttribute('width', pool.width);
        rect.setAttribute('height', pool.height);
        rect.setAttribute('class', 'bpmn-pool');
        g.appendChild(rect);

        // Pool label (vertical on the left)
        const labelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        labelBg.setAttribute('x', pool.x);
        labelBg.setAttribute('y', pool.y);
        labelBg.setAttribute('width', 30);
        labelBg.setAttribute('height', pool.height);
        labelBg.setAttribute('fill', '#d6eaf8');
        labelBg.setAttribute('stroke', '#2c3e50');
        labelBg.setAttribute('stroke-width', 2);
        g.appendChild(labelBg);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', pool.x + 15);
        text.setAttribute('y', pool.y + pool.height / 2);
        text.setAttribute('class', 'pool-label');
        text.setAttribute('transform', `rotate(-90, ${pool.x + 15}, ${pool.y + pool.height / 2})`);
        text.textContent = pool.name;
        g.appendChild(text);

        // Render lanes
        let currentY = pool.y;
        pool.lanes.forEach((lane, index) => {
            const laneRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            laneRect.setAttribute('x', pool.x + 30);
            laneRect.setAttribute('y', currentY);
            laneRect.setAttribute('width', pool.width - 30);
            laneRect.setAttribute('height', lane.height);
            laneRect.setAttribute('class', 'bpmn-lane');
            laneRect.setAttribute('data-lane-id', lane.id);
            g.appendChild(laneRect);

            const laneText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            laneText.setAttribute('x', pool.x + 40);
            laneText.setAttribute('y', currentY + 20);
            laneText.setAttribute('class', 'lane-label');
            laneText.textContent = lane.name;
            g.appendChild(laneText);

            currentY += lane.height;
        });

        this.poolsLayer.appendChild(g);
        this.makePoolDraggable(g, pool);
        this.makePoolSelectable(g, pool);
    }

    renderElement(element) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'bpmn-element');
        g.setAttribute('data-id', element.id);
        g.setAttribute('transform', `translate(${element.x}, ${element.y})`);

        const shape = this.createShape(element);
        g.appendChild(shape);

        // Add connection points
        const points = this.getConnectionPoints(element);
        points.forEach((point, index) => {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', point.x);
            circle.setAttribute('cy', point.y);
            circle.setAttribute('r', 5);
            circle.setAttribute('class', 'connection-point');
            circle.setAttribute('data-point', index);
            circle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleConnectionPoint(element, point);
            });
            g.appendChild(circle);
        });

        this.elementsLayer.appendChild(g);
        this.makeElementDraggable(g, element);
        this.makeElementSelectable(g, element);
    }

    createShape(element) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        switch (element.type) {
            case 'startEvent':
                const startCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                startCircle.setAttribute('cx', 0);
                startCircle.setAttribute('cy', 0);
                startCircle.setAttribute('r', 20);
                startCircle.setAttribute('class', 'bpmn-event');
                startCircle.setAttribute('stroke-width', 2);
                g.appendChild(startCircle);

                const startText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                startText.setAttribute('y', 35);
                startText.setAttribute('class', 'element-text');
                startText.textContent = element.name;
                g.appendChild(startText);
                break;

            case 'endEvent':
                const endCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                endCircle.setAttribute('cx', 0);
                endCircle.setAttribute('cy', 0);
                endCircle.setAttribute('r', 20);
                endCircle.setAttribute('class', 'bpmn-event');
                endCircle.setAttribute('stroke-width', 4);
                g.appendChild(endCircle);

                const endText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                endText.setAttribute('y', 35);
                endText.setAttribute('class', 'element-text');
                endText.textContent = element.name;
                g.appendChild(endText);
                break;

            case 'intermediateEvent':
            case 'timerIntermediateCatchEvent':
                const intCircle1 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                intCircle1.setAttribute('cx', 0);
                intCircle1.setAttribute('cy', 0);
                intCircle1.setAttribute('r', 20);
                intCircle1.setAttribute('class', 'bpmn-event');
                intCircle1.setAttribute('stroke-width', 2);
                g.appendChild(intCircle1);

                const intCircle2 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                intCircle2.setAttribute('cx', 0);
                intCircle2.setAttribute('cy', 0);
                intCircle2.setAttribute('r', 16);
                intCircle2.setAttribute('fill', 'none');
                intCircle2.setAttribute('stroke', '#2c3e50');
                intCircle2.setAttribute('stroke-width', 2);
                g.appendChild(intCircle2);

                // Add timer clock icon if it's a timer event
                if (element.type === 'timerIntermediateCatchEvent') {
                    const clockCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    clockCircle.setAttribute('cx', 0);
                    clockCircle.setAttribute('cy', 0);
                    clockCircle.setAttribute('r', 11);
                    clockCircle.setAttribute('fill', 'none');
                    clockCircle.setAttribute('stroke', '#2c3e50');
                    clockCircle.setAttribute('stroke-width', 1);
                    g.appendChild(clockCircle);

                    const clockHour = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    clockHour.setAttribute('x1', 0);
                    clockHour.setAttribute('y1', 0);
                    clockHour.setAttribute('x2', 0);
                    clockHour.setAttribute('y2', -6);
                    clockHour.setAttribute('stroke', '#2c3e50');
                    clockHour.setAttribute('stroke-width', 1.5);
                    g.appendChild(clockHour);

                    const clockMinute = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    clockMinute.setAttribute('x1', 0);
                    clockMinute.setAttribute('y1', 0);
                    clockMinute.setAttribute('x2', 5);
                    clockMinute.setAttribute('y2', 0);
                    clockMinute.setAttribute('stroke', '#2c3e50');
                    clockMinute.setAttribute('stroke-width', 1.5);
                    g.appendChild(clockMinute);
                }

                const intText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                intText.setAttribute('y', 35);
                intText.setAttribute('class', 'element-text');
                intText.textContent = element.name;
                g.appendChild(intText);
                break;

            case 'boundaryTimerEvent':
                const boundCircle1 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                boundCircle1.setAttribute('cx', 0);
                boundCircle1.setAttribute('cy', 0);
                boundCircle1.setAttribute('r', 15);
                boundCircle1.setAttribute('class', 'bpmn-event');
                boundCircle1.setAttribute('stroke-width', 2);
                g.appendChild(boundCircle1);

                const boundCircle2 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                boundCircle2.setAttribute('cx', 0);
                boundCircle2.setAttribute('cy', 0);
                boundCircle2.setAttribute('r', 12);
                boundCircle2.setAttribute('fill', 'none');
                boundCircle2.setAttribute('stroke', '#2c3e50');
                boundCircle2.setAttribute('stroke-width', 2);
                g.appendChild(boundCircle2);

                // Timer clock icon
                const bClockCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                bClockCircle.setAttribute('cx', 0);
                bClockCircle.setAttribute('cy', 0);
                bClockCircle.setAttribute('r', 8);
                bClockCircle.setAttribute('fill', 'none');
                bClockCircle.setAttribute('stroke', '#2c3e50');
                bClockCircle.setAttribute('stroke-width', 1);
                g.appendChild(bClockCircle);

                const bClockHour = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                bClockHour.setAttribute('x1', 0);
                bClockHour.setAttribute('y1', 0);
                bClockHour.setAttribute('x2', 0);
                bClockHour.setAttribute('y2', -4);
                bClockHour.setAttribute('stroke', '#2c3e50');
                bClockHour.setAttribute('stroke-width', 1);
                g.appendChild(bClockHour);

                const bClockMinute = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                bClockMinute.setAttribute('x1', 0);
                bClockMinute.setAttribute('y1', 0);
                bClockMinute.setAttribute('x2', 4);
                bClockMinute.setAttribute('y2', 0);
                bClockMinute.setAttribute('stroke', '#2c3e50');
                bClockMinute.setAttribute('stroke-width', 1);
                g.appendChild(bClockMinute);

                const boundText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                boundText.setAttribute('y', 28);
                boundText.setAttribute('class', 'element-text');
                boundText.setAttribute('font-size', '10');
                boundText.textContent = element.name;
                g.appendChild(boundText);
                break;

            case 'task':
            case 'userTask':
            case 'serviceTask':
            case 'scriptTask':
            case 'sendTask':
            case 'receiveTask':
            case 'manualTask':
            case 'businessRuleTask':
            case 'agenticTask':
            case 'subProcess':
            case 'callActivity':
                // Determine size based on expansion state
                const isExpanded = element.type === 'subProcess' && element.expanded;
                const width = isExpanded ? element.width : 120;  // Increased from 100 to 120
                const height = isExpanded ? element.height : 80; // Increased from 60 to 80
                const halfWidth = width / 2;
                const halfHeight = height / 2;

                const taskRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                taskRect.setAttribute('x', -halfWidth);
                taskRect.setAttribute('y', -halfHeight);
                taskRect.setAttribute('width', width);
                taskRect.setAttribute('height', height);
                taskRect.setAttribute('rx', 5);
                taskRect.setAttribute('class', 'bpmn-task');
                taskRect.setAttribute('stroke-width', element.type === 'callActivity' ? 4 : 2);

                // Add light background for expanded subprocesses
                if (isExpanded) {
                    taskRect.setAttribute('fill', '#f8f9fa');
                    taskRect.setAttribute('stroke', '#495057');
                }

                g.appendChild(taskRect);

                // Use multiline text for tasks
                const textMaxWidth = width - 20; // Leave padding
                this.createMultilineText(g, element.name,
                    isExpanded ? -halfWidth + 10 : 0,
                    isExpanded ? -halfHeight + 20 : 0,
                    textMaxWidth, {
                        fontSize: isExpanded ? 13 : 11,
                        textAnchor: isExpanded ? 'start' : 'middle',
                        fontWeight: isExpanded ? 'bold' : 'normal',
                        className: 'element-text'
                    });

                // Add task type markers
                if (element.type === 'subProcess') {
                    // Expand/Collapse button
                    const toggleBtn = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    toggleBtn.setAttribute('x', isExpanded ? -halfWidth + 10 : 0);
                    toggleBtn.setAttribute('y', halfHeight - 8);
                    toggleBtn.setAttribute('class', 'subprocess-toggle');
                    toggleBtn.setAttribute('text-anchor', isExpanded ? 'start' : 'middle');
                    toggleBtn.setAttribute('font-size', 16);
                    toggleBtn.setAttribute('font-weight', 'bold');
                    toggleBtn.setAttribute('cursor', 'pointer');
                    toggleBtn.textContent = element.expanded ? '−' : '+';
                    toggleBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.toggleSubProcess(element);
                    });
                    g.appendChild(toggleBtn);

                    // If expanded, render child elements
                    if (isExpanded) {
                        this.renderSubProcessChildren(g, element);
                    }
                } else if (element.type === 'userTask') {
                    // User icon (person) - positioned in top-left corner
                    const userCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    userCircle.setAttribute('cx', -48);
                    userCircle.setAttribute('cy', -28);
                    userCircle.setAttribute('r', 4);
                    userCircle.setAttribute('fill', 'none');
                    userCircle.setAttribute('stroke', '#000');
                    userCircle.setAttribute('stroke-width', 1);
                    g.appendChild(userCircle);
                    const userBody = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    userBody.setAttribute('d', 'M -52 -20 Q -48 -24 -44 -20');
                    userBody.setAttribute('fill', 'none');
                    userBody.setAttribute('stroke', '#000');
                    userBody.setAttribute('stroke-width', 1);
                    g.appendChild(userBody);
                } else if (element.type === 'serviceTask') {
                    // Gear icon - positioned in top-left corner
                    const gearCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    gearCircle.setAttribute('cx', -48);
                    gearCircle.setAttribute('cy', -28);
                    gearCircle.setAttribute('r', 6);
                    gearCircle.setAttribute('fill', 'none');
                    gearCircle.setAttribute('stroke', '#000');
                    gearCircle.setAttribute('stroke-width', 1);
                    g.appendChild(gearCircle);
                    // Gear teeth
                    const teeth = [
                        { x1: -48, y1: -34, x2: -48, y2: -36 },
                        { x1: -48, y1: -22, x2: -48, y2: -20 },
                        { x1: -42, y1: -28, x2: -40, y2: -28 },
                        { x1: -54, y1: -28, x2: -56, y2: -28 }
                    ];
                    teeth.forEach(t => {
                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        line.setAttribute('x1', t.x1);
                        line.setAttribute('y1', t.y1);
                        line.setAttribute('x2', t.x2);
                        line.setAttribute('y2', t.y2);
                        line.setAttribute('stroke', '#000');
                        line.setAttribute('stroke-width', 1);
                        g.appendChild(line);
                    });
                } else if (element.type === 'scriptTask') {
                    // Scroll icon - positioned in top-left corner
                    // Main scroll body (rectangle)
                    const scrollBody = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    scrollBody.setAttribute('x', -54);
                    scrollBody.setAttribute('y', -32);
                    scrollBody.setAttribute('width', 12);
                    scrollBody.setAttribute('height', 10);
                    scrollBody.setAttribute('fill', 'none');
                    scrollBody.setAttribute('stroke', '#000');
                    scrollBody.setAttribute('stroke-width', 1);
                    g.appendChild(scrollBody);

                    // Top scroll roll (curved edge at top)
                    const topRoll = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    topRoll.setAttribute('d', 'M -54 -32 Q -48 -34 -42 -32');
                    topRoll.setAttribute('fill', 'none');
                    topRoll.setAttribute('stroke', '#000');
                    topRoll.setAttribute('stroke-width', 1);
                    g.appendChild(topRoll);

                    // Bottom scroll roll (curved edge at bottom)
                    const bottomRoll = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    bottomRoll.setAttribute('d', 'M -54 -22 Q -48 -20 -42 -22');
                    bottomRoll.setAttribute('fill', 'none');
                    bottomRoll.setAttribute('stroke', '#000');
                    bottomRoll.setAttribute('stroke-width', 1);
                    g.appendChild(bottomRoll);

                    // Script lines on scroll (3 horizontal lines)
                    const scriptLine1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    scriptLine1.setAttribute('x1', -52);
                    scriptLine1.setAttribute('y1', -30);
                    scriptLine1.setAttribute('x2', -44);
                    scriptLine1.setAttribute('y2', -30);
                    scriptLine1.setAttribute('stroke', '#000');
                    scriptLine1.setAttribute('stroke-width', 0.8);
                    g.appendChild(scriptLine1);

                    const scriptLine2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    scriptLine2.setAttribute('x1', -52);
                    scriptLine2.setAttribute('y1', -27);
                    scriptLine2.setAttribute('x2', -44);
                    scriptLine2.setAttribute('y2', -27);
                    scriptLine2.setAttribute('stroke', '#000');
                    scriptLine2.setAttribute('stroke-width', 0.8);
                    g.appendChild(scriptLine2);

                    const scriptLine3 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    scriptLine3.setAttribute('x1', -52);
                    scriptLine3.setAttribute('y1', -24);
                    scriptLine3.setAttribute('x2', -44);
                    scriptLine3.setAttribute('y2', -24);
                    scriptLine3.setAttribute('stroke', '#000');
                    scriptLine3.setAttribute('stroke-width', 0.8);
                    g.appendChild(scriptLine3);
                } else if (element.type === 'sendTask') {
                    // Filled envelope - positioned in top-left corner
                    const envelope = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    envelope.setAttribute('d', 'M -56 -32 L -56 -22 L -42 -22 L -42 -32 Z');
                    envelope.setAttribute('fill', '#000');
                    envelope.setAttribute('stroke', '#000');
                    envelope.setAttribute('stroke-width', 1);
                    g.appendChild(envelope);
                    const flap = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    flap.setAttribute('d', 'M -56 -32 L -49 -27 L -42 -32');
                    flap.setAttribute('fill', '#000');
                    flap.setAttribute('stroke', '#000');
                    flap.setAttribute('stroke-width', 1);
                    g.appendChild(flap);
                } else if (element.type === 'receiveTask') {
                    // Empty envelope - positioned in top-left corner
                    const envelope = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    envelope.setAttribute('d', 'M -56 -32 L -56 -22 L -42 -22 L -42 -32 Z');
                    envelope.setAttribute('fill', 'white');
                    envelope.setAttribute('stroke', '#000');
                    envelope.setAttribute('stroke-width', 1);
                    g.appendChild(envelope);
                    const flap = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    flap.setAttribute('d', 'M -56 -32 L -49 -27 L -42 -32');
                    flap.setAttribute('fill', 'white');
                    flap.setAttribute('stroke', '#000');
                    flap.setAttribute('stroke-width', 1);
                    g.appendChild(flap);
                } else if (element.type === 'manualTask') {
                    // Hand icon - positioned in top-left corner
                    const hand = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    hand.setAttribute('d', 'M -54 -22 L -54 -28 L -50 -28 L -50 -32 L -48 -32 L -48 -26 L -52 -26 L -52 -22 Z');
                    hand.setAttribute('fill', 'none');
                    hand.setAttribute('stroke', '#000');
                    hand.setAttribute('stroke-width', 1);
                    g.appendChild(hand);
                } else if (element.type === 'businessRuleTask') {
                    // Table icon - positioned in top-left corner
                    const table = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    table.setAttribute('x', -56);
                    table.setAttribute('y', -32);
                    table.setAttribute('width', 14);
                    table.setAttribute('height', 12);
                    table.setAttribute('fill', 'none');
                    table.setAttribute('stroke', '#000');
                    table.setAttribute('stroke-width', 1);
                    g.appendChild(table);
                    const hLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    hLine.setAttribute('x1', -56);
                    hLine.setAttribute('y1', -28);
                    hLine.setAttribute('x2', -42);
                    hLine.setAttribute('y2', -28);
                    hLine.setAttribute('stroke', '#000');
                    hLine.setAttribute('stroke-width', 1);
                    g.appendChild(hLine);
                    const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    vLine.setAttribute('x1', -50);
                    vLine.setAttribute('y1', -32);
                    vLine.setAttribute('x2', -50);
                    vLine.setAttribute('y2', -20);
                    vLine.setAttribute('stroke', '#000');
                    vLine.setAttribute('stroke-width', 1);
                    g.appendChild(vLine);
                } else if (element.type === 'agenticTask') {
                    // Brain icon (AI/LLM indicator) - positioned in top-left corner
                    const aiColor = '#ec4899'; // Pink color for AI

                    // Brain outline (simplified brain shape) - compact version
                    const brainPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    brainPath.setAttribute('d', 'M -56 -28 C -57 -29 -57 -30 -56 -31 C -55 -32 -53 -32 -52 -31 C -51.5 -32 -50.5 -32 -50 -31 C -49 -32 -47 -32 -46 -31 C -45 -30 -45 -29 -46 -28 C -46 -27 -46 -26 -47 -25 C -48 -24 -49 -24 -50 -25 C -50.5 -24 -51.5 -24 -52 -25 C -53 -24 -54 -24 -55 -25 C -56 -26 -56 -27 -56 -28 Z');
                    brainPath.setAttribute('fill', 'none');
                    brainPath.setAttribute('stroke', aiColor);
                    brainPath.setAttribute('stroke-width', 1.2);
                    g.appendChild(brainPath);

                    // Brain folds/wrinkles (left hemisphere)
                    const fold1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    fold1.setAttribute('d', 'M -55 -29 Q -54 -28 -54 -27');
                    fold1.setAttribute('fill', 'none');
                    fold1.setAttribute('stroke', aiColor);
                    fold1.setAttribute('stroke-width', 0.8);
                    g.appendChild(fold1);

                    const fold2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    fold2.setAttribute('d', 'M -53 -30 Q -52 -29 -52 -28');
                    fold2.setAttribute('fill', 'none');
                    fold2.setAttribute('stroke', aiColor);
                    fold2.setAttribute('stroke-width', 0.8);
                    g.appendChild(fold2);

                    // Brain folds/wrinkles (right hemisphere)
                    const fold3 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    fold3.setAttribute('d', 'M -50 -30 Q -49 -29 -49 -28');
                    fold3.setAttribute('fill', 'none');
                    fold3.setAttribute('stroke', aiColor);
                    fold3.setAttribute('stroke-width', 0.8);
                    g.appendChild(fold3);

                    const fold4 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    fold4.setAttribute('d', 'M -48 -29 Q -47 -28 -47 -27');
                    fold4.setAttribute('fill', 'none');
                    fold4.setAttribute('stroke', aiColor);
                    fold4.setAttribute('stroke-width', 0.8);
                    g.appendChild(fold4);

                    // Center line (corpus callosum)
                    const centerLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    centerLine.setAttribute('x1', -51);
                    centerLine.setAttribute('y1', -31);
                    centerLine.setAttribute('x2', -51);
                    centerLine.setAttribute('y2', -25);
                    centerLine.setAttribute('stroke', aiColor);
                    centerLine.setAttribute('stroke-width', 0.6);
                    centerLine.setAttribute('stroke-dasharray', '1.5,0.8');
                    g.appendChild(centerLine);
                }
                break;

            case 'exclusiveGateway':
                const exPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                exPath.setAttribute('d', 'M 0 -25 L 25 0 L 0 25 L -25 0 Z');
                exPath.setAttribute('class', 'bpmn-gateway');
                g.appendChild(exPath);

                const exX = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                exX.setAttribute('y', 8);
                exX.setAttribute('class', 'element-text');
                exX.setAttribute('font-size', 20);
                exX.setAttribute('font-weight', 'bold');
                exX.textContent = '×';
                g.appendChild(exX);

                // Multiline text below gateway
                this.createMultilineText(g, element.name, 0, 40, 120, {
                    fontSize: 11,
                    textAnchor: 'middle',
                    className: 'element-text'
                });
                break;

            case 'parallelGateway':
                const parPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                parPath.setAttribute('d', 'M 0 -25 L 25 0 L 0 25 L -25 0 Z');
                parPath.setAttribute('class', 'bpmn-gateway');
                g.appendChild(parPath);

                const parPlus = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                parPlus.setAttribute('y', 7);
                parPlus.setAttribute('class', 'element-text');
                parPlus.setAttribute('font-size', 20);
                parPlus.setAttribute('font-weight', 'bold');
                parPlus.textContent = '+';
                g.appendChild(parPlus);

                // Multiline text below gateway
                this.createMultilineText(g, element.name, 0, 40, 120, {
                    fontSize: 11,
                    textAnchor: 'middle',
                    className: 'element-text'
                });
                break;

            case 'inclusiveGateway':
                const incPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                incPath.setAttribute('d', 'M 0 -25 L 25 0 L 0 25 L -25 0 Z');
                incPath.setAttribute('class', 'bpmn-gateway');
                g.appendChild(incPath);

                const incCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                incCircle.setAttribute('cx', 0);
                incCircle.setAttribute('cy', 0);
                incCircle.setAttribute('r', 10);
                incCircle.setAttribute('fill', 'none');
                incCircle.setAttribute('stroke', '#2c3e50');
                incCircle.setAttribute('stroke-width', 2);
                g.appendChild(incCircle);

                // Multiline text below gateway
                this.createMultilineText(g, element.name, 0, 40, 120, {
                    fontSize: 11,
                    textAnchor: 'middle',
                    className: 'element-text'
                });
                break;
        }

        return g;
    }

    getConnectionPoints(element) {
        const points = [];

        if (element.type.includes('Event')) {
            points.push({ x: 20, y: 0 }); // right
            points.push({ x: -20, y: 0 }); // left
            points.push({ x: 0, y: -20 }); // top
            points.push({ x: 0, y: 20 }); // bottom
        } else if (element.type === 'task' || element.type === 'userTask' || element.type === 'serviceTask' ||
                   element.type === 'scriptTask' || element.type === 'sendTask' || element.type === 'receiveTask' ||
                   element.type === 'manualTask' || element.type === 'businessRuleTask' || element.type === 'agenticTask' ||
                   element.type === 'subProcess' || element.type === 'callActivity') {
            points.push({ x: 60, y: 0 }); // right (increased from 50 to 60)
            points.push({ x: -60, y: 0 }); // left (increased from 50 to 60)
            points.push({ x: 0, y: -40 }); // top (increased from 30 to 40)
            points.push({ x: 0, y: 40 }); // bottom (increased from 30 to 40)
        } else if (element.type.includes('Gateway')) {
            points.push({ x: 25, y: 0 }); // right
            points.push({ x: -25, y: 0 }); // left
            points.push({ x: 0, y: -25 }); // top
            points.push({ x: 0, y: 25 }); // bottom
        }

        return points;
    }

    makeElementDraggable(svgElement, element) {
        let isDragging = false;
        let startX, startY;

        svgElement.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('connection-point')) return;

            isDragging = true;
            startX = e.clientX - element.x;
            startY = e.clientY - element.y;
            svgElement.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            element.x = e.clientX - startX;
            element.y = e.clientY - startY;
            svgElement.setAttribute('transform', `translate(${element.x}, ${element.y})`);

            this.updateConnections(element.id);
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                svgElement.style.cursor = 'move';
            }
        });
    }

    makePoolDraggable(svgElement, pool) {
        let isDragging = false;
        let startX, startY;

        svgElement.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX - pool.x;
            startY = e.clientY - pool.y;
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            pool.x = e.clientX - startX;
            pool.y = e.clientY - startY;

            this.rerenderPools();
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    makeElementSelectable(svgElement, element) {
        svgElement.addEventListener('click', (e) => {
            if (e.target.classList.contains('connection-point')) return;
            e.stopPropagation();
            this.selectElement(element);
        });
    }

    makePoolSelectable(svgElement, pool) {
        svgElement.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectElement(pool);
        });
    }

    selectElement(element) {
        // Deselect previous
        if (this.selectedElement) {
            const prev = document.querySelector(`[data-id="${this.selectedElement.id}"]`);
            if (prev) prev.classList.remove('selected');
        }

        this.selectedElement = element;
        const current = document.querySelector(`[data-id="${element.id}"]`);
        if (current) current.classList.add('selected');

        this.showProperties(element);
    }

    showProperties(element) {
        this.propertiesContent.innerHTML = '';

        // Handle connection (sequence flow) properties
        if (element.type === 'sequenceFlow') {
            return this.showConnectionProperties(element);
        }

        const createInput = (label, value, property) => {
            const group = document.createElement('div');
            group.className = 'property-group';

            const labelEl = document.createElement('label');
            labelEl.textContent = label;
            group.appendChild(labelEl);

            const input = document.createElement('input');
            input.type = 'text';
            input.value = value || '';
            input.addEventListener('input', (e) => {
                element[property] = e.target.value;
                this.rerenderElement(element);
            });
            group.appendChild(input);

            return group;
        };

        const createSelect = (label, value, property, options) => {
            const group = document.createElement('div');
            group.className = 'property-group';

            const labelEl = document.createElement('label');
            labelEl.textContent = label;
            group.appendChild(labelEl);

            const select = document.createElement('select');
            select.value = value || '';
            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt.value;
                option.textContent = opt.label;
                if (opt.value === value) option.selected = true;
                select.appendChild(option);
            });
            select.addEventListener('change', (e) => {
                element[property] = e.target.value;
                element.name = this.getDefaultName(e.target.value);
                this.rerenderElements();
            });
            group.appendChild(select);

            return group;
        };

        this.propertiesContent.appendChild(createInput('ID', element.id, 'id'));
        this.propertiesContent.appendChild(createInput('Name', element.name, 'name'));

        // Add expansion toggle for subprocesses
        if (element.type === 'subProcess') {
            const expandGroup = document.createElement('div');
            expandGroup.className = 'property-group';
            const expandLabel = document.createElement('label');
            expandLabel.textContent = 'Display';
            expandGroup.appendChild(expandLabel);
            const expandCheckbox = document.createElement('input');
            expandCheckbox.type = 'checkbox';
            expandCheckbox.checked = element.expanded || false;
            expandCheckbox.addEventListener('change', (e) => {
                this.toggleSubProcess(element);
                this.showProperties(element); // Refresh properties panel
            });
            const expandLabelText = document.createElement('span');
            expandLabelText.textContent = ' Expanded (show internal flow)';
            expandLabelText.style.marginLeft = '0.5rem';
            expandGroup.appendChild(expandCheckbox);
            expandGroup.appendChild(expandLabelText);
            this.propertiesContent.appendChild(expandGroup);
        }

        // Add task type selector if it's a task-based element
        const taskTypes = ['task', 'userTask', 'serviceTask', 'scriptTask', 'sendTask',
                          'receiveTask', 'manualTask', 'businessRuleTask', 'agenticTask', 'subProcess', 'callActivity'];
        if (taskTypes.includes(element.type)) {
            const typeOptions = [
                { value: 'task', label: 'Task' },
                { value: 'userTask', label: 'User Task' },
                { value: 'serviceTask', label: 'Service Task' },
                { value: 'scriptTask', label: 'Script Task' },
                { value: 'sendTask', label: 'Send Task' },
                { value: 'receiveTask', label: 'Receive Task' },
                { value: 'manualTask', label: 'Manual Task' },
                { value: 'businessRuleTask', label: 'Business Rule Task' },
                { value: 'agenticTask', label: 'Agentic Task (Custom)' },
                { value: 'subProcess', label: 'Sub-Process' },
                { value: 'callActivity', label: 'Call Activity' }
            ];
            this.propertiesContent.appendChild(createSelect('Task Type', element.type, 'type', typeOptions));
        } else {
            this.propertiesContent.appendChild(createInput('Type', element.type, 'type'));
        }

        if (element.type !== 'pool') {
            const docGroup = document.createElement('div');
            docGroup.className = 'property-group';
            const docLabel = document.createElement('label');
            docLabel.textContent = 'Documentation';
            docGroup.appendChild(docLabel);
            const docInput = document.createElement('textarea');
            docInput.value = element.properties?.documentation || '';
            docInput.addEventListener('input', (e) => {
                if (!element.properties) element.properties = {};
                element.properties.documentation = e.target.value;
            });
            docGroup.appendChild(docInput);
            this.propertiesContent.appendChild(docGroup);

            // Add task-type-specific properties
            this.addTaskSpecificProperties(element);

            // Add custom properties editor
            this.addCustomPropertiesEditor(element);
        }
    }

    showConnectionProperties(connection) {
        // Title
        const title = document.createElement('h3');
        title.textContent = 'Connection Properties';
        title.style.marginTop = '0';
        this.propertiesContent.appendChild(title);

        // ID (read-only)
        const idGroup = document.createElement('div');
        idGroup.className = 'property-group';
        const idLabel = document.createElement('label');
        idLabel.textContent = 'ID';
        idGroup.appendChild(idLabel);
        const idInput = document.createElement('input');
        idInput.type = 'text';
        idInput.value = connection.id;
        idInput.disabled = true;
        idInput.style.backgroundColor = '#f0f0f0';
        idGroup.appendChild(idInput);
        this.propertiesContent.appendChild(idGroup);

        // Name (label)
        const nameGroup = document.createElement('div');
        nameGroup.className = 'property-group';
        const nameLabel = document.createElement('label');
        nameLabel.textContent = 'Name (Label)';
        nameGroup.appendChild(nameLabel);
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = connection.name || '';
        nameInput.placeholder = 'e.g., "sum > 10", "approved", "default"';
        nameInput.addEventListener('input', (e) => {
            connection.name = e.target.value;
            this.updateConnectionLabel(connection);
        });
        nameGroup.appendChild(nameInput);
        this.propertiesContent.appendChild(nameGroup);

        // Condition
        const condGroup = document.createElement('div');
        condGroup.className = 'property-group';
        const condLabel = document.createElement('label');
        condLabel.textContent = 'Condition';
        condGroup.appendChild(condLabel);
        const condInput = document.createElement('input');
        condInput.type = 'text';
        condInput.value = connection.properties?.condition || '';
        condInput.placeholder = 'e.g., "${sum} > 10", "${approved}", "" (empty = default)';
        condInput.addEventListener('input', (e) => {
            if (!connection.properties) connection.properties = {};
            connection.properties.condition = e.target.value;
        });
        condGroup.appendChild(condInput);
        this.propertiesContent.appendChild(condGroup);

        // Help text
        const helpText = document.createElement('div');
        helpText.style.marginTop = '1rem';
        helpText.style.padding = '0.75rem';
        helpText.style.backgroundColor = '#f8f9fa';
        helpText.style.borderRadius = '4px';
        helpText.style.fontSize = '0.85rem';
        helpText.innerHTML = `
            <strong>Condition Syntax:</strong><br>
            • <code>\${sum} > 10</code> - Greater than<br>
            • <code>\${sum} >= 10</code> - Greater or equal<br>
            • <code>\${approved} == true</code> - Equality<br>
            • <code>\${status} == 'approved'</code> - String match<br>
            • <code>\${age} >= 18 and \${hasLicense}</code> - Multiple conditions<br>
            • <code>""</code> (empty) - Default path (always taken if no other matches)
        `;
        this.propertiesContent.appendChild(helpText);

        // Example section
        const exampleSection = document.createElement('div');
        exampleSection.style.marginTop = '1rem';
        exampleSection.style.padding = '0.75rem';
        exampleSection.style.backgroundColor = '#e8f4f8';
        exampleSection.style.borderRadius = '4px';
        exampleSection.style.fontSize = '0.85rem';
        exampleSection.innerHTML = `
            <strong>💡 Examples:</strong><br>
            <strong>Numeric:</strong> \${amount} > 1000<br>
            <strong>Boolean:</strong> \${approved}<br>
            <strong>String:</strong> \${status} == 'success'<br>
            <strong>Default:</strong> Leave empty for fallback path
        `;
        this.propertiesContent.appendChild(exampleSection);
    }

    updateConnectionLabel(connection) {
        // Find the connection line in DOM and update its label
        const line = document.querySelector(`line[data-id="${connection.id}"]`);
        if (line) {
            // For now, re-render the connection to show updated label
            this.rerenderConnection(connection);
        }
    }

    rerenderConnection(connection) {
        // Remove old connection line
        const oldLine = document.querySelector(`line[data-id="${connection.id}"]`);
        if (oldLine) {
            oldLine.remove();
        }

        // Re-render
        this.renderConnection(connection);
    }

    addTaskSpecificProperties(element) {
        // Task-specific property templates
        const templates = {
            userTask: [
                { key: 'assignee', label: 'Assignee', type: 'text', placeholder: 'user@example.com' },
                { key: 'candidateGroups', label: 'Candidate Groups', type: 'text', placeholder: 'managers, approvers' },
                { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
                { key: 'dueDate', label: 'Due Date', type: 'text', placeholder: 'ISO date or expression' }
            ],
            serviceTask: [
                { key: 'implementation', label: 'Implementation', type: 'select', options: ['Java Class', 'Expression', 'Delegate Expression', 'External', 'Web Service'] },
                { key: 'class', label: 'Java Class', type: 'text', placeholder: 'com.example.MyDelegate' },
                { key: 'expression', label: 'Expression', type: 'text', placeholder: '${myBean.execute()}' },
                { key: 'resultVariable', label: 'Result Variable', type: 'text', placeholder: 'result' },
                { key: 'topic', label: 'External Task Topic', type: 'text', placeholder: 'payment-processing' }
            ],
            scriptTask: [
                { key: 'scriptFormat', label: 'Script Format', type: 'select', options: ['JavaScript', 'Groovy', 'Python', 'Ruby'] },
                { key: 'script', label: 'Script', type: 'textarea', placeholder: 'Enter script code...' },
                { key: 'resultVariable', label: 'Result Variable', type: 'text', placeholder: 'scriptResult' }
            ],
            sendTask: [
                { key: 'messageType', label: 'Message Type', type: 'select', options: ['Email', 'SMS', 'Push Notification', 'Webhook', 'Message Queue'] },
                { key: 'to', label: 'To', type: 'text', placeholder: 'recipient@example.com' },
                { key: 'subject', label: 'Subject', type: 'text', placeholder: 'Email subject' },
                { key: 'messageBody', label: 'Message Body', type: 'textarea', placeholder: 'Message content...' },
                { key: 'useGmail', label: 'Use Gmail API', type: 'checkbox', helpText: 'Send emails via Gmail (requires OAuth setup)' },
                { key: 'fromEmail', label: 'From Email (optional)', type: 'text', placeholder: 'sender@gmail.com' },
                { key: 'htmlFormat', label: 'HTML Format', type: 'checkbox', helpText: 'Send message as HTML instead of plain text' },
                { key: 'includeApprovalLinks', label: 'Include Approval Links', type: 'checkbox', helpText: 'Add approve/deny buttons to email (requires ngrok URL)' },
                { key: 'approvalMessageRef', label: 'Approval Message Ref', type: 'text', placeholder: 'approvalRequest' },
                { key: 'approvalCorrelationKey', label: 'Approval Correlation Key', type: 'text', placeholder: '${orderId}', helpText: 'Use ${variable} to reference context variables' }
            ],
            receiveTask: [
                { key: 'messageRef', label: 'Message Reference', type: 'text', placeholder: 'paymentConfirmation' },
                { key: 'correlationKey', label: 'Correlation Key', type: 'text', placeholder: '${orderId}', helpText: 'Use ${variable} to reference context variables' },
                { key: 'timeout', label: 'Timeout (ms)', type: 'number', placeholder: '30000' },
                { key: 'useWebhook', label: 'Use Webhook', type: 'checkbox', helpText: 'Wait for external webhook message instead of simulating' }
            ],
            businessRuleTask: [
                { key: 'decisionRef', label: 'Decision Reference', type: 'text', placeholder: 'discountRules' },
                { key: 'resultVariable', label: 'Result Variable', type: 'text', placeholder: 'decisionResult' },
                { key: 'decisionTable', label: 'Decision Table', type: 'text', placeholder: 'path/to/rules.dmn' }
            ],
            agenticTask: [
                { key: 'agentType', label: 'Agent Type', type: 'text', placeholder: 'nlp-classifier, decision-maker' },
                { key: 'model', label: 'AI Model', type: 'select', options: ['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet', 'gemini-pro'] },
                { key: 'capabilities', label: 'Capabilities', type: 'text', placeholder: 'intent-detection, sentiment-analysis' },
                { key: 'confidenceThreshold', label: 'Confidence Threshold', type: 'number', placeholder: '0.85' },
                { key: 'maxRetries', label: 'Max Retries', type: 'number', placeholder: '3' },
                { key: 'learningEnabled', label: 'Learning Enabled', type: 'checkbox' }
            ],
            callActivity: [
                { key: 'calledElement', label: 'Called Process', type: 'text', placeholder: 'subprocess-id' },
                { key: 'calledElementBinding', label: 'Binding', type: 'select', options: ['latest', 'deployment', 'version'] },
                { key: 'inheritVariables', label: 'Inherit Variables', type: 'checkbox' },
                { key: 'async', label: 'Asynchronous', type: 'checkbox' }
            ],
            timerIntermediateCatchEvent: [
                { key: 'timerType', label: 'Timer Type', type: 'select', options: ['duration', 'date', 'cycle'] },
                { key: 'timerDuration', label: 'Duration', type: 'text', placeholder: 'PT5M (5 minutes), PT1H (1 hour), P1D (1 day)' },
                { key: 'timerDate', label: 'Date/Time', type: 'text', placeholder: '2024-12-25T10:00:00Z' },
                { key: 'timerCycle', label: 'Cycle (Cron)', type: 'text', placeholder: 'R3/PT10M (repeat 3 times every 10 min)' }
            ],
            boundaryTimerEvent: [
                { key: 'timerType', label: 'Timer Type', type: 'select', options: ['duration', 'date'] },
                { key: 'timerDuration', label: 'Duration (Timeout)', type: 'text', placeholder: 'PT30M (30 minutes), PT2H (2 hours)' },
                { key: 'timerDate', label: 'Date/Time (Deadline)', type: 'text', placeholder: '2024-12-31T23:59:59Z' },
                { key: 'cancelActivity', label: 'Cancel Activity', type: 'checkbox', defaultValue: true },
                { key: 'attachedTo', label: 'Attached To Task ID', type: 'text', placeholder: 'task_element_id' }
            ]
        };

        const template = templates[element.type];
        if (!template) return;

        // Add section header
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'property-section-header';
        sectionHeader.innerHTML = `<h4>Task-Specific Properties</h4>`;
        this.propertiesContent.appendChild(sectionHeader);

        // Initialize properties if needed
        if (!element.properties) element.properties = {};

        template.forEach(field => {
            const group = document.createElement('div');
            group.className = 'property-group';

            const label = document.createElement('label');
            label.textContent = field.label;
            group.appendChild(label);

            let input;
            if (field.type === 'select') {
                input = document.createElement('select');
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = '-- Select --';
                input.appendChild(emptyOption);

                field.options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = opt;
                    if (element.properties[field.key] === opt) option.selected = true;
                    input.appendChild(option);
                });
            } else if (field.type === 'textarea') {
                input = document.createElement('textarea');
                input.value = element.properties[field.key] || '';
                input.placeholder = field.placeholder || '';
            } else if (field.type === 'checkbox') {
                input = document.createElement('input');
                input.type = 'checkbox';
                input.checked = element.properties[field.key] || false;
            } else if (field.type === 'number') {
                input = document.createElement('input');
                input.type = 'number';
                input.value = element.properties[field.key] || '';
                input.placeholder = field.placeholder || '';
                input.step = field.key === 'confidenceThreshold' ? '0.01' : '1';
            } else {
                input = document.createElement('input');
                input.type = 'text';
                input.value = element.properties[field.key] || '';
                input.placeholder = field.placeholder || '';
            }

            input.addEventListener(field.type === 'checkbox' ? 'change' : 'input', (e) => {
                if (!element.properties) element.properties = {};
                element.properties[field.key] = field.type === 'checkbox' ? e.target.checked : e.target.value;
            });

            group.appendChild(input);

            // Add help text if provided
            if (field.helpText) {
                const helpText = document.createElement('small');
                helpText.className = 'help-text';
                helpText.style.display = 'block';
                helpText.style.marginTop = '0.25rem';
                helpText.style.color = '#6c757d';
                helpText.style.fontSize = '0.85rem';
                helpText.textContent = field.helpText;
                group.appendChild(helpText);
            }

            this.propertiesContent.appendChild(group);
        });

        // Add special fields for Agentic Task
        if (element.type === 'agenticTask') {
            this.addAgenticTaskFields(element);
        }
    }

    addAgenticTaskFields(element) {
        // Initialize custom properties if needed
        if (!element.properties.custom) {
            element.properties.custom = {
                systemPrompt: '',
                mcpTools: []
            };
        }

        // System Prompt Section
        const promptSection = document.createElement('div');
        promptSection.className = 'property-section-header';
        promptSection.innerHTML = `<h4>AI Configuration</h4>`;
        this.propertiesContent.appendChild(promptSection);

        // System Prompt
        const promptGroup = document.createElement('div');
        promptGroup.className = 'property-group';

        const promptLabel = document.createElement('label');
        promptLabel.textContent = 'System Prompt';
        promptGroup.appendChild(promptLabel);

        const promptTextarea = document.createElement('textarea');
        promptTextarea.rows = 8;
        promptTextarea.value = element.properties.custom.systemPrompt || '';
        promptTextarea.placeholder = `You are an expert DevOps engineer analyzing system logs.

Your tasks:
1. Read and parse log files using MCP tools
2. Search for error patterns
3. Identify root causes
4. Classify issue severity
5. Generate diagnostic steps`;
        promptTextarea.addEventListener('input', (e) => {
            if (!element.properties.custom) element.properties.custom = {};
            element.properties.custom.systemPrompt = e.target.value;
        });
        promptGroup.appendChild(promptTextarea);
        this.propertiesContent.appendChild(promptGroup);

        // MCP Tools Section
        const mcpSection = document.createElement('div');
        mcpSection.className = 'property-section-header';
        mcpSection.innerHTML = `<h4>MCP Tools</h4>`;
        this.propertiesContent.appendChild(mcpSection);

        const mcpHelp = document.createElement('p');
        mcpHelp.className = 'help-text';
        mcpHelp.textContent = 'Configure which MCP tools this agent can use. Tools should match your MCP server configuration.';
        this.propertiesContent.appendChild(mcpHelp);

        // MCP Tools Container
        const mcpToolsContainer = document.createElement('div');
        mcpToolsContainer.className = 'mcp-tools-container';
        mcpToolsContainer.id = `mcp-tools-${element.id}`;

        // Render existing MCP tools
        const currentTools = element.properties.custom.mcpTools || [];
        currentTools.forEach(tool => {
            const toolRow = this.createMCPToolRow(element, tool);
            mcpToolsContainer.appendChild(toolRow);
        });

        this.propertiesContent.appendChild(mcpToolsContainer);

        // Add MCP Tool button
        const addMCPBtn = document.createElement('button');
        addMCPBtn.className = 'btn-small';
        addMCPBtn.textContent = '+ Add MCP Tool';
        addMCPBtn.style.marginTop = '0.5rem';
        addMCPBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const toolRow = this.createMCPToolRow(element, '');
            mcpToolsContainer.appendChild(toolRow);
        });
        this.propertiesContent.appendChild(addMCPBtn);

        // Common MCP Tools quick add
        const quickAddSection = document.createElement('div');
        quickAddSection.className = 'quick-add-section';
        quickAddSection.style.marginTop = '1rem';
        quickAddSection.style.padding = '0.75rem';
        quickAddSection.style.background = '#f8f9fa';
        quickAddSection.style.borderRadius = '4px';

        const quickAddLabel = document.createElement('div');
        quickAddLabel.innerHTML = '<strong>Quick Add Common Tools:</strong>';
        quickAddLabel.style.marginBottom = '0.5rem';
        quickAddSection.appendChild(quickAddLabel);

        const commonTools = [
            { name: 'filesystem', tools: ['filesystem-read', 'filesystem-write', 'filesystem-list'] },
            { name: 'search', tools: ['grep-search', 'regex-match'] },
            { name: 'logs', tools: ['log-parser', 'error-classifier'] },
            { name: 'web', tools: ['fetch-url', 'scrape-content'] },
            { name: 'database', tools: ['query-db', 'schema-info'] },
            { name: 'redhat-security', tools: ['search_cve', 'get_rhsa', 'search_affected_packages', 'get_errata'] },
            { name: 'redhat-kb', tools: ['search_kb', 'get_kb_article', 'search_solutions', 'search_by_symptom'] }
        ];

        commonTools.forEach(category => {
            const categoryBtn = document.createElement('button');
            categoryBtn.className = 'btn-small';
            categoryBtn.textContent = category.name;
            categoryBtn.style.marginRight = '0.5rem';
            categoryBtn.style.marginBottom = '0.5rem';
            categoryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // Add all tools from this category
                category.tools.forEach(tool => {
                    if (!element.properties.custom.mcpTools) {
                        element.properties.custom.mcpTools = [];
                    }
                    if (!element.properties.custom.mcpTools.includes(tool)) {
                        element.properties.custom.mcpTools.push(tool);
                        const toolRow = this.createMCPToolRow(element, tool);
                        mcpToolsContainer.appendChild(toolRow);
                    }
                });
            });
            quickAddSection.appendChild(categoryBtn);
        });

        this.propertiesContent.appendChild(quickAddSection);
    }

    createMCPToolRow(element, toolName) {
        const row = document.createElement('div');
        row.className = 'mcp-tool-row';
        row.style.display = 'flex';
        row.style.gap = '0.5rem';
        row.style.marginBottom = '0.5rem';
        row.style.alignItems = 'center';

        const toolInput = document.createElement('input');
        toolInput.type = 'text';
        toolInput.placeholder = 'MCP tool name (e.g., filesystem-read)';
        toolInput.value = toolName;
        toolInput.style.flex = '1';
        toolInput.className = 'mcp-tool-input';

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = '×';
        deleteBtn.className = 'btn-small btn-danger';
        deleteBtn.style.padding = '0.2rem 0.5rem';

        // Store original value
        let originalValue = toolName;

        const updateTools = () => {
            if (!element.properties.custom) element.properties.custom = {};
            if (!element.properties.custom.mcpTools) element.properties.custom.mcpTools = [];

            // Remove old value
            const index = element.properties.custom.mcpTools.indexOf(originalValue);
            if (index > -1) {
                element.properties.custom.mcpTools.splice(index, 1);
            }

            // Add new value
            if (toolInput.value) {
                element.properties.custom.mcpTools.push(toolInput.value);
                originalValue = toolInput.value;
            }
        };

        toolInput.addEventListener('input', updateTools);

        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!element.properties.custom.mcpTools) element.properties.custom.mcpTools = [];
            const index = element.properties.custom.mcpTools.indexOf(originalValue);
            if (index > -1) {
                element.properties.custom.mcpTools.splice(index, 1);
            }
            row.remove();
        });

        row.appendChild(toolInput);
        row.appendChild(deleteBtn);

        return row;
    }

    addCustomPropertiesEditor(element) {
        // Add section header
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'property-section-header';
        sectionHeader.innerHTML = `<h4>Custom Properties</h4>`;
        this.propertiesContent.appendChild(sectionHeader);

        // Initialize custom properties if needed
        if (!element.properties) element.properties = {};
        if (!element.properties.custom) element.properties.custom = {};

        // Container for custom properties
        const customPropsContainer = document.createElement('div');
        customPropsContainer.className = 'custom-properties-container';
        customPropsContainer.id = `custom-props-${element.id}`;

        // Render existing custom properties
        Object.entries(element.properties.custom).forEach(([key, value]) => {
            const propRow = this.createCustomPropertyRow(element, key, value);
            customPropsContainer.appendChild(propRow);
        });

        this.propertiesContent.appendChild(customPropsContainer);

        // Add new property button
        const addBtn = document.createElement('button');
        addBtn.className = 'btn-small';
        addBtn.textContent = '+ Add Custom Property';
        addBtn.style.marginTop = '0.5rem';
        addBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const propRow = this.createCustomPropertyRow(element, '', '');
            customPropsContainer.appendChild(propRow);
        });
        this.propertiesContent.appendChild(addBtn);
    }

    createCustomPropertyRow(element, key, value) {
        const row = document.createElement('div');
        row.className = 'custom-property-row';

        const keyInput = document.createElement('input');
        keyInput.type = 'text';
        keyInput.placeholder = 'Property Name';
        keyInput.value = key;
        keyInput.className = 'custom-prop-key';

        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.placeholder = 'Value';
        valueInput.value = value;
        valueInput.className = 'custom-prop-value';

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = '×';
        deleteBtn.className = 'btn-small btn-danger';
        deleteBtn.style.padding = '0.2rem 0.5rem';

        const updateProperty = () => {
            if (!element.properties) element.properties = {};
            if (!element.properties.custom) element.properties.custom = {};

            // Remove old key if it changed
            if (key && key !== keyInput.value) {
                delete element.properties.custom[key];
            }

            // Set new key-value
            if (keyInput.value) {
                element.properties.custom[keyInput.value] = valueInput.value;
                key = keyInput.value;
            }
        };

        keyInput.addEventListener('input', updateProperty);
        valueInput.addEventListener('input', updateProperty);

        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (key && element.properties.custom) {
                delete element.properties.custom[key];
            }
            row.remove();
        });

        row.appendChild(keyInput);
        row.appendChild(valueInput);
        row.appendChild(deleteBtn);

        return row;
    }

    toggleSubProcess(element) {
        if (element.type !== 'subProcess') return;

        element.expanded = !element.expanded;

        // If expanding for the first time, add default child elements
        if (element.expanded && element.childElements.length === 0) {
            this.initializeSubProcessChildren(element);
        }

        // Re-render the subprocess
        this.rerenderElements();
    }

    initializeSubProcessChildren(subprocess) {
        // Add default start and end events inside the subprocess
        const centerX = 0;
        const centerY = 0;

        subprocess.childElements.push({
            id: this.generateId(),
            type: 'startEvent',
            name: 'Start',
            x: centerX - 100,
            y: centerY,
            properties: {}
        });

        subprocess.childElements.push({
            id: this.generateId(),
            type: 'endEvent',
            name: 'End',
            x: centerX + 100,
            y: centerY,
            properties: {}
        });
    }

    renderSubProcessChildren(parentGroup, subprocess) {
        const childGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        childGroup.setAttribute('class', 'subprocess-children');

        // Render child elements (relative to subprocess center)
        subprocess.childElements.forEach(child => {
            const childElement = this.createSubProcessChildShape(child);
            childGroup.appendChild(childElement);
        });

        // Render child connections
        subprocess.childConnections.forEach(conn => {
            const connection = this.createSubProcessConnection(conn, subprocess);
            if (connection) childGroup.appendChild(connection);
        });

        parentGroup.appendChild(childGroup);
    }

    createSubProcessChildShape(element) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'subprocess-child-element');
        g.setAttribute('data-child-id', element.id);
        g.setAttribute('transform', `translate(${element.x}, ${element.y})`);

        // Simplified rendering for child elements
        if (element.type.includes('Event')) {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', 0);
            circle.setAttribute('cy', 0);
            circle.setAttribute('r', 12);
            circle.setAttribute('class', 'bpmn-event');
            circle.setAttribute('fill', 'white');
            circle.setAttribute('stroke-width', element.type === 'endEvent' ? 3 : 1.5);
            g.appendChild(circle);

            // Label below the event
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', 0);
            text.setAttribute('y', 26);
            text.setAttribute('class', 'subprocess-child-text');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', 9);
            text.setAttribute('fill', '#2c3e50');
            text.textContent = element.name;
            g.appendChild(text);
        } else if (element.type.includes('Gateway')) {
            // Gateway rendering
            const diamond = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            diamond.setAttribute('d', 'M 0 -18 L 18 0 L 0 18 L -18 0 Z');
            diamond.setAttribute('class', 'bpmn-gateway');
            diamond.setAttribute('fill', 'white');
            diamond.setAttribute('stroke-width', 2);
            g.appendChild(diamond);

            // Add gateway symbol based on type
            if (element.type === 'exclusiveGateway') {
                const x = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                x.setAttribute('x', 0);
                x.setAttribute('y', 6);
                x.setAttribute('text-anchor', 'middle');
                x.setAttribute('font-size', 16);
                x.setAttribute('font-weight', 'bold');
                x.textContent = '×';
                g.appendChild(x);
            }

            // Label below
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', 0);
            text.setAttribute('y', 32);
            text.setAttribute('class', 'subprocess-child-text');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', 9);
            text.setAttribute('fill', '#2c3e50');
            text.textContent = element.name;
            g.appendChild(text);
        } else {
            // Task rendering
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', -35);
            rect.setAttribute('y', -20);
            rect.setAttribute('width', 70);
            rect.setAttribute('height', 40);
            rect.setAttribute('rx', 4);
            rect.setAttribute('class', 'bpmn-task');
            rect.setAttribute('fill', 'white');
            rect.setAttribute('stroke-width', 1.5);
            g.appendChild(rect);

            // Wrapped text inside the task
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', 0);
            text.setAttribute('y', 2);
            text.setAttribute('class', 'subprocess-child-text');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', 9);
            text.setAttribute('fill', '#2c3e50');

            // Wrap long text
            const words = element.name.split(' ');
            if (words.length > 2 || element.name.length > 12) {
                // Multi-line
                const tspan1 = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
                tspan1.setAttribute('x', 0);
                tspan1.setAttribute('dy', -4);
                tspan1.textContent = words.slice(0, Math.ceil(words.length / 2)).join(' ');
                text.appendChild(tspan1);

                const tspan2 = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
                tspan2.setAttribute('x', 0);
                tspan2.setAttribute('dy', 10);
                tspan2.textContent = words.slice(Math.ceil(words.length / 2)).join(' ');
                text.appendChild(tspan2);
            } else {
                text.textContent = element.name;
            }

            g.appendChild(text);
        }

        return g;
    }

    createSubProcessConnection(conn, subprocess) {
        const fromEl = subprocess.childElements.find(e => e.id === conn.from);
        const toEl = subprocess.childElements.find(e => e.id === conn.to);

        if (!fromEl || !toEl) return null;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', fromEl.x);
        line.setAttribute('y1', fromEl.y);
        line.setAttribute('x2', toEl.x);
        line.setAttribute('y2', toEl.y);
        line.setAttribute('class', 'bpmn-connection');
        line.setAttribute('stroke-width', 1.5);
        line.setAttribute('marker-end', 'url(#arrowhead)');

        return line;
    }

    rerenderElement(element) {
        const svgElement = document.querySelector(`[data-id="${element.id}"]`);
        if (svgElement && element.type !== 'pool') {
            const textElement = svgElement.querySelector('.element-text');
            if (textElement) {
                textElement.textContent = element.name;
            }
        }
    }

    rerenderElements() {
        // Full re-render of all elements (used when type changes)
        this.elementsLayer.innerHTML = '';
        this.elements.forEach(element => this.renderElement(element));
        this.connectionsLayer.innerHTML = '';
        this.connections.forEach(connection => this.renderConnection(connection));
    }

    rerenderPools() {
        this.poolsLayer.innerHTML = '';
        this.pools.forEach(pool => this.renderPool(pool));
    }

    handleCanvasClick(e) {
        if (e.target === this.canvas || e.target === this.mainGroup) {
            this.deselectAll();
        }
    }

    handleCanvasMouseMove(e) {
        // Could be used for connection preview
    }

    deselectAll() {
        if (this.selectedElement) {
            const prev = document.querySelector(`[data-id="${this.selectedElement.id}"]`);
            if (prev) prev.classList.remove('selected');
            this.selectedElement = null;
            this.propertiesContent.innerHTML = '<p class="placeholder">Select an element to edit properties</p>';
        }
    }

    enterConnectionMode() {
        alert('Click on a connection point (small circles) of an element to start drawing a connection, then click on another connection point to complete it.');
    }

    handleConnectionPoint(element, point) {
        if (!this.connectionStart) {
            this.connectionStart = { element, point };
        } else {
            this.createConnection(this.connectionStart.element, element);
            this.connectionStart = null;
        }
    }

    createConnection(from, to) {
        if (from.id === to.id) return;

        const connection = {
            id: this.generateId(),
            type: 'sequenceFlow',
            name: '',
            from: from.id,
            to: to.id,
            properties: {}
        };

        this.connections.push(connection);
        this.renderConnection(connection);
        this.saveState(); // Save state for undo
    }

    renderConnection(connection) {
        const fromElement = this.elements.find(e => e.id === connection.from);
        const toElement = this.elements.find(e => e.id === connection.to);

        if (!fromElement || !toElement) return;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', fromElement.x);
        line.setAttribute('y1', fromElement.y);
        line.setAttribute('x2', toElement.x);
        line.setAttribute('y2', toElement.y);
        line.setAttribute('class', 'bpmn-connection');
        line.setAttribute('marker-end', 'url(#arrowhead)');
        line.setAttribute('data-id', connection.id);

        line.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectElement(connection);
        });

        this.connectionsLayer.appendChild(line);
    }

    updateConnections(elementId) {
        this.connections.forEach(connection => {
            if (connection.from === elementId || connection.to === elementId) {
                const line = document.querySelector(`line[data-id="${connection.id}"]`);
                if (line) {
                    const fromElement = this.elements.find(e => e.id === connection.from);
                    const toElement = this.elements.find(e => e.id === connection.to);

                    if (fromElement && toElement) {
                        line.setAttribute('x1', fromElement.x);
                        line.setAttribute('y1', fromElement.y);
                        line.setAttribute('x2', toElement.x);
                        line.setAttribute('y2', toElement.y);
                    }
                }
            }
        });
    }

    deleteSelected() {
        if (!this.selectedElement) {
            alert('Please select an element to delete');
            return;
        }

        const element = this.selectedElement;
        const id = element.id;
        const elementName = element.name || element.type || 'element';

        // Confirm deletion
        if (!confirm(`Delete "${elementName}"?`)) {
            return;
        }

        // Remove from arrays
        this.elements = this.elements.filter(e => e.id !== id);
        this.connections = this.connections.filter(c => c.id !== id && c.from !== id && c.to !== id);
        this.pools = this.pools.filter(p => p.id !== id);

        // Remove from subprocess child elements if applicable
        this.elements.forEach(el => {
            if (el.childElements) {
                el.childElements = el.childElements.filter(child => child.id !== id);
            }
            if (el.childConnections) {
                el.childConnections = el.childConnections.filter(conn =>
                    conn.id !== id && conn.from !== id && conn.to !== id
                );
            }
        });

        // Remove from DOM
        const svgElement = document.querySelector(`[data-id="${id}"]`);
        if (svgElement) {
            svgElement.remove();
        }

        // Remove associated connections from DOM
        this.connectionsLayer.querySelectorAll('.bpmn-connection').forEach(conn => {
            const connId = conn.getAttribute('data-id');
            if (!this.connections.find(c => c.id === connId)) {
                conn.remove();
            }
        });

        // Also remove any connection lines associated with this element
        document.querySelectorAll(`line[data-id]`).forEach(line => {
            const lineData = this.connections.find(c => c.id === line.getAttribute('data-id'));
            if (!lineData) {
                line.remove();
            }
        });

        // Clear selection
        this.selectedElement = null;
        this.propertiesContent.innerHTML = '<p class="placeholder">Select an element to edit properties</p>';

        console.log(`Deleted element: ${elementName} (${id})`);

        this.saveState(); // Save state for undo
    }

    setZoom(zoom) {
        this.zoom = Math.max(0.1, Math.min(3, zoom));
        this.updateTransform();
    }

    updateTransform() {
        this.mainGroup.setAttribute('transform',
            `translate(${this.panX}, ${this.panY}) scale(${this.zoom})`);
    }

    handlePanStart(e) {
        // Start panning with middle mouse button or space + left click
        if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
            e.preventDefault();
            this.isPanning = true;
            this.panStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
            this.canvas.style.cursor = 'grabbing';
        }
    }

    handlePanMove(e) {
        if (this.isPanning) {
            e.preventDefault();
            this.panX = e.clientX - this.panStart.x;
            this.panY = e.clientY - this.panStart.y;
            this.updateTransform();
        }
    }

    handlePanEnd(e) {
        if (this.isPanning) {
            this.isPanning = false;
            this.canvas.style.cursor = 'default';
        }
    }

    handleWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.setZoom(this.zoom + delta);
    }

    resetView() {
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        this.updateTransform();
    }

    fitToView() {
        if (this.elements.length === 0 && this.pools.length === 0) {
            this.resetView();
            return;
        }

        // Calculate bounding box of all elements
        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        // Include elements
        this.elements.forEach(elem => {
            minX = Math.min(minX, elem.x);
            minY = Math.min(minY, elem.y);
            maxX = Math.max(maxX, elem.x + 100); // Assuming 100px element width
            maxY = Math.max(maxY, elem.y + 80);  // Assuming 80px element height
        });

        // Include pools
        this.pools.forEach(pool => {
            minX = Math.min(minX, pool.x);
            minY = Math.min(minY, pool.y);
            maxX = Math.max(maxX, pool.x + pool.width);
            maxY = Math.max(maxY, pool.y + pool.height);
        });

        // Add some padding
        const padding = 50;
        minX -= padding;
        minY -= padding;
        maxX += padding;
        maxY += padding;

        // Calculate canvas dimensions
        const canvasRect = this.canvas.getBoundingClientRect();
        const contentWidth = maxX - minX;
        const contentHeight = maxY - minY;

        // Calculate zoom to fit
        const zoomX = canvasRect.width / contentWidth;
        const zoomY = canvasRect.height / contentHeight;
        const newZoom = Math.min(zoomX, zoomY, 1.5); // Cap at 1.5x

        // Calculate pan to center
        const scaledWidth = contentWidth * newZoom;
        const scaledHeight = contentHeight * newZoom;
        const newPanX = (canvasRect.width - scaledWidth) / 2 - minX * newZoom;
        const newPanY = (canvasRect.height - scaledHeight) / 2 - minY * newZoom;

        this.zoom = newZoom;
        this.panX = newPanX;
        this.panY = newPanY;
        this.updateTransform();
    }

    newDiagram(skipConfirm = false) {
        if (skipConfirm || confirm('Create a new diagram? This will clear the current diagram.')) {
            this.elements = [];
            this.connections = [];
            this.pools = [];
            this.selectedElement = null;
            this.idCounter = 0;

            this.poolsLayer.innerHTML = '';
            this.connectionsLayer.innerHTML = '';
            this.elementsLayer.innerHTML = '';
            this.propertiesContent.innerHTML = '<p class="placeholder">Select an element to edit properties</p>';
        }
    }

    exportYAML() {
        const data = {
            process: {
                id: 'process_1',
                name: 'BPMN Process',
                pools: this.pools.map(pool => ({
                    id: pool.id,
                    name: pool.name,
                    x: pool.x,
                    y: pool.y,
                    width: pool.width,
                    height: pool.height,
                    lanes: pool.lanes
                })),
                elements: this.elements.map(element => {
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

                    // Include subprocess-specific fields
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
                connections: this.connections.map(connection => ({
                    id: connection.id,
                    type: connection.type,
                    name: connection.name,
                    from: connection.from,
                    to: connection.to,
                    properties: connection.properties || {}
                }))
            }
        };

        const yaml = jsyaml.dump(data, { indent: 2 });
        document.getElementById('yamlOutput').value = yaml;
        document.getElementById('yamlModal').classList.add('active');
    }

    importYAML(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const yaml = e.target.result;
                const data = jsyaml.load(yaml);

                this.newDiagram(true);

                if (data.process) {
                    if (data.process.pools) {
                        data.process.pools.forEach(pool => {
                            this.pools.push(pool);
                            this.renderPool(pool);
                        });
                    }

                    if (data.process.elements) {
                        data.process.elements.forEach(element => {
                            // Ensure subprocess fields are initialized
                            if (element.type === 'subProcess') {
                                element.expanded = element.expanded || false;
                                element.width = element.width || 300;
                                element.height = element.height || 200;
                                element.childElements = element.childElements || [];
                                element.childConnections = element.childConnections || [];
                            }
                            this.elements.push(element);
                            this.renderElement(element);
                        });
                    }

                    if (data.process.connections) {
                        data.process.connections.forEach(connection => {
                            // Ensure properties object exists
                            if (!connection.properties) {
                                connection.properties = {};
                            }
                            this.connections.push(connection);
                            this.renderConnection(connection);
                        });
                    }

                    this.idCounter = Math.max(
                        ...this.pools.map(p => parseInt(p.id.split('_')[1]) || 0),
                        ...this.elements.map(e => parseInt(e.id.split('_')[1]) || 0),
                        ...this.connections.map(c => parseInt(c.id.split('_')[1]) || 0),
                        0
                    );
                }

                // Auto-fit the imported workflow to view after a small delay
                setTimeout(() => {
                    this.fitToView();
                }, 100);

                alert('YAML imported successfully!');
            } catch (error) {
                alert('Error importing YAML: ' + error.message);
            }
        };
        reader.readAsText(file);
        event.target.value = '';
    }

    copyYAML() {
        const textarea = document.getElementById('yamlOutput');
        textarea.select();
        document.execCommand('copy');
        alert('YAML copied to clipboard!');
    }

    downloadYAML() {
        const yaml = document.getElementById('yamlOutput').value;
        const blob = new Blob([yaml], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'bpmn_diagram.yaml';
        a.click();
        URL.revokeObjectURL(url);
    }

    // ===== UNDO/REDO FUNCTIONALITY =====

    saveState() {
        // Don't save state during undo/redo operations
        if (this.isUndoRedoAction) return;

        // Create deep copy of current state
        const state = {
            elements: JSON.parse(JSON.stringify(this.elements)),
            connections: JSON.parse(JSON.stringify(this.connections)),
            pools: JSON.parse(JSON.stringify(this.pools)),
            idCounter: this.idCounter
        };

        // Add to undo stack
        this.undoStack.push(state);

        // Limit stack size
        if (this.undoStack.length > this.maxUndoSteps) {
            this.undoStack.shift();
        }

        // Clear redo stack when new action is performed
        this.redoStack = [];

        // Update button states
        this.updateUndoRedoButtons();
    }

    undo() {
        if (this.undoStack.length === 0) {
            console.log('Nothing to undo');
            return;
        }

        // Save current state to redo stack
        const currentState = {
            elements: JSON.parse(JSON.stringify(this.elements)),
            connections: JSON.parse(JSON.stringify(this.connections)),
            pools: JSON.parse(JSON.stringify(this.pools)),
            idCounter: this.idCounter
        };
        this.redoStack.push(currentState);

        // Get previous state from undo stack
        const previousState = this.undoStack.pop();

        // Restore previous state
        this.isUndoRedoAction = true;
        this.restoreState(previousState);
        this.isUndoRedoAction = false;

        // Update button states
        this.updateUndoRedoButtons();

        console.log('Undo performed');
    }

    redo() {
        if (this.redoStack.length === 0) {
            console.log('Nothing to redo');
            return;
        }

        // Save current state to undo stack
        const currentState = {
            elements: JSON.parse(JSON.stringify(this.elements)),
            connections: JSON.parse(JSON.stringify(this.connections)),
            pools: JSON.parse(JSON.stringify(this.pools)),
            idCounter: this.idCounter
        };
        this.undoStack.push(currentState);

        // Get next state from redo stack
        const nextState = this.redoStack.pop();

        // Restore next state
        this.isUndoRedoAction = true;
        this.restoreState(nextState);
        this.isUndoRedoAction = false;

        // Update button states
        this.updateUndoRedoButtons();

        console.log('Redo performed');
    }

    restoreState(state) {
        // Restore data
        this.elements = JSON.parse(JSON.stringify(state.elements));
        this.connections = JSON.parse(JSON.stringify(state.connections));
        this.pools = JSON.parse(JSON.stringify(state.pools));
        this.idCounter = state.idCounter;

        // Clear selection
        this.selectedElement = null;

        // Re-render everything
        this.rerenderAll();
    }

    rerenderAll() {
        // Clear DOM
        this.poolsLayer.innerHTML = '';
        this.elementsLayer.innerHTML = '';
        this.connectionsLayer.innerHTML = '';

        // Re-render pools
        this.pools.forEach(pool => this.renderPool(pool));

        // Re-render elements
        this.elements.forEach(element => this.renderElement(element));

        // Re-render connections
        this.connections.forEach(connection => this.renderConnection(connection));

        // Clear properties panel
        this.propertiesContent.innerHTML = '<p class="placeholder">Select an element to edit properties</p>';
    }

    updateUndoRedoButtons() {
        const undoBtn = document.getElementById('undoBtn');
        const redoBtn = document.getElementById('redoBtn');

        if (undoBtn) {
            undoBtn.disabled = this.undoStack.length === 0;
            undoBtn.style.opacity = this.undoStack.length === 0 ? '0.5' : '1';
        }

        if (redoBtn) {
            redoBtn.disabled = this.redoStack.length === 0;
            redoBtn.style.opacity = this.redoStack.length === 0 ? '0.5' : '1';
        }
    }

    // ===== COLLAPSIBLE PALETTE SECTIONS =====

    setupCollapsibleSections() {
        const sections = document.querySelectorAll('.palette-section');

        sections.forEach(section => {
            const header = section.querySelector('h4');
            if (!header) return;

            // Load collapsed state from localStorage
            const sectionName = header.textContent.trim();
            const isCollapsed = localStorage.getItem(`palette-section-${sectionName}`) === 'true';

            if (isCollapsed) {
                section.classList.add('collapsed');
            }

            // Add click handler
            header.addEventListener('click', () => {
                section.classList.toggle('collapsed');

                // Save state to localStorage
                const collapsed = section.classList.contains('collapsed');
                localStorage.setItem(`palette-section-${sectionName}`, collapsed);
            });
        });
    }

    // ===== THEME MANAGEMENT =====

    setupThemeSelector() {
        const themeSelect = document.getElementById('themeSelect');
        if (!themeSelect) return;

        themeSelect.addEventListener('change', (e) => {
            this.setTheme(e.target.value);
        });
    }

    loadTheme() {
        // Load theme from localStorage or use default
        const savedTheme = localStorage.getItem('bpmn-modeler-theme') || 'blue';
        this.setTheme(savedTheme);

        // Update select dropdown
        const themeSelect = document.getElementById('themeSelect');
        if (themeSelect) {
            themeSelect.value = savedTheme;
        }
    }

    setTheme(themeName) {
        // Apply theme to document
        if (themeName === 'blue') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', themeName);
        }

        // Save to localStorage
        localStorage.setItem('bpmn-modeler-theme', themeName);

        console.log(`Theme changed to: ${themeName}`);
    }
}

// Initialize the application
const modeler = new BPMNModeler();
