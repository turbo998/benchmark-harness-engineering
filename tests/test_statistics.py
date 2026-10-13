from benchmark_harness.statistics import clustered_interval, matched_comparison, pareto_frontier


def test_repeats_do_not_create_independent_sample_size() -> None:
    data = {"one-task": [1] * 10000}
    interval = clustered_interval(data)
    assert interval["low"] is None and interval["high"] is None
    assert interval["independent_tasks"] == 1
    independent = {str(i): [i / 10, i / 10] for i in range(10)}
    assert clustered_interval(independent) == clustered_interval(independent)
    assert clustered_interval(independent)["low"] is not None


def test_matched_pair_uses_task_and_repeat_not_unpaired_counts() -> None:
    left = {("a", 0): 1.0, ("a", 1): 0.5, ("b", 0): None, ("c", 0): 1.0}
    right = {("a", 0): 0.5, ("a", 1): 0.5, ("b", 0): 0.0, ("d", 0): 0.0}
    paired = matched_comparison(left, right)
    assert paired["macro_paired_difference"] == 0.25
    assert paired["matched_repeat_pairs"] == 2
    assert paired["uncertainty"]["independent_tasks"] == 1


def test_pareto_missing_excluded_and_equal_points_retained() -> None:
    points = [
        {"point_id": "cheap", "cost_usd": 1, "quality": 0.8},
        {"point_id": "dominated", "cost_usd": 2, "quality": 0.7},
        {"point_id": "quality", "cost_usd": 3, "quality": 1},
        {"point_id": "duplicate", "cost_usd": 1, "quality": 0.8},
        {"point_id": "unknown", "cost_usd": None, "quality": 1},
        {"point_id": "pending", "cost_usd": 0, "quality": None},
    ]
    assert pareto_frontier(points) == ["cheap", "duplicate", "quality"]
