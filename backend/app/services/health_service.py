from datetime import datetime, timezone
from time import monotonic

from flask import current_app
from pymongo.errors import PyMongoError

STARTED_AT = datetime.now(timezone.utc)
STARTED_MONOTONIC = monotonic()


def utc_now():
    return datetime.now(timezone.utc)


def check_database():
    try:
        client = current_app.extensions["mongo_client"]
        client.admin.command("ping")

        return {
            "status": "UP",
            "message": "MongoDB connection is available.",
        }
    except (KeyError, PyMongoError, RuntimeError):
        current_app.logger.exception(
            "MongoDB health check failed."
        )

        return {
            "status": "DOWN",
            "message": "MongoDB connection is unavailable.",
        }


def liveness_status():
    return {
        "status": "UP",
        "service": "load-balancing-api",
        "checked_at": utc_now().isoformat(),
    }


def readiness_status():
    database = check_database()
    ready = database["status"] == "UP"

    return {
        "status": "UP" if ready else "DOWN",
        "ready": ready,
        "services": {
            "api": {
                "status": "UP",
                "message": "Flask API process is running.",
            },
            "database": database,
        },
        "checked_at": utc_now().isoformat(),
    }


def system_status():
    readiness = readiness_status()

    return {
        **readiness,
        "started_at": STARTED_AT.isoformat(),
        "uptime_seconds": round(
            max(0, monotonic() - STARTED_MONOTONIC),
            2,
        ),
        "environment": current_app.config.get(
            "ENV",
            "development",
        ),
    }