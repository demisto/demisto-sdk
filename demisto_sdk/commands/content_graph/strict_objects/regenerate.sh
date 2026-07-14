#!/usr/bin/env bash
# Regenerate every Pydantic model in _generated/ from every *.schema.json in
# schemas/, then run isort + black-style formatting via datamodel-codegen itself.
#
# Usage (from the repository root):
#   bash demisto_sdk/commands/content_graph/strict_objects/regenerate.sh
#
# Requirements (install once into the poetry venv):
#   poetry run pip install 'datamodel-code-generator==0.25.9'
#
# Design notes:
# - We deliberately pin datamodel-code-generator to 0.25.9 because releases
#   from 0.26 onward dropped the `pydantic.BaseModel` output target. When the
#   SDK migrates to Pydantic v2, bump this pin and change --output-model-type
#   to `pydantic_v2.BaseModel`.
# - Cross-file $ref (e.g. `{"$ref": "definitions/field.json"}`) resolves
#   correctly when the tool is invoked against the whole `schemas/` directory
#   instead of one file at a time.
# - The generated directory is wiped and recreated on every run, so removals
#   upstream are reflected here without stale files lingering.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMAS_DIR="${SCRIPT_DIR}/schemas"
GENERATED_DIR="${SCRIPT_DIR}/_generated"

if [[ ! -d "${SCHEMAS_DIR}" ]]; then
    echo "ERROR: schemas directory not found at ${SCHEMAS_DIR}" >&2
    exit 1
fi

# Verify datamodel-codegen is available. Fail with a clear hint otherwise.
if ! command -v datamodel-codegen >/dev/null 2>&1; then
    if command -v poetry >/dev/null 2>&1 && poetry run datamodel-codegen --help >/dev/null 2>&1; then
        CODEGEN=(poetry run datamodel-codegen)
    else
        cat >&2 <<EOF
ERROR: datamodel-codegen is not available.

Install it into the poetry venv with:
    poetry run pip install 'datamodel-code-generator==0.25.9'

Do NOT use a newer version - releases from 0.26 dropped pydantic v1 output.
EOF
        exit 1
    fi
else
    CODEGEN=(datamodel-codegen)
fi

# Count schema files so we can fail loudly if the folder is empty.
shopt -s nullglob
SCHEMA_FILES=("${SCHEMAS_DIR}"/*.schema.json)
shopt -u nullglob
if [[ ${#SCHEMA_FILES[@]} -eq 0 ]]; then
    echo "ERROR: no *.schema.json files found in ${SCHEMAS_DIR}" >&2
    echo "The infra-side CI job is expected to populate this folder." >&2
    exit 1
fi

echo "Regenerating Pydantic models from ${#SCHEMA_FILES[@]} schema file(s)..."

# Wipe stale output but keep the folder + __init__ so imports do not break
# transiently between the rm and the codegen writing new files.
rm -rf "${GENERATED_DIR}"
mkdir -p "${GENERATED_DIR}"

# Stage the schemas into a temp dir that contains *only* JSON files.
# datamodel-codegen with --input <dir> will try to parse *every* file it
# finds, including README.md, which fails on the YAML loader. We also copy
# the definitions/ subfolder so $ref targets resolve.
STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "${STAGE_DIR}"' EXIT
for f in "${SCHEMA_FILES[@]}"; do
    cp "$f" "${STAGE_DIR}/"
done
if [[ -d "${SCHEMAS_DIR}/definitions" ]]; then
    cp -R "${SCHEMAS_DIR}/definitions" "${STAGE_DIR}/definitions"
fi

# Generate: one Python file per input schema, into a package.
# --reuse-model collapses identical sub-schemas across files.
"${CODEGEN[@]}" \
    --input "${STAGE_DIR}" \
    --input-file-type jsonschema \
    --use-schema-description \
    --use-default \
    --reuse-model \
    --output-model-type pydantic.BaseModel \
    --target-python-version 3.9 \
    --output "${GENERATED_DIR}"

# Ensure the package is importable.
touch "${GENERATED_DIR}/__init__.py"

echo "Done. Generated files:"
find "${GENERATED_DIR}" -name '*.py' -not -name '__pycache__' | sort
