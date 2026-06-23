from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.camunda.specs.user_task import EnumFormField, UserTask
from SpiffWorkflow.util.task import TaskState
import uuid
import json
import os

app = FastAPI()

# Хранилище workflow в памяти (в проде — БД)
workflows = {}

# Парсим BPMN один раз при старте
parser = CamundaParser()
parser.add_bpmn_file("ducks.bpmn")
spec = parser.get_spec("duck_process")

templates = Jinja2Templates(directory="templates")



@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Главная — список активных процессов и кнопка создать новый."""
    return templates.TemplateResponse(request, "index.html", {
        "workflows": workflows
    })


@app.post("/start")
def start_workflow():
    """Создать новый экземпляр workflow."""
    workflow_id = str(uuid.uuid4())[:8]
    workflow = BpmnWorkflow(spec)
    workflow.do_engine_steps()
    workflows[workflow_id] = workflow
    return RedirectResponse(url=f"/workflow/{workflow_id}", status_code=303)


@app.get("/workflow/{workflow_id}", response_class=HTMLResponse)
def workflow_page(request: Request, workflow_id: str):
    """Страница workflow — показывает текущие задачи или результат."""
    if workflow_id not in workflows:
        return HTMLResponse("Workflow not found", status_code=404)

    workflow = workflows[workflow_id]

    # Если workflow завершен
    if workflow.is_completed():
        return templates.TemplateResponse(request, "completed.html", {
            "workflow_id": workflow_id,
            "data": workflow.data
        })

    # Ищем готовые UserTask
    ready_tasks = workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)

    if not ready_tasks:
        # Нет ручных задач — возможно, нужно подождать или ошибка
        return templates.TemplateResponse(request, "waiting.html", {
            "workflow_id": workflow_id
        })

    # Берем первую задачу (в нашем процессе всегда одна)
    task = ready_tasks[0]
    form = task.task_spec.form

    # Формируем описание полей для шаблона
    fields = []
    for field in form.fields:
        field_info = {
            "id": field.id,
            "label": field.label,
            "type": field.type,
            "required": True,
        }
        if isinstance(field, EnumFormField):
            field_info["type"] = "enum"
            field_info["options"] = [{"id": opt.id, "name": opt.name} for opt in field.options]
        elif field.type == "boolean":
            field_info["type"] = "boolean"
        elif field.type == "long":
            field_info["type"] = "number"
        else:
            field_info["type"] = "text"
        fields.append(field_info)

    return templates.TemplateResponse(request, "form.html", {
        "workflow_id": workflow_id,
        "task_id": task.id,
        "task_name": task.task_spec.name,
        "fields": fields
    })


@app.post("/workflow/{workflow_id}/task/{task_id}/complete")
async def complete_task(
    workflow_id: str,
    task_id: str,
    request: Request
):
    """Принять данные формы и продолжить workflow."""
    if workflow_id not in workflows:
        return HTMLResponse("Workflow not found", status_code=404)

    workflow = workflows[workflow_id]

    # Находим задачу по ID
    task = None
    for t in workflow.get_tasks():
        if str(t.id) == task_id:
            task = t
            break

    if task is None:
        return HTMLResponse("Task not found", status_code=404)

    # Читаем данные формы
    form = await request.form()
    for key, value in form.multi_items():
        # value может быть UploadFile или str — берем только str
        if hasattr(value, 'filename'):
            continue
        val_str = str(value)

        # Приводим типы
        field_type = None
        for f in task.task_spec.form.fields:
            if f.id == key:
                field_type = f.type
                break

        if field_type == "long":
            val_str = int(val_str)
        elif field_type == "boolean":
            val_str = val_str.lower() == "true"

        task.data[key] = val_str

    task.complete()
    workflow.do_engine_steps()

    return RedirectResponse(url=f"/workflow/{workflow_id}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
