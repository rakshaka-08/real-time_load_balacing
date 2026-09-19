from datetime import datetime, timezone

from bson import ObjectId
from flask import current_app
from pymongo import ReturnDocument


def get_vms_collection():
    return current_app.extensions["mongo_db"]["virtual_machines"]


def create_vm_indexes():
    get_vms_collection().create_index(
        [("owner_id", 1), ("created_at", -1), ("_id", -1)]
    )


def vm_filter(owner_id, vm_id):
    if not isinstance(vm_id, str) or not ObjectId.is_valid(vm_id):
        return None

    return {
        "_id": ObjectId(vm_id),
        "owner_id": ObjectId(owner_id),
    }


def create_vm(owner_id, name, capacity_mips, overload_threshold):
    vm = {
        "owner_id": ObjectId(owner_id),
        "name": name,
        "capacity_mips": capacity_mips,
        "overload_threshold": overload_threshold,
        "created_at": datetime.now(timezone.utc),
    }

    result = get_vms_collection().insert_one(vm)
    vm["_id"] = result.inserted_id
    return vm


def list_vms_by_owner(owner_id, skip=0, limit=20):
    return list(
        get_vms_collection()
        .find({"owner_id": ObjectId(owner_id)})
        .sort([("created_at", -1), ("_id", -1)])
        .skip(skip)
        .limit(limit)
    )


def count_vms_by_owner(owner_id):
    return get_vms_collection().count_documents(
        {"owner_id": ObjectId(owner_id)}
    )


def find_vm_by_id(owner_id, vm_id):
    query = vm_filter(owner_id, vm_id)
    if query is None:
        return None

    return get_vms_collection().find_one(query)


def update_vm_by_id(owner_id, vm_id, updates):
    query = vm_filter(owner_id, vm_id)
    if query is None:
        return None

    changes = {
        key: value
        for key, value in updates.items()
        if key in {"name", "capacity_mips", "overload_threshold"}
    }

    if not changes:
        raise ValueError("No editable VM fields supplied.")

    changes["updated_at"] = datetime.now(timezone.utc)

    return get_vms_collection().find_one_and_update(
        query,
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )


def delete_vm_by_id(owner_id, vm_id):
    query = vm_filter(owner_id, vm_id)
    if query is None:
        return False

    return get_vms_collection().delete_one(query).deleted_count == 1