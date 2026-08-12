from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.metrics import cohen_kappa_score


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "real_jobs"


def average_ranks(values: list[int]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = (index + 1 + end) / 2
        for position in order[index:end]:
            ranks[position] = rank
        index = end
    return ranks


def pearson(left: list[float], right: list[float]) -> float:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_scale = sum((x - left_mean) ** 2 for x in left) ** 0.5
    right_scale = sum((y - right_mean) ** 2 for y in right) ** 0.5
    return numerator / (left_scale * right_scale) if left_scale and right_scale else 0.0


def metrics(left: list[int], right: list[int]) -> dict:
    distances = [abs(x - y) for x, y in zip(left, right)]
    return {
        "pairs": len(left),
        "exact_agreement": round(sum(distance == 0 for distance in distances) / len(distances), 4),
        "within_one_agreement": round(sum(distance <= 1 for distance in distances) / len(distances), 4),
        "mean_absolute_difference": round(sum(distances) / len(distances), 4),
        "linear_weighted_kappa": round(float(cohen_kappa_score(left, right, labels=[0, 1, 2, 3], weights="linear")), 4),
        "quadratic_weighted_kappa": round(float(cohen_kappa_score(left, right, labels=[0, 1, 2, 3], weights="quadratic")), 4),
        "spearman_rho": round(pearson(average_ranks(left), average_ranks(right)), 4),
        "distance_distribution": {str(key): value for key, value in sorted(Counter(distances).items())},
    }


def load_index(path: Path) -> dict[tuple[str, str], dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    index = {(row["candidate_id"], row["job_id"]): row for row in rows}
    if len(index) != len(rows):
        raise ValueError(f"duplicate candidate-job pair in {path}")
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, default=DATA / "relevance_labels.json")
    parser.add_argument("--second", type=Path, default=DATA / "relevance_labels_second.json")
    parser.add_argument("--output", type=Path, default=DATA / "annotation_agreement.json")
    parser.add_argument("--disagreements", type=Path, default=DATA / "annotation_disagreements.json")
    args = parser.parse_args()

    first = load_index(args.first)
    second = load_index(args.second)
    if first.keys() != second.keys():
        missing_second = sorted(set(first) - set(second))
        missing_first = sorted(set(second) - set(first))
        raise ValueError(f"label coverage differs: missing_second={missing_second}, missing_first={missing_first}")

    jobs = {row["job_id"]: row for row in json.loads((DATA / "jobs.json").read_text(encoding="utf-8"))}
    keys = sorted(first)
    first_grades = [int(first[key]["grade"]) for key in keys]
    second_grades = [int(second[key]["grade"]) for key in keys]
    by_candidate: dict[str, list[tuple[int, int]]] = defaultdict(list)
    disagreements = []
    for key, first_grade, second_grade in zip(keys, first_grades, second_grades):
        candidate_id, job_id = key
        by_candidate[candidate_id].append((first_grade, second_grade))
        if first_grade != second_grade:
            job = jobs[job_id]
            disagreements.append(
                {
                    "candidate_id": candidate_id,
                    "job_id": job_id,
                    "company": job["company"],
                    "title": job["title"],
                    "first_grade": first_grade,
                    "second_grade": second_grade,
                    "distance": abs(first_grade - second_grade),
                    "first_rationale": first[key]["rationale"],
                    "second_rationale": second[key]["rationale"],
                }
            )

    result = {
        "dataset": {"jobs": len(jobs), "candidates": len(by_candidate), "pairs": len(keys), "scale": [0, 1, 2, 3]},
        "annotators": {
            "first": next(iter(first.values()))["annotator"],
            "second": next(iter(second.values()))["annotator"],
        },
        "overall": metrics(first_grades, second_grades),
        "by_candidate": {
            candidate: metrics([pair[0] for pair in pairs], [pair[1] for pair in pairs])
            for candidate, pairs in sorted(by_candidate.items())
        },
        "disagreements": {
            "count": len(disagreements),
            "severe_count": sum(row["distance"] > 1 for row in disagreements),
        },
        "interpretation_note": "Kappa measures agreement beyond chance; weighted variants respect the ordinal 0-3 scale. This is model-assisted annotation, not human inter-rater validation.",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.disagreements.write_text(json.dumps(disagreements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
