from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

from .source import SourceDefinition
from .util import sha256_file, slugify, write_json


@dataclass(frozen=True)
class BookmarkNode:
    id: int
    title: str
    page_index: int
    depth: int
    ancestors: tuple[int, ...]
    ancestor_titles: tuple[str, ...]


def open_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        result = reader.decrypt("")
        if not result:
            raise ValueError("PDF is encrypted and could not be opened with its document password")
    return reader


def flatten_outline(reader: PdfReader) -> list[BookmarkNode]:
    nodes: list[BookmarkNode] = []
    counter = 0

    def walk(
        items: list[Any],
        depth: int = 0,
        ancestor_ids: tuple[int, ...] = (),
        ancestor_titles: tuple[str, ...] = (),
    ) -> None:
        nonlocal counter
        previous: BookmarkNode | None = None
        for item in items:
            if isinstance(item, list):
                if previous is not None:
                    walk(
                        item,
                        depth + 1,
                        previous.ancestors + (previous.id,),
                        previous.ancestor_titles + (previous.title,),
                    )
                continue
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:
                previous = None
                continue
            node = BookmarkNode(
                id=counter,
                title=getattr(item, "title", str(item)).strip(),
                page_index=page_index,
                depth=depth,
                ancestors=ancestor_ids,
                ancestor_titles=ancestor_titles,
            )
            counter += 1
            nodes.append(node)
            previous = node

    walk(reader.outline)
    return nodes


def inspect_catalog(path: Path, definition: SourceDefinition) -> dict[str, Any]:
    reader = open_reader(path)
    nodes = flatten_outline(reader)
    metadata = reader.metadata or {}
    report: dict[str, Any] = {
        "source_id": definition.id,
        "path": str(path.resolve()),
        "pages": len(reader.pages),
        "title": metadata.get("/Title"),
        "encrypted": PdfReader(str(path)).is_encrypted,
        "bookmarks": len(nodes),
        "catalog_roots": {},
    }
    errors = identify_source(reader, definition)
    report["identity_errors"] = errors
    for catalog_name, rule in definition.catalog_roots.items():
        matches = [
            node
            for node in nodes
            if node.depth == 0 and rule.title_contains.lower() in node.title.lower()
        ]
        report["catalog_roots"][catalog_name] = [
            {"title": node.title, "physical_page": node.page_index + 1} for node in matches
        ]
    return report


def identify_source(reader: PdfReader, definition: SourceDefinition) -> list[str]:
    errors: list[str] = []
    expected = definition.expected
    if expected.pages is not None and len(reader.pages) != expected.pages:
        errors.append(f"expected {expected.pages} pages, found {len(reader.pages)}")
    title = str((reader.metadata or {}).get("/Title", ""))
    if expected.title_contains and expected.title_contains.lower() not in title.lower():
        errors.append(f"PDF title does not contain {expected.title_contains!r}; found {title!r}")
    return errors


def _catalog_roots(
    nodes: list[BookmarkNode], definition: SourceDefinition
) -> dict[str, BookmarkNode]:
    roots: dict[str, BookmarkNode] = {}
    for name, rule in definition.catalog_roots.items():
        matches = [
            node
            for node in nodes
            if node.depth == 0 and rule.title_contains.lower() in node.title.lower()
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one {name!r} root containing {rule.title_contains!r}; "
                f"found {[node.title for node in matches]}"
            )
        roots[name] = matches[0]
    return roots


def _has_children(node: BookmarkNode, all_nodes: list[BookmarkNode]) -> bool:
    return any(node.id in other.ancestors for other in all_nodes)


