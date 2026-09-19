from time import perf_counter

from .base_algorithm import AlgorithmResult, BaseAlgorithm


class HoneyBeeAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        problem,
        seed=42,
        scout_bees=30,
        iterations=100,
        selected_sites=10,
        elite_sites=3,
        elite_recruits=10,
        other_recruits=5,
        neighborhood_moves=1,
    ):
        super().__init__(problem, seed)

        self.scout_bees = self._positive_integer(
            scout_bees, "scout_bees", minimum=2
        )
        self.iterations = self._positive_integer(
            iterations, "iterations"
        )
        self.selected_sites = self._positive_integer(
            selected_sites, "selected_sites"
        )
        self.elite_sites = self._positive_integer(
            elite_sites, "elite_sites"
        )
        self.elite_recruits = self._positive_integer(
            elite_recruits, "elite_recruits"
        )
        self.other_recruits = self._positive_integer(
            other_recruits, "other_recruits"
        )
        self.neighborhood_moves = self._positive_integer(
            neighborhood_moves, "neighborhood_moves"
        )

        if self.selected_sites >= self.scout_bees:
            raise ValueError(
                "selected_sites must be smaller than scout_bees "
                "to retain random exploration."
            )

        if self.elite_sites > self.selected_sites:
            raise ValueError(
                "elite_sites cannot exceed selected_sites."
            )

        if self.elite_recruits < self.other_recruits:
            raise ValueError(
                "elite_recruits must be at least other_recruits."
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

    def _neighbor(self, order):
        if len(order) < 2:
            return order

        genes = list(order)

        for _ in range(self.neighborhood_moves):
            first, second = self.rng.sample(range(len(genes)), 2)

            if self.rng.random() < 0.5:
                genes[first], genes[second] = (
                    genes[second],
                    genes[first],
                )
            else:
                task_id = genes.pop(first)
                genes.insert(second, task_id)

        return tuple(genes)

    def _search_site(self, site, recruits, evaluate):
        # Retain the original site unless a recruit finds an improvement.
        best = site

        for _ in range(recruits):
            candidate_order = self._neighbor(site.task_order)
            candidate = evaluate(candidate_order)

            if candidate.fitness < best.fitness:
                best = candidate

        return best

    def optimize(self):
        started = perf_counter()

        self.rng.seed(self.seed)
        self.best_fitness_history = []

        if len(self.problem.task_ids) <= 1:
            schedule = self.evaluate(self.problem.task_ids)
            self.best_fitness_history.append(schedule.fitness)

            return AlgorithmResult(
                algorithm="HBA",
                schedule=schedule,
                execution_seconds=perf_counter() - started,
                iterations=0,
                seed=self.seed,
            )

        cache = {}

        def evaluate(order):
            if order not in cache:
                cache[order] = self.evaluate(order)
            return cache[order]

        # Preserve input order as one candidate; scouts explore the rest.
        population = [evaluate(self.problem.task_ids)]
        population.extend(
            evaluate(self.random_order())
            for _ in range(self.scout_bees - 1)
        )

        best = min(population, key=lambda site: site.fitness)
        self.best_fitness_history.append(best.fitness)

        for _ in range(self.iterations):
            ranked = sorted(
                population,
                key=lambda site: site.fitness,
            )
            selected = ranked[:self.selected_sites]
            next_population = []

            for index, site in enumerate(selected):
                recruits = (
                    self.elite_recruits
                    if index < self.elite_sites
                    else self.other_recruits
                )

                winner = self._search_site(
                    site,
                    recruits,
                    evaluate,
                )
                next_population.append(winner)

            # Remaining scouts search new, randomly generated sites.
            next_population.extend(
                evaluate(self.random_order())
                for _ in range(self.scout_bees - self.selected_sites)
            )

            population = next_population
            iteration_best = min(
                population,
                key=lambda site: site.fitness,
            )

            if iteration_best.fitness < best.fitness:
                best = iteration_best

            self.best_fitness_history.append(best.fitness)

        return AlgorithmResult(
            algorithm="HBA",
            schedule=best,
            execution_seconds=perf_counter() - started,
            iterations=self.iterations,
            seed=self.seed,
        )