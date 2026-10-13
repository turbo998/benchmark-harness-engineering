"""Original, deterministic fixture packs. No model is called by generation or acceptance."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from benchmark_harness.contracts import Case, canonical, make_case
from benchmark_harness.scoring import score_api

SLUG_REFERENCE = """import re
def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
"""
SLUG_NEGATIVE = """def slug(text):
    return text.lower().replace(' ', '-')
"""
SLUG_VERIFIER = """from solution import slug
assert slug(' Hello, WORLD! ') == 'hello-world'
assert slug('A___B---C') == 'a-b-c'
assert slug('中文 Café 42') == 'caf-42'
assert slug('---') == ''
assert slug('a0B9') == 'a0b9'
print('VERIFIER_PASS')
"""
INTERVAL_REFERENCE = """def merge(intervals):
    rows = sorted((int(a), int(b)) for a, b in intervals)
    if any(a > b for a, b in rows):
        raise ValueError('reversed interval')
    result = []
    for a, b in rows:
        if result and a <= result[-1][1]:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result
"""
INTERVAL_NEGATIVE = """def merge(intervals):
    return sorted([list(row) for row in intervals])
"""
INTERVAL_NEGATIVE_ADJACENT = INTERVAL_REFERENCE.replace(
    "a <= result[-1][1]", "a <= result[-1][1] + 1"
)
INTERVAL_VERIFIER = """from solution import merge
assert merge([]) == []
assert merge([[5, 7], [1, 3], [3, 6]]) == [[1, 7]]
assert merge([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]
assert merge([[1, 9], [2, 3], [9, 9]]) == [[1, 9]]
try:
    merge([[3, 1]])
except ValueError:
    pass
else:
    raise AssertionError('reversed interval accepted')
print('VERIFIER_PASS')
"""
GRAPH_REFERENCE = """import heapq
def route(edges, start, target):
    graph = {}
    for u, v, w in edges:
        if type(w) is not int or w <= 0:
            raise ValueError('weights must be positive integers')
        graph.setdefault(u, []).append((v, w))
    queue = [(0, (start,), start)]
    best = {}
    while queue:
        cost, path, node = heapq.heappop(queue)
        if node in best:
            continue
        best[node] = (cost, path)
        if node == target:
            return {'distance': cost, 'path': list(path)}
        for dest, weight in graph.get(node, []):
            if dest not in best:
                heapq.heappush(queue, (cost + weight, path + (dest,), dest))
    return {'distance': None, 'path': []}
"""
GRAPH_NEGATIVE = """def route(edges, start, target):
    for u, v, w in edges:
        if u == start and v == target:
            return {'distance': w, 'path': [start, target]}
    return {'distance': None, 'path': []}
"""
GRAPH_VERIFIER = """from solution import route
assert route([('a','c',8),('a','b',2),('b','c',1)], 'a','c') == {'distance':3,'path':['a','b','c']}
assert route([('a','c',1),('a','b',1),('c','d',1),('b','d',1)], 'a','d') == {'distance':2,'path':['a','b','d']}
assert route([('a','b',1)], 'b','a') == {'distance':None,'path':[]}
assert route([], 'x','x') == {'distance':0,'path':['x']}
assert route([('a','b',1),('b','a',1),('b','z',4)], 'a','z') == {'distance':5,'path':['a','b','z']}
for weight in [0,-1,1.5,True]:
    try:
        route([('a','b',weight)], 'a','b')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid weight accepted')
print('VERIFIER_PASS')
"""


def _api(
    *,
    title: str,
    language: str,
    difficulty: str,
    prompt: str,
    expected: Any,
    rejected: list[Any],
    seed: int,
    json_output: bool = False,
) -> Case:
    assertions: list[dict[str, Any]] = [
        {
            "name": "exact-answer",
            "kind": "json_equal" if json_output else "exact",
            "expected": expected,
            "weight": 3.0,
            "category": "functional",
        }
    ]
    if json_output:
        assertions.append(
            {
                "name": "declared-shape",
                "kind": "json_keys",
                "expected": sorted(expected),
                "weight": 1.0,
                "category": "compliance",
            }
        )
    else:
        assertions.append(
            {
                "name": "no-explanation",
                "kind": "exact",
                "expected": expected,
                "weight": 1.0,
                "category": "compliance",
            }
        )
    return make_case(
        track="api",
        title=title,
        language=language,
        difficulty=difficulty,
        prompt=prompt,
        assertions=assertions,
        accepted=[expected],
        rejected=rejected,
        seed=seed,
    )


def _coding(
    title: str,
    difficulty: str,
    instruction: str,
    reference: str,
    negatives: list[str],
    verifier: str,
    seed: int,
) -> Case:
    return make_case(
        track="coding",
        title=title,
        language="en",
        difficulty=difficulty,
        prompt=instruction,
        seed=seed,
        coding={
            "entrypoint": "solution.py",
            "instruction": instruction,
            "reference": reference,
            "negatives": negatives,
            "verifier": verifier,
            "seed_files": {"solution.py": ""},
            "verifier_hash": hashlib.sha256(verifier.encode()).hexdigest(),
        },
    )


def template_cases(seed: int = 42) -> list[Case]:
    return [
        _api(
            title="English sum",
            language="en",
            difficulty="atomic",
            prompt="Return only the decimal sum of 17 and 25.",
            expected="42",
            rejected=["41", "The answer is 42", ""],
            seed=seed,
        ),
        _api(
            title="中文分类",
            language="zh",
            difficulty="atomic",
            prompt="仅输出季节名称：在北半球，一月通常属于哪个季节？",
            expected="冬季",
            rejected=["夏季", "一月是冬季。", ""],
            seed=seed + 1,
        ),
        _api(
            title="English structured extraction",
            language="en",
            difficulty="medium",
            prompt='Return only JSON with keys "city" and "count" for: Oslo has 3 stops.',
            expected={"city": "Oslo", "count": 3},
            rejected=[
                "{bad",
                {"city": "Oslo"},
                {"city": "Oslo", "count": "3"},
                {"city": "Paris", "count": 3},
            ],
            seed=seed + 2,
            json_output=True,
        ),
        _api(
            title="中文结构化提取",
            language="zh",
            difficulty="medium",
            prompt='只输出JSON，键为"城市"和"人数"：成都有12人。',
            expected={"城市": "成都", "人数": 12},
            rejected=["不是JSON", {"城市": "成都"}, {"城市": "成都", "人数": 21}],
            seed=seed + 3,
            json_output=True,
        ),
        _api(
            title="English rule precedence",
            language="en",
            difficulty="complex",
            prompt="Sort jobs by descending priority, then ascending name: b=2,a=2,c=1. "
            'Return only JSON {"order":[names]}.',
            expected={"order": ["a", "b", "c"]},
            rejected=[{"order": ["b", "a", "c"]}, {"order": ["c", "a", "b"]}, {"order": []}],
            seed=seed + 4,
            json_output=True,
        ),
        _api(
            title="中文约束计算",
            language="zh",
            difficulty="complex",
            prompt='只输出JSON {"总价":整数,"件数":整数}。苹果每件7元，买3件；'
            "梨每件4元，买2件。满25元减5元。",
            expected={"总价": 24, "件数": 5},
            rejected=[{"总价": 29, "件数": 5}, {"总价": 24}, {"总价": 24, "件数": 4}],
            seed=seed + 5,
            json_output=True,
        ),
        _coding(
            "ASCII slug",
            "atomic",
            "Implement slug(text) in solution.py. Lowercase ASCII letters, keep ASCII "
            "digits, replace each maximal run of other characters by one hyphen, "
            "and remove leading/trailing hyphens. Return a string.",
            SLUG_REFERENCE,
            [SLUG_NEGATIVE],
            SLUG_VERIFIER,
            seed + 6,
        ),
        _coding(
            "Closed interval merge",
            "medium",
            "Implement merge(intervals) in solution.py for pairs of integer closed "
            "endpoints. Return sorted disjoint [start,end] lists, merging overlaps "
            "including equal endpoints, but NOT adjacent disjoint integers. "
            "Empty input gives []; reversed endpoints raise ValueError.",
            INTERVAL_REFERENCE,
            [INTERVAL_NEGATIVE, INTERVAL_NEGATIVE_ADJACENT],
            INTERVAL_VERIFIER,
            seed + 7,
        ),
        _coding(
            "Deterministic directed route",
            "complex",
            "Implement route(edges,start,target) in solution.py. Node names are strings; "
            "each directed (from,to,weight) edge requires a strictly positive integer "
            "weight (bool is invalid); otherwise raise ValueError. Return a dict with "
            "distance and path for the shortest route, breaking equal-distance ties "
            "by lexicographic order of the entire node-name path. Unreachable gives "
            "{'distance':None,'path':[]}; start==target gives distance 0 and [start].",
            GRAPH_REFERENCE,
            [GRAPH_NEGATIVE],
            GRAPH_VERIFIER,
            seed + 8,
        ),
    ]


def write_dataset(path: Path, cases: list[Case]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical(c) + b"\n" for c in sorted(cases, key=lambda c: c.case_id))
    if path.exists() and path.read_bytes() != payload:
        raise ValueError("Refusing to overwrite a different dataset; choose a new output")
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(payload)


def export_coding(cases: list[Case], directory: Path) -> None:
    for case in cases:
        if case.coding is None:
            continue
        root = directory / case.difficulty
        visible = root / "agent-visible"
        hidden = root / "trusted-verifier"
        reference = root / "reference"
        for path in (visible, hidden, reference):
            path.mkdir(parents=True, exist_ok=True)
        (visible / "instruction.md").write_text(case.prompt + "\n", encoding="utf-8")
        (visible / "solution.py").write_text("", encoding="utf-8")
        (hidden / "verify.py").write_text(case.coding.verifier, encoding="utf-8")
        (reference / "solution.py").write_text(case.coding.reference, encoding="utf-8")
        for i, code in enumerate(case.coding.negatives):
            (root / f"negative-{i}.py").write_text(code, encoding="utf-8")
        (root / "case.json").write_bytes(canonical(case) + b"\n")


def trusted_fixture_check(case: Case, code: str, workspace: Path) -> bool:
    """Runs only ORIGINAL trusted fixtures on the host; this is not an agent sandbox."""
    if case.coding is None:
        raise ValueError("No coding verifier")
    trusted = {
        SLUG_VERIFIER: (SLUG_REFERENCE, (SLUG_NEGATIVE,)),
        INTERVAL_VERIFIER: (INTERVAL_REFERENCE, (INTERVAL_NEGATIVE, INTERVAL_NEGATIVE_ADJACENT)),
        GRAPH_VERIFIER: (GRAPH_REFERENCE, (GRAPH_NEGATIVE,)),
    }
    specification = trusted.get(case.coding.verifier)
    if (
        specification is None
        or (case.coding.reference, case.coding.negatives) != specification
        or code not in (specification[0], *specification[1])
    ):
        raise ValueError(
            "Host acceptance only permits frozen original fixtures; use a validated sandbox"
        )
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "solution.py").write_text(code, encoding="utf-8")
    (workspace / "verify.py").write_text(case.coding.verifier, encoding="utf-8")
    command = [
        sys.executable,
        "-I",
        "-B",
        "-c",
        "import sys,runpy; sys.path.insert(0,'.'); runpy.run_path('verify.py')",
    ]
    process = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=5)
    return process.returncode == 0 and "VERIFIER_PASS" in process.stdout


def accept_cases(cases: list[Case], workspace: Path) -> dict[str, Any]:
    accepted: list[str] = []
    rejected: list[dict[str, str]] = []
    for case in cases:
        reason: str | None = None
        if case.track == "api":
            if any(score_api(case, x).functional != 1 for x in case.accepted):
                reason = "Reference response fails"
            elif any(score_api(case, x).functional == 1 for x in case.rejected):
                reason = "Negative response passes"
        elif case.coding is not None:
            try:
                if not trusted_fixture_check(
                    case, case.coding.reference, workspace / case.case_id[5:21] / "reference"
                ):
                    reason = "Reference solution fails"
                elif any(
                    trusted_fixture_check(
                        case, code, workspace / case.case_id[5:21] / f"negative-{i}"
                    )
                    for i, code in enumerate(case.coding.negatives)
                ):
                    reason = "Negative solution passes"
            except (ValueError, subprocess.TimeoutExpired) as error:
                reason = f"Trusted fixture rejected: {error}"
        if reason:
            rejected.append({"case_id": case.case_id, "reason": reason})
        else:
            accepted.append(case.case_id)
    return {
        "accepted": accepted,
        "rejected": rejected,
        "fixture_tier": "trusted-host-check",
        "sandbox_tier": "unvalidated",
        "statistical_scope": "engineering fixtures, not a ranking",
    }


def write_acceptance(path: Path, acceptance: dict[str, Any]) -> None:
    path.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
