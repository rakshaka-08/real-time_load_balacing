from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from ..services.auth_service import AuthServiceError, get_current_user
from ..services.task_service import (
    TaskServiceError,
    create_task_for_user,
    delete_task_for_user,
    generate_tasks_for_user,
    get_task_for_user,
    list_tasks_for_user,
    update_task_for_user,
)

task_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def authenticated_task_route(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        try:
            user = get_current_user(get_jwt_identity())
            return view(user["id"], *args, **kwargs)
        except (AuthServiceError, TaskServiceError) as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except PyMongoError:
            current_app.logger.exception("Task database operation failed.")
            return jsonify({
                "error": "Database operation failed. Please try again."
            }), 503

    return wrapped


def read_json_body():
    if not request.is_json:
        raise TaskServiceError(
            "Content-Type must be application/json.",
            status_code=415,
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise TaskServiceError(
            "Request body must be a valid JSON object."
        )
    return data


@task_bp.post("")
@authenticated_task_route
def create(owner_id):
    task = create_task_for_user(owner_id, read_json_body())
    return jsonify({
        "message": "Task created successfully.",
        "task": task,
    }), 201


@task_bp.get("")
@authenticated_task_route
def list_tasks(owner_id):
    result = list_tasks_for_user(
        owner_id,
        page=request.args.get("page", "1"),
        limit=request.args.get("limit", "20"),
    )
    return jsonify(result), 200


@task_bp.post("/generate")
@authenticated_task_route
def generate(owner_id):
    result = generate_tasks_for_user(owner_id, read_json_body())
    return jsonify(result), 201


@task_bp.get("/<task_id>")
@authenticated_task_route
def get_task(owner_id, task_id):
    return jsonify({
        "task": get_task_for_user(owner_id, task_id)
    }), 200


@task_bp.patch("/<task_id>")
@authenticated_task_route
def update_task(owner_id, task_id):
    task = update_task_for_user(owner_id, task_id, read_json_body())
    return jsonify({
        "message": "Task updated successfully.",
        "task": task,
    }), 200


@task_bp.delete("/<task_id>")
@authenticated_task_route
def delete_task(owner_id, task_id):
    delete_task_for_user(owner_id, task_id)
    return "", 204