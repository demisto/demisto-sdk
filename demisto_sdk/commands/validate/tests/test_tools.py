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
    """Creating an integration object with altered fields from a default integration yml structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The integration object.
    """
    yml_content = load_yaml("integration.yml")
    if key_path and new_value:
        set_val(yml_content, key_path, new_value)
    pack = REPO.create_pack()
    integration = pack.create_integration(yml=yml_content)
    integration.code.write("from MicrosoftApiModule import *")
    return BaseContent.from_path(Path(integration.path))


def create_script_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    """Creating an script object with altered fields from a default script yml structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The script object.
    """
    yml_content = load_yaml("script.yml")
    if key_path and new_value:
        set_val(yml_content, key_path, new_value)
    pack = REPO.create_pack()
    script = pack.create_script(yml=yml_content)
    script.code.write("from MicrosoftApiModule import *")
    return BaseContent.from_path(Path(script.path))


def create_metadata_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    """Creating an pack_metadata object with altered fields from a default pack_metadata json structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The pack_metadata object.
    """
    json_content = load_json("pack_metadata.json")
    if key_path and new_value is not None:
        set_val(json_content, key_path, new_value)
    pack = REPO.create_pack()
    pack.pack_metadata.write_json(json_content)
    return BaseContent.from_path(Path(pack.pack_metadata.path))


def create_classifier_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    """Creating an classifier object with altered fields from a default classifier json structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The classifier object.
    """
    json_content = load_json("classifier.json")
    if key_path and new_value is not None:
        set_val(json_content, key_path, new_value)
    pack = REPO.create_pack()
    pack.create_classifier(name="test_classifier", content=json_content)
    return BaseContent.from_path(Path(pack.classifiers[0].path))


def create_dashboard_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    """Creating an dashboard object with altered fields from a default dashboard json structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The dashboard object.
    """
    json_content = load_json("dashboard.json")
    if key_path and new_value is not None:
        set_val(json_content, key_path, new_value)
    pack = REPO.create_pack()
    pack.create_dashboard(name="dashboard", content=json_content)
    return BaseContent.from_path(Path(pack.dashboards[0].path))


def create_incident_type_object(
    key_path: Optional[Any] = None, new_value: Optional[Any] = None
):
    """Creating an incident_type object with altered fields from a default incident_type json structure.

    Args:
        key_path (Optional[Any], optional): The key to update.
        new_value (Optional[Any], optional): The value to update.

    Returns:
        The incident_type object.
    """
    json_content = load_json("incident_type.json")
    if key_path and new_value is not None:
        set_val(json_content, key_path, new_value)
    pack = REPO.create_pack()
    pack.create_incident_type(name="incident_type", content=json_content)
    return BaseContent.from_path(Path(pack.incident_types[0].path))


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
