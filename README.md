# PortalWars2 Prefix Intake

**XDanfr / PortalWars2-Prefix-Intake** is an offline-first forensic intake utility for **SPLITGATE: Arena Reloaded / PortalWars2** local application data.

It exists because a Windows `%LOCALAPPDATA%` directory is not a clean game-only folder. It can contain unrelated applications, temporary installers, crash data and other personal material. The tool therefore finds the `PortalWars2` directory inside a broader LocalAppData tree and produces a **sanitised metadata record** of that game prefix instead of copying the prefix itself.

The tool was extracted from the ReMaverick research workflow so the reusable mechanism can be versioned, tested and used independently of the research repository.

## What it does

The intake records:

- every file beneath the selected `PortalWars2` root;
- file size and modification time;
- SHA-256 hashes (unless `--no-hash` is used);
- file categories such as game logs, CMS snapshots, localisation, cloud saves, crash dumps and render caches;
- `CacheManifest.json` entries, including dataset/version/content identifiers and local cache paths;
- version sets for datasets appearing in the cache manifest.

It **does not copy proprietary game payloads** into the output.

By default, cache-manifest source URLs are redacted. Use `--allow-source-urls` only when you have reviewed the resulting CSV and deliberately want those URLs preserved.

## Windows: one-click intake from `%LOCALAPPDATA%`

Copy the repository somewhere convenient and double-click:

```text
windows\\Run-PortalWars2-Intake.cmd
```

The launcher:

1. uses the current user's `%LOCALAPPDATA%` automatically;
2. searches that larger directory tree for `PortalWars2`;
3. refuses to guess if multiple `PortalWars2` roots exist;
4. creates a timestamped `portalwars2-intake-YYYYMMDD-HHMMSS` directory **beside the launcher**;
5. leaves the original prefix untouched.

A Python 3.10+ installation is required. The launcher tries `py -3` first and then `python`.

For a command window:

```powershell
windows\\Run-PortalWars2-Intake.cmd
```

## Command line

Explicit prefix:

```bash
python -m portalwars2_prefix_intake "C:\\Users\\you\\AppData\\Local\\PortalWars2" --output ./intake
```

Automatically use `%LOCALAPPDATA%` on Windows:

```powershell
python -m portalwars2_prefix_intake --localappdata --output .\\intake
```

Extracted `Local` archive:

```bash
python -m portalwars2_prefix_intake ./Local --output ./intake
```

Fast triage without hashes:

```bash
python -m portalwars2_prefix_intake --localappdata --no-hash
```

## Output

A normal intake contains:

```text
artifact-inventory.csv
cache-manifest.csv
intake-summary.json
```

### `artifact-inventory.csv`

One row per file. Paths are normalised and account/session identifiers in path components are redacted.

### `cache-manifest.csv`

A parsed view of `Saved/PersistentDownloadDir/CacheManifest.json`.

Fields include `category`, `dataset`, `version`, `content_id`, `local_path`, `size_bytes`, `saved_timestamp`, `expiration_seconds` and `source_url`.

`source_url` is `<redacted>` unless `--allow-source-urls` is supplied.

### `intake-summary.json`

Machine-readable counts and version sets suitable for attaching to a research session or issue.

## Privacy and publication

Treat the input prefix as sensitive. It can contain authentication-related material, account identifiers, cloud saves, crash dumps and proprietary game data.

Before publication:

- never publish credentials, tokens, cookies or authentication data;
- inspect output for account/player identifiers;
- keep raw prefixes and proprietary payloads private;
- publish hashes, sizes, timestamps, redacted paths, derived observations and reproduction steps instead.

This tool is intentionally conservative, but it is **not a proof that an output is safe to publish**. Human review is still required.

See [`docs/privacy.md`](docs/privacy.md) for the exact sanitisation policy.

## ReMaverick provenance

This project was created from analysis tooling used during the ReMaverick research and preservation project. ReMaverick remains the evidence/source-of-truth repository; this repository contains the reusable intake implementation.

The ReMaverick project documents a policy of publishing metadata and hashes instead of proprietary game files, and requires AI-assisted research to record tool usage and independently verify claims. The standalone tool follows the same principles. See [`docs/research-provenance.md`](docs/research-provenance.md).

## Development

Run the standard-library test suite:

```bash
python -m unittest discover -s tests -v
```

Run a local CLI smoke test:

```bash
python -m portalwars2_prefix_intake --help
```

No third-party runtime dependencies are required.

## Release

The first release is **v1.0.0**. Release notes are described in [`CHANGELOG.md`](CHANGELOG.md); the packaged release artefacts are intended for GitHub Releases rather than source control.

## Licence

MIT. See [`LICENSE`](LICENSE).
