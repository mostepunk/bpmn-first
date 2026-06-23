from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.camunda.specs.user_task import EnumFormField, UserTask
from SpiffWorkflow.util.task import TaskState


def show_form(task):
    form = task.task_spec.form

    if task.data is None:
        task.data = {}

    for field in form.fields:
        prompt = field.label
        if isinstance(field, EnumFormField):
            prompt += (
                " (Options: "
                + ", ".join([str(option.id) for option in field.options])
                + ")"
            )
        if field.type == "boolean":
            prompt += " (Options: true, false)"
        prompt += " : "
        answer = input(prompt)
        if field.type == "long":
            answer = int(answer)
        if field.type == "boolean":
            answer = answer.lower().strip()
            answer = answer == "true" or answer == "yes"

        task.data[field.id] = answer


if __name__ == "__main__":
    parser = CamundaParser()
    parser.add_bpmn_file("ducks.bpmn")
    spec = parser.get_spec("duck_process")
    workflow = BpmnWorkflow(spec)

    workflow.do_engine_steps()
    ready_tasks = workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)
    while len(ready_tasks) > 0:
        for task in ready_tasks:
            if isinstance(task.task_spec, UserTask):
                show_form(task)
                print(task.data)
            else:
                print("Complete Task ", task.task_spec.name)
            task.complete()
        workflow.do_engine_steps()
        ready_tasks = workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)
