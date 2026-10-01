from ..models.simulation_model import (
    load_owned_inputs,
)
from ..simulation.benchmark import (
    BENCHMARK_ALGORITHMS,
    benchmark_algorithms,
)
from .simulation_service import (
    ALGORITHMS,
    PARAMETERS,
    SimulationServiceError,
    build_problem,
    validate_ids,
)


class BenchmarkServiceError(
    SimulationServiceError
):
    pass


def _validate_seed(seed):
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 2**32 - 1
    ):
        raise BenchmarkServiceError(
            "seed must be an integer between "
            "0 and 4294967295."
        )

    return seed


def _validate_parameters(parameters):
    if parameters is None:
        return {}

    if not isinstance(parameters, dict):
        raise BenchmarkServiceError(
            "parameters must be a JSON object."
        )

    unsupported_algorithms = (
        set(parameters)
        - set(BENCHMARK_ALGORITHMS)
    )

    if unsupported_algorithms:
        raise BenchmarkServiceError(
            "Parameters contain an unsupported "
            "algorithm."
        )

    normalized = {}

    for algorithm_name, values in parameters.items():
        if not isinstance(values, dict):
            raise BenchmarkServiceError(
                f"{algorithm_name} parameters "
                "must be a JSON object."
            )

        supported_fields = PARAMETERS.get(
            algorithm_name,
            set(),
        )

        unsupported_fields = (
            set(values) - supported_fields
        )

        if unsupported_fields:
            raise BenchmarkServiceError(
                f"{algorithm_name} contains "
                "unsupported parameters."
            )

        normalized[algorithm_name] = dict(values)

    return normalized


def benchmark_algorithms_for_user(
    owner_id,
    data,
):
    if not isinstance(data, dict):
        raise BenchmarkServiceError(
            "Request body must be a JSON object."
        )

    allowed_fields = {
        "task_ids",
        "vm_ids",
        "seed",
        "parameters",
        "enable_redistribution",
    }

    if set(data) - allowed_fields:
        raise BenchmarkServiceError(
            "Request contains unsupported fields."
        )

    task_ids = validate_ids(
        data.get("task_ids"),
        "task_ids",
        500,
    )
    vm_ids = validate_ids(
        data.get("vm_ids"),
        "vm_ids",
        100,
    )

    seed = _validate_seed(
        data.get("seed", 42)
    )

    enable_redistribution = data.get(
        "enable_redistribution",
        True,
    )

    if not isinstance(
        enable_redistribution,
        bool,
    ):
        raise BenchmarkServiceError(
            "enable_redistribution must be "
            "a boolean."
        )

    parameters = _validate_parameters(
        data.get("parameters", {})
    )

    missing_algorithms = [
        name
        for name in BENCHMARK_ALGORITHMS
        if name not in ALGORITHMS
    ]

    if missing_algorithms:
        raise BenchmarkServiceError(
            "The server is missing these algorithms: "
            + ", ".join(missing_algorithms)
            + ".",
            status_code=503,
        )

    owned_inputs = load_owned_inputs(
        owner_id,
        task_ids,
        vm_ids,
    )

    if owned_inputs is None:
        raise BenchmarkServiceError(
            "One or more tasks or VMs were "
            "not found.",
            status_code=404,
        )

    tasks, vms = owned_inputs

    task_snapshot = [
        {
            "id": str(task["_id"]),
            "name": task["name"],
            "work_mi": task["work_mi"],
            "arrival_time": (
                task["arrival_time"]
            ),
        }
        for task in tasks
    ]

    vm_snapshot = [
        {
            "id": str(vm["_id"]),
            "name": vm["name"],
            "capacity_mips": (
                vm["capacity_mips"]
            ),
            "overload_threshold": (
                vm["overload_threshold"]
            ),
        }
        for vm in vms
    ]

    problem = build_problem(
        task_snapshot,
        vm_snapshot,
    )

    thresholds = {
        vm["id"]: vm["overload_threshold"]
        for vm in vm_snapshot
    }

    try:
        benchmark = benchmark_algorithms(
            problem=problem,
            overload_thresholds=thresholds,
            algorithm_types=ALGORITHMS,
            seed=seed,
            parameters=parameters,
            enable_redistribution=(
                enable_redistribution
            ),
        )
    except (TypeError, ValueError) as exc:
        raise BenchmarkServiceError(
            str(exc)
        ) from None

    return {
        "benchmark": benchmark,
        "tasks": task_snapshot,
        "vms": vm_snapshot,
    }