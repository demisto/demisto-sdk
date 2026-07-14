# UCC schemas (runtime-loaded)

This folder is a **local development fallback** for the UCC (Unified Content
Connectors) JSON Schema files. In real CI runs the schemas are provided at
runtime by the *infra* CI job and loaded in-memory - see below.

## How the SDK finds schemas at runtime

Resolution is handled by
[`../schema_loader.py`](../schema_loader.py) and happens in this order:

1. **`$UCC_SCHEMAS_DIR` environment variable** (production path).
   Points at a directory that contains:
   ```
   $UCC_SCHEMAS_DIR/
     connector.schema.json
     connection.schema.json
     capabilities.schema.json
     configurations.schema.json
     handler.schema.json
     serializer.schema.json
     triggers.schema.json
     summary.schema.json
     availability.schema.json
     services.schema.json
     definitions/
       field.schema.json
       field-options.schema.json
       metadata.schema.json
       validation.schema.json
   ```
   Every `*.schema.json` at the top level becomes a Pydantic module. Files
   under `definitions/` are preserved as a subfolder so cross-file `$ref`
   like `{"$ref": "definitions/field.json"}` resolves correctly.

2. **This folder** (`strict_objects/schemas/`), used only when
   `$UCC_SCHEMAS_DIR` is unset. It holds a snapshot of `connector.schema.json`
   so `pytest`, IDE checks, and local runs work without infra plumbing.

3. **Neither present** -> `StrictConnector` is `None`, strict validation is
   silently skipped, and the `Connector` graph object degrades to
   conservative hand-written field shapes.

## Contract for the infra CI job

Your CI job MUST:

1. Copy every `<UCC>/schema/*.schema.json` into `$UCC_SCHEMAS_DIR/`.
2. Copy every `<UCC>/schema/definitions/*.schema.json` into
   `$UCC_SCHEMAS_DIR/definitions/` (preserve the subfolder).
3. NOT rename files. Python module names are derived from stems:
   `connector.schema.json` -> `ConnectorYaml` class.
4. NOT modify the JSON. It is the source of truth.
5. Export `UCC_SCHEMAS_DIR=<absolute path>` before invoking the SDK.
6. Ensure `datamodel-code-generator==0.25.9` is installed alongside the SDK
   (pinned because 0.26+ dropped the Pydantic v1 output target).

Recommended CI shell:
```bash
rsync -a --delete <UCC>/schema/ "$UCC_SCHEMAS_DIR/"
pip install 'datamodel-code-generator==0.25.9'
export UCC_SCHEMAS_DIR
demisto-sdk validate ...
```

## What happens automatically once schemas are loaded

- The runtime loader stages the schemas into a tmp dir, runs
  `datamodel-codegen`, and imports the generated `.py` files as real
  modules under `demisto_sdk.commands.content_graph.strict_objects._runtime_generated.*`.
- [`StrictConnector`](../connector.py) picks up the generated `ConnectorYaml`
  as its base, so every upstream field + constraint becomes live.
- The `Connector` graph object's `ConnectorMetadata` / `ConnectorSettings` /
  `ConnectorOwnership` inherit from the generated types, so any new upstream
  field on `Metadata` (e.g. `documentation`, `is_recommended`) appears as a
  typed attribute on the graph object with zero SDK code changes.
- `ConnectorParser` calls `validate_structure(StrictConnector, ...)` on
  every parsed `connector.yaml`, populating `structure_errors`.
- ST110 (`SchemaValidator`) reads those errors and surfaces upstream drift
  as validation failures on the offending connector.

## Do NOT edit anything in this folder by hand

The committed `connector.schema.json` here is a byte-identical copy of the
UCC upstream file. To refresh it locally, re-copy from the UCC repo. All
production runs go through `$UCC_SCHEMAS_DIR` and ignore this snapshot.
