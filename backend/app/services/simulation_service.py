from copy import deepcopy

from bson import ObjectId

from ..algorithms.base_algorithm import (
    AlgorithmResult,
    SchedulingProblem,
    TaskSpec,
    VMSpec,
    validate_number,
)
from ..algorithms.genetic_algorithm import GeneticAlgorithm
from ..algorithms.honey_bee_algorithm import HoneyBeeAlgorithm
from ..algorithms.lpt import LPTAlgorithm
from ..algorithms.spt import SPTAlgorithm
from ..models.simulation_model import (
    find_simulation,
    insert_simulation,
    list_simulations,
    load_owned_inputs,
    save_simulation_command,
)
from ..simulation.simulation_engine import SimulationEngine


class SimulationServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


ALGORITHMS = {
    "GA": GeneticAlgorithm,
    "HBA": HoneyBeeAlgorithm,
    "LPT": LPTAlgorithm,
    "SPT": SPTAlgorithm,
}

PARAMETERS = {
    "GA": {
        "population_size",
        "generations",
        "crossover_rate",
        "mutation_rate",
        "tournament_size",
        "elite_count",
    },
    "HBA": {
        "scout_bees",
        "iterations",
        "selected_sites",
        "elite_sites",
        "elite_recruits",
        "other_recruits",
        "neighborhood_moves",
    },
    "LPT": set(),
    "SPT": set(),
}


def validate_ids(values, field, maximum):
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise SimulationServiceError(
            f"{field} must contain between 1 and {maximum} IDs."
        )

    if any(
        not isinstance(value, str) or not ObjectId.is_valid(value)
        for value in values
    ):
        raise SimulationServiceError(f"{field} contains an invalid ID.")

    normalized = [str(ObjectId(value)) for value in values]

    if len(set(normalized)) != len(normalized):
        raise SimulationServiceError(f"{field} cannot contain duplicates.")

    return normalized


def positive_integer(value, field, maximum):
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise SimulationServiceError(
                f"{field} must be an integer."
            ) from None

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise SimulationServiceError(
            f"{field} must be an integer between 1 and {maximum}."
        )

    return value


def build_problem(task_snapshot, vm_snapshot):
    return SchedulingProblem(
        [
            TaskSpec(
                task["id"],
                task["work_mi"],
                task["arrival_time"],
            )
            for task in task_snapshot
        ],
        [
            VMSpec(vm["id"], vm["capacity_mips"])
            for vm in vm_snapshot
        ],
    )


def restore_engine(document):
    problem = build_problem(
        document["task_snapshot"],
        document["vm_snapshot"],
    )
    saved = document["algorithm_result"]

    result = AlgorithmResult(
        algorithm=saved["algorithm"],
        schedule=problem.evaluate(saved["task_order"]),
        execution_seconds=saved["execution_seconds"],
        iterations=saved["iterations"],
        seed=saved["seed"],
    )

    engine = SimulationEngine(
        problem,
        result,
        {
            vm["id"]: vm["overload_threshold"]
            for vm in document["vm_snapshot"]
        },
        enable_redistribution=document["enable_redistribution"],
    )

    for command in document["commands"]:
        action = command["action"]

        if action == "advance":
            engine.advance(command["seconds"])
        else:
            getattr(engine, action)()

    return engine


def public_simulation(document):
    state = deepcopy(document["snapshot"])

    task_names = {
        task["id"]: task["name"]
        for task in document["task_snapshot"]
    }
    vm_names = {
        vm["id"]: vm["name"]
        for vm in document["vm_snapshot"]
    }

    for task in state["tasks"]:
        task["name"] = task_names[task["id"]]

    for vm in state["vms"]:
        vm["name"] = vm_names[vm["id"]]

    return {
        "id": str(document["_id"]),
        "created_at": document["created_at"].isoformat(),
        "revision": document["revision"],
        **state,
    }


def require_simulation(owner_id, simulation_id):
    document = find_simulation(owner_id, simulation_id)

    if document is None:
        raise SimulationServiceError(
            "Simulation not found.", status_code=404
        )

    return document


