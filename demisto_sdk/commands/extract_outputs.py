from json import dumps, load
from typing import Optional

from ruamel.yaml import YAML


def get_outputs(yml: dict, ignore_prefix: Optional[str]):
    result = {}
    for command in yml.get("script", {}).get("commands", []):
        for output in command.get("outputs", []):
            path = output["contextPath"]
            if ignore_prefix is None or not path.startswith(ignore_prefix + "."):
                result[path] = output["description"]
    return result


path = "/Users/dschwartz/dev/demisto/content/Packs/AutoFocus/Integrations/AutofocusV2/AutofocusV2.yml"
d2 = get_outputs(YAML().load(open(path)), "AutoFocus")
d1 = load(
    open(
        "/Users/dschwartz/dev/demisto/demisto-sdk/demisto_sdk/commands/common/default_output_descriptions.json"
    )
)
d1.update(d2)
print(dumps(d1))
