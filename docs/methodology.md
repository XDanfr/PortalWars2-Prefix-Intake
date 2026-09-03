# Methodology

The intake tool is deliberately an **inventory, not a payload extractor**.

1. Resolve a `PortalWars2` root.
2. Enumerate files below that root.
3. Record stable metadata and optionally hashes.
4. Parse only the JSON cache manifest.
5. Produce CSV/JSON derived outputs.
6. Apply conservative identifier redaction.

The tool does not attempt to interpret Unreal Compact Binary payloads. That is a separate research step and should operate on private source material.
