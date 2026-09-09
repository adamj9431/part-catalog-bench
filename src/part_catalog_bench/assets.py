from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont

from .catalog import load_manifest
from .models import ContextPage, RegionAnnotation
from .util import sha256_file, sha256_text, slugify

_RENDER_LOCKS: dict[str, threading.Lock] = {}
_RENDER_LOCKS_GUARD = threading.Lock()
_FONTCONFIG_LOCK = threading.Lock()


def _render_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _RENDER_LOCKS_GUARD:
        return _RENDER_LOCKS.setdefault(key, threading.Lock())


def _valid_image(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def _fontconfig_environment(manifest_path: Path) -> dict[str, str]:
    """Give bundled Poppler a writable, deterministic Fontconfig cache on macOS."""
    if sys.platform != "darwin":
        return dict(os.environ)
    root = manifest_path.parent / ".render-cache" / "fontconfig"
    cache = root / "cache"
    config = root / "fonts.conf"
    with _FONTCONFIG_LOCK:
        cache.mkdir(parents=True, exist_ok=True)
        if not config.exists():
            config.write_text(
                '<?xml version="1.0"?>\n'
                '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                "<fontconfig>\n"
                "  <dir>/System/Library/Fonts</dir>\n"
                "  <dir>/Library/Fonts</dir>\n"
                f"  <cachedir>{escape(str(cache))}</cachedir>\n"
                "</fontconfig>\n",
                encoding="utf-8",
            )
    return {
        **os.environ,
        "FONTCONFIG_FILE": str(config),
        "FONTCONFIG_PATH": str(root),
    }


def find_pdftoppm() -> str:
    executable = shutil.which("pdftoppm")
    if not executable:
        raise FileNotFoundError(
            "pdftoppm is required to render catalog pages. Install Poppler and try again."
        )
    return executable


def render_catalog_ref(
    manifest_path: Path,
    catalog_ref: str,
    *,
    dpi: int = 300,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> Path:
    manifest = load_manifest(manifest_path)
    page = manifest.get("logical_pages", {}).get(catalog_ref)
    physical_match = re.fullmatch(r"(?P<catalog>[a-z_]+)@source:(?P<page>\d+)", catalog_ref)
    if not page and physical_match:
        catalog = physical_match.group("catalog")
        source_page = int(physical_match.group("page"))
        bounds = manifest.get("catalogs", {}).get(catalog)
        if bounds and bounds["source_start_page"] <= source_page <= bounds["source_end_page"]:
            document = next(
                (
                    item
                    for item in manifest.get("documents", [])
                    if item["catalog"] == catalog
                    and item["source_start_page"] <= source_page <= item["source_end_page"]
                ),
                None,
            )
            page = {"source_page": source_page}
            if document:
                page.update(
                    {
                        "document_path": document["relative_path"],
                        "document_page": source_page - document["source_start_page"] + 1,
                    }
                )
    if not page:
        examples = ", ".join(list(manifest.get("logical_pages", {}))[:8])
        raise KeyError(f"unknown catalog reference {catalog_ref!r}; examples: {examples}")
    source_path = Path(manifest["source"]["path"])
    if not source_path.exists():
        raise FileNotFoundError(
            f"source PDF is not at {source_path}; rerun catalog split with your local source"
        )
    render_path = source_path
    render_page = page["source_page"]
    if page.get("document_path") and page.get("document_page"):
        candidate = manifest_path.parent / page["document_path"]
        if candidate.exists():
            render_path = candidate
            render_page = page["document_page"]
    if output_path is None:
        output_path = manifest_path.parent / "pages" / f"{slugify(catalog_ref)}-{dpi}dpi.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with _render_lock(output_path):
        if not overwrite and _valid_image(output_path):
            return output_path
        temporary = output_path.parent / (f".{output_path.stem}-{uuid.uuid4().hex}.rendering.png")
        prefix = temporary.with_suffix("")
        command = [
            find_pdftoppm(),
            "-f",
            str(render_page),
            "-l",
            str(render_page),
            "-r",
            str(dpi),
            "-png",
            "-singlefile",
            str(render_path),
            str(prefix),
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=_fontconfig_environment(manifest_path),
        )
        if completed.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"pdftoppm failed: {completed.stderr.strip()}")
        if not _valid_image(temporary):
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"renderer did not create a valid PNG for {catalog_ref}")
        temporary.replace(output_path)
    return output_path


