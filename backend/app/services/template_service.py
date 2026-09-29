from bson import ObjectId
from pymongo.errors import PyMongoError

from ..models.template_model import get_templates_collection, utc_now
from ..models.user_model import find_user_by_email

ALGORITHMS = {"LPT", "SPT", "GA", "HBA"}


class TemplateServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def public_template(document):
    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "task_ids": document["task_ids"],
        "vm_ids": document["vm_ids"],
        "algorithm": document["algorithm"],
        "parameters": document.get("parameters", {}),
        "seed": document["seed"],
        "redistribution_enabled": document["redistribution_enabled"],
        "created_at": document["created_at"].isoformat(),
        "collaborators": document.get("collaborators", []),
        "updated_at": document["updated_at"].isoformat(),
    }


def validate_configuration(data, require_configuration=True):
    name = str(data.get("name", "")).strip()

    if not name or len(name) > 80:
        raise TemplateServiceError(
            "Template name must contain between 1 and 80 characters."
        )

    if not require_configuration:
        return {"name": name}

    task_ids = data.get("task_ids")
    vm_ids = data.get("vm_ids")
    algorithm = data.get("algorithm")
    parameters = data.get("parameters", {})
    seed = data.get("seed", 42)
    redistribution = data.get("redistribution_enabled", True)

    if not isinstance(task_ids, list) or not task_ids:
        raise TemplateServiceError("Select at least one task.")
    if not isinstance(vm_ids, list) or not vm_ids:
        raise TemplateServiceError("Select at least one virtual machine.")
    if algorithm not in ALGORITHMS:
        raise TemplateServiceError("Choose a supported scheduling algorithm.")
    if not isinstance(parameters, dict):
        raise TemplateServiceError("Parameters must be a JSON object.")
    if not isinstance(seed, int) or seed < 0 or seed > 4294967295:
        raise TemplateServiceError(
            "Seed must be a whole number between 0 and 4294967295."
        )
    if not isinstance(redistribution, bool):
        raise TemplateServiceError(
            "redistribution_enabled must be true or false."
        )

    return {
        "name": name,
        "task_ids": task_ids,
        "vm_ids": vm_ids,
        "algorithm": algorithm,
        "parameters": parameters,
        "seed": seed,
        "redistribution_enabled": redistribution,
    }


def list_templates_for_user(owner_id):
    documents = get_templates_collection().find(
        {"owner_id": owner_id}
    ).sort("created_at", -1)

    return {"templates": [public_template(document) for document in documents]}


def create_template_for_user(owner_id, data):
    template = validate_configuration(data)
    now = utc_now()

    document = {
        "owner_id": owner_id,
        **template,
        "created_at": now,
        "updated_at": now,
    }

    result = get_templates_collection().insert_one(document)
    document["_id"] = result.inserted_id
    return public_template(document)


def rename_template_for_user(owner_id, template_id, data):
    values = validate_configuration(data, require_configuration=False)

    try:
        object_id = ObjectId(template_id)
    except Exception as exc:
        raise TemplateServiceError("Template was not found.", 404) from exc

    document = get_templates_collection().find_one_and_update(
        {"_id": object_id, "owner_id": owner_id},
        {"$set": {"name": values["name"], "updated_at": utc_now()}},
        return_document=True,
    )

    if not document:
        raise TemplateServiceError("Template was not found.", 404)

    return public_template(document)


def delete_template_for_user(owner_id, template_id):
    try:
        object_id = ObjectId(template_id)
    except Exception as exc:
        raise TemplateServiceError("Template was not found.", 404) from exc

    result = get_templates_collection().delete_one(
        {"_id": object_id, "owner_id": owner_id}
    )

    if not result.deleted_count:
        raise TemplateServiceError("Template was not found.", 404)
def list_shared_templates_for_user(user_id):
    documents = get_templates_collection().find(
        {"collaborators.user_id": user_id}
    ).sort("created_at", -1)

    return {
        "templates": [
            {
                **public_template(document),
                "is_owner": False,
                "owner_id": document["owner_id"],
                "collaborators": document.get("collaborators", []),
            }
            for document in documents
        ]
    }


def share_template_for_user(owner_id, template_id, email):
    try:
        object_id = ObjectId(template_id)
    except Exception as exc:
        raise TemplateServiceError("Template was not found.", 404) from exc

    document = get_templates_collection().find_one(
        {"_id": object_id, "owner_id": owner_id}
    )

    if not document:
        raise TemplateServiceError("Template was not found.", 404)

    user = find_user_by_email(str(email or "").strip().lower())

    if not user:
        raise TemplateServiceError("No registered user has this email.", 404)

    collaborator_id = str(user["_id"])

    if collaborator_id == owner_id:
        raise TemplateServiceError("You already own this template.")

    collaborators = document.get("collaborators", [])

    if any(item["user_id"] == collaborator_id for item in collaborators):
        raise TemplateServiceError("This user already has access.", 409)

    collaborator = {
        "user_id": collaborator_id,
        "email": user["email"],
    }

    get_templates_collection().update_one(
        {"_id": object_id, "owner_id": owner_id},
        {
            "$push": {"collaborators": collaborator},
            "$set": {"updated_at": utc_now()},
        },
    )

    document["collaborators"] = [*collaborators, collaborator]

    return {
        **public_template(document),
        "collaborators": document["collaborators"],
    }


def revoke_template_access_for_user(
    owner_id,
    template_id,
    collaborator_id,
):
    try:
        object_id = ObjectId(template_id)
    except Exception as exc:
        raise TemplateServiceError("Template was not found.", 404) from exc

    result = get_templates_collection().update_one(
        {"_id": object_id, "owner_id": owner_id},
        {
            "$pull": {"collaborators": {"user_id": collaborator_id}},
            "$set": {"updated_at": utc_now()},
        },
    )

    if not result.matched_count:
        raise TemplateServiceError("Template was not found.", 404)