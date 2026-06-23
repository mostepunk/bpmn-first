# BPMN-First: От демо-проекта к веб-приложению

> **Исходный проект:** [SpiffyDuck](https://github.com/sartography/SpiffyDuck) от Sartography  
> **Статья:** [Build your own Low-Code Business Applications with SpiffWorkflow](https://medium.com/spiffworkflow/build-your-own-low-code-business-applications-with-spiffworkflow-1d0730acc1f3) by Dan Funk  
> **Форк:** [github.com/mostepunk/bpmn-first](https://github.com/mostepunk/bpmn-first)

---

## Что такое SpiffyDuck

SpiffyDuck — это демонстрационный проект, показывающий, как управлять бизнес-логикой через BPMN-схемы. Идея в том, что бизнес-аналитик может изменять поведение приложения, редактируя схему в визуальном редакторе (Camunda Modeler), без изменения кода.

### Оригинальный функционал

- Консольное приложение на Python
- Парсит BPMN-схему через SpiffWorkflow
- Выполняет UserTask через `input()` в терминале
- ScriptTask выполняет Python-код из BPMN
- ExclusiveGateway выбирает ветку по условию

### Оригинальный процесс (упрощённо)

```
Start → Interview Client (форма) → Determine Duck Worthiness (скрипт)
→ Gateway (is_safe?)
  → True:  Deliver Real Duck → End
  → False: Deliver Decoy Duck → End
```

Форма спрашивала:
- `variety` — вид утки (enum: Mallard, Wood Duck, Widgeon, Dead)
- `tolerant` — готов ли терпеть перья дома (boolean)

Скрипт определял: если не tolerant или выбрали Dead → `is_safe = False` (муляж).

---

## Что было сделано в этом форке

### 1. Исправление совместимости с новой версией SpiffWorkflow

Оригинальный код написан под старую версию SpiffWorkflow. При запуске на актуальной версии возникали ошибки:

| Ошибка | Причина | Исправление |
|--------|---------|-------------|
| `ModuleNotFoundError: SpiffWorkflow.camunda.specs.UserTask` | Модуль переименован в `user_task` (мелкий регистр) | `from SpiffWorkflow.camunda.specs.user_task import ...` |
| `AttributeError: 'BpmnWorkflow' object has no attribute 'get_ready_user_tasks'` | API изменился | `workflow.get_tasks(state=TaskState.READY, spec_class=UserTask)` |
| `AttributeError: 'BpmnWorkflow' object has no attribute 'complete_task_from_id'` | Метод перенесён на Task | `task.complete()` |
| `AttributeError: 'Task' object has no attribute 'update_data_var'` | Метод удалён | `task.data[field.id] = answer` |

Также добавлен `if __name__ == "__main__":` для возможности импорта как модуля.

### 2. Добавление веб-интерфейса (FastAPI)

Вместо консольного `input()` создан полноценный веб-сервер:

- **FastAPI** — HTTP-сервер
- **Jinja2** — шаблонизация HTML
- **In-memory storage** — хранение workflow по UUID (в проде → БД)

#### Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Главная: список процессов + кнопка "Создать" |
| `/start` | POST | Создаёт новый экземпляр workflow |
| `/workflow/{id}` | GET | Показывает форму или результат |
| `/workflow/{id}/task/{task_id}/complete` | POST | Принимает данные формы, продолжает workflow |

#### Flow работы с веб-интерфейсом

1. Пользователь открывает `/` и нажимает "Создать процесс"
2. Сервер создаёт `BpmnWorkflow`, запускает `do_engine_steps()`
3. Workflow останавливается на UserTask (состояние READY)
4. Сервер рендерит HTML-форму из `camunda:formData`
5. Пользователь заполняет форму, отправляет POST
6. Сервер приводит типы (long→int, boolean→bool), сохраняет в `task.data`
7. Вызывает `task.complete()`, снова `do_engine_steps()`
8. Движок проходит ScriptTask, Gateway, EndEvent
9. Пользователь видит страницу "Процесс завершен" с результатом

### 3. Читаемые ID в BPMN-схеме

Оригинальные ID были автоматически сгенерированы (например, `Activity_0fmjk85`, `Flow_06xo1t0`). Они нечитаемы для человека.

**Было:**
```xml
<bpmn:scriptTask id="Activity_0fmjk85" name="Deliver real Duck">
```

**Стало:**
```xml
<bpmn:scriptTask id="deliver_real_duck" name="Deliver real Duck">
```

Переименованы все элементы:

| Старое ID | Новое ID | Тип |
|-----------|----------|-----|
| `StartEvent_1` | `start` | startEvent |
| `Flow_1` | `flow_start_to_interview` | sequenceFlow |
| `interview_client` | `interview_client` | userTask (без изменений) |
| `Flow_2` | `flow_interview_to_determine` | sequenceFlow |
| `Activity_1jz3ih0` | `determine_worthiness` | scriptTask |
| `Flow_1olpa6l` | `flow_determine_to_check` | sequenceFlow |
| `Gateway_0vqsmxy` | `check_safety` | exclusiveGateway |
| `Flow_06xo1t0` | `flow_safe_to_real` | sequenceFlow |
| `Flow_0wkvu0e` | `flow_unsafe_to_decoy` | sequenceFlow |
| `Activity_0fmjk85` | `deliver_real_duck` | scriptTask |
| `Flow_4` | `flow_real_to_end` | sequenceFlow |
| `Event_0fj8eo7` | `end_real` | endEvent |
| `Activity_0mwove7` | `deliver_decoy` | scriptTask |
| `Flow_0wmf1w5` | `flow_decoy_to_end` | sequenceFlow |
| `Event_1pkdfjl` | `end_decoy` | endEvent |

Теперь схему можно читать как текст: `start → flow_start_to_interview → interview_client → ...`

### 4. BPMN-first: добавление нового поля без изменения кода

Демонстрация концепции: бизнес-аналитик добавляет поле в схему, и логика приложения меняется автоматически.

**Что добавлено в схему:**
```xml
<camunda:formField id="quantity" label="How many ducks do you want?" type="long" />
```

**Что изменено в скрипте:**
```python
# Было:
if not tolerant or variety == 'Dead':
    is_safe = False

# Стало:
if not tolerant or variety == 'Dead' or quantity > 5:
    is_safe = False
```

**Что изменено в Python-коде:** ничего. FastAPI-сервер уже умеет:
- Динамически генерировать HTML-форму из любых полей `camunda:formData`
- Приводить тип `long` к `int`
- Передавать данные в workflow

**Результат:**
- 2 утки + tolerant + Wood_Duck → настоящая утка
- 10 уток + tolerant + Wood_Duck → муляж (подозрительно много)

---

## Структура проекта

```
bpmn-first/
├── ducks.bpmn              # BPMN-схема (бизнес-логика)
├── ducks.py                # Консольная версия (исправленная)
├── app.py                  # FastAPI веб-сервер
├── requirements.txt        # Зависимости
├── templates/
│   ├── index.html          # Главная: список процессов
│   ├── form.html           # Форма для UserTask
│   ├── completed.html      # Результат: процесс завершен
│   └── waiting.html        # Ожидание (нет задач)
└── README.rst              # Оригинальная документация
```

---

## Как запустить

```bash
# Клонировать
https://github.com/mostepunk/bpmn-first.git

# Создать venv
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить веб-сервер
uvicorn app:app --host 0.0.0.0 --port 8000

# Открыть в браузере
http://localhost:8000/
```

---

## Ключевые выводы

1. **BPMN-first работает:** бизнес-аналитик может менять логику, редактируя только схему. Код адаптируется автоматически.

2. **Читаемые ID важны:** при осмысленных именах схема становится документацией. Не нужно открывать редактор, чтобы понять поток.

3. **Веб-интерфейс обязателен:** консольный `input()` — только для демо. Реальные пользователи работают через браузер.

4. **Типизация данных:** BPMN-формы содержат типы (enum, boolean, long). Сервер должен приводить строки из HTTP к правильным типам Python.

5. **Состояние workflow:** в демо хранится в памяти. Для продакшена нужна сериализация в БД (через `workflow.serialize()`).

---

## Что можно развивать дальше

- **Персистентность:** сохранять workflow в SQLite/PostgreSQL между перезапусками сервера
- **Параллельные процессы:** parallel gateway, subprocesses
- **Таймеры:** boundary timer events ("если через 2 дня не ответили — напоминание")
- **Роли и назначение:** задачи назначаются ролям, не просто "пользователю"
- **Service Task:** вызов внешних API вместо `print()`
- **Версионирование:** новые версии BPMN не ломают запущенные процессы
- **Визуализация:** отображать текущее состояние процесса на диаграмме BPMN
