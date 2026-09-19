import math
from time import perf_counter

from .base_algorithm import AlgorithmResult, BaseAlgorithm


class GeneticAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        problem,
        seed=42,
        population_size=50,
        generations=100,
        crossover_rate=0.9,
        mutation_rate=0.15,
        tournament_size=3,
        elite_count=2,
    ):
        super().__init__(problem, seed)

        self.population_size = self._positive_integer(
            population_size, "population_size", minimum=2
        )
        self.generations = self._positive_integer(
            generations, "generations"
        )
        self.tournament_size = self._positive_integer(
            tournament_size, "tournament_size"
        )
        self.elite_count = self._positive_integer(
            elite_count, "elite_count"
        )

        if self.tournament_size > self.population_size:
            raise ValueError(
                "tournament_size cannot exceed population_size."
            )

        if self.elite_count >= self.population_size:
            raise ValueError(
                "elite_count must be smaller than population_size."
            )

        self.crossover_rate = self._probability(
            crossover_rate, "crossover_rate"
        )
        self.mutation_rate = self._probability(
            mutation_rate, "mutation_rate"
        )

        self.best_fitness_history = []

    @staticmethod
    def _positive_integer(value, field, minimum=1):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
        ):
            raise ValueError(
                f"{field} must be an integer of at least {minimum}."
            )
        return value

    @staticmethod
    def _probability(value, field):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 1
        ):
            raise ValueError(f"{field} must be between 0 and 1.")

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(f"{field} must be finite.")

        return value

    def _select_parent(self, evaluations):
        contestants = self.rng.sample(
            evaluations, self.tournament_size
        )
        return min(
            contestants,
            key=lambda candidate: candidate.fitness,
        ).task_order

    @staticmethod
    def _ordered_child(primary, secondary, start, end):
        size = len(primary)
        child = [None] * size

        child[start:end] = primary[start:end]
        retained = set(primary[start:end])

        # Read the second parent cyclically from the end of the segment.
        donor_order = secondary[end:] + secondary[:end]
        remaining = iter(
            task_id
            for task_id in donor_order
            if task_id not in retained
        )

        # Fill the remaining positions in the same cyclic order.
        positions = list(range(end, size)) + list(range(start))

        for position in positions:
            child[position] = next(remaining)

        return tuple(child)

    def _crossover(self, first, second):
        size = len(first)

        if size < 2 or self.rng.random() >= self.crossover_rate:
            return first, second

        start, end = sorted(
            self.rng.sample(range(size + 1), 2)
        )

        return (
            self._ordered_child(first, second, start, end),
            self._ordered_child(second, first, start, end),
        )

    def _mutate(self, chromosome):
        if (
            len(chromosome) < 2
            or self.rng.random() >= self.mutation_rate
        ):
            return chromosome

        genes = list(chromosome)
        first, second = self.rng.sample(range(len(genes)), 2)
        genes[first], genes[second] = genes[second], genes[first]

        return tuple(genes)

    def optimize(self):
        started = perf_counter()

        # Repeated runs with the same configuration reproduce the search.
        self.rng.seed(self.seed)
        self.best_fitness_history = []

        if len(self.problem.task_ids) <= 1:
            schedule = self.evaluate(self.problem.task_ids)
            self.best_fitness_history.append(schedule.fitness)

            return AlgorithmResult(
                algorithm="GA",
                schedule=schedule,
                execution_seconds=perf_counter() - started,
                iterations=0,
                seed=self.seed,
            )

        # The first member preserves input order; others are randomized.
        population = [self.problem.task_ids]
        population.extend(
            self.random_order()
            for _ in range(self.population_size - 1)
        )

        # Cache repeated chromosomes within this run.
        cache = {}

        def evaluate_population(chromosomes):
            results = []

            for chromosome in chromosomes:
                if chromosome not in cache:
                    cache[chromosome] = self.evaluate(chromosome)
                results.append(cache[chromosome])

            return results

        evaluations = evaluate_population(population)
        best = min(evaluations, key=lambda item: item.fitness)
        self.best_fitness_history.append(best.fitness)

        for _ in range(self.generations):
            ranked = sorted(
                evaluations,
                key=lambda item: item.fitness,
            )

            # Preserve elite solutions without crossover or mutation.
            next_population = [
                item.task_order
                for item in ranked[:self.elite_count]
            ]

            while len(next_population) < self.population_size:
                first = self._select_parent(evaluations)
                second = self._select_parent(evaluations)

                children = self._crossover(first, second)

                for child in children:
                    next_population.append(self._mutate(child))

                    if len(next_population) == self.population_size:
                        break

            evaluations = evaluate_population(next_population)
            generation_best = min(
                evaluations,
                key=lambda item: item.fitness,
            )

            if generation_best.fitness < best.fitness:
                best = generation_best

            self.best_fitness_history.append(best.fitness)

        return AlgorithmResult(
            algorithm="GA",
            schedule=best,
            execution_seconds=perf_counter() - started,
            iterations=self.generations,
            seed=self.seed,
        )