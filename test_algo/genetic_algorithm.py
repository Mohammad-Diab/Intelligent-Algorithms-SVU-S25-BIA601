import random
import numpy as np

DIVERSITY_BONUS = 0.10
REPETITION_PENALTY = 0.05
PURCHASED_PENALTY = 0.30


def fitness(chromosome, user_id, score_matrix, product_categories, user_purchased):
    total = 0.0
    seen_categories = set()
    purchased = user_purchased.get(user_id, set())

    for product_id in chromosome:
        score = score_matrix.get((user_id, product_id), 0.0)
        category = product_categories.get(product_id)

        if category not in seen_categories:
            total += DIVERSITY_BONUS
        else:
            total -= REPETITION_PENALTY

        if product_id in purchased:
            total -= PURCHASED_PENALTY

        total += score
        seen_categories.add(category)

    return total


def init_population(product_pool, pop_size, chromosome_length):
    pool = list(product_pool)
    return [random.sample(pool, chromosome_length) for _ in range(pop_size)]


def tournament_select(population, fitnesses, k=5):
    indices = random.sample(range(len(population)), k)
    best = max(indices, key=lambda i: fitnesses[i])
    return population[best]


def order_crossover(parent1, parent2):
    n = len(parent1)
    a, b = sorted(random.sample(range(n), 2))
    child = [None] * n
    child[a:b] = parent1[a:b]
    fill = [x for x in parent2 if x not in child]
    idx = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[idx]
            idx += 1
    return child


def swap_mutation(chromosome, rate=0.05):
    result = chromosome[:]
    n = len(result)
    for i in range(n):
        if random.random() < rate:
            j = random.randint(0, n - 1)
            result[i], result[j] = result[j], result[i]
    return result


def run_ga(
    user_id,
    product_pool,
    score_matrix,
    product_categories,
    user_purchased,
    chromosome_length=10,
    pop_size=100,
    generations=200,
    crossover_rate=0.8,
    mutation_rate=0.05,
    tournament_k=5,
    elite_ratio=0.05,
    seed=None,
):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    population = init_population(product_pool, pop_size, chromosome_length)
    elite_count = max(1, int(pop_size * elite_ratio))
    history = []

    for gen in range(generations):
        fitnesses = [
            fitness(c, user_id, score_matrix, product_categories, user_purchased)
            for c in population
        ]

        order = sorted(range(pop_size), key=lambda i: fitnesses[i], reverse=True)
        new_population = [population[i][:] for i in order[:elite_count]]

        while len(new_population) < pop_size:
            p1 = tournament_select(population, fitnesses, tournament_k)
            p2 = tournament_select(population, fitnesses, tournament_k)
            if random.random() < crossover_rate:
                child = order_crossover(p1, p2)
            else:
                child = p1[:]
            child = swap_mutation(child, mutation_rate)
            new_population.append(child)

        population = new_population
        best_fit = max(fitnesses)
        avg_fit = sum(fitnesses) / pop_size
        history.append({"gen": gen + 1, "best": best_fit, "avg": avg_fit})

    final_fitnesses = [
        fitness(c, user_id, score_matrix, product_categories, user_purchased)
        for c in population
    ]
    best_idx = max(range(pop_size), key=lambda i: final_fitnesses[i])
    return {
        "user_id": user_id,
        "recommendations": population[best_idx],
        "fitness": final_fitnesses[best_idx],
        "history": history,
    }


if __name__ == "__main__":
    from data_loader import load_all

    data = load_all()
    product_pool = list(data["product_categories"].keys())

    test_user = 1
    result = run_ga(
        user_id=test_user,
        product_pool=product_pool,
        score_matrix=data["score_matrix"],
        product_categories=data["product_categories"],
        user_purchased=data["user_purchased"],
        generations=100,
        seed=42,
    )

    print(f"User {test_user} — final fitness: {result['fitness']:.3f}")
    print("Top 10 recommendations:")
    for rank, pid in enumerate(result["recommendations"], 1):
        cat = data["product_categories"].get(pid, "?")
        score = data["score_matrix"].get((test_user, pid), 0.0)
        print(f"  {rank:2d}. product {pid:3d}  [{cat:16s}]  score={score:.3f}")

    print("\nFitness curve (every 10th generation):")
    for h in result["history"][::10]:
        print(f"  gen {h['gen']:3d}: best={h['best']:.3f}  avg={h['avg']:.3f}")