def _relative_output_path(
    catalog_name: str, node: BookmarkNode, root: BookmarkNode, all_nodes: list[BookmarkNode]
) -> Path:
    path_titles = node.ancestor_titles + (node.title,)
    try:
        root_position = path_titles.index(root.title)
    except ValueError as exc:
        raise ValueError(f"bookmark {node.title!r} is not beneath {root.title!r}") from exc
    relative_titles = path_titles[root_position + 1 :]
    direct_group = slugify(relative_titles[0])
    has_children = _has_children(node, all_nodes)

    if len(relative_titles) == 1:
        filename = "divider.pdf" if has_children else "content.pdf"
        return Path(catalog_name) / direct_group / filename

    parent_dirs = [slugify(value) for value in relative_titles[1:-1]]
    node_slug = slugify(relative_titles[-1])
    if has_children:
        return Path(catalog_name).joinpath(
            direct_group, *parent_dirs, node_slug, f"{node_slug}.pdf"
        )
    return Path(catalog_name).joinpath(direct_group, *parent_dirs, f"{node_slug}.pdf")


def _unique_boundary_nodes(nodes: list[BookmarkNode]) -> list[BookmarkNode]:
    grouped: dict[int, list[BookmarkNode]] = defaultdict(list)
    for node in nodes:
        grouped[node.page_index].append(node)
    selected = []
    for _page_index, candidates in grouped.items():
        # The deepest destination is the most specific label for a shared boundary.
        selected.append(max(candidates, key=lambda node: (node.depth, node.id)))
    return sorted(selected, key=lambda node: (node.page_index, node.id))


