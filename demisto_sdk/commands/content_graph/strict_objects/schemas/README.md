# UCC Connector Schemas - Ingestion Contract

This folder receives the JSON Schema files that describe the shape of the
`connector.yaml`, `connection.yaml`, `capabilities.yaml`, `configurations.yaml`,
`handler.yaml`, `serializer.yaml`, `triggers.yaml`, `summary.yaml`,
`availability.yaml`, and `services.yaml` files consumed by the UCC (Unified
Content Connectors) tooling. It is the **single source of truth** for the
Pydantic classes generated into
[`../_generated/`](../_generated/) via [`../regenerate.sh`](../regenerate.sh).

The SDK never edits these files by hand. They are copied in from the UCC
repository as part of a CI job on the infra side, then this SDK's own CI
regenerates the Python models and (in future phases) runs the drift tests.

## Expected layout

```
schemas/
├── README.md                       (this file)
├── availability.schema.json        (Tier 3)
├── capabilities.schema.json        (Tier 1)
├── configurations.schema.json      (Tier 1)
├── connection.schema.json          (Tier 1)
├── connector.schema.json           (Tier 1, already present)
├── handler.schema.json             (Tier 1)
├── serializer.schema.json          (Tier 1)
├── services.schema.json            (Tier 3)
├── summary.schema.json             (Tier 2)
├── triggers.schema.json            (Tier 2)
└── definitions/
    └── *.json                      (shared $ref targets)
```

## Contract for the infra-side CI job

The infra job that populates this folder must:

1. Copy every `*.schema.json` file from `<ucc-repo>/schema/` into this folder,
   preserving filenames exactly.
2. Copy the entire contents of `<ucc-repo>/schema/definitions/` into
   `definitions/` here, preserving the sub-folder structure.
3. Not modify the JSON content in any way. If a schema needs to be tweaked for
   the SDK, do it via a downstream override, not by editing the file here.
4. Commit the result to a branch of this SDK repo (or open a PR) whenever the
   upstream files change. The SDK CI will then re-run
   [`../regenerate.sh`](../regenerate.sh), fail if the generated files diverge,
   and run the drift tests in [`../tests/`](../tests/).

## Contract for the SDK-side developer

If you are working on `objects/connector.py` and want to check parity against
upstream locally:

```bash
poetry run pip install 'datamodel-code-generator==0.25.9'
bash demisto_sdk/commands/content_graph/strict_objects/regenerate.sh
poetry run pytest demisto_sdk/commands/content_graph/strict_objects/tests/ -v
```

## Why the schemas live inside the SDK repo (rather than being fetched at runtime)

- The generated Pydantic classes are static artifacts that participate in the
  same static-typing story as every other SDK model (IDE autocomplete, `mypy`).
- Changes to the upstream schema become **diff-reviewable PRs** on the SDK repo.
- The SDK can be installed and run in air-gapped environments without needing
  network access to the UCC repo at import time.
- CI drift-detection is a simple `git diff --exit-code` on the generated files.
