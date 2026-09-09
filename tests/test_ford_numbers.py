from part_catalog_bench.ford_numbers import parse_ford_number
from part_catalog_bench.models import PartNumberFamily


def test_service_number_separator_variants_are_equivalent() -> None:
    values = ["C7SZ-9092-A", "C7SZ 9092 A", "C7SZ9092A"]
    parsed = [parse_ford_number(value) for value in values]
    assert {item.compact for item in parsed} == {"C7SZ9092A"}
    assert {item.family for item in parsed} == {PartNumberFamily.SERVICE}


def test_engineering_and_standard_number_families() -> None:
    assert parse_ford_number("C7SA-9092-A").family == PartNumberFamily.ENGINEERING
    standard = parse_ford_number("34445 S8")
    assert standard.family == PartNumberFamily.STANDARD
    assert standard.display == "34445-S8"
    assert parse_ford_number("34445-S").compact != standard.compact
