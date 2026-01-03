# Loops and Parallel Events - Complete Guide

## Quick Answer to Your Question

**Q: How can this BPMN handle:**
1. **Preserving Task Results in Loops** ✅ IMPLEMENTED
2. **Multi-Instance Loops** ✅ IMPLEMENTED
3. **Multiple Events in Different Phases** ✅ ALREADY WORKING

### Summary of Capabilities

| Feature | Status | How It Works |
|---------|--------|--------------|
| **Multi-Instance Parallel** | ✅ Full Support | Execute task N times simultaneously, collect all results |
| **Multi-Instance Sequential** | ✅ Full Support | Execute task N times one-by-one, results in order |
| **Standard Loops** | ✅ Full Support | Repeat task until condition is false |
| **Result Preservation** | ✅ Full Support | Results stored in context arrays |
| **Parallel Events** | ✅ Full Support | Multiple async event streams run simultaneously |
| **Event Synchronization** | ✅ Full Support | Parallel gateway joins wait for all paths |

## 1. Multi-Instance Loops - Result Preservation

### Parallel Multi-Instance

Execute the same task multiple times in parallel and collect all results.

**YAML Configuration:**
```yaml
- id: task_process_items
  type: scriptTask
  name: Process Item
  properties:
    # Multi-Instance Settings
    isMultiInstance: true
    isSequential: false          # Parallel execution
    inputCollection: orders       # Array to iterate over
    inputElement: order           # Variable name for current item
    outputCollection: results     # Where to store results
    outputElement: result         # What to collect from each iteration

    # Script runs once per item
    scriptFormat: python
    script: |
      # Available variables:
      # - order: Current item from orders array
      # - loopCounter: 0-based iteration index
      # - nrOfInstances: Total number of iterations
      # - nrOfActiveInstances: Currently running (parallel only)

      processed_data = process_order(order)

      # This will be collected into 'results' array
      result = {
        'orderId': order['id'],
        'data': processed_data,
        'iteration': loopCounter
      }
```

**How Results Are Preserved:**

```python
# After loop completes, context contains:
results = [
  {'orderId': 'A', 'data': {...}, 'iteration': 0},
  {'orderId': 'B', 'data': {...}, 'iteration': 1},
  {'orderId': 'C', 'data': {...}, 'iteration': 2}
]

# Access in next task:
total_processed = len(results)
all_order_ids = [r['orderId'] for r in results]
```

### Sequential Multi-Instance

Execute iterations one after another - useful when order matters or when previous results affect next iteration.

```yaml
- id: task_sequential_approval
  type: userTask
  name: Get Approval
  properties:
    isMultiInstance: true
    isSequential: true           # One at a time
    inputCollection: approvers
    inputElement: approver
    outputCollection: approvals
    outputElement: decision
```

**Result Preservation in Sequential Mode:**

```python
# Results maintain order:
approvals = [
  {'approver': 'manager', 'decision': 'approved'},
  {'approver': 'director', 'decision': 'approved'},
  {'approver': 'cfo', 'decision': 'rejected'}
]

# Check if all approved:
all_approved = all(a['decision'] == 'approved' for a in approvals)
```

## 2. Standard Loops - Retry Pattern

Repeat a task until a condition is met (like retry logic).

**YAML Configuration:**
```yaml
- id: task_call_api
  type: scriptTask
  name: Call API with Retry
  properties:
    # Standard Loop Settings
    loopCondition: "${retry_count < max_retries and not success}"
    loopMaximum: 5               # Safety limit

    scriptFormat: python
    script: |
      # Loop counter is automatically available
      retry_count = loopCounter

      # Try the operation
      success = call_external_api()

      if not success:
        backoff = 2 ** retry_count
        print(f"Retry {retry_count + 1} failed, waiting {backoff}s")
        time.sleep(backoff)
```

**How Loop Counter Is Preserved:**

```python
# loopCounter is automatically injected:
# - Iteration 0: loopCounter = 0
# - Iteration 1: loopCounter = 1
# - Iteration 2: loopCounter = 2

# Use it to track state across iterations:
if loopCounter == 0:
  retry_count = 0
  max_retries = 3
else:
  retry_count = loopCounter  # Preserved from previous iteration
```

## 3. Multiple Events in Different Phases

### Parallel Event Streams

The workflow engine uses Python's `asyncio` to handle multiple independent event streams simultaneously.

**Example: Payment + Inventory + Shipping**

```yaml
elements:
  # Fork gateway starts 3 parallel paths
  - id: gateway_fork
    type: parallelGateway

  # Path 1: Payment processing
  - id: task_payment
    type: scriptTask
    properties:
      script: |
        # This runs in parallel with other paths
        process_payment()

  # Timeout boundary (independent event stream)
  - id: timer_payment
    type: timerBoundaryEvent
    attachedToRef: task_payment
    properties:
      timerDuration: PT10M

  # Path 2: Inventory (runs simultaneously)
  - id: task_inventory
    type: scriptTask

  # Another independent timer
  - id: timer_inventory
    type: timerBoundaryEvent
    attachedToRef: task_inventory
    properties:
      timerDuration: PT15M

  # Join gateway waits for ALL paths
  - id: gateway_join
    type: parallelGateway

connections:
  # Fork
  - from: gateway_fork
    to: task_payment

  - from: gateway_fork
    to: task_inventory

  # Join (waits for both)
  - from: task_payment
    to: gateway_join

  - from: task_inventory
    to: gateway_join
```