def render_prepared_page(
    manifest_path: Path,
    page: ContextPage,
    annotations: list[RegionAnnotation],
    *,
    dpi: int = 300,
) -> Path:
    """Render, crop, and visibly mark one page without using its OCR layer."""
    base = render_catalog_ref(manifest_path, page.ref, dpi=dpi)
    matching = [annotation for annotation in annotations if annotation.page_ref == page.ref]
    if page.crop is None and not matching:
        return base
    signature = json.dumps(
        {
            "render_version": 3,
            "base": sha256_file(base),
            "crop": page.crop.model_dump(exclude_none=True) if page.crop else None,
            "annotations": [annotation.model_dump(exclude_none=True) for annotation in matching],
        },
        sort_keys=True,
    )
    output = (
        manifest_path.parent / "pages" / (f"{slugify(page.ref)}-{sha256_text(signature)[:12]}.png")
    )
    if output.exists():
        return output

    with Image.open(base) as opened:
        image = opened.convert("RGBA")
    full_width, full_height = image.size
    crop = page.crop
    crop_x = crop.x if crop else 0.0
    crop_y = crop.y if crop else 0.0
    crop_width = crop.width if crop else 1.0
    crop_height = crop.height if crop else 1.0
    box = (
        round(crop_x * full_width),
        round(crop_y * full_height),
        round((crop_x + crop_width) * full_width),
        round((crop_y + crop_height) * full_height),
    )
    image = image.crop(box)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    line_width = max(4, round(min(image.size) / 250))
    font = ImageFont.load_default(size=max(16, round(min(image.size) / 45)))
    for annotation in matching:
        if annotation.polygon is not None:
            points = [
                (
                    (point.x - crop_x) / crop_width * image.width,
                    (point.y - crop_y) / crop_height * image.height,
                )
                for point in annotation.polygon
            ]
            left = min(point[0] for point in points)
            top = min(point[1] for point in points)
            right = max(point[0] for point in points)
            bottom = max(point[1] for point in points)
        else:
            rect = annotation.rect
            assert rect is not None
            left = (rect.x - crop_x) / crop_width * image.width
            top = (rect.y - crop_y) / crop_height * image.height
            right = (rect.x + rect.width - crop_x) / crop_width * image.width
            bottom = (rect.y + rect.height - crop_y) / crop_height * image.height
        left, top = max(0, left), max(0, top)
        right, bottom = min(image.width, right), min(image.height, bottom)
        if right <= left or bottom <= top:
            continue
        red, green, blue = ImageColor.getrgb(annotation.color)
        if annotation.polygon is not None:
            draw.polygon(points, fill=(red, green, blue, 48))
            draw.line(
                [*points, points[0]],
                fill=(red, green, blue, 255),
                width=line_width,
                joint="curve",
            )
        else:
            draw.rectangle(
                (left, top, right, bottom),
                fill=(red, green, blue, 48),
                outline=(red, green, blue, 255),
                width=line_width,
            )
        label_box = draw.textbbox((left, top), annotation.label, font=font, stroke_width=2)
        draw.rectangle(label_box, fill=(red, green, blue, 235))
        draw.text(
            (left, top),
            annotation.label,
            fill="black",
            font=font,
            stroke_width=1,
            stroke_fill="white",
        )
    image = Image.alpha_composite(image, overlay)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output


def resolve_context_assets(
    manifest_path: Path | None,
    catalog_refs: list[str],
    pages: list[ContextPage],
    direct_assets: list[str],
    annotations: list[RegionAnnotation],
    *,
    exercise_path: Path,
    dpi: int = 300,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if (catalog_refs or pages) and manifest_path is None:
        raise ValueError("exercise uses catalog_refs but no catalog manifest was supplied")
    page_specs = [ContextPage(ref=ref) for ref in catalog_refs] + pages
    for page in page_specs:
        path = render_prepared_page(
            manifest_path,
            page,
            annotations,
            dpi=dpi,  # type: ignore[arg-type]
        )
        assets.append(_asset_record(path, page.ref))
    for value in direct_assets:
        path = Path(value)
        if not path.is_absolute():
            path = (exercise_path.parent / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"context asset does not exist: {path}")
        assets.append(_asset_record(path, value))
    return assets


def _asset_record(path: Path, label: str) -> dict[str, Any]:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "path": str(path.resolve()),
        "label": label,
        "mime_type": mime_type,
        "sha256": sha256_file(path),
    }
