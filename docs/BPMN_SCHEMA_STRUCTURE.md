# BPMN Schema Structure

How to read and understand the BPMN XML schema in raw form, without a visual editor.

---

## Table of Contents

1. [What is BPMN XML](#what-is-bpmn-xml)
2. [Root Element: definitions](#root-element-definitions)
3. [The process Element](#the-process-element)
4. [Node Types](#node-types)
   - [startEvent](#startevent)
   - [userTask](#usertask)
   - [scriptTask](#scripttask)
   - [exclusiveGateway](#exclusivegateway)
   - [endEvent](#endevent)
5. [Connecting Nodes: sequenceFlow](#connecting-nodes-sequenceflow)
6. [Complete Flow Walkthrough](#complete-flow-walkthrough)
7. [Human-Readable IDs](#human-readable-ids)
8. [Camunda Extensions](#camunda-extensions)
9. [Visual Diagram Section (bpmndi)](#visual-diagram-section-bpmndi)
10. [Key Takeaways](#key-takeaways)

---

## What is BPMN XML

BPMN (Business Process Model and Notation) is a standardized graphical notation for drawing business processes. The XML representation is the machine-readable format that engines like SpiffWorkflow execute.

Key principle: **the XML is the single source of truth**. The visual diagram is just a rendering of this XML.

---

## Root Element: definitions

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions
    xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
    id="Definitions_1ntgj7m"
    targetNamespace="http://bpmn.io/schema/bpmn">
```

| Attribute | Purpose |
|-----------|---------|
| `xmlns:bpmn` | Standard BPMN 2.0 namespace |
| `xmlns:camunda` | Camunda-specific extensions (forms, scripts) |
| `id` | Unique document identifier |
| `targetNamespace` | XML namespace for this document |

---

## The process Element

```xml
<bpmn:process id="duck_process" isExecutable="true">
```

| Attribute | Purpose |
|-----------|---------|
| `id` | Process identifier. Used in code: `parser.get_spec("duck_process")` |
| `isExecutable="true"` | Marks this as a runnable process (not just a diagram) |

All process nodes live inside this element.

---

## Node Types

### startEvent

Entry point of the process.

```xml
<bpmn:startEvent id="start">
  <bpmn:outgoing>flow_start_to_interview</bpmn:outgoing>
</bpmn:startEvent>
```

| Element | Meaning |
|---------|---------|
| `outgoing` | Which sequenceFlow to follow next |

### userTask

A task that requires human interaction. The workflow engine pauses here until `task.complete()` is called.

```xml
<bpmn:userTask id="interview_client" name="Interview Client" camunda:formKey="duck_application">
  <bpmn:extensionElements>
    <camunda:formData>
      <camunda:formField id="variety" label="What is your favorite kind of duck?" type="enum">
        <camunda:value id="Mallard" name="Mallard" />
        <camunda:value id="Wood_Duck" name="Wood Duck" />
      </camunda:formField>
      <camunda:formField id="tolerant" label="I don't mind feathers..." type="boolean" />
      <camunda:formField id="quantity" label="How many ducks?" type="long" />
    </camunda:formData>
  </bpmn:extensionElements>
  <bpmn:incoming>flow_start_to_interview</bpmn:incoming>
  <bpmn:outgoing>flow_interview_to_determine</bpmn:outgoing>
</bpmn:userTask>
```

| Element | Meaning |
|---------|---------|
| `camunda:formKey` | Form identifier for the application |
| `camunda:formField` | Form field definition with id, label, type |
| `camunda:value` | Enum option (id = value sent, name = display text) |
| `incoming` | Which flow leads into this task |
| `outgoing` | Which flow to follow after completion |

**Field types:** `enum`, `boolean`, `long`, `string`, `date`

### scriptTask

An automatic task that executes Python code.

```xml
<bpmn:scriptTask id="determine_worthiness" name="Determine Duck Worthiness">
  <bpmn:incoming>flow_interview_to_determine</bpmn:incoming>
  <bpmn:outgoing>flow_determine_to_check</bpmn:outgoing>
  <bpmn:script>if not tolerant or variety == 'Dead' or quantity > 5:
    is_safe = False
else:
    is_safe = True
</bpmn:script>
</bpmn:scriptTask>
```

| Element | Meaning |
|---------|---------|
| `bpmn:script` | Python code executed by the engine. Variables are shared in the workflow context |

**Important:** Variables created here (`is_safe`) become available to all subsequent nodes.

### exclusiveGateway

A decision point (diamond shape in diagrams). Exactly one outgoing path is chosen based on conditions.

```xml
<bpmn:exclusiveGateway id="check_safety" name="will real duck be safe?">
  <bpmn:incoming>flow_determine_to_check</bpmn:incoming>
  <bpmn:outgoing>flow_safe_to_real</bpmn:outgoing>
  <bpmn:outgoing>flow_unsafe_to_decoy</bpmn:outgoing>
</bpmn:exclusiveGateway>
```

| Element | Meaning |
|---------|---------|
| `outgoing` | Multiple possible exits. Only one is taken |

### endEvent

Process termination. No `outgoing` flows.

```xml
<bpmn:endEvent id="end_real">
  <bpmn:incoming>flow_real_to_end</bpmn:incoming>
</bpmn:endEvent>
```

---

## Connecting Nodes: sequenceFlow

The arrows between nodes. Each flow has a `sourceRef` (where it starts) and `targetRef` (where it ends).

```xml
<!-- Simple flow -->
<bpmn:sequenceFlow
    id="flow_start_to_interview"
    sourceRef="start"
    targetRef="interview_client" />

<!-- Conditional flow -->
<bpmn:sequenceFlow
    id="flow_safe_to_real"
    name="is_safe == True"
    sourceRef="check_safety"
    targetRef="deliver_real_duck">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">
    is_safe == True
  </bpmn:conditionExpression>
</bpmn:sequenceFlow>
```

| Attribute/Element | Meaning |
|-------------------|---------|
| `id` | Flow identifier |
| `sourceRef` | ID of the source node |
| `targetRef` | ID of the target node |
| `name` | Human-readable label (shown on diagram) |
| `conditionExpression` | Python condition for exclusiveGateway branches |

---

## Complete Flow Walkthrough

Reading the schema as a story:

```
start
  → flow_start_to_interview
  → interview_client (user fills form: variety, tolerant, quantity)
  → flow_interview_to_determine
  → determine_worthiness (script calculates is_safe)
  → flow_determine_to_check
  → check_safety (exclusiveGateway)
    → flow_safe_to_real [if is_safe == True]
    → deliver_real_duck (script: print("Delivering a Real Duck!"))
    → flow_real_to_end
    → end_real

    → flow_unsafe_to_decoy [if is_safe == False]
    → deliver_decoy (script: print("Delivering a Decoy Duck!"))
    → flow_decoy_to_end
    → end_decoy
```

---

## Human-Readable IDs

Always use meaningful IDs. Compare:

**Bad (auto-generated):**
```xml
<bpmn:scriptTask id="Activity_0fmjk85" name="Deliver real Duck">
```

**Good (human-readable):**
```xml
<bpmn:scriptTask id="deliver_real_duck" name="Deliver real Duck">
```

Benefits:
- Schema becomes self-documenting
- No need to open a visual editor to understand the flow
- Easier debugging and code review
- Better diffs in version control

Naming convention used in this project:

| Node Type | ID Pattern | Example |
|-----------|------------|---------|
| startEvent | `start` | `start` |
| endEvent | `end_{outcome}` | `end_real`, `end_decoy` |
| userTask | `{action}_{object}` | `interview_client` |
| scriptTask | `{verb}_{noun}` | `determine_worthiness`, `deliver_real_duck` |
| exclusiveGateway | `check_{criteria}` | `check_safety` |
| sequenceFlow | `flow_{source}_to_{target}` | `flow_start_to_interview` |

---

## Camunda Extensions

Standard BPMN doesn't define forms. Camunda adds extensions via `extensionElements`:

```xml
<bpmn:extensionElements>
  <camunda:formData>
    <camunda:formField id="quantity" label="How many?" type="long" />
  </camunda:formData>
</bpmn:extensionElements>
```

These extensions are parsed by `CamundaParser` in SpiffWorkflow and become accessible as `task.task_spec.form.fields`.

---

## Visual Diagram Section (bpmndi)

Everything inside `<bpmndi:BPMNDiagram>` is purely visual — coordinates, sizes, colors. It does not affect execution logic.

```xml
<bpmndi:BPMNDiagram id="BPMNDiagram_1">
  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="duck_process">
    <bpmndi:BPMNShape id="start_di" bpmnElement="start">
      <dc:Bounds x="152" y="192" width="36" height="36" />
    </bpmndi:BPMNShape>
    <!-- ... more shapes and edges ... -->
  </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>
```

When reading BPMN for logic, you can ignore this entire section.

---

## Key Takeaways

1. **XML is the source of truth** — the diagram is just a view
2. **Read `incoming`/`outgoing` to trace the flow** — ignore coordinates
3. **Use meaningful IDs** — the schema becomes documentation
4. **Understand the three layers:**
   - BPMN standard (nodes, flows, gateways)
   - Camunda extensions (forms, scripts)
   - Visual diagram (bpmndi — purely cosmetic)
5. **ScriptTask executes Python** — variables are shared across the workflow
6. **ExclusiveGateway chooses one path** — based on `conditionExpression`
7. **UserTask pauses execution** — until `task.complete()` is called