### How Multiple Events Work Simultaneously

**Engine Implementation:**
```python
# When parallel gateway fork is reached:
async def execute_parallel_paths(paths):
    # Create async task for each path
    tasks = [
        asyncio.create_task(execute_path(path1)),  # Payment
        asyncio.create_task(execute_path(path2)),  # Inventory
        asyncio.create_task(execute_path(path3))   # Shipping
    ]

    # All execute simultaneously
    results = await asyncio.gather(*tasks)

# Each path has its own event stream:
# - Path 1: task_payment + timer_payment boundary
# - Path 2: task_inventory + timer_inventory boundary
# - Path 3: task_shipping

# Events fire independently based on their own conditions
```

### Context Preservation Across Parallel Paths

**Problem:** Each parallel path needs its own context but must share results.

**Solution:** Copy context for each path, merge results at join.

```python
# Path 1 (Payment)
payment_authorized = True
payment_auth_code = "AUTH-123"

# Path 2 (Inventory) - runs simultaneously
inventory_reserved = True
reservation_id = "RES-456"

# Path 3 (Shipping) - also simultaneous
shipping_cost = 15.00

# After join, all variables are available:
if payment_authorized and inventory_reserved:
    complete_order(payment_auth_code, reservation_id, shipping_cost)
```

## 4. Real-World Example: Batch Processing with Progress

**Scenario:** Process 100 orders in parallel, preserve all results, show progress.

```yaml
- id: task_batch_process
  type: scriptTask
  name: Process Order
  properties:
    isMultiInstance: true
    isSequential: false
    inputCollection: orders      # 100 orders
    inputElement: order
    outputCollection: processedOrders
    outputElement: result

    script: |
      # This runs 100 times in parallel

      # Progress tracking (automatic)
      print(f"Processing {loopCounter + 1}/{nrOfInstances}")

      # Process this order
      total = sum(item['price'] for item in order['items'])

      # Result for this instance
      result = {
        'orderId': order['id'],
        'total': total,
        'status': 'processed',
        'iteration': loopCounter
      }

# Next task can access all 100 results:
- id: task_generate_report
  type: scriptTask
  properties:
    script: |
      # processedOrders contains all 100 results
      total_revenue = sum(order['total'] for order in processedOrders)
      successful = len([o for o in processedOrders if o['status'] == 'processed'])

      print(f"Processed {successful}/{len(processedOrders)} orders")
      print(f"Total revenue: ${total_revenue}")
```

## 5. Testing the Examples

### Test Multi-Instance Parallel

```bash
# Start workflow
python3 -m backend.start_workflow \
  workflows/multi-instance-parallel-example.yaml \
  context-examples/multi-instance-parallel-context.json
```

**Expected Output:**
```
🔄 Executing multi-instance task: Process Item
   Collection: orders (5 items)
   Mode: Parallel

   Instance 1/5: Processing order
   Instance 2/5: Processing order
   Instance 3/5: Processing order
   Instance 4/5: Processing order
   Instance 5/5: Processing order

✅ Multi-instance complete: 5 results stored in processedOrders

📊 BATCH PROCESSING SUMMARY
Total Orders Processed: 5
Total Revenue: $3085.00
Average Order Value: $617.00
```

### Test Standard Loop (Retry)

```bash
python3 -m backend.start_workflow \
  workflows/standard-loop-retry-example.yaml \
  context-examples/standard-loop-retry-context.json
```

**Expected Output:**
```
🔁 Executing standard loop task: Call External API
   Condition: ${retry_count < max_retries and not success}
   Maximum iterations: 5

   Loop iteration 1
🔄 API Call Attempt 1/3
❌ API call failed (attempt 1)
   Waiting 1s before retry...

   Loop iteration 2
🔄 API Call Attempt 2/3
❌ API call failed (attempt 2)
   Waiting 2s before retry...

   Loop iteration 3
🔄 API Call Attempt 3/3
✅ API call succeeded!

✅ Standard loop complete: 3 iterations
```

### Test Parallel Events with Sync

```bash
python3 -m backend.start_workflow \
  workflows/parallel-events-sync-example.yaml \
  context-examples/parallel-events-sync-context.json
```

**Expected Output:**
```
🔀 Parallel Gateway Fork: Start Parallel Processing

💳 Payment Path: Authorizing payment...
📦 Inventory Path: Reserving inventory...
🚚 Shipping Path: Calculating shipping...

✅ Payment authorized: AUTH-order-par
✅ Inventory reserved: RES-order-par
✅ Shipping calculated: $23.75 (Standard Ground)

🔀 Parallel Gateway Join: Join All Processes
   Waiting for 3 paths to complete...
   All paths joined!

✅ ORDER COMPLETED SUCCESSFULLY
Payment: AUTH-order-par
Inventory: RES-order-par
Shipping: $23.75
```

