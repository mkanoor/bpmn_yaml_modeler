# Advanced BPMN Execution Patterns

This document explains how the BPMN workflow engine handles advanced execution patterns.

## 1. Multi-Instance Loops

Multi-instance activities execute the same task multiple times, either sequentially or in parallel, over a collection of items.

### Parallel Multi-Instance
All instances execute simultaneously using asyncio.gather().

```yaml
elements:
  - id: task_process_orders
    type: serviceTask
    name: Process Order
    properties:
      # Multi-instance configuration
      isMultiInstance: true
      isSequential: false  # Parallel execution
      loopCardinality: "${len(orders)}"  # Number of instances
      inputCollection: orders  # Collection to iterate over
      inputElement: order  # Variable name for current item
      outputCollection: processedOrders  # Collect results here
      outputElement: result  # What to collect from each instance
```

**How it works:**
- Engine creates N instances based on `loopCardinality`
- Each instance gets its own context with `order` variable
- All instances execute in parallel
- Results are collected into `processedOrders` array

### Sequential Multi-Instance
Instances execute one after another.

```yaml
  - id: task_approve_sequentially
    type: userTask
    name: Approval Required
    properties:
      isMultiInstance: true
      isSequential: true  # Sequential execution
      inputCollection: approvers
      inputElement: approver
      outputCollection: approvals
      outputElement: decision
```

**How it works:**
- Engine executes instances one by one
- Each instance must complete before the next starts
- Results preserve order
- Context from previous iteration is available

## 2. Standard Loops

Standard loops repeat a task based on a condition.

```yaml
  - id: task_retry_api
    type: serviceTask
    name: Call External API
    properties:
      # Loop configuration
      loopCondition: "${retry_count < max_retries and not success}"
      loopMaximum: 5  # Safety limit
```

**How it works:**
- Task executes, then condition is evaluated
- If condition is true, task executes again
- Loop counter `loopCounter` is automatically available
- Continues until condition is false or maximum reached

## 3. Preserving Task Results in Loops

### Result Collection Patterns

#### Pattern 1: Array Collection
Each iteration adds result to an array.

```python
# In scriptTask inside multi-instance loop
result = {
    'orderId': order['id'],
    'status': 'processed',
    'total': calculate_total(order)
}
# Engine automatically collects into outputCollection
```

Result after loop:
```python
processedOrders = [
    {'orderId': 'A123', 'status': 'processed', 'total': 150.00},
    {'orderId': 'B456', 'status': 'processed', 'total': 200.00},
    {'orderId': 'C789', 'status': 'processed', 'total': 75.50}
]
```

#### Pattern 2: Aggregation
Combine results from all iterations.

```yaml
  - id: task_aggregate
    type: scriptTask
    name: Sum All Totals
    properties:
      script: |
        total_revenue = sum(order['total'] for order in processedOrders)
        average_order = total_revenue / len(processedOrders)
```

#### Pattern 3: Indexed Results
Use loop counter to track iteration.

```python
# Available variables in multi-instance:
# - loopCounter: Current iteration (0-based)
# - nrOfInstances: Total number of iterations
# - nrOfActiveInstances: Currently executing (parallel only)
# - nrOfCompletedInstances: Already finished

result = {
    'iteration': loopCounter,
    'total_iterations': nrOfInstances,
    'data': process_item(inputElement)
}
```

## 4. Multiple Events in Different Phases

### Parallel Event Streams

The engine can handle multiple independent event streams simultaneously.

```yaml
# Example: Order processing with payment timeout
elements:
  # Main flow
  - id: start_order
    type: startEvent

  - id: task_create_order
    type: serviceTask

  - id: task_await_payment
    type: receiveTask
    properties:
      messageRef: payment_received

  # Timer boundary on payment task
  - id: timer_payment_timeout
    type: timerBoundaryEvent
    attachedToRef: task_await_payment
    properties:
      timerDuration: PT10M  # 10 minutes

  # Parallel flow: Inventory reservation
  - id: task_reserve_inventory
    type: serviceTask

  - id: timer_inventory_expiry
    type: timerBoundaryEvent
    attachedToRef: task_reserve_inventory
    properties:
      timerDuration: PT15M  # 15 minutes
```

**How it works:**
1. Main flow starts order creation
2. Two parallel tasks start: await payment & reserve inventory
3. Each has its own timer boundary event
4. Events fire independently based on their own timers
5. Each event path executes in its own async task

### Event Synchronization

Use parallel gateways to synchronize multiple event paths.

```yaml
  # Fork: Start parallel event listeners
  - id: gateway_fork
    type: parallelGateway

  # Path 1: Wait for customer confirmation
  - id: receive_confirmation
    type: receiveTask
    properties:
      messageRef: customer_confirmed

  # Path 2: Wait for payment
  - id: receive_payment
    type: receiveTask
    properties:
      messageRef: payment_received

  # Join: Wait for BOTH events
  - id: gateway_join
    type: parallelGateway

  - id: task_proceed
    type: serviceTask
    name: Process Order
```

