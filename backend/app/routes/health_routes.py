from flask import Blueprint, jsonify

from ..services.health_service import (
    liveness_status,
    readiness_status,
    system_status,
)

health_bp = Blueprint(
    "health",
    __name__,
    url_prefix="/api/health",
)


@health_bp.get("/live")
def live():
    return jsonify(liveness_status()), 200


@health_bp.get("/ready")
def ready():
    result = readiness_status()
    return jsonify(result), 200 if result["ready"] else 503


@health_bp.get("/status")
def status():
    result = system_status()
    return jsonify(result), 200 if result["ready"] else 503