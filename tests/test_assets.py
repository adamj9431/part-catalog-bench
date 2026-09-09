import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from part_catalog_bench import assets
from part_catalog_bench.models import ContextPage, RegionAnnotation


def test_page_cache_is_dpi_specific_and_repairs_invalid_png(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"test source")
    section = tmp_path / "section.pdf"
    section.write_bytes(b"test section")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": {"path": str(source)},
                "logical_pages": {
                    "illustrations:1-1": {
                        "source_page": 1,
                        "document_path": "section.pdf",
                        "document_page": 1,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        Image.new("RGB", (20, 20), "white").save(Path(str(command[-1]) + ".png"))
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(assets, "find_pdftoppm", lambda: "pdftoppm")
    monkeypatch.setattr(assets.subprocess, "run", fake_run)
    at_180 = assets.render_catalog_ref(manifest, "illustrations:1-1", dpi=180)
    at_300 = assets.render_catalog_ref(manifest, "illustrations:1-1", dpi=300)
    assert at_180 != at_300
    assert "180dpi" in at_180.name
    assert "300dpi" in at_300.name
    assert len(calls) == 2
    assert all(command[-2] == str(section) for command in calls)

    at_180.write_bytes(b"incomplete")
    repaired = assets.render_catalog_ref(manifest, "illustrations:1-1", dpi=180)
    assert repaired == at_180
    assert len(calls) == 3
    with Image.open(repaired) as image:
        image.verify()


def test_crop_and_annotation_are_rendered_in_normalized_coordinates(
    tmp_path: Path, monkeypatch
) -> None:
    base = tmp_path / "base.png"
    Image.new("RGB", (1000, 800), "white").save(base)
    monkeypatch.setattr(assets, "render_catalog_ref", lambda *args, **kwargs: base)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    page = ContextPage(
        ref="illustrations:24-2",
        crop={"x": 0.1, "y": 0.25, "width": 0.5, "height": 0.5},
    )
    annotation = RegionAnnotation(
        id="a",
        label="A",
        page_ref=page.ref,
        rect={"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.1},
    )
    output = assets.render_prepared_page(manifest, page, [annotation], dpi=180)
    with Image.open(output) as image:
        assert image.size == (500, 400)
        assert image.getpixel((100, 40)) != (255, 255, 255)


def test_polygon_annotation_is_rendered(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.png"
    Image.new("RGB", (1000, 800), "white").save(base)
    monkeypatch.setattr(assets, "render_catalog_ref", lambda *args, **kwargs: base)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    page = ContextPage(ref="illustrations:24-2")
    annotation = RegionAnnotation(
        id="polygon-a",
        label="A",
        page_ref=page.ref,
        polygon=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.4, "y": 0.1},
            {"x": 0.25, "y": 0.4},
        ],
    )

    output = assets.render_prepared_page(manifest, page, [annotation], dpi=180)

    with Image.open(output) as image:
        assert image.getpixel((250, 160)) != (255, 255, 255)
