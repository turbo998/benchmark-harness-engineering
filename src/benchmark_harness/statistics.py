"""Matched task-clustered bootstrap; repeat observations are not independent tasks."""

from __future__ import annotations

import random
import statistics
from collections.abc import Mapping, Sequence
from typing import Any


def clustered_interval(
    task_values: Mapping[str, Sequence[float]],
    *,
    seed: int = 42,
    draws: int = 2000,
    minimum_tasks: int = 10,
) -> dict[str, Any]:
    means = [statistics.mean(v) for _, v in sorted(task_values.items()) if v]
    if len(means) < minimum_tasks:
        return {
            "low": None,
            "high": None,
            "method": "task-cluster-bootstrap",
            "reason": f"Only {len(means)} independent tasks; minimum {minimum_tasks}",
            "independent_tasks": len(means),
        }
    if draws < 100:
        raise ValueError("Bootstrap needs at least 100 draws")
    rng = random.Random(seed)
    boot = sorted(statistics.mean(rng.choices(means, k=len(means))) for _ in range(draws))
    return {
        "low": boot[int(0.025 * (draws - 1))],
        "high": boot[int(0.975 * (draws - 1))],
        "method": "task-cluster-bootstrap",
        "reason": None,
        "independent_tasks": len(means),
    }


def matched_comparison(
    left: Mapping[tuple[str, int], float | None],
    right: Mapping[tuple[str, int], float | None],
    *,
    seed: int = 42,
) -> dict[str, Any]:
    clusters: dict[str, list[float]] = {}
    for key in sorted(left.keys() & right.keys()):
        a, b = left[key], right[key]
        if a is not None and b is not None:
            clusters.setdefault(key[0], []).append(a - b)
    mean = statistics.mean(statistics.mean(v) for v in clusters.values()) if clusters else None
    return {
        "macro_paired_difference": mean,
        "matched_repeat_pairs": sum(len(v) for v in clusters.values()),
        "uncertainty": clustered_interval(clusters, seed=seed),
        "direction": "left minus right; repeated observations clustered by task",
    }


def pareto_frontier(points: list[dict[str, Any]]) -> list[str]:
    """Minimize cost, maximize quality; missing/partial costs never qualify."""
    valid = [p for p in points if p.get("cost_usd") is not None and p.get("quality") is not None]
    frontier = []
    for point in valid:
        dominated = any(
            other["cost_usd"] <= point["cost_usd"]
            and other["quality"] >= point["quality"]
            and (other["cost_usd"] < point["cost_usd"] or other["quality"] > point["quality"])
            for other in valid
        )
        if not dominated:
            frontier.append(point["point_id"])
    return sorted(frontier)
