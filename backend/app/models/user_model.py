from datetime import datetime, timezone

from bson import ObjectId
from flask import current_app
from datetime import datetime, timezone


def get_users_collection():
    return current_app.extensions["mongo_db"]["users"]


def create_user_indexes():
    get_users_collection().create_index("email", unique=True)


def find_user_by_email(email):
    return get_users_collection().find_one({"email": email})


def find_user_by_id(user_id):
    if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
        return None

    return get_users_collection().find_one({"_id": ObjectId(user_id)})


def create_user(email, password_hash):
    user = {
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }

    result = get_users_collection().insert_one(user)
    user["_id"] = result.inserted_id
    return user 

from bson import ObjectId
from flask import current_app


def get_users_collection():
    return current_app.extensions["mongo_db"]["users"]


def create_user_indexes():
    get_users_collection().create_index("email", unique=True)


def find_user_by_email(email):
    return get_users_collection().find_one({"email": email})


def find_user_by_id(user_id):
    if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
        return None

    return get_users_collection().find_one({"_id": ObjectId(user_id)})


def create_user(email, password_hash):
    user = {
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }

    result = get_users_collection().insert_one(user)
    user["_id"] = result.inserted_id
    return user