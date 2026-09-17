import re

from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from ..models.user_model import (
    create_user,
    find_user_by_email,
    find_user_by_id,
)
from flask_jwt_extended import create_access_token


class AuthServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def register_user(email, password):
    if not isinstance(email, str):
        raise AuthServiceError("Email must be a string.")

    email = email.strip().lower()

    if len(email) > 254 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        raise AuthServiceError("Enter a valid email address.")

    if not isinstance(password, str):
        raise AuthServiceError("Password must be a string.")

    if not 12 <= len(password) <= 128:
        raise AuthServiceError(
            "Password must contain between 12 and 128 characters."
        )

    password_hash = generate_password_hash(password, method="scrypt")

    try:
        user = create_user(email, password_hash)
    except DuplicateKeyError:
        raise AuthServiceError(
            "An account with this email already exists.",
            status_code=409,
        ) from None

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "created_at": user["created_at"].isoformat(),
    }

def login_user(email, password):
    if not isinstance(email, str) or not isinstance(password, str):
        raise AuthServiceError("Email and password must be strings.")

    email = email.strip().lower()

    if not email or len(email) > 254 or not 12 <= len(password) <= 128:
        raise AuthServiceError("Invalid email or password.", status_code=401)

    user = find_user_by_email(email)

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        raise AuthServiceError("Invalid email or password.", status_code=401)

    access_token = create_access_token(identity=str(user["_id"]))

    return {
        "access_token": access_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
        },
    }

def get_current_user(user_id):
    user = find_user_by_id(user_id)

    if user is None:
        raise AuthServiceError(
            "Account no longer exists or token identity is invalid.",
            status_code=401,
        )

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "created_at": user["created_at"].isoformat(),
    }