**How it works:**
- Fork gateway spawns two async tasks
- Each task waits for its event independently
- Join gateway waits for ALL incoming paths to complete
- Only then does the next task execute

## 5. Context Management Across Phases

### Phase-Specific Context

Each parallel path maintains its own context but can access shared variables.

```python
# In workflow_engine.py
async def execute_parallel_paths(self, paths: List[Element]):
    # Each path gets a copy of context
    tasks = []
    for path in paths:
        # Copy context for isolation
        path_context = self.context.copy()
        task = asyncio.create_task(
            self.execute_path_with_context(path, path_context)
        )
        tasks.append(task)

    # Wait for all paths to complete
    results = await asyncio.gather(*tasks)

    # Merge results back into main context
    for result in results:
        self.context.update(result)
```

### Shared State Pattern

Use specific keys for shared state across parallel paths.

```python
# Task in parallel path A
shared_state['inventory_reserved'] = True
shared_state['reservation_id'] = 'RES-123'

# Task in parallel path B (can read path A's state)
if shared_state.get('inventory_reserved'):
    payment_amount = calculate_with_reservation()
```

## 6. Real-World Examples

### Example 1: Batch Processing with Progress Tracking

```yaml
process:
  elements:
    - id: task_process_batch
      type: scriptTask
      name: Process Items in Batch
      properties:
        isMultiInstance: true
        isSequential: false  # Parallel
        inputCollection: items
        inputElement: item
        outputCollection: results
        outputElement: result
        script: |
          import time

          # Process this item
          print(f"Processing {loopCounter + 1}/{nrOfInstances}: {item['id']}")

          result = {
            'item_id': item['id'],
            'processed_at': time.time(),
            'iteration': loopCounter,
            'status': 'success'
          }

          # Progress is automatically tracked:
          # nrOfCompletedInstances increments after each instance

    - id: task_summary
      type: scriptTask
      name: Generate Summary
      properties:
        script: |
          total_processed = len(results)
          successful = sum(1 for r in results if r['status'] == 'success')
          failed = total_processed - successful

          print(f"Batch complete: {successful}/{total_processed} successful")

          summary = {
            'total': total_processed,
            'successful': successful,
            'failed': failed,
            'results': results
          }
```

### Example 2: Multi-Phase Approval with Timeout

```yaml
process:
  elements:
    # Sequential multi-instance: Each approver in sequence
    - id: task_approvals
      type: userTask
      name: Approval Required
      properties:
        isMultiInstance: true
        isSequential: true
        inputCollection: approvers
        inputElement: approver
        outputCollection: approvals
        outputElement: decision
        assignee: "${approver['email']}"

    # Timeout boundary on entire approval process
    - id: timer_approval_timeout
      type: timerBoundaryEvent
      attachedToRef: task_approvals
      properties:
        timerDuration: PT2H  # 2 hours for all approvals
        cancelActivity: true

    # Timeout path
    - id: task_escalate
      type: sendTask
      name: Escalate to Manager

    # Normal completion path
    - id: gateway_check_approvals
      type: exclusiveGateway

    - id: task_all_approved
      type: serviceTask
      name: Process Approved Request

    - id: task_any_rejected
      type: serviceTask
      name: Handle Rejection

connections:
  - from: task_approvals
    to: gateway_check_approvals

  - from: gateway_check_approvals
    to: task_all_approved
    properties:
      condition: "${all(a['decision'] == 'approved' for a in approvals)}"

  - from: gateway_check_approvals
    to: task_any_rejected
    properties:
      condition: "${any(a['decision'] == 'rejected' for a in approvals)}"

  - from: timer_approval_timeout
    to: task_escalate
```

### Example 3: Parallel API Calls with Individual Timeouts

```yaml
process:
  elements:
    # Multi-instance parallel: Call multiple APIs simultaneously
    - id: task_call_apis
      type: serviceTask
      name: Call External API
      properties:
        isMultiInstance: true
        isSequential: false  # All APIs called in parallel
        inputCollection: api_endpoints
        inputElement: endpoint
        outputCollection: api_responses
        outputElement: response
        script: |
          import requests

          try:
              response = requests.get(
                  endpoint['url'],
                  timeout=endpoint.get('timeout', 30)
              )
              response = {
                  'endpoint': endpoint['name'],
                  'status': response.status_code,
                  'data': response.json(),
                  'success': True
              }
          except Exception as e:
              response = {
                  'endpoint': endpoint['name'],
                  'error': str(e),
                  'success': False
              }

    # Each instance can have its own boundary event
    - id: timer_api_timeout
      type: timerBoundaryEvent
      attachedToRef: task_call_apis
      properties:
        timerDuration: PT1M  # 1 minute per API call
        cancelActivity: true  # Cancel this instance only

    - id: task_aggregate_results
      type: scriptTask
      name: Aggregate API Results
      properties:
        script: |
          successful_apis = [r for r in api_responses if r.get('success')]
          failed_apis = [r for r in api_responses if not r.get('success')]

          aggregated = {
            'total_apis': len(api_endpoints),
            'successful': len(successful_apis),
            'failed': len(failed_apis),
            'responses': api_responses
          }
```

