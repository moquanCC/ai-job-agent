from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from src.config import load_yaml


@lru_cache(maxsize=1)
def alias_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for canonical, aliases in load_yaml("configs/skill_aliases.yaml").items():
        result[canonical.casefold()] = canonical
        for alias in aliases:
            result[str(alias).casefold()] = canonical
    return result


def normalize_skill(value: str) -> str:
    stripped = re.sub(r"^[\s•·\-]+|[\s,，。;；]+$", "", value).strip()
    return alias_map().get(stripped.casefold(), stripped)


def normalize_skills(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(normalize_skill(v) for v in values if v and normalize_skill(v)))


def detect_skills(text: str) -> list[str]:
    lowered = text.casefold()
    found: list[str] = []
    for alias, canonical in sorted(alias_map().items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
            found.append(canonical)
    return list(dict.fromkeys(found))
