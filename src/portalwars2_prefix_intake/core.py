from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

PACKAGE_VERSION = "1.0.0"
PORTALWARS2_NAME = "PortalWars2"
DEFAULT_OUTPUT_PREFIX = "portalwars2-intake"

_STEAM_DIR_RE = re.compile(r"(^|/)Steam_[0-9]{8,}(?=/|$)", re.IGNORECASE)
_UUID_DIR_RE = re.compile(
    r"(^|/)([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?=/|$)"
)
_STEAM_ID_RE = re.compile(r"(?i)(steam[_-]?)([0-9]{8,})")
_UUID_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_MANIFEST_DATASET_RE = re.compile(r"^(.*)-(\d+\.\d+\.\d+)-([0-9A-Fa-f]{64})$")


@dataclass(frozen=True)
class CacheRow:
    category: str
    dataset: str
    version: str
    content_id: str
    local_path: str
    size_bytes: int | None
    saved_timestamp: float | int | str
    expiration_seconds: int | float | str
    source_url: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def sanitise_text(value: str) -> str:
    value = _STEAM_ID_RE.sub(r"\1<redacted>", value)
    return _UUID_RE.sub("<uuid>", value)


def public_relpath(relative: str) -> str:
    """Remove account/session identifiers unnecessary for public metadata."""
    relative = relative.replace("\\", "/")
    relative = _STEAM_DIR_RE.sub(r"\1Steam_<redacted>", relative)
    relative = _UUID_DIR_RE.sub(r"\1<uuid>", relative)
    return sanitise_text(relative)


def classify(relative: str) -> str:
    path = relative.replace("\\", "/")
    if "/Saved/Logs/" in path:
        return "game-log"
    if "/Saved/PersistentDownloadDir/CMS/Snapshots/" in path:
        return "cms-snapshot"
    if "/Saved/PersistentDownloadDir/CMS/Assets/" in path:
        return "cms-asset"
    if "/Saved/PersistentDownloadDir/Localization/" in path:
        return "localization"
    if "/Saved/Cloud/" in path:
        return "cloud-save"
    if "/.sentry-native/reports/" in path:
        return "crash-dump"
    if "/.sentry-native/" in path:
        return "sentry-runtime"
    if path.endswith("GameUserSettings.ini"):
        return "user-settings"
    if "/ImGui/" in path:
        return "imgui-config"
    if path.endswith("upipelinecache") or path.endswith(".shaderCacheVersion"):
        return "render-cache"
    if "/UnrealEngine/" in path:
        return "engine-config"
    return "other"


def normalise_manifest_path(raw_path: str) -> str:
    raw_path = raw_path.replace("\\", "/")
    marker = "AppData/Local/PortalWars2/"
    if marker.lower() in raw_path.lower():
        marker_start = raw_path.lower().index(marker.lower())
        return "PortalWars2/" + raw_path[marker_start + len(marker):]
    return public_relpath(raw_path)


def find_portalwars2_candidates(localappdata: Path) -> list[Path]:
    """Find PortalWars2 roots inside a broader LocalAppData tree."""
    candidates: set[Path] = set()

    def onerror(_: OSError) -> None:
        return

    for root, dirs, _files in os.walk(localappdata, topdown=True, followlinks=False, onerror=onerror):
        root_path = Path(root)
        keep_dirs: list[str] = []
        for name in dirs:
            candidate = root_path / name
            if name.lower() == PORTALWARS2_NAME.lower():
                try:
                    candidates.add(candidate.resolve())
                except OSError:
                    pass
                continue
            keep_dirs.append(name)
        dirs[:] = keep_dirs
    return sorted(candidates, key=lambda p: str(p).lower())


def resolve_prefix(path: Path) -> Path:
    path = path.expanduser().resolve()
    direct_candidates = [path]
    if path.name.lower() != PORTALWARS2_NAME.lower():
        direct_candidates.extend([path / PORTALWARS2_NAME, path / "Local" / PORTALWARS2_NAME])
    for candidate in direct_candidates:
        if candidate.is_dir() and candidate.name.lower() == PORTALWARS2_NAME.lower():
            return candidate
    candidates = find_portalwars2_candidates(path)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"No {PORTALWARS2_NAME} directory found below {path}")
    pretty = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise RuntimeError(
        f"Found multiple {PORTALWARS2_NAME} directories below {path}. "
        f"Use an explicit prefix. Candidates:\n{pretty}"
    )


def cache_rows(prefix: Path) -> Iterable[CacheRow]:
    manifest_path = prefix / "Saved/PersistentDownloadDir/CacheManifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("Entries")
    if not isinstance(entries, list):
        raise ValueError("CacheManifest.json has no list-valued 'Entries' field")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        category = str(entry.get("Category", ""))
        ident = str(entry.get("Id", ""))
        dataset = version = content_id = source_url = ""
        if category == "CMS/Assets":
            dataset = "asset"
            source_url = sanitise_text(ident)
        else:
            match = _MANIFEST_DATASET_RE.match(ident)
            if match:
                dataset, version, content_id = match.groups()
            else:
                dataset = ident
        local_path = normalise_manifest_path(str(entry.get("FilePath", "")))
        local = prefix.parent / local_path
        if not local.exists():
            candidate = prefix / local_path.removeprefix("PortalWars2/")
            local = candidate if candidate.exists() else None
        yield CacheRow(
            category=category,
            dataset=sanitise_text(dataset),
            version=version,
            content_id=content_id,
            local_path=local_path,
            size_bytes=local.stat().st_size if local else None,
            saved_timestamp=entry.get("SavedTimestamp", ""),
            expiration_seconds=entry.get("DiskExpirationTimeSeconds", ""),
            source_url=source_url,
        )


