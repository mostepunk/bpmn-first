# BPMN-First: From Demo Project to Web Application

> **Original project:** [SpiffyDuck](https://github.com/sartography/SpiffyDuck) by Sartography  
> **Article:** [Build your own Low-Code Business Applications with SpiffWorkflow](https://medium.com/spiffworkflow/build-your-own-low-code-business-applications-with-spiffworkflow-1d0730acc1f3) by Dan Funk  
> **Fork:** [github.com/mostepunk/bpmn-first](https://github.com/mostepunk/bpmn-first)

---

## What is SpiffyDuck

SpiffyDuck is a demonstration project showing how to manage business logic through BPMN schemas. The idea is that a business analyst can change application behavior by editing the schema in a visual editor (Camunda Modeler), without touching the code.

### Original Functionality

- Console application in Python
- Parses BPMN schema via SpiffWorkflow
- Executes UserTask via `input()` in terminal
- ScriptTask executes Python code from BPMN
- ExclusiveGateway selects branch by condition

### Original Process (Simplified)

```
Start → Interview Client (form) → Determine Duck Worthiness (script)
→ Gateway (is_safe?)
  → True:  Deliver Real Duck → End
  → False: Deliver Decoy Duck → End
```

The form asked:
- `variety` — duck type (enum: Mallard, Wood Duck, Widgeon, Dead)
- `tolerant` — willing to tolerate feathers at home (boolean)

The script determined: if not tolerant or Dead selected → `is_safe = False` (decoy).

---

## What Was Done in This Fork

### 1. Compatibility Fix for Newer SpiffWorkflow

The original code was written for an older version of SpiffWorkflow. Running on the current version produced errors:

| Error                                                                            | Cause                                     | Fix                                                              |
|----------------------------------------------------------------------------------|-------------------------------------------|------------------------------------------------------------------|
| `ModuleNotFoundError: SpiffWorkflow.camunda.specs.UserTask`                      | Module renamed to `user_task` (lowercase) | `from SpiffWorkflow.camunda.specs.user_task import ...`          |
| `AttributeError: 'BpmnWorkflow' object has no attribute 'get_ready_user_tasks'`  | API changed                               | `workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)` |
| `AttributeError: 'BpmnWorkflow' object has no attribute 'complete_task_from_id'` | Method moved to Task                      | `task.complete()`                                                |
| `AttributeError: 'Task' object has no attribute 'update_data_var'`               | Method removed                            | `task.data[field.id] = answer`                                   |

Also added `if __name__ == "__main__":` for module import capability.

### 2. Web Interface (FastAPI)

Instead of console `input()`, a full web server was created:

- **FastAPI** — HTTP server
- **Jinja2** — HTML templating
- **In-memory storage** — workflow storage by UUID (in production → database)

#### Endpoints

| Endpoint                                 | Method | Description                           |
|------------------------------------------|--------|---------------------------------------|
| `/`                                      | GET    | Home: process list + "Create" button  |
| `/start`                                 | POST   | Creates new workflow instance         |
| `/workflow/{id}`                         | GET    | Shows form or result                  |
| `/workflow/{id}/task/{task_id}/complete` | POST   | Accepts form data, continues workflow |

#### Web Interface Flow

1. User opens `/` and clicks "Create process"
2. Server creates `BpmnWorkflow`, runs `do_engine_steps()`
3. Workflow stops at UserTask (READY state)
4. Server renders HTML form from `camunda:formData`
5. User fills form, submits POST
6. Server casts types (long→int, boolean→bool), saves to `task.data`
7. Calls `task.complete()`, runs `do_engine_steps()` again
8. Engine processes ScriptTask, Gateway, EndEvent
9. User sees "Process completed" page with result

### 3. Human-Readable IDs in BPMN Schema

Original IDs were auto-generated (e.g., `Activity_0fmjk85`, `Flow_06xo1t0`). They are unreadable for humans.

**Before:**
```xml
<bpmn:scriptTask id="Activity_0fmjk85" name="Deliver real Duck">
```

**After:**
```xml
<bpmn:scriptTask id="deliver_real_duck" name="Deliver real Duck">
```

All elements renamed:

| Old ID             | New ID                        | Type                 |
|--------------------|-------------------------------|----------------------|
| `StartEvent_1`     | `start`                       | startEvent           |
| `Flow_1`           | `flow_start_to_interview`     | sequenceFlow         |
| `interview_client` | `interview_client`            | userTask (unchanged) |
| `Flow_2`           | `flow_interview_to_determine` | sequenceFlow         |
| `Activity_1jz3ih0` | `determine_worthiness`        | scriptTask           |
| `Flow_1olpa6l`     | `flow_determine_to_check`     | sequenceFlow         |
| `Gateway_0vqsmxy`  | `check_safety`                | exclusiveGateway     |
| `Flow_06xo1t0`     | `flow_safe_to_real`           | sequenceFlow         |
| `Flow_0wkvu0e`     | `flow_unsafe_to_decoy`        | sequenceFlow         |
| `Activity_0fmjk85` | `deliver_real_duck`           | scriptTask           |
| `Flow_4`           | `flow_real_to_end`            | sequenceFlow         |
| `Event_0fj8eo7`    | `end_real`                    | endEvent             |
| `Activity_0mwove7` | `deliver_decoy`               | scriptTask           |
| `Flow_0wmf1w5`     | `flow_decoy_to_end`           | sequenceFlow         |
| `Event_1pkdfjl`    | `end_decoy`                   | endEvent             |

Now the schema can be read as text: `start → flow_start_to_interview → interview_client → ...`

### 4. BPMN-First: Adding a New Field Without Code Changes

Demonstration of the concept: a business analyst adds a field to the schema, and application logic changes automatically.

**What was added to the schema:**
```xml
<camunda:formField id="quantity" label="How many ducks do you want?" type="long" />
```

**What changed in the script:**
```python
# Before:
if not tolerant or variety == 'Dead':
    is_safe = False

# After:
if not tolerant or variety == 'Dead' or quantity > 5:
    is_safe = False
```

**What changed in Python code:** nothing. The FastAPI server already knows how to:
- Dynamically generate HTML form from any `camunda:formData` fields
- Cast `long` type to `int`
- Pass data into workflow

**Result:**
- 2 ducks + tolerant + Wood_Duck → real duck
- 10 ducks + tolerant + Wood_Duck → decoy (suspiciously many)

---

## Project Structure

```
bpmn-first/
├── ducks.bpmn              # BPMN schema (business logic)
├── ducks.py                # Console version (fixed)
├── app.py                  # FastAPI web server
├── requirements.txt        # Dependencies
├── templates/
│   ├── index.html          # Home: process list
│   ├── form.html           # Form for UserTask
│   ├── completed.html      # Result: process completed
│   └── waiting.html        # Waiting (no tasks)
└── README.rst              # Original documentation
```

---

## How to Run

```bash
# Clone
git clone https://github.com/mostepunk/bpmn-first.git
cd bpmn-first

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start web server
uvicorn app:app --host 0.0.0.0 --port 8000

# Open in browser
http://localhost:8000/
```

---

## Key Takeaways
1. **BPMN-first works:** a business analyst can change logic by editing only the schema. Code adapts automatically.
2. **Human-readable IDs matter:** with meaningful names, the schema becomes documentation. No need to open an editor to understand the flow.
3. **Web interface is essential:** console `input()` is demo-only. Real users work through a browser.
4. **Data typing:** BPMN forms contain types (enum, boolean, long). The server must cast HTTP strings to correct Python types.
5. **Workflow state:** in the demo stored in memory. For production, serialization to a database is needed (via `workflow.serialize()`).

---

## Future Directions

- **Persistence:** save workflows to SQLite/PostgreSQL between server restarts
- **Parallel processes:** parallel gateway, subprocesses
- **Timers:** boundary timer events ("if no response in 2 days — send reminder")
- **Roles and assignment:** tasks assigned to roles, not just "user"
- **Service Task:** calling external APIs instead of `print()`
- **Versioning:** new BPMN versions don't break running processes
- **Visualization:** display current process state on BPMN diagram
