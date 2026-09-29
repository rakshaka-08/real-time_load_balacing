from datetime import datetime, timezone

from flask import current_app
from pymongo import ASCENDING, DESCENDING


def get_templates_collection():
    return current_app.extensions["mongo_db"]["scenario_templates"]


def create_template_indexes():
    collection = get_templates_collection()

    collection.create_index(
        [("owner_id", ASCENDING), ("created_at", DESCENDING)]
    )

    collection.create_index(
        [
            ("collaborators.user_id", ASCENDING),
            ("created_at", DESCENDING),
        ]
    )


def utc_now():
    return datetime.now(timezone.utc)