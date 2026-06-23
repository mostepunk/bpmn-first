# BPMN Execution Walkthrough

Step-by-step explanation of how the BPMN engine executes the workflow, from XML parsing to completion.

---

## Table of Contents

1. [How the Parser Works](#how-the-parser-works)
2. [Stage 1: Parse XML](#stage-1-parse-xml)
3. [Stage 2: Build Spec](#stage-2-build-spec)
4. [Stage 3: Create Workflow Instance](#stage-3-create-workflow-instance)
5. [Stage 4: Execute](#stage-4-execute)
6. [Step-by-Step Execution](#step-by-step-execution)
7. [Task States](#task-states)
8. [Code Example](#code-example)
9. [Key Takeaways](#key-takeaways)

---

## How the Parser Works

SpiffWorkflow's `CamundaParser` processes the XML in four stages. Each stage transforms the raw XML into something the engine can execute.

---

## Stage 1: Parse XML

```python
from SpiffWorkflow.bpmn.parser import CamundaParser

parser = CamundaParser()
parser.add_bpmn_file("ducks.bpmn")
```

What happens:
1. Opens the XML file
2. Validates namespace (`xmlns:bpmn`) and structure
3. Builds an internal DOM tree representation
4. Identifies all `bpmn:process` elements inside

At this point, the parser knows what nodes exist but hasn't connected them into a flow.

---

## Stage 2: Build Spec

```python
spec = parser.get_spec("duck_process")
```

What happens:
1. Finds the `<bpmn:process id="duck_process">` element
2. Creates a `WorkflowSpec` object — the blueprint of the process
3. For each XML node, creates a task spec:
   - `startEvent` → `StartTask` spec
   - `userTask` → `UserTask` spec (with form fields from Camunda extensions)
   - `scriptTask` → `ScriptTask` spec (with Python code from `<bpmn:script>`)
   - `exclusiveGateway` → `ExclusiveGateway` spec
   - `endEvent` → `EndEvent` spec
4. Connects specs via transitions using `sequenceFlow`:
   - `sourceRef` → `targetRef` becomes a transition between task specs
5. Parses Camunda extensions into `form` attributes on UserTask specs

Result: a `WorkflowSpec` object that knows the entire process graph but hasn't been executed yet.

---

## Stage 3: Create Workflow Instance

```python
from SpiffWorkflow.bpmn import BpmnWorkflow

workflow = BpmnWorkflow(spec)
```

What happens:
1. Creates a runtime instance from the static `WorkflowSpec`
2. Builds a task tree starting from `startEvent`
3. Every node in the spec gets a corresponding `Task` object
4. All tasks start in `FUTURE` state (not yet reached)

The workflow instance holds:
- The task tree (current state of execution)
- The data context (variables shared between tasks)
- The spec reference (blueprint)

---

## Stage 4: Execute

```python
workflow.do_engine_steps()
```

What happens:
1. The engine walks through the task tree
2. For each task in `READY` or `WAITING` state:
   - If it's automatic (scriptTask, startEvent, endEvent) — executes immediately
   - If it's a userTask — stops and waits for `task.complete()`
   - If it's a gateway — evaluates conditions and picks one path
3. Updates task states: `FUTURE` → `READY` → `COMPLETED` (or `CANCELLED`)
4. Continues until no more automatic steps can be taken

---

## Step-by-Step Execution

Let's trace the full execution with concrete data.

### Scenario: User wants 2 Wood Ducks, is tolerant

### Initial State (before any execution)

```
[start]              → FUTURE
[interview_client]   → FUTURE
[determine_worthiness] → FUTURE
[check_safety]       → FUTURE
[deliver_real_duck]  → FUTURE
[deliver_decoy]      → FUTURE
[end_real]           → FUTURE
[end_decoy]          → FUTURE

Data context: {} (empty)
```

---

### Step 1: First do_engine_steps()

```python
workflow.do_engine_steps()
```

Engine actions:
1. `start` task is reached → transitions to `COMPLETED`
2. Follows `flow_start_to_interview` → activates `interview_client`
3. `interview_client` is a userTask → transitions to `READY`
4. Engine stops — user input required

```
[start]              → COMPLETED
[interview_client]   → READY ← waiting for user
[determine_worthiness] → FUTURE
[check_safety]       → FUTURE
[deliver_real_duck]  → FUTURE
[deliver_decoy]      → FUTURE
[end_real]           → FUTURE
[end_decoy]          → FUTURE

Data context: {}
```

---

### Step 2: User fills the form

```python
# Get the ready task
tasks = workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)
task = tasks[0]  # interview_client

# Fill form data
task.data["variety"] = "Wood_Duck"
task.data["tolerant"] = True
task.data["quantity"] = 2
```

Form data is stored in the task's data context. These variables will be accessible to subsequent tasks.

---

### Step 3: Complete the task

```python
task.complete()
```

What happens:
1. `interview_client` transitions to `COMPLETED`
2. Form data is merged into the global workflow context
3. The engine is ready to continue

```
[start]              → COMPLETED
[interview_client]   → COMPLETED
[determine_worthiness] → FUTURE
[check_safety]       → FUTURE
[deliver_real_duck]  → FUTURE
[deliver_decoy]      → FUTURE
[end_real]           → FUTURE
[end_decoy]          → FUTURE

Data context: {variety: "Wood_Duck", tolerant: True, quantity: 2}
```

---

### Step 4: Second do_engine_steps()

```python
workflow.do_engine_steps()
```

Engine actions:
1. Follows `flow_interview_to_determine` → activates `determine_worthiness`
2. `determine_worthiness` is a scriptTask → executes Python code:

```python
# Script from BPMN:
if not tolerant or variety == 'Dead' or quantity > 5:
    is_safe = False
else:
    is_safe = True

# With current context:
# not True → False
# "Wood_Duck" == 'Dead' → False
# 2 > 5 → False
# Result: is_safe = True
```

3. Script creates `is_safe = True` in the workflow context
4. `determine_worthiness` transitions to `COMPLETED`
5. Follows `flow_determine_to_check` → activates `check_safety`

```
[start]              → COMPLETED
[interview_client]   → COMPLETED
[determine_worthiness] → COMPLETED
[check_safety]       → READY (gateway evaluating)
[deliver_real_duck]  → FUTURE
[deliver_decoy]      → FUTURE
[end_real]           → FUTURE
[end_decoy]          → FUTURE

Data context: {variety: "Wood_Duck", tolerant: True, quantity: 2, is_safe: True}
```

---

### Step 5: Gateway Evaluation

The `check_safety` exclusiveGateway has two outgoing flows:

```xml
<!-- Flow 1: is_safe == True -->
<sequenceFlow id="flow_safe_to_real" sourceRef="check_safety" targetRef="deliver_real_duck">
  <conditionExpression>is_safe == True</conditionExpression>
</sequenceFlow>

<!-- Flow 2: is_safe == False -->
<sequenceFlow id="flow_unsafe_to_decoy" sourceRef="check_safety" targetRef="deliver_decoy">
  <conditionExpression>is_safe == False</conditionExpression>
</sequenceFlow>
```

Engine evaluates:
- `is_safe == True` → `True == True` → **matches**
- `is_safe == False` → `True == False` → does not match

Only the matching flow is taken. The other branch is marked as `CANCELLED`.

```
[start]              → COMPLETED
[interview_client]   → COMPLETED
[determine_worthiness] → COMPLETED
[check_safety]       → COMPLETED
[deliver_real_duck]  → READY (will auto-execute)
[deliver_decoy]      → CANCELLED ← not taken
[end_real]           → FUTURE
[end_decoy]          → FUTURE
```

---

### Step 6: Execute Real Duck Branch

```python
workflow.do_engine_steps()
```

Engine actions:
1. `deliver_real_duck` is a scriptTask → executes:

```python
print("Delivering a Real Duck!")
```

2. `deliver_real_duck` transitions to `COMPLETED`
3. Follows `flow_real_to_end` → activates `end_real`
4. `end_real` is an endEvent → transitions to `COMPLETED`
5. No more outgoing flows → engine stops

```
[start]              → COMPLETED
[interview_client]   → COMPLETED
[determine_worthiness] → COMPLETED
[check_safety]       → COMPLETED
[deliver_real_duck]  → COMPLETED
[deliver_decoy]      → CANCELLED
[end_real]           → COMPLETED ← process ends here
[end_decoy]          → FUTURE

Data context: {variety: "Wood_Duck", tolerant: True, quantity: 2, is_safe: True}
```

---

### Step 7: Check Completion

```python
workflow.is_completed()  # → True
```

The workflow is complete because an endEvent was reached.

---

## Alternative Scenario: User wants 10 Dead Ducks, not tolerant

### After Step 3 (form data):

```python
task.data["variety"] = "Dead"
task.data["tolerant"] = False
task.data["quantity"] = 10
```

### Step 4: Script Execution

```python
# Script from BPMN:
if not tolerant or variety == 'Dead' or quantity > 5:
    is_safe = False
else:
    is_safe = True

# With current context:
# not False → True ← condition met!
# "Dead" == 'Dead' → True ← condition met!
# 10 > 5 → True ← condition met!
# Result: is_safe = False
```

### Step 5: Gateway Evaluation

- `is_safe == True` → `False == True` → does not match
- `is_safe == False` → `False == False` → **matches**

```
[deliver_real_duck]  → CANCELLED ← not taken
[deliver_decoy]      → READY (will auto-execute)
```

### Step 6: Execute Decoy Branch

```python
print("Delivering a Decoy Duck!")
```

```
[deliver_decoy]      → COMPLETED
[end_decoy]          → COMPLETED ← process ends here
```

---

## Task States

| State | Meaning | When Used |
|-------|---------|-----------|
| `FUTURE` | Task not yet reached | Initial state for all tasks |
| `READY` | Task is waiting to execute | UserTask waiting for input, or auto-task ready to run |
| `COMPLETED` | Task finished successfully | After execution or user completion |
| `CANCELLED` | Task was skipped | Gateway branches not taken |
| `WAITING` | Task waiting for external event | Timer, message, signal |

State transitions:
```
FUTURE → READY → COMPLETED
              → CANCELLED (gateway)
       → WAITING → READY (after event)
```

---

## Code Example

Complete Python code showing the full execution:

```python
from SpiffWorkflow.bpmn.parser import CamundaParser
from SpiffWorkflow.bpmn import BpmnWorkflow
from SpiffWorkflow.camunda.specs.user_task import UserTask
from SpiffWorkflow.task import TaskState

# Stage 1 & 2: Parse and build spec
parser = CamundaParser()
parser.add_bpmn_file("ducks.bpmn")
spec = parser.get_spec("duck_process")

# Stage 3: Create workflow instance
workflow = BpmnWorkflow(spec)

# Stage 4: Execute until user task
workflow.do_engine_steps()

# Get the ready user task
tasks = workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)
task = tasks[0]

# Fill form data
task.data["variety"] = "Wood_Duck"
task.data["tolerant"] = True
task.data["quantity"] = 2

# Complete the task
task.complete()

# Continue execution
workflow.do_engine_steps()

# Check result
print(f"Completed: {workflow.is_completed()}")
print(f"Data: {workflow.data}")
# Output: Completed: True
#         Data: {'variety': 'Wood_Duck', 'tolerant': True, 'quantity': 2, 'is_safe': True}
```

---

## Key Takeaways

1. **Four stages:** Parse XML → Build Spec → Create Instance → Execute
2. **Spec is static** (blueprint), **Workflow is dynamic** (runtime state)
3. **UserTask pauses execution** — the engine stops until `task.complete()`
4. **ScriptTask runs automatically** — Python code executes in the workflow context
5. **Gateway picks one path** — other branches are marked `CANCELLED`
6. **Variables are shared** — data set in one task is available to all subsequent tasks
7. **EndEvent signals completion** — `workflow.is_completed()` returns `True`
8. **Task states tell the story** — `FUTURE` → `READY` → `COMPLETED`/`CANCELLED`