## 7. Implementation Details

### Multi-Instance Execution Flow

```python
async def execute_multi_instance_task(self, task: Element):
    """Execute a multi-instance task"""
    props = task.properties

    # Get collection to iterate over
    collection = self.context.get(props['inputCollection'], [])
    input_var = props['inputElement']
    output_var = props.get('outputElement', 'result')
    is_sequential = props.get('isSequential', False)

    results = []

    if is_sequential:
        # Sequential execution
        for idx, item in enumerate(collection):
            # Create instance context
            instance_context = self.context.copy()
            instance_context[input_var] = item
            instance_context['loopCounter'] = idx
            instance_context['nrOfInstances'] = len(collection)
            instance_context['nrOfCompletedInstances'] = idx

            # Execute instance
            result = await self.execute_task_instance(task, instance_context)
            results.append(result.get(output_var))
    else:
        # Parallel execution
        tasks = []
        for idx, item in enumerate(collection):
            instance_context = self.context.copy()
            instance_context[input_var] = item
            instance_context['loopCounter'] = idx
            instance_context['nrOfInstances'] = len(collection)

            task_coro = self.execute_task_instance(task, instance_context)
            tasks.append(task_coro)

        # Execute all instances in parallel
        instance_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for result in instance_results:
            if isinstance(result, Exception):
                results.append({'error': str(result)})
            else:
                results.append(result.get(output_var))

    # Store results in output collection
    output_collection = props.get('outputCollection')
    if output_collection:
        self.context[output_collection] = results
```

### Standard Loop Execution

```python
async def execute_loop_task(self, task: Element):
    """Execute a task with standard loop"""
    props = task.properties
    loop_condition = props.get('loopCondition')
    loop_maximum = props.get('loopMaximum', 100)

    loop_counter = 0

    while loop_counter < loop_maximum:
        # Add loop counter to context
        self.context['loopCounter'] = loop_counter

        # Execute task
        await self.execute_task(task)

        # Evaluate loop condition
        if loop_condition:
            should_continue = self.gateway_evaluator.evaluate_condition(
                loop_condition,
                self.context
            )
            if not should_continue:
                break
        else:
            # No condition = execute once
            break

        loop_counter += 1
```

### Parallel Gateway Synchronization

```python
async def execute_parallel_gateway_join(self, gateway: Element):
    """Wait for all incoming paths to complete"""
    incoming = self.workflow.get_incoming_connections(gateway)

    # Track which paths have arrived
    if not hasattr(self, 'gateway_arrivals'):
        self.gateway_arrivals = {}

    gateway_key = f"gateway_{gateway.id}"

    if gateway_key not in self.gateway_arrivals:
        self.gateway_arrivals[gateway_key] = set()

    # Mark this path as arrived (would need path tracking)
    current_path_id = self.current_path_id  # Would need to implement
    self.gateway_arrivals[gateway_key].add(current_path_id)

    # Check if all paths have arrived
    if len(self.gateway_arrivals[gateway_key]) == len(incoming):
        # All paths complete - proceed
        logger.info(f"All paths joined at {gateway.name}")
        self.gateway_arrivals.pop(gateway_key)
        return self.workflow.get_outgoing_elements(gateway)
    else:
        # Wait for other paths
        logger.info(f"Waiting at join: {len(self.gateway_arrivals[gateway_key])}/{len(incoming)} arrived")
        return []  # Don't proceed yet
```

## 8. Best Practices

### Loop Result Management

1. **Always name output collections** - Makes debugging easier
2. **Limit collection sizes** - Use pagination for large datasets
3. **Handle errors per instance** - Don't let one failure stop all instances
4. **Use loop counters for progress** - Especially in UI updates

### Parallel Event Handling

1. **Use timeouts** - Every long-running task should have a boundary timer
2. **Graceful degradation** - Handle partial failures in parallel paths
3. **Clear synchronization points** - Use parallel gateway joins explicitly
4. **Context isolation** - Each path should not interfere with others

### Performance Optimization

1. **Parallel when possible** - Use `isSequential: false` for independent items
2. **Batch processing** - Group small items before multi-instance
3. **Resource limits** - Don't spawn thousands of parallel tasks
4. **Async all the way** - Use async/await for I/O operations

## Summary

| Pattern | Current Support | Implementation Status |
|---------|----------------|---------------------|
| Parallel Gateway Fork | ✅ Full | Uses asyncio.gather() |
| Parallel Gateway Join | ⚠️ Simplified | Needs path tracking |
| Multi-Instance Parallel | ❌ Not implemented | Needs enhancement |
| Multi-Instance Sequential | ❌ Not implemented | Needs enhancement |
| Standard Loops | ❌ Not implemented | Needs enhancement |
| Result Collection | ✅ Partial | Context storage works |
| Multiple Concurrent Events | ✅ Full | Async event handlers |
| Event Synchronization | ✅ Full | Gateway evaluation |

**Next Steps:**
1. Implement multi-instance loop support
2. Add standard loop conditions
3. Enhance parallel gateway join synchronization
4. Add loop progress tracking to AG-UI
5. Create comprehensive test workflows