def create_simulation_for_user(owner_id, data):
    allowed = {
        "task_ids",
        "vm_ids",
        "algorithm",
        "parameters",
        "seed",
        "enable_redistribution",
    }

    if not isinstance(data, dict):
        raise SimulationServiceError("Request body must be a JSON object.")

    if set(data) - allowed:
        raise SimulationServiceError("Request contains unsupported fields.")

    task_ids = validate_ids(data.get("task_ids"), "task_ids", 500)
    vm_ids = validate_ids(data.get("vm_ids"), "vm_ids", 100)

    algorithm_name = data.get("algorithm")
    if not isinstance(algorithm_name, str) or algorithm_name not in ALGORITHMS:
        raise SimulationServiceError("Choose GA, HBA, LPT, or SPT.")

    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        raise SimulationServiceError("parameters must be a JSON object.")

    if set(parameters) - PARAMETERS[algorithm_name]:
        raise SimulationServiceError("Unsupported algorithm parameters.")

    seed = data.get("seed", 42)
    redistribution = data.get("enable_redistribution", True)

    if not isinstance(redistribution, bool):
        raise SimulationServiceError(
            "enable_redistribution must be a boolean."
        )

    # Bound search settings accepted through the web API.
    for key, value in parameters.items():
        if key not in {"crossover_rate", "mutation_rate"}:
            maximum = 1000 if key in {"generations", "iterations"} else 200
            positive_integer(value, key, maximum)

    owned_inputs = load_owned_inputs(owner_id, task_ids, vm_ids)
    if owned_inputs is None:
        raise SimulationServiceError(
            "One or more tasks or VMs were not found.",
            status_code=404,
        )

    tasks, vms = owned_inputs

    task_snapshot = [
        {
            "id": str(task["_id"]),
            "name": task["name"],
            "work_mi": task["work_mi"],
            "arrival_time": task["arrival_time"],
        }
        for task in tasks
    ]
    vm_snapshot = [
        {
            "id": str(vm["_id"]),
            "name": vm["name"],
            "capacity_mips": vm["capacity_mips"],
            "overload_threshold": vm["overload_threshold"],
        }
        for vm in vms
    ]

    problem = build_problem(task_snapshot, vm_snapshot)

    try:
        algorithm = ALGORITHMS[algorithm_name](
            problem,
            seed=seed,
            **parameters,
        )
        result = algorithm.optimize()

        engine = SimulationEngine(
            problem,
            result,
            {
                vm["id"]: vm["overload_threshold"]
                for vm in vm_snapshot
            },
            enable_redistribution=redistribution,
        )
    except (TypeError, ValueError) as exc:
        raise SimulationServiceError(str(exc)) from None

    document = insert_simulation(owner_id, {
        "task_snapshot": task_snapshot,
        "vm_snapshot": vm_snapshot,
        "parameters": deepcopy(parameters),
        "enable_redistribution": redistribution,
        "algorithm_result": {
            "algorithm": result.algorithm,
            "task_order": list(result.schedule.task_order),
            "execution_seconds": result.execution_seconds,
            "iterations": result.iterations,
            "seed": result.seed,
        },
        "commands": [],
        "snapshot": engine.snapshot(),
    })

    return public_simulation(document)


def get_simulation_for_user(owner_id, simulation_id):
    return public_simulation(
        require_simulation(owner_id, simulation_id)
    )


def list_simulations_for_user(owner_id, page=1, limit=20):
    page = positive_integer(page, "page", 1_000_000)
    limit = positive_integer(limit, "limit", 100)

    documents, total = list_simulations(owner_id, page, limit)

    return {
        "simulations": [
            {
                "id": str(document["_id"]),
                "created_at": document["created_at"].isoformat(),
                "revision": document["revision"],
                **document["snapshot"],
            }
            for document in documents
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


def control_simulation_for_user(
    owner_id,
    simulation_id,
    action,
    data=None,
):
    allowed_actions = {
        "start", "pause", "resume", "stop", "reset", "advance"
    }
    if action not in allowed_actions:
        raise SimulationServiceError("Unknown control.", status_code=404)

    document = require_simulation(owner_id, simulation_id)
    engine = restore_engine(document)

    try:
        if action == "reset":
            fresh = engine.reset()

            new_document = insert_simulation(owner_id, {
                "task_snapshot": deepcopy(document["task_snapshot"]),
                "vm_snapshot": deepcopy(document["vm_snapshot"]),
                "parameters": deepcopy(document["parameters"]),
                "enable_redistribution": document["enable_redistribution"],
                "algorithm_result": deepcopy(document["algorithm_result"]),
                "commands": [],
                "snapshot": fresh.snapshot(),
            })
            return public_simulation(new_document)

        if action == "advance":
            if not isinstance(data, dict) or set(data) != {"seconds"}:
                raise SimulationServiceError(
                    "Supply a JSON object containing only seconds."
                )

            seconds = validate_number(
                data["seconds"], "seconds", allow_zero=True
            )
            if seconds > 3600:
                raise SimulationServiceError(
                    "Advance by at most 3600 simulated seconds per request."
                )

            state = engine.advance(seconds)
            command = {"action": action, "seconds": seconds}
        else:
            state = getattr(engine, action)()
            command = {"action": action}

    except ValueError as exc:
        raise SimulationServiceError(str(exc)) from None

    saved = save_simulation_command(
        owner_id,
        simulation_id,
        document["revision"],
        state,
        command,
    )

    if saved is None:
        raise SimulationServiceError(
            "Simulation changed during this request. Refresh and retry.",
            status_code=409,
        )

    return public_simulation(saved)