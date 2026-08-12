from __future__ import annotations

from src.config import load_yaml


def weights() -> dict[str, float]:
    return {key: float(value) for key, value in load_yaml("configs/scoring.yaml")["weights"].items()}


def fuse(subscores: dict[str, float], custom_weights: dict[str, float] | None = None) -> float:
    selected = custom_weights or weights()
    total_weight = sum(selected.values())
    if total_weight <= 0:
        raise ValueError("评分权重总和必须大于 0")
    return round(sum(subscores[key] * selected[key] for key in selected) / total_weight, 2)


def recommendation(score: float) -> str:
    if score >= 85:
        return "高度匹配：优先投递并定制简历"
    if score >= 70:
        return "较为匹配：建议投递，补强少量技能"
    if score >= 55:
        return "一般匹配：可作为扩展选择"
    return "匹配较低：暂不优先"
