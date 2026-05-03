import random

DIVERSITY_BONUS = 0.10
REPETITION_PENALTY = 0.05
PURCHASED_PENALTY = 0.30
DT_CATEGORY_BONUS = 0.20


def fitness(chromosome, user_id, score_matrix, product_categories,
            user_purchased, preferred_category=None):
    total = 0.0
    seen = set()
    purchased = user_purchased.get(user_id, set())

    for pid in chromosome:
        score = score_matrix.get((user_id, pid), 0.0)
        cat = product_categories.get(pid)

        total += DIVERSITY_BONUS if cat not in seen else -REPETITION_PENALTY
        if pid in purchased:
            total -= PURCHASED_PENALTY
        if preferred_category and cat == preferred_category:
            total += DT_CATEGORY_BONUS

        total += score
        seen.add(cat)
    return total


def _init_population(pool, pop_size, length):
    pool = list(pool)
    return [random.sample(pool, length) for _ in range(pop_size)]


def _tournament(population, fits, k):
    idx = random.sample(range(len(population)), k)
    return population[max(idx, key=lambda i: fits[i])]


def _ox(p1, p2):
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))
    child = [None] * n
    child[a:b] = p1[a:b]
    fill = [x for x in p2 if x not in child]
    j = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[j]
            j += 1
    return child


def _swap_mutate(chrom, rate):
    out = chrom[:]
    n = len(out)
    for i in range(n):
        if random.random() < rate:
            j = random.randint(0, n - 1)
            out[i], out[j] = out[j], out[i]
    return out


def run(user_id, product_pool, score_matrix, product_categories, user_purchased,
        preferred_category=None,
        length=10, pop_size=60, generations=40,
        crossover_rate=0.8, mutation_rate=0.05,
        tournament_k=5, elite_ratio=0.05, seed=None):
    if seed is not None:
        random.seed(seed)
    if len(product_pool) < length:
        length = max(1, len(product_pool))

    population = _init_population(product_pool, pop_size, length)
    elite = max(1, int(pop_size * elite_ratio))
    history = []

    for _ in range(generations):
        fits = [fitness(c, user_id, score_matrix, product_categories,
                        user_purchased, preferred_category) for c in population]
        order = sorted(range(pop_size), key=lambda i: fits[i], reverse=True)
        nxt = [population[i][:] for i in order[:elite]]
        while len(nxt) < pop_size:
            p1 = _tournament(population, fits, tournament_k)
            p2 = _tournament(population, fits, tournament_k)
            child = _ox(p1, p2) if random.random() < crossover_rate else p1[:]
            nxt.append(_swap_mutate(child, mutation_rate))
        population = nxt
        history.append({"best": max(fits), "avg": sum(fits) / pop_size})

    final = [fitness(c, user_id, score_matrix, product_categories,
                     user_purchased, preferred_category) for c in population]
    best = max(range(pop_size), key=lambda i: final[i])
    return {
        "recommendations": population[best],
        "fitness": final[best],
        "history": history,
    }
