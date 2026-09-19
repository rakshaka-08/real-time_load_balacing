from datetime import datetime, timezone

from bson import ObjectId
from flask import current_app
from pymongo import ReturnDocument


def get_tasks_collection():
    return current_app.extensions["mongo_db"]["tasks"]


def create_task_indexes():
    get_tasks_collection().create_index(
        [("owner_id", 1), ("created_at", -1), ("_id", -1)]
    )


def task_filter(owner_id, task_id):
    if not isinstance(task_id, str) or not ObjectId.is_valid(task_id):
        return None

    return {
        "_id": ObjectId(task_id),
        "owner_id": ObjectId(owner_id),
    }


def create_task(owner_id, name, work_mi, arrival_time):
    task = {
        "owner_id": ObjectId(owner_id),
        "name": name,
        "work_mi": work_mi,
        "arrival_time": arrival_time,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_tasks_collection().insert_one(task)
    task["_id"] = result.inserted_id
    return task


def create_many_tasks(owner_id, tasks):
    now = datetime.now(timezone.utc)
    documents = [
        {
            "owner_id": ObjectId(owner_id),
            "name": task["name"],
            "work_mi": task["work_mi"],
            "arrival_time": task["arrival_time"],
            "created_at": now,
        }
        for task in tasks
    ]

    if not documents:
        return []

    get_tasks_collection().insert_many(documents)
    return documents


def list_tasks_by_owner(owner_id, skip=0, limit=50):
    return list(
        get_tasks_collection()
        .find({"owner_id": ObjectId(owner_id)})
        .sort([("created_at", -1), ("_id", -1)])
        .skip(skip)
        .limit(limit)
    )


def count_tasks_by_owner(owner_id):
    return get_tasks_collection().count_documents(
        {"owner_id": ObjectId(owner_id)}
    )


def find_task_by_id(owner_id, task_id):
    query = task_filter(owner_id, task_id)
    if query is None:
        return None
    return get_tasks_collection().find_one(query)


def update_task_by_id(owner_id, task_id, updates):
    query = task_filter(owner_id, task_id)
    if query is None:
        return None

    changes = {
        key: value
        for key, value in updates.items()
        if key in {"name", "work_mi", "arrival_time"}
    }
    if not changes:
        raise ValueError("No editable task fields supplied.")

    changes["updated_at"] = datetime.now(timezone.utc)

    return get_tasks_collection().find_one_and_update(
        query,
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )


def delete_task_by_id(owner_id, task_id):
    query = task_filter(owner_id, task_id)
    if query is None:
        return False

    return get_tasks_collection().delete_one(query).deleted_count == 1