## 6. Advanced Patterns

### Pattern 1: Nested Multi-Instance

Process batches of items, where each batch is processed in parallel, but batches are sequential.

```yaml
# Outer loop: Sequential batches
- id: task_process_batch
  type: scriptTask
  properties:
    isMultiInstance: true
    isSequential: true           # One batch at a time
    inputCollection: batches
    inputElement: batch
    outputCollection: batchResults

    script: |
      # Inner loop: Parallel items within batch
      # (Would need separate subprocess for true nesting)
      results = []
      for item in batch:
        results.append(process_item(item))

      result = {
        'batchId': batch['id'],
        'items': results
      }
```

### Pattern 2: Loop with Error Accumulation

Collect errors from each iteration for batch error reporting.

```yaml
- id: task_validate_items
  type: scriptTask
  properties:
    isMultiInstance: true
    isSequential: false
    inputCollection: items
    inputElement: item
    outputCollection: validationResults
    outputElement: result

    script: |
      errors = []

      if not item.get('name'):
        errors.append('Missing name')
      if item.get('price', 0) <= 0:
        errors.append('Invalid price')

      result = {
        'item': item['id'],
        'valid': len(errors) == 0,
        'errors': errors
      }

# Next task
- id: task_check_validation
  type: scriptTask
  properties:
    script: |
      failed_items = [r for r in validationResults if not r['valid']]

      if failed_items:
        print(f"❌ {len(failed_items)} items failed validation:")
        for item in failed_items:
          print(f"  {item['item']}: {', '.join(item['errors'])}")
```

### Pattern 3: Dynamic Parallel Paths

Number of parallel paths determined at runtime.

```yaml
- id: task_process_regions
  type: scriptTask
  properties:
    isMultiInstance: true
    isSequential: false
    inputCollection: regions     # Could be 3 or 300 regions
    inputElement: region
    outputCollection: regionalResults

    script: |
      # Each region processed in parallel
      # Automatically scales to any number of regions
      sales_data = fetch_sales_for_region(region)

      result = {
        'region': region['name'],
        'sales': sales_data['total'],
        'timestamp': time.time()
      }
```

## 7. Performance Considerations

### Multi-Instance Limits

```python
# Don't do this:
orders = range(10000)  # 10,000 parallel tasks!

# Instead, batch them:
batch_size = 100
batches = [orders[i:i+batch_size] for i in range(0, len(orders), batch_size)]

# Process batches sequentially, items within batch in parallel
```

### Context Size Management

```python
# Bad: Storing huge results in every iteration
result = {
  'data': entire_database_dump,  # Don't do this!
  'iteration': loopCounter
}

# Good: Store only what you need
result = {
  'id': record_id,
  'status': 'processed',
  'summary': compute_summary(data)  # Aggregated data only
}
```

## 8. Debugging Tips

### Enable Loop Logging

```yaml
script: |
  print(f"=== Loop Iteration {loopCounter}/{nrOfInstances} ===")
  print(f"Input: {inputElement}")
  print(f"Context keys: {list(context.keys())}")

  # Your logic here

  print(f"Output: {result}")
  print(f"=== End Iteration {loopCounter} ===")
```

### Track Parallel Progress

```yaml
script: |
  import time

  start = time.time()
  # Process item
  elapsed = time.time() - start

  result = {
    'item': item['id'],
    'elapsed': elapsed,
    'thread': threading.current_thread().name
  }

# Later, analyze performance
- id: task_analyze
  properties:
    script: |
      avg_time = sum(r['elapsed'] for r in results) / len(results)
      slowest = max(results, key=lambda r: r['elapsed'])
      print(f"Average: {avg_time:.2f}s, Slowest: {slowest['item']}")
```

## Summary

| Question | Answer |
|----------|--------|
| **Can it preserve task results in loops?** | ✅ YES - `outputCollection` stores results from each iteration |
| **Can it handle multi-instance loops?** | ✅ YES - Both parallel and sequential modes fully supported |
| **Can it handle multiple events at different phases?** | ✅ YES - Async architecture allows independent event streams |
| **How are results collected?** | Automatically into arrays specified by `outputCollection` |
| **How do parallel events synchronize?** | Parallel gateway join waits for all incoming paths |
| **What happens if an iteration fails?** | Error is caught and stored in results array with `{'error': str(e)}` |
| **Can I nest loops?** | Partially - use subprocesses for true nested multi-instance |
| **Performance limits?** | Use batching for >100 parallel instances |

**Example Workflows Created:**
1. `multi-instance-parallel-example.yaml` - Batch order processing
2. `standard-loop-retry-example.yaml` - API retry with exponential backoff
3. `parallel-events-sync-example.yaml` - Payment + Inventory + Shipping in parallel

All workflows are production-ready and demonstrate best practices for loop result preservation and parallel event handling! 🎉
