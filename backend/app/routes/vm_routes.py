from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from ..services.auth_service import AuthServiceError, get_current_user
from ..services.vm_service import (
    VMServiceError,
    create_vm_for_user,
    delete_vm_for_user,
    get_vm_for_user,
    list_vms_for_user,
    update_vm_for_user,
)

vm_bp = Blueprint("vms", __name__, url_prefix="/api/vms")


def authenticated_vm_route(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        try:
            user = get_current_user(get_jwt_identity())
            return view(user["id"], *args, **kwargs)
        except (AuthServiceError, VMServiceError) as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except PyMongoError:
            current_app.logger.exception("VM database operation failed.")
            return jsonify({
                "error": "Database operation failed. Please try again."
            }), 503

    return wrapped


def read_json_body():
    if not request.is_json:
        raise VMServiceError(
            "Content-Type must be application/json.",
            status_code=415,
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise VMServiceError(
            "Request body must be a valid JSON object."
        )

    return data


@vm_bp.post("")
@authenticated_vm_route
def create(owner_id):
    vm = create_vm_for_user(owner_id, read_json_body())
    return jsonify({
        "message": "VM created successfully.",
        "vm": vm,
    }), 201


@vm_bp.get("")
@authenticated_vm_route
def list_vms(owner_id):
    result = list_vms_for_user(
        owner_id,
        page=request.args.get("page", "1"),
        limit=request.args.get("limit", "20"),
    )
    return jsonify(result), 200


@vm_bp.get("/<vm_id>")
@authenticated_vm_route
def get_vm(owner_id, vm_id):
    return jsonify({
        "vm": get_vm_for_user(owner_id, vm_id)
    }), 200


@vm_bp.patch("/<vm_id>")
@authenticated_vm_route
def update_vm(owner_id, vm_id):
    vm = update_vm_for_user(owner_id, vm_id, read_json_body())
    return jsonify({
        "message": "VM updated successfully.",
        "vm": vm,
    }), 200


@vm_bp.delete("/<vm_id>")
@authenticated_vm_route
def delete_vm(owner_id, vm_id):
    delete_vm_for_user(owner_id, vm_id)
    return "", 204