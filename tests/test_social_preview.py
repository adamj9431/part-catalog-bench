from pathlib import Path

from PIL import Image

from part_catalog_bench.social_preview import _frontier, render_social_preview


def test_preview_handles_missing_cost(tmp_path):
    path = tmp_path / "preview.png"
    render_social_preview([], path)
    with Image.open(path) as image:
        assert image.size == (1200, 630)


def test_social_frontier():
    rows = [
        {"cost_usd": 1, "score": .3}, {"cost_usd": 2, "score": .8},
        {"cost_usd": 3, "score": .7}, {"cost_usd": 4, "score": .9},
    ]
    assert _frontier(rows) == [rows[0], rows[1], rows[3]]


def test_static_sharing_metadata_points_to_generated_image():
    html = Path("site/index.html").read_text()
    url = "https://adamj9431.github.io/part-catalog-bench/data/pareto-preview.png"
    assert f'property="og:image" content="{url}"' in html
    assert f'name="twitter:image" content="{url}"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html
