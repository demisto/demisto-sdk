from pathlib import Path

from demisto_sdk.commands.common.constants import IS_CONTENT_PRIVATE_KEY, FileType
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from TestSuite.pack import Pack

SCHEMAS_PATH = Path(__file__).parents[1] / "schemas"
# Schemas of files that are not content items (the CI does not inject the key into them).
NON_ITEM_SCHEMAS = {
    "releasenotesconfig",
    "modelingruleschema",
    "assetsmodelingruleschema",
}


def _is_valid(item, extra: dict) -> bool:
    item.update(extra)
    return StructureValidator(
        item.path, predefined_scheme=FileType.INTEGRATION
    ).is_valid_scheme()


def test_schema_accepts_flag_but_not_other_keys(pack: Pack):
    integration = pack.create_integration(yml=load_yaml("integration.yml")).yml

    assert _is_valid(integration, {IS_CONTENT_PRIVATE_KEY: True})
    assert not _is_valid(integration, {"unrelated_key": 1})


def test_every_item_schema_declares_the_flag_at_the_root():
    schemas = [p for p in SCHEMAS_PATH.glob("*.yml") if p.stem not in NON_ITEM_SCHEMAS]
    assert schemas
    for schema_path in schemas:
        schema = yaml.load(schema_path.read_text())
        assert schema["mapping"][IS_CONTENT_PRIVATE_KEY] == {
            "type": "bool"
        }, schema_path
