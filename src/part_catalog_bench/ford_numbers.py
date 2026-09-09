from __future__ import annotations

import re
from dataclasses import dataclass

from .models import PartNumberFamily

_SEPARATORS = re.compile(r"[\s-]+")
_STANDARD = re.compile(r"^(?P<number>\d{5,6})S(?P<finish>\d*)$")
_PREFIXED = re.compile(
    r"^(?P<prefix>[A-Z]\d[A-Z][A-Z])(?P<basic>\d[A-Z0-9]{2,5})(?P<suffix>[A-Z]{1,3})$"
)
_BASIC = re.compile(r"^\d[A-Z0-9]{2,5}$")
_OCCURRENCE = re.compile(r"^(?P<number>[^#]+)(?P<marker>#.+)$")


@dataclass(frozen=True)
class FordNumber:
    original: str
    compact: str
    family: PartNumberFamily
    display: str


def compact_number(value: str) -> str:
    return _SEPARATORS.sub("", value.strip().upper())


def parse_ford_number(value: str, family: PartNumberFamily = PartNumberFamily.AUTO) -> FordNumber:
    original = str(value).strip()
    compact = compact_number(original)

    standard = _STANDARD.fullmatch(compact)
    prefixed = _PREFIXED.fullmatch(compact)

    detected = family
    display = compact
    if standard and family in {PartNumberFamily.AUTO, PartNumberFamily.STANDARD}:
        detected = PartNumberFamily.STANDARD
        finish = standard.group("finish")
        display = f"{standard.group('number')}-S{finish}"
    elif prefixed and family in {
        PartNumberFamily.AUTO,
        PartNumberFamily.SERVICE,
        PartNumberFamily.ENGINEERING,
    }:
        if family == PartNumberFamily.AUTO:
            detected = (
                PartNumberFamily.SERVICE
                if prefixed.group("prefix").endswith("Z")
                else PartNumberFamily.ENGINEERING
            )
        display = f"{prefixed.group('prefix')}-{prefixed.group('basic')}-{prefixed.group('suffix')}"
    elif _BASIC.fullmatch(compact) and family in {
        PartNumberFamily.AUTO,
        PartNumberFamily.BASIC,
    }:
        detected = PartNumberFamily.BASIC
    elif family == PartNumberFamily.AUTO:
        detected = PartNumberFamily.AUTO

    return FordNumber(original=original, compact=compact, family=detected, display=display)


def normalize_part_number(value: str, family: PartNumberFamily = PartNumberFamily.AUTO) -> str:
    return parse_ford_number(value, family).compact


def normalize_number_with_occurrence(
    value: str, family: PartNumberFamily = PartNumberFamily.AUTO
) -> str:
    text = str(value).strip().upper().replace(" ", "")
    match = _OCCURRENCE.fullmatch(text)
    if not match:
        return normalize_part_number(text, family)
    number = normalize_part_number(match.group("number"), family)
    return f"{number}{match.group('marker')}"
