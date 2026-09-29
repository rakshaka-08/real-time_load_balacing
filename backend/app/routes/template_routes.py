from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.auth_service import AuthServiceError, get_current_user
from ..services.template_service import (
    TemplateServiceError,
    create_template_for_user,
    delete_template_for_user,
    list_templates_for_user,
    rename_template_for_user,
)

template_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


def authenticated_template_route(view):
    @wraps(view)
    @jwt_required()
    def wrapped(*args, **kwargs):
        try:
            user = get_current_user(get_jwt_identity())
            return view(user["id"], *args, **kwargs)
        except (AuthServiceError, TemplateServiceError) as exc:
            return jsonify({"error": str(exc)}), exc.status_code

    return wrapped


def json_body():
    if not request.is_json:
        raise TemplateServiceError(
            "Content-Type must be application/json.", 415
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise TemplateServiceError("Request body must be a JSON object.")

    return data


@template_bp.get("")
@authenticated_template_route
def list_templates(owner_id):
    return jsonify(list_templates_for_user(owner_id)), 200


@template_bp.post("")
@authenticated_template_route
def create_template(owner_id):
    template = create_template_for_user(owner_id, json_body())
    return jsonify({"template": template}), 201


@template_bp.put("/<template_id>")
@authenticated_template_route
def rename_template(owner_id, template_id):
    template = rename_template_for_user(owner_id, template_id, json_body())
    return jsonify({"template": template}), 200


@template_bp.delete("/<template_id>")
@authenticated_template_route
def delete_template(owner_id, template_id):
    delete_template_for_user(owner_id, template_id)
    return "", 204