def write_csv(path: Path, headers: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def inventory(prefix: Path, calculate_hashes: bool = True) -> list[list[object]]:
    files = sorted((p for p in prefix.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    rows: list[list[object]] = []
    for path in files:
        relative_raw = path.relative_to(prefix).as_posix()
        rows.append([
            public_relpath(relative_raw),
            classify("PortalWars2/" + relative_raw),
            path.stat().st_size,
            mtime_utc(path),
            "" if not calculate_hashes else sha256(path),
        ])
    return rows


def summarise(inventory_rows: list[list[object]], manifest_entries: list[CacheRow]) -> dict[str, object]:
    summary: dict[str, object] = {
        "tool_version": PACKAGE_VERSION,
        "files": len(inventory_rows),
        "bytes": sum(int(row[2]) for row in inventory_rows),
        "categories": dict(sorted(Counter(str(row[1]) for row in inventory_rows).items())),
        "cache_entries": len(manifest_entries),
        "cache_categories": dict(sorted(Counter(row.category for row in manifest_entries).items())),
        "versioned_datasets": {},
    }
    versions: defaultdict[str, set[str]] = defaultdict(set)
    for row in manifest_entries:
        if row.version:
            versions[row.dataset].add(row.version)
    summary["versioned_datasets"] = {
        dataset: sorted(values, key=lambda item: tuple(map(int, item.split("."))))
        for dataset, values in sorted(versions.items())
    }
    return summary


def write_intake(prefix: Path, output: Path, calculate_hashes: bool = True, allow_source_urls: bool = False) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    inventory_rows = inventory(prefix, calculate_hashes=calculate_hashes)
    write_csv(
        output / "artifact-inventory.csv",
        ["relative_path", "category", "size_bytes", "mtime_utc", "sha256"],
        inventory_rows,
    )

    manifest_entries = list(cache_rows(prefix))
    manifest_rows = []
    for row in manifest_entries:
        manifest_rows.append([
            row.category,
            row.dataset,
            row.version,
            row.content_id,
            public_relpath(row.local_path),
            "" if row.size_bytes is None else row.size_bytes,
            row.saved_timestamp,
            row.expiration_seconds,
            row.source_url if allow_source_urls else "<redacted>",
        ])
    write_csv(
        output / "cache-manifest.csv",
        [
            "category", "dataset", "version", "content_id", "local_path", "size_bytes",
            "saved_timestamp", "expiration_seconds", "source_url",
        ],
        manifest_rows,
    )

    summary = summarise(inventory_rows, manifest_entries)
    summary["source_urls_in_output"] = bool(allow_source_urls)
    (output / "intake-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def default_output_directory(script_dir: Path) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    candidate = script_dir / f"{DEFAULT_OUTPUT_PREFIX}-{stamp}"
    index = 2
    while candidate.exists():
        candidate = script_dir / f"{DEFAULT_OUTPUT_PREFIX}-{stamp}-{index}"
        index += 1
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portalwars2-prefix-intake",
        description="Safely inventory a private PortalWars2 local prefix for research metadata.",
    )
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("prefix", nargs="?", type=Path, help="Explicit PortalWars2 directory, LocalAppData root, or extracted Local directory")
    source.add_argument("--localappdata", action="store_true", help="Use Windows %%LOCALAPPDATA%% and find PortalWars2 automatically")
    parser.add_argument("--output", type=Path, help="Output directory (default: next to the launcher/script)")
    parser.add_argument("--no-hash", action="store_true", help="Skip SHA-256 calculation for faster triage")
    parser.add_argument("--allow-source-urls", action="store_true", help="Preserve source URLs in cache-manifest.csv; review before publishing")
    parser.add_argument("--version", action="version", version=PACKAGE_VERSION)
    return parser


def main(argv: Sequence[str] | None = None, *, script_dir: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.localappdata:
        if os.name != "nt" and "LOCALAPPDATA" not in os.environ:
            parser.error("--localappdata expects the Windows LOCALAPPDATA environment variable")
        raw = os.environ.get("LOCALAPPDATA")
        if not raw:
            parser.error("LOCALAPPDATA is not set")
        source_root = Path(raw)
    elif args.prefix is not None:
        source_root = args.prefix
    else:
        raw = os.environ.get("LOCALAPPDATA")
        if raw and os.name == "nt":
            source_root = Path(raw)
        else:
            parser.error("Provide PREFIX or use --localappdata on Windows")

    try:
        prefix = resolve_prefix(source_root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    output = args.output or default_output_directory(script_dir or Path.cwd())
    try:
        summary = write_intake(
            prefix,
            output,
            calculate_hashes=not args.no_hash,
            allow_source_urls=args.allow_source_urls,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 3

    print(f"PortalWars2 Prefix Intake {PACKAGE_VERSION}")
    print(f"Source: {prefix}")
    print(f"Output: {output}")
    print(f"Inventoried {summary['files']} files ({int(summary['bytes']):,} bytes)")
    print(f"Cache manifest: {summary['cache_entries']} entries")
    print("No proprietary payloads were copied to the output.")
    return 0
