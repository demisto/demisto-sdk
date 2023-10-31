import tempfile
from pathlib import Path
from typing import Any, Optional

from demisto_sdk.commands.common.tools import set_val
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from TestSuite.repo import Repo

REPO = Repo(tmpdir=Path(tempfile.mkdtemp()))


def create_integration_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    yml_content = load_yaml("integration.yml")
    if key_path and new_value:
        set_val(yml_content, key_path, new_value)
    pack = REPO.create_pack()
    integration = pack.create_integration(yml=yml_content)
    integration.code.write("from MicrosoftApiModule import *")
    integration_object = BaseContent.from_path(Path(integration.path))
    return integration_object


def create_script_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    yml_content = load_yaml("script.yml")
    if key_path and new_value:
        set_val(yml_content, key_path, new_value)
    pack = REPO.create_pack()
    script = pack.create_script(yml=yml_content)
    script.code.write("from MicrosoftApiModule import *")
    script_object = BaseContent.from_path(Path(script.path))
    return script_object


def create_metadata_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    json_content = load_json("pack_metadata.json")
    if key_path and new_value is not None:
        set_val(json_content, key_path, new_value)
    pack = REPO.create_pack()
    pack.pack_metadata.write_json(json_content)
    pack_metadata_object = BaseContent.from_path(Path(pack.pack_metadata.path))
    return pack_metadata_object