def build_split_plan(
    reader: PdfReader, definition: SourceDefinition
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_nodes = flatten_outline(reader)
    roots = _catalog_roots(all_nodes, definition)
    top_nodes = sorted([node for node in all_nodes if node.depth == 0], key=lambda n: n.page_index)
    plan: list[dict[str, Any]] = []
    catalog_meta: dict[str, Any] = {}

    for catalog_name, root in roots.items():
        later_roots = [node.page_index for node in top_nodes if node.page_index > root.page_index]
        root_end = min(later_roots) - 1 if later_roots else len(reader.pages) - 1
        descendants = [node for node in all_nodes if root.id in node.ancestors]
        boundaries = _unique_boundary_nodes(descendants)
        if not boundaries or boundaries[0].page_index > root.page_index:
            synthetic = BookmarkNode(
                id=-1,
                title="Front Matter",
                page_index=root.page_index,
                depth=1,
                ancestors=(root.id,),
                ancestor_titles=(root.title,),
            )
            boundaries.insert(0, synthetic)

        for index, node in enumerate(boundaries):
            next_start = (
                boundaries[index + 1].page_index if index + 1 < len(boundaries) else root_end + 1
            )
            end_index = min(next_start - 1, root_end)
            if end_index < node.page_index:
                continue
            relative_path = _relative_output_path(catalog_name, node, root, all_nodes)
            plan.append(
                {
                    "id": f"{catalog_name}-{node.page_index + 1:05d}",
                    "catalog": catalog_name,
                    "title": node.title,
                    "bookmark_path": list(node.ancestor_titles + (node.title,)),
                    "source_start_page": node.page_index + 1,
                    "source_end_page": end_index + 1,
                    "page_count": end_index - node.page_index + 1,
                    "relative_path": relative_path.as_posix(),
                }
            )
        catalog_meta[catalog_name] = {
            "root_title": root.title,
            "source_start_page": root.page_index + 1,
            "source_end_page": root_end + 1,
        }
    return sorted(plan, key=lambda item: item["source_start_page"]), catalog_meta


def _logical_page_map(
    plan: list[dict[str, Any]], definition: SourceDefinition
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for document in plan:
        for rule in definition.logical_page_rules:
            if rule.catalog != document["catalog"]:
                continue
            match = rule.match(document["title"])
            if not match:
                continue
            values = match.groupdict()
            for offset in range(document["page_count"]):
                ref = rule.format.format(**values, page=offset + 1)
                candidates[ref].append(
                    (
                        {
                            "catalog": document["catalog"],
                            "document_id": document["id"],
                            "document_path": document["relative_path"],
                            "document_page": offset + 1,
                            "source_page": document["source_start_page"] + offset,
                        },
                        document,
                    )
                )
            break
    logical: dict[str, dict[str, Any]] = {}
    for ref, matches in candidates.items():
        if len(matches) == 1:
            logical[ref] = matches[0][0]
            continue
        for page, document in matches:
            parent = document["bookmark_path"][-2]
            section = document["title"].removeprefix("Section ").strip()
            qualifier = parent
            if " - " in parent and section:
                qualifier = parent.split(" - ", 1)[1]
            qualified = ref.replace("-", f"@{slugify(qualifier)}-", 1)
            if qualified in logical:
                qualified = ref.replace("-", f"@{document['id']}-", 1)
            logical[qualified] = page
    return logical


def split_catalog(
    source_path: Path,
    output_root: Path,
    definition: SourceDefinition,
    *,
    overwrite: bool = False,
) -> Path:
    reader = open_reader(source_path)
    errors = identify_source(reader, definition)
    if errors:
        raise ValueError("source identification failed: " + "; ".join(errors))

    plan, catalog_meta = build_split_plan(reader, definition)
    destination = output_root / definition.id
    destination.mkdir(parents=True, exist_ok=True)

    for item in plan:
        output_path = destination / item["relative_path"]
        if output_path.exists() and not overwrite:
            item["sha256"] = sha256_file(output_path)
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        for page_index in range(item["source_start_page"] - 1, item["source_end_page"]):
            writer.add_page(reader.pages[page_index])
        writer.add_metadata(
            {
                "/Title": f"{definition.title} - {item['title']}",
                "/Subject": (
                    "Local benchmark derivative; source pages "
                    f"{item['source_start_page']}-{item['source_end_page']}"
                ),
            }
        )
        with output_path.open("wb") as stream:
            writer.write(stream)
        item["sha256"] = sha256_file(output_path)

    source_hash = sha256_file(source_path)
    manifest = {
        "schema_version": 1,
        "source": {
            "id": definition.id,
            "title": definition.title,
            "path": str(source_path.resolve()),
            "filename": source_path.name,
            "sha256": source_hash,
            "pages": len(reader.pages),
            "acquisition_url": definition.acquisition_url,
            "product_id": definition.product_id,
        },
        "input_policy": {
            "primary": "image-native",
            "description": "Models receive PNG renders, not PDF OCR text layers.",
        },
        "catalogs": catalog_meta,
        "documents": plan,
        "logical_pages": _logical_page_map(plan, definition),
    }
    manifest_path = destination / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(path: Path, *, verify_hashes: bool = True) -> list[str]:
    manifest = load_manifest(path)
    root = path.parent
    errors: list[str] = []
    by_catalog: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in manifest.get("documents", []):
        document_path = root / item["relative_path"]
        by_catalog[item["catalog"]].append(item)
        if not document_path.exists():
            errors.append(f"missing document: {item['relative_path']}")
            continue
        try:
            reader = open_reader(document_path)
            if len(reader.pages) != item["page_count"]:
                errors.append(
                    f"page-count mismatch for {item['relative_path']}: "
                    f"expected {item['page_count']}, found {len(reader.pages)}"
                )
        except Exception as exc:
            errors.append(f"cannot open {item['relative_path']}: {exc}")
        if verify_hashes and item.get("sha256"):
            actual = sha256_file(document_path)
            if actual != item["sha256"]:
                errors.append(f"hash mismatch for {item['relative_path']}")

    for catalog, items in by_catalog.items():
        ordered = sorted(items, key=lambda item: item["source_start_page"])
        meta = manifest["catalogs"][catalog]
        expected_page = meta["source_start_page"]
        for item in ordered:
            if item["source_start_page"] != expected_page:
                errors.append(
                    f"coverage gap/overlap in {catalog}: expected page {expected_page}, "
                    f"found {item['source_start_page']}"
                )
            expected_page = item["source_end_page"] + 1
        if expected_page - 1 != meta["source_end_page"]:
            errors.append(
                f"coverage for {catalog} ends at {expected_page - 1}, "
                f"expected {meta['source_end_page']}"
            )

    for ref, page in manifest.get("logical_pages", {}).items():
        source_page = page.get("source_page")
        if not isinstance(source_page, int) or not 1 <= source_page <= manifest["source"]["pages"]:
            errors.append(f"invalid source page for logical ref {ref}: {source_page}")
    return errors
