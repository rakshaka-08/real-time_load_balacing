from flask import Blueprint, jsonify, request

from ..services.auth_service import (
    AuthServiceError,
    get_current_user,
    login_user,
    register_user,
)
from flask_jwt_extended import get_jwt_identity, jwt_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    try:
        user = register_user(
            email=data.get("email"),
            password=data.get("password"),
        )
    except AuthServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    return jsonify({
        "message": "Account created successfully.",
        "user": user,
    }), 201

@auth_bp.post("/login")
def login():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    try:
        result = login_user(
            email=data.get("email"),
            password=data.get("password"),
        )
    except AuthServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    return jsonify(result), 200

@auth_bp.get("/me")
@jwt_required()
def me():
    try:
        user = get_current_user(get_jwt_identity())
    except AuthServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    return jsonify({"user": user}), 200