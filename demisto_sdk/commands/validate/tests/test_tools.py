import tempfile
from pathlib import Path
from typing import Any, List, Optional
from unittest.mock import MagicMock

from demisto_sdk.commands.common.tools import set_value
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from TestSuite.file import File
from TestSuite.repo import Repo

REPO = Repo(tmpdir=Path(tempfile.mkdtemp()))


def create_integration_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
) -> Integration:
    """Creating an integration object with altered fields from a default integration yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The integration object.
    """
    yml_content = load_yaml("integration.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    integration = pack.create_integration(yml=yml_content)
    integration.code.write("from MicrosoftApiModule import *")
    return BaseContent.from_path(Path(integration.path))  # type:ignore


def create_ps_integration_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
) -> Integration:
    """Creating an integration object with altered fields from a default integration yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The integration object.
    """
    yml_content = load_yaml("integration.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    integration = pack.create_integration(yml=yml_content)
    integration.code = File(
        Path(f"{integration.path}/integration_0.ps1"), integration.repo_path
    )
    integration.code.write(r". $PSScriptRoot\CommonServerPowerShell.ps1")
    return BaseContent.from_path(Path(integration.path))  # type:ignore


def create_script_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an script object with altered fields from a default script yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The script object.
    """
    yml_content = load_yaml("script.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    script = pack.create_script(yml=yml_content)
    script.code.write("from MicrosoftApiModule import *")
    return BaseContent.from_path(Path(script.path))


def create_metadata_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
):
    """Creating an pack_metadata object with altered fields from a default pack_metadata json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The pack_metadata object.
    """
    json_content = load_json("pack_metadata.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    PackParser.parse_ignored_errors = MagicMock(return_value={})
    pack.pack_metadata.write_json(json_content)
    return PackParser(Path(pack.path))


def create_classifier_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an classifier object with altered fields from a default classifier json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The classifier object.
    """
    json_content = load_json("classifier.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_classifier(name="test_classifier", content=json_content)
    return BaseContent.from_path(Path(pack.classifiers[0].path))


def create_dashboard_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an dashboard object with altered fields from a default dashboard json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The dashboard object.
    """
    json_content = load_json("dashboard.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_dashboard(name="dashboard", content=json_content)
    return BaseContent.from_path(Path(pack.dashboards[0].path))


def create_incident_type_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an incident_type object with altered fields from a default incident_type json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The incident_type object.
    """
    json_content = load_json("incident_type.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_incident_type(name="incident_type", content=json_content)
    return BaseContent.from_path(Path(pack.incident_types[0].path))


def create_incident_field_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an incident_field object with altered fields from a default incident_field json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The incident_field object.
    """
    json_content = load_json("incident_field.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_incident_field(name="incident_field", content=json_content)
    return BaseContent.from_path(Path(pack.incident_fields[0].path))


def create_indicator_field_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an indicator_field object with altered fields from a default indicator_field json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The indicator_field object.
    """
    json_content = load_json("indicator_field.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_indicator_field(name="indicator_field", content=json_content)
    return BaseContent.from_path(Path(pack.indicator_fields[0].path))


def create_wizard_object(dict_to_update: Optional[Any] = None):
    """Creating a wizard object with altered fields from a default wizard json structure.

    Args:
        dict_to_update (Optional[Any], optional): The dict to update into the wizards dict.

    Returns:
        The wizard object.
    """
    pack = REPO.create_pack()
    pack.create_wizard(name="test_wizard")
    if dict_to_update:
        pack.wizards[0].update(dict_to_update)
    wizard_object = BaseContent.from_path(Path(pack.wizards[0].path))
    return wizard_object


def create_old_file_pointers(content_items, old_content_items):
    for content_item, old_content_item in zip(content_items, old_content_items):
        content_item.old_base_content_object = old_content_item


def update_keys(dict_obj, paths, values):
    if paths and values:
        for path, value in zip(paths, values):
            set_value(dict_obj, path, value)
