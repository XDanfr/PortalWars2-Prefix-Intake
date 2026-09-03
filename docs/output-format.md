# Output format

## artifact-inventory.csv

| Field | Meaning |
|---|---|
| `relative_path` | Sanitised path relative to the PortalWars2 root |
| `category` | Broad artifact class |
| `size_bytes` | File size |
| `mtime_utc` | Source modification time in UTC |
| `sha256` | SHA-256, blank when `--no-hash` is used |

## cache-manifest.csv

This is a parsed representation of `Saved/PersistentDownloadDir/CacheManifest.json`.

`source_url` is deliberately redacted by default. The original cache payload is not copied to the intake output.

## intake-summary.json

Contains tool version, file/byte totals, category counts, cache counts and version sets. It is intended to be cited from research notes rather than treated as raw evidence on its own.
