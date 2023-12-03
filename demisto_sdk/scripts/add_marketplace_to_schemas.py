from copy import deepcopy
from pathlib import Path

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_file, write_dict

GIT_ROOT = Path(git_path())
SCHEMA_FOLDER = GIT_ROOT / "demisto_sdk" / "commands" / "common" / "schemas"
NON_SUPPORTED_KEYS = ["id"]


def add_key(mapping):
    if not mapping:
        return
    keys_to_add = []
    keys_to_delete = []
    for key, value in mapping.items():
        if key in NON_SUPPORTED_KEYS:
            for key, value in mapping.items():
                if f"regex;{key}:" in key:
                    keys_to_delete.append(key)
            continue
        if value.get("type") != "map":
            if "regex;" in key and "(.+)" in key:
                continue
            value = deepcopy(value)
            value.pop("required", None)
            if "regex;" in key:
                keys_to_delete.append(key)
                continue
            new_key = f"regex;({key}:(xsoar)|(marketplacev2)|(xpanse)|(xsoar_on_prem)|(xsoar_saas))"
            keys_to_add.append((new_key, value))
        else:
            add_key(value.get("mapping"))
    for key in keys_to_delete:
        mapping.pop(key, None)
    for new_key, new_value in keys_to_add:
        mapping[new_key] = new_value


def main():
    schema_files = [
        schema for schema in SCHEMA_FOLDER.iterdir() if schema.suffix == ".yml"
    ]
    for schema_file in schema_files:
        schema = get_file(schema_file, keep_order=True)
        add_key(schema["mapping"])
        write_dict(schema_file, schema)


if __name__ == "__main__":
    main()
