import math
import random

from ..models.task_model import (
    count_tasks_by_owner,
    create_many_tasks,
    create_task,
    delete_task_by_id,
    find_task_by_id,
    list_tasks_by_owner,
    update_task_by_id,
)


class TaskServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def validate_number(value, field_name, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskServiceError(f"{field_name} must be a number.")

    try:
        number = float(value)
    except OverflowError:
        raise TaskServiceError(f"{field_name} is too large.") from None

    if not math.isfinite(number):
        raise TaskServiceError(f"{field_name} must be finite.")

    if number < 0 or (number == 0 and not allow_zero):
        requirement = "zero or greater" if allow_zero else "greater than zero"
        raise TaskServiceError(f"{field_name} must be {requirement}.")

    return number


def validate_integer(value, field_name, minimum, maximum):
    if isinstance(value, bool):
        raise TaskServiceError(f"{field_name} must be an integer.")

    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise TaskServiceError(
                f"{field_name} must be an integer."
            ) from None

    if not isinstance(value, int):
        raise TaskServiceError(f"{field_name} must be an integer.")

    if not minimum <= value <= maximum:
        raise TaskServiceError(
            f"{field_name} must be between {minimum} and {maximum}."
        )

    return value


def validate_object(data, allowed_fields):
    if not isinstance(data, dict):
        raise TaskServiceError("Request body must be a JSON object.")

    unknown = set(data) - allowed_fields
    if unknown:
        raise TaskServiceError(
            f"Unknown fields: {', '.join(sorted(unknown))}."
        )


def validate_task_fields(data, partial=False):
    validate_object(data, {"name", "work_mi", "arrival_time"})

    if partial and not data:
        raise TaskServiceError("Supply at least one editable field.")

    fields = {}

    if not partial or "name" in data:
        name = data.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise TaskServiceError(
                "Task name must contain between 1 and 120 characters."
            )
        fields["name"] = name.strip()

    if not partial or "work_mi" in data:
        fields["work_mi"] = validate_number(
            data.get("work_mi"), "work_mi"
        )

    if not partial or "arrival_time" in data:
        fields["arrival_time"] = validate_number(
            data.get("arrival_time", 0),
            "arrival_time",
            allow_zero=True,
        )

    return fields


def serialize_task(task):
    result = {
        "id": str(task["_id"]),
        "name": task["name"],
        "work_mi": task["work_mi"],
        "arrival_time": task["arrival_time"],
        "created_at": task["created_at"].isoformat(),
    }
    if "updated_at" in task:
        result["updated_at"] = task["updated_at"].isoformat()
    return result


def create_task_for_user(owner_id, data):
    fields = validate_task_fields(data)
    return serialize_task(create_task(owner_id=owner_id, **fields))


def list_tasks_for_user(owner_id, page=1, limit=20):
    page = validate_integer(page, "page", 1, 1_000_000)
    limit = validate_integer(limit, "limit", 1, 100)

    tasks = list_tasks_by_owner(
        owner_id,
        skip=(page - 1) * limit,
        limit=limit,
    )
    total = count_tasks_by_owner(owner_id)

    return {
        "tasks": [serialize_task(task) for task in tasks],
        "page": page,
        "limit": limit,
        "count": len(tasks),
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


def get_task_for_user(owner_id, task_id):
    task = find_task_by_id(owner_id, task_id)
    if task is None:
        raise TaskServiceError("Task not found.", status_code=404)
    return serialize_task(task)


def update_task_for_user(owner_id, task_id, data):
    fields = validate_task_fields(data, partial=True)
    task = update_task_by_id(owner_id, task_id, fields)
    if task is None:
        raise TaskServiceError("Task not found.", status_code=404)
    return serialize_task(task)


def delete_task_for_user(owner_id, task_id):
    if not delete_task_by_id(owner_id, task_id):
        raise TaskServiceError("Task not found.", status_code=404)


def generate_tasks_for_user(owner_id, data):
    validate_object(
        data,
        {
            "count",
            "seed",
            "min_work_mi",
            "max_work_mi",
            "min_arrival_time",
            "max_arrival_time",
        },
    )

    count = validate_integer(data.get("count"), "count", 1, 1000)
    seed = validate_integer(data.get("seed", 42), "seed", 0, 2**32 - 1)

    min_work = validate_number(
        data.get("min_work_mi", 100), "min_work_mi"
    )
    max_work = validate_number(
        data.get("max_work_mi", 1000), "max_work_mi"
    )
    min_arrival = validate_number(
        data.get("min_arrival_time", 0),
        "min_arrival_time",
        allow_zero=True,
    )
    max_arrival = validate_number(
        data.get("max_arrival_time", 0),
        "max_arrival_time",
        allow_zero=True,
    )

    if min_work > max_work:
        raise TaskServiceError(
            "min_work_mi cannot exceed max_work_mi."
        )
    if min_arrival > max_arrival:
        raise TaskServiceError(
            "min_arrival_time cannot exceed max_arrival_time."
        )

    rng = random.Random(seed)
    tasks = [
        {
            "name": f"Generated Task {index + 1}",
            "work_mi": rng.uniform(min_work, max_work),
            "arrival_time": rng.uniform(min_arrival, max_arrival),
        }
        for index in range(count)
    ]

    documents = create_many_tasks(owner_id, tasks)

    return {
        "tasks": [serialize_task(task) for task in documents],
        "count": len(documents),
        "seed": seed,
    }