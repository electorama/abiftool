#!/usr/bin/env python3
"""Convert an abiftool fetchspec JSON file into bifelsrc or awt catalog YAML."""
import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover
    sys.stderr.write("PyYAML is required to run fetchspec_conv.py\n")
    raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fetchspec", help="Path to fetchspec JSON file")
    parser.add_argument(
        "--fmt",
        choices=("bifelsrc", "awtyaml"),
        default="bifelsrc",
        help="Output format: bifhub elsrc (default) or awt abif_list entries",
    )
    parser.add_argument(
        "-t",
        "--tag",
        action="append",
        dest="extra_tags",
        help="Tag to apply to every election (may be given multiple times)",
    )
    parser.add_argument(
        "--title-prefix",
        default="",
        help="Prefix to add to every title that appears in the output",
    )
    return parser.parse_args()


def infer_provenance(path: Path) -> str:
    stem = path.stem
    if stem.endswith(".fetchspec"):
        stem = stem[: -len(".fetchspec")]
    return stem


def load_fetchspec(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_tags(existing: Optional[Any], extras: Optional[Iterable[str]]) -> Optional[List[str]]:
    tags: List[str] = []
    if existing:
        if isinstance(existing, str):
            parts = [piece.strip() for piece in existing.split(",")]
            tags.extend(filter(None, parts))
        else:
            tags.extend(str(tag).strip() for tag in existing)
    if extras:
        tags.extend(tag.strip() for tag in extras if tag and tag.strip())

    seen = set()
    unique: List[str] = []
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique or None


def apply_title_prefix(entry: Dict[str, Any], prefix: str) -> None:
    if prefix and entry.get("title"):
        entry["title"] = f"{prefix}{entry['title']}"


def web_entries(fetchspec: Dict[str, Any], extras: Optional[Iterable[str]], prefix: str) -> List[Dict[str, Any]]:
    desired = ("abifloc", "desc", "metaurls", "contest_string", "title", "tags", "id")
    entries: List[Dict[str, Any]] = []
    for item in fetchspec.get("web_urls", []) or []:
        entry: Dict[str, Any] = {}
        if "url" in item:
            entry["source_url"] = item["url"]
        if "urls" in item:
            entry["source_urls"] = item["urls"]
        for key in desired:
            if key == "tags":
                tags = normalize_tags(item.get("tags"), extras)
                if tags:
                    entry["tags"] = tags
                continue
            if key in item:
                entry[key] = item[key]
        if "tags" not in entry:
            tags = normalize_tags(None, extras)
            if tags:
                entry["tags"] = tags
        apply_title_prefix(entry, prefix)
        entries.append(entry)
    return entries


def ext_entries(fetchspec: Dict[str, Any], extras: Optional[Iterable[str]], prefix: str) -> List[Dict[str, Any]]:
    desired = ("abifloc", "desc", "metaurls", "srcfmt", "tags", "title", "id")
    entries: List[Dict[str, Any]] = []
    for item in fetchspec.get("extfiles", []) or []:
        entry: Dict[str, Any] = {}
        if "localcopy" in item:
            entry["repo_path"] = item["localcopy"]
        if "localcopies" in item:
            entry["repo_paths"] = item["localcopies"]
        for key in desired:
            if key == "tags":
                tags = normalize_tags(item.get("tags"), extras)
                if tags:
                    entry["tags"] = tags
                continue
            if key in item:
                entry[key] = item[key]
        if "tags" not in entry:
            tags = normalize_tags(None, extras)
            if tags:
                entry["tags"] = tags
        apply_title_prefix(entry, prefix)
        entries.append(entry)
    return entries


def archive_entries(fetchspec: Dict[str, Any], extras: Optional[Iterable[str]], prefix: str) -> List[Dict[str, Any]]:
    desired = ("abifloc", "desc", "tags", "title", "id")
    entries: List[Dict[str, Any]] = []
    for item in fetchspec.get("archive_subfiles", []) or []:
        entry: Dict[str, Any] = {}
        if "archive_subfile" in item:
            entry["archive_subfile"] = item["archive_subfile"]
        for key in desired:
            if key == "tags":
                tags = normalize_tags(item.get("tags"), extras)
                if tags:
                    entry["tags"] = tags
                continue
            if key in item:
                entry[key] = item[key]
        if "tags" not in entry:
            tags = normalize_tags(None, extras)
            if tags:
                entry["tags"] = tags
        apply_title_prefix(entry, prefix)
        entries.append(entry)
    return entries


def build_bifelsrc(
    fetchspec_path: Path,
    fetchspec: Dict[str, Any],
    extras: Optional[Iterable[str]],
    prefix: str,
) -> Dict[str, Any]:
    document: Dict[str, Any] = {
        "schema": "elsrc-0.33",
        "provenance": infer_provenance(fetchspec_path),
        "batch": "auto-generated",
        "elections": [],
    }

    if fetchspec.get("gitrepo_url"):
        document["source_repo"] = fetchspec["gitrepo_url"]
    if fetchspec.get("download_subdir"):
        document["download_subdir"] = fetchspec["download_subdir"]
    if fetchspec.get("abifloc_subdir"):
        document["abifloc_subdir"] = fetchspec["abifloc_subdir"]

    document["elections"].extend(web_entries(fetchspec, extras, prefix))
    document["elections"].extend(ext_entries(fetchspec, extras, prefix))
    document["elections"].extend(archive_entries(fetchspec, extras, prefix))
    return document


def slug_from_text(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", text.strip())
    return slug.strip("-") or "unnamed"


def resolve_abif_path(base_dir: str, abifloc: str) -> str:
    if not base_dir:
        return abifloc
    base_dir = base_dir.rstrip("/")
    if abifloc.startswith(base_dir + "/"):
        return abifloc
    return f"{base_dir}/{abifloc.lstrip('/')}"


def make_awt_entry(
    fetchspec: Dict[str, Any],
    item: Dict[str, Any],
    extras: Optional[Iterable[str]],
    prefix: str,
) -> Dict[str, Any]:
    abifloc = item.get("abifloc")
    if not abifloc:
        raise ValueError("abifloc is required to build awt catalog entries")
    abifloc_subdir = fetchspec.get("abifloc_subdir", "")
    filename = resolve_abif_path(abifloc_subdir, abifloc)

    entry: Dict[str, Any] = {"filename": filename}

    id_source = item.get("id") or Path(abifloc).stem
    entry["id"] = slug_from_text(id_source)

    base_title = (
        item.get("title") or
        item.get("contest_string") or
        item.get("desc") or
        entry["id"]
    )
    entry["title"] = f"{prefix}{base_title}" if prefix else base_title

    if item.get("desc"):
        entry["desc"] = item["desc"]

    merged_tags = normalize_tags(item.get("tags"), extras)
    if merged_tags:
        entry["tags"] = ", ".join(merged_tags)

    return entry


def build_awtyaml(
    fetchspec: Dict[str, Any],
    extras: Optional[Iterable[str]],
    prefix: str,
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for item in web_entries(fetchspec, extras, prefix):
        if "abifloc" in item:
            entries.append(make_awt_entry(fetchspec, item, extras, prefix))
    for item in ext_entries(fetchspec, extras, prefix):
        if "abifloc" in item:
            entries.append(make_awt_entry(fetchspec, item, extras, prefix))
    for item in archive_entries(fetchspec, extras, prefix):
        if "abifloc" in item:
            entries.append(make_awt_entry(fetchspec, item, extras, prefix))
    return entries


def main() -> None:
    args = parse_args()
    fetchspec_path = Path(args.fetchspec)
    if not fetchspec_path.exists():
        sys.stderr.write(f"Fetchspec not found: {fetchspec_path}\n")
        sys.exit(1)

    fetchspec = load_fetchspec(fetchspec_path)

    if args.fmt == "bifelsrc":
        document = build_bifelsrc(fetchspec_path, fetchspec, args.extra_tags, args.title_prefix)
    else:
        document = build_awtyaml(fetchspec, args.extra_tags, args.title_prefix)

    yaml.safe_dump(document, stream=sys.stdout, sort_keys=False)


if __name__ == "__main__":
    main()
