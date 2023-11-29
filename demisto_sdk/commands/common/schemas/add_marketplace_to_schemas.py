from copy import deepcopy
from pathlib import Path

from demisto_sdk.commands.common.tools import get_file, write_dict

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
            value = deepcopy(value)
            value.pop("required", None)
            if f"regex;{key}:" in key:
                keys_to_delete.append(key)
                continue
            new_key = f"regex;{key}:(xsoar)|(marketplacev2)|(xpanse)|(xsoar_on_prem)|(xsoar_saas)"
            if new_key not in mapping:
                keys_to_add.append((new_key, value))
        else:
            add_key(value.get("mapping"))
    for new_key, new_value in keys_to_add:
        mapping[new_key] = new_value
    for key in keys_to_delete:
        mapping.pop(key, None)


def main():
    schema_files = [
        schema for schema in Path(__file__).parent.iterdir() if schema.suffix == ".yml"
    ]
    for schema_file in schema_files:
        schema = get_file(schema_file, keep_order=True)
        add_key(schema["mapping"])
        write_dict(schema_file, schema)
