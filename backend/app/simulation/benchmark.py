from ..algorithms.base_algorithm import (
    SchedulingProblem,
)
from .simulation_engine import SimulationEngine


BENCHMARK_ALGORITHMS = (
    "GA",
    "HBA",
    "GA_HBA",
    "LPT",
    "SPT",
)


def _validate_seed(seed):
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 2**32 - 1
    ):
        raise ValueError(
            "seed must be an integer between "
            "0 and 4294967295."
        )

    return seed


def benchmark_algorithms(
    problem,
    overload_thresholds,
    algorithm_types,
    seed=42,
    parameters=None,
    enable_redistribution=True,
):
    if not isinstance(
        problem,
        SchedulingProblem,
    ):
        raise ValueError(
            "problem must be a SchedulingProblem."
        )

    if not isinstance(
        overload_thresholds,
        dict,
    ):
        raise ValueError(
            "overload_thresholds must be a dictionary."
        )

    if not isinstance(algorithm_types, dict):
        raise ValueError(
            "algorithm_types must be a dictionary."
        )

    missing_algorithms = [
        name
        for name in BENCHMARK_ALGORITHMS
        if name not in algorithm_types
    ]

    if missing_algorithms:
        raise ValueError(
            "Missing benchmark algorithms: "
            + ", ".join(missing_algorithms)
            + "."
        )

    if not isinstance(
        enable_redistribution,
        bool,
    ):
        raise ValueError(
            "enable_redistribution must be a boolean."
        )

    seed = _validate_seed(seed)

    if parameters is None:
        parameters = {}

    if not isinstance(parameters, dict):
        raise ValueError(
            "parameters must be a dictionary."
        )

    unsupported_names = (
        set(parameters)
        - set(BENCHMARK_ALGORITHMS)
    )

    if unsupported_names:
        raise ValueError(
            "Parameters contain an unsupported "
            "algorithm."
        )

    results = []

    for algorithm_name in BENCHMARK_ALGORITHMS:
        algorithm_parameters = parameters.get(
            algorithm_name,
            {},
        )

        if not isinstance(
            algorithm_parameters,
            dict,
        ):
            raise ValueError(
                f"{algorithm_name} parameters "
                "must be a dictionary."
            )

        algorithm_factory = algorithm_types[
            algorithm_name
        ]

        if not callable(algorithm_factory):
            raise ValueError(
                f"{algorithm_name} algorithm "
                "must be callable."
            )

        algorithm = algorithm_factory(
            problem,
            seed=seed,
            **algorithm_parameters,
        )

        algorithm_result = algorithm.optimize()

        engine = SimulationEngine(
            problem,
            algorithm_result,
            dict(overload_thresholds),
            enable_redistribution=(
                enable_redistribution
            ),
        )

        state = engine.start()

        advance_seconds = max(
            algorithm_result.schedule.makespan,
            1.0,
        )

        cycles = 0

        while state["status"] == "RUNNING":
            state = engine.advance(
                advance_seconds
            )
            cycles += 1

            if cycles > 1000:
                raise RuntimeError(
                    "Benchmark simulation did not "
                    "complete."
                )

        if state["status"] != "COMPLETED":
            raise RuntimeError(
                f"{algorithm_name} benchmark ended "
                f"with status {state['status']}."
            )

        results.append({
            "algorithm": algorithm_name,
            "seed": seed,
            "iterations": (
                algorithm_result.iterations
            ),
            "task_order": list(
                algorithm_result.schedule.task_order
            ),
            **state["metrics"],
        })

    return {
        "seed": seed,
        "task_count": len(problem.tasks),
        "vm_count": len(problem.vms),
        "redistribution_enabled": (
            enable_redistribution
        ),
        "algorithms": results,
    }