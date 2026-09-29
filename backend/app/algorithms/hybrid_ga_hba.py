from time import perf_counter

from .base_algorithm import AlgorithmResult, BaseAlgorithm
from .genetic_algorithm import GeneticAlgorithm
from .honey_bee_algorithm import HoneyBeeAlgorithm


class HybridGAHBAAlgorithm(BaseAlgorithm):
    """
    Run Genetic Algorithm exploration first, then refine the best
    GA schedule with Honey Bee Algorithm neighborhood search.
    """

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
        scout_bees=30,
        hba_iterations=100,
        selected_sites=10,
        elite_sites=3,
        elite_recruits=10,
        other_recruits=5,
        neighborhood_moves=1,
    ):
        super().__init__(problem, seed)

        self.generations = generations
        self.hba_iterations = hba_iterations

        # Constructing the existing implementations validates every
        # parameter while preserving their current behavior.
        self.ga = GeneticAlgorithm(
            problem,
            seed=seed,
            population_size=population_size,
            generations=generations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            tournament_size=tournament_size,
            elite_count=elite_count,
        )

        self.hba = HoneyBeeAlgorithm(
            problem,
            seed=(seed + 1) % (2**32),
            scout_bees=scout_bees,
            iterations=hba_iterations,
            selected_sites=selected_sites,
            elite_sites=elite_sites,
            elite_recruits=elite_recruits,
            other_recruits=other_recruits,
            neighborhood_moves=neighborhood_moves,
        )

        self.best_fitness_history = []

    def optimize(self):
        started = perf_counter()

        ga_result = self.ga.optimize()
        best = ga_result.schedule

        self.best_fitness_history = list(
            self.ga.best_fitness_history
        )

        if len(self.problem.task_ids) <= 1:
            return AlgorithmResult(
                algorithm="GA_HBA",
                schedule=best,
                execution_seconds=perf_counter() - started,
                iterations=0,
                seed=self.seed,
            )

        self.hba.rng.seed(self.hba.seed)

        cache = {
            best.task_order: best,
        }

        def evaluate(order):
            order = tuple(order)

            if order not in cache:
                cache[order] = self.evaluate(order)

            return cache[order]

        # The best GA schedule is the first HBA site. Remaining scouts
        # preserve HBA's global exploration.
        population = [best]
        population.extend(
            evaluate(self.hba.random_order())
            for _ in range(self.hba.scout_bees - 1)
        )

        population_best = min(
            population,
            key=lambda candidate: candidate.fitness,
        )

        if population_best.fitness < best.fitness:
            best = population_best

        self.best_fitness_history.append(best.fitness)

        for _ in range(self.hba_iterations):
            ranked = sorted(
                population,
                key=lambda candidate: candidate.fitness,
            )

            selected = ranked[:self.hba.selected_sites]
            next_population = []

            for index, site in enumerate(selected):
                recruits = (
                    self.hba.elite_recruits
                    if index < self.hba.elite_sites
                    else self.hba.other_recruits
                )

                winner = self.hba._search_site(
                    site,
                    recruits,
                    evaluate,
                )

                next_population.append(winner)

            next_population.extend(
                evaluate(self.hba.random_order())
                for _ in range(
                    self.hba.scout_bees
                    - self.hba.selected_sites
                )
            )

            population = next_population

            iteration_best = min(
                population,
                key=lambda candidate: candidate.fitness,
            )

            if iteration_best.fitness < best.fitness:
                best = iteration_best

            self.best_fitness_history.append(best.fitness)

        return AlgorithmResult(
            algorithm="GA_HBA",
            schedule=best,
            execution_seconds=perf_counter() - started,
            iterations=self.generations + self.hba_iterations,
            seed=self.seed,
        )