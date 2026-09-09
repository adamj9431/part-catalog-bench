from pathlib import Path

from pypdf import PdfWriter

from part_catalog_bench.catalog import split_catalog, validate_manifest
from part_catalog_bench.source import SourceDefinition


def test_bookmark_split_covers_both_catalogs(tmp_path: Path) -> None:
    source = tmp_path / "catalog.pdf"
    writer = PdfWriter()
    for _ in range(6):
        writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Test Master Parts Catalog"})
    text_root = writer.add_outline_item("Test Catalog (Text)", 0)
    text_group = writer.add_outline_item("Section 20 - Brakes", 0, parent=text_root)
    writer.add_outline_item("Section 20", 1, parent=text_group)
    illustrations_root = writer.add_outline_item("Test Catalog (Illustrations)", 3)
    illustrations_group = writer.add_outline_item(
        "Section 20 - Brakes", 3, parent=illustrations_root
    )
    writer.add_outline_item("Illustrations Section 20", 4, parent=illustrations_group)
    with source.open("wb") as stream:
        writer.write(stream)

    definition = SourceDefinition.model_validate(
        {
            "id": "test",
            "title": "Test",
            "expected": {"pages": 6, "title_contains": "Master Parts"},
            "catalog_roots": {
                "text": {"title_contains": "(Text)"},
                "illustrations": {"title_contains": "(Illustrations)"},
            },
            "logical_page_rules": [
                {
                    "catalog": "illustrations",
                    "bookmark_regex": "^Illustrations Section (?P<section>\\d+)$",
                    "format": "illustrations:{section}-{page}",
                }
            ],
            "guide": "unused.md",
        }
    )
    manifest = split_catalog(source, tmp_path / "out", definition)
    assert validate_manifest(manifest) == []
