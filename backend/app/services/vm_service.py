import math

from ..models.vm_model import (
    count_vms_by_owner,
    create_vm,
    delete_vm_by_id,
    find_vm_by_id,
    list_vms_by_owner,
    update_vm_by_id,
)


class VMServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def positive_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VMServiceError(f"{field} must be a number.")

    try:
        number = float(value)
    except OverflowError:
        raise VMServiceError(f"{field} is too large.") from None

    if not math.isfinite(number) or number <= 0:
        raise VMServiceError(
            f"{field} must be a finite number greater than zero."
        )

    return number


def pagination_integer(value, field, minimum, maximum):
    if isinstance(value, bool):
        raise VMServiceError(f"{field} must be an integer.")

    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise VMServiceError(f"{field} must be an integer.") from None

    if not isinstance(value, int):
        raise VMServiceError(f"{field} must be an integer.")

    if not minimum <= value <= maximum:
        raise VMServiceError(
            f"{field} must be between {minimum} and {maximum}."
        )

    return value


def validate_vm_fields(data, partial=False):
    if not isinstance(data, dict):
        raise VMServiceError("Request body must be a JSON object.")

    allowed = {"name", "capacity_mips", "overload_threshold"}
    unknown = set(data) - allowed

    if unknown:
        raise VMServiceError(
            f"Unknown fields: {', '.join(sorted(unknown))}."
        )

    if partial and not data:
        raise VMServiceError("Supply at least one editable field.")

    fields = {}

    if not partial or "name" in data:
        name = data.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise VMServiceError(
                "VM name must contain between 1 and 120 characters."
            )
        fields["name"] = name.strip()

    for field in ("capacity_mips", "overload_threshold"):
        if not partial or field in data:
            fields[field] = positive_number(data.get(field), field)

    return fields


def serialize_vm(vm):
    result = {
        "id": str(vm["_id"]),
        "name": vm["name"],
        "capacity_mips": vm["capacity_mips"],
        "overload_threshold": vm["overload_threshold"],
        "created_at": vm["created_at"].isoformat(),
    }

    if "updated_at" in vm:
        result["updated_at"] = vm["updated_at"].isoformat()

    return result


def create_vm_for_user(owner_id, data):
    fields = validate_vm_fields(data)
    return serialize_vm(create_vm(owner_id=owner_id, **fields))


def list_vms_for_user(owner_id, page=1, limit=20):
    page = pagination_integer(page, "page", 1, 1_000_000)
    limit = pagination_integer(limit, "limit", 1, 100)

    vms = list_vms_by_owner(
        owner_id,
        skip=(page - 1) * limit,
        limit=limit,
    )
    total = count_vms_by_owner(owner_id)

    return {
        "vms": [serialize_vm(vm) for vm in vms],
        "page": page,
        "limit": limit,
        "count": len(vms),
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


def get_vm_for_user(owner_id, vm_id):
    vm = find_vm_by_id(owner_id, vm_id)
    if vm is None:
        raise VMServiceError("VM not found.", status_code=404)
    return serialize_vm(vm)


def update_vm_for_user(owner_id, vm_id, data):
    fields = validate_vm_fields(data, partial=True)
    vm = update_vm_by_id(owner_id, vm_id, fields)

    if vm is None:
        raise VMServiceError("VM not found.", status_code=404)

    return serialize_vm(vm)


def delete_vm_for_user(owner_id, vm_id):
    if not delete_vm_by_id(owner_id, vm_id):
        raise VMServiceError("VM not found.", status_code=404)