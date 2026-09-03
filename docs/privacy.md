# Privacy and sanitisation

The utility analyses a private local prefix but emits derived metadata intended for research.

## Input assumptions

The input can contain:

- game logs;
- crash dumps and Sentry runtime material;
- cloud saves;
- cached CMS payloads and images;
- account/player identifiers;
- other unrelated files when the source is `%LOCALAPPDATA%`.

The program only reads files beneath the resolved `PortalWars2` directory. It does not delete, rewrite or upload input files.

## Built-in redaction

The public inventory and cache output:

- replace Steam-style numeric directory names such as `Steam_1234567890` with `Steam_<redacted>`;
- replace UUID directory components with `<uuid>`;
- redact Steam-style numeric identifiers and UUIDs from normalised manifest paths and dataset labels;
- redact cache source URLs unless `--allow-source-urls` is explicitly supplied.

## What is not guaranteed

Hashing a private file is useful provenance, but a hash does not remove privacy risk. File size, timestamps, filenames, source URLs and combinations of metadata can still identify a session.

Human review is required before publishing an intake.
