import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from unittest.mock import MagicMock

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    RELEASE_NOTES_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import set_value
from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
    AssetsModelingRule,
)
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.generic_definition import (
    GenericDefinition,
)
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.report import Report
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.parsers.parsing_rule import (
    ParsingRuleParser,
)
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
from demisto_sdk.commands.content_graph.parsers.related_files import (
    ImageRelatedFile,
    TestUseCaseRelatedFile,
)
from demisto_sdk.commands.content_graph.parsers.test_playbook import TestPlaybookParser
from demisto_sdk.commands.content_graph.parsers.agentix_action import AgentixActionParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from TestSuite.file import File
from TestSuite.repo import Repo

REPO = Repo(tmpdir=Path(tempfile.mkdtemp()), init_git=True)


def create_integration_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
    readme_content: Optional[str] = None,
    description_content: Optional[str] = None,
    name: Optional[str] = None,
    code: Optional[str] = None,
    unit_test_name: Optional[str] = None,
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
    if pack_info:
        pack.set_data(**pack_info)

    additional_params = {}

    if description_content:
        additional_params["description"] = description_content

    if readme_content is not None:
        additional_params["readme"] = readme_content

    if name is not None:
        additional_params["name"] = name

    if unit_test_name:
        additional_params["unit_test_name"] = unit_test_name

    integration = pack.create_integration(yml=yml_content, **additional_params)
    code = code or "from MicrosoftApiModule import *"
    integration.code.write(code)
    return cast(Integration, BaseContent.from_path(Path(integration.path)))


def create_parsing_rule_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
) -> ParsingRule:
    """Creating an parsing_rule object with altered fields from a default parsing_rule yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The parsing_rule object.
    """
    yml_content = load_yaml("parsing_rule.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    parsing_rule = pack.create_parsing_rule("TestParsingRule", yml_content)
    parser = ParsingRuleParser(
        Path(parsing_rule.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    return ParsingRule.from_orm(parser)


def create_correlation_rule_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
) -> CorrelationRule:
    """Creating an correlation_rule object with altered fields from a default correlation_rule yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The correlation_rule object.
    """
    yml_content = load_yaml("correlation_rule_test.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    pack.create_correlation_rule(name="correlation_rule", content=yml_content)
    return cast(
        CorrelationRule, BaseContent.from_path(Path(pack.correlation_rules[0].path))
    )


def create_playbook_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
    readme_content: Optional[str] = None,
    file_name: Optional[str] = None,
) -> Playbook:
    """Creating a playbook object with altered fields from a default playbook yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        pack_info (Optional[List[str]]): The playbook's pack name.
        readme_content (Optional[List[Any]]): The playbook's readme.
        file_name (Optional[List[Any]]): The playbook's file name.
    Returns:
        The playbook object.
    """
    yml_content = load_yaml("playbook.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    if pack_info:
        pack.set_data(**pack_info)
    additional_params = {}
    if file_name:
        additional_params["name"] = file_name
    if readme_content is not None:
        additional_params["readme"] = readme_content

    playbook = pack.create_playbook(**additional_params)
    playbook.create_default_playbook(name="sample")
    playbook.yml.update(yml_content)
    parser = PlaybookParser(
        Path(playbook.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    return Playbook.from_orm(parser)


def create_test_playbook_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
    readme_content: Optional[str] = None,
) -> TestPlaybook:
    """Creating a test playbook object with altered fields from a default test playbook yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        pack_info (Optional[List[str]]): The playbook's pack name.
        readme_content (Optional[List[Any]]): The playbook's readme.
    Returns:
        The test playbook object.
    """
    yml_content = load_yaml("playbook.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    if pack_info:
        pack.set_data(**pack_info)
    additional_params = {}

    if readme_content is not None:
        additional_params["readme"] = readme_content

    playbook = pack.create_test_playbook(**additional_params)
    playbook.create_default_test_playbook(name="sample")
    playbook.yml.update(yml_content)
    parser = TestPlaybookParser(
        Path(playbook.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    return TestPlaybook.from_orm(parser)


def create_doc_file_object(
    pack_path: Path, image_name: Optional[str] = "example.png"
) -> ImageRelatedFile:
    """Creating a doc file object.

    Args:
        pack_path: The path to the pack the doc file should be created in.
        image_name: The image name to create.
    Returns:
        The doc file object.
    """
    doc_path = pack_path / "doc_files" / image_name
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(doc_path, "wb") as f:
        f.write(b"")
    return ImageRelatedFile(doc_path)


def create_test_use_case_file_object(
    playbook_path: Path,
    test_use_case_name: str,
    test_use_case_content: str,
) -> TestUseCaseRelatedFile:
    """Creating test use case file object.

    Args:
        playbook_path (Path): The path to the playbook that is tested by the test use case.
        test_use_case_name (str): The name of the test use case (without the `.py` extension).
        test_use_case_content (str): The contents of the test use case file.
    Returns:
        TestUseCaseRelatedFile: The test use case file object.
    """
    test_use_case_path = (
        playbook_path.parent.parent / "TestUseCases" / f"{test_use_case_name}.py"
    )
    test_use_case_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_use_case_path, "w") as f:
        f.write(test_use_case_content)
    return TestUseCaseRelatedFile(playbook_path, test_use_case_name)


def create_modeling_rule_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    rules: Optional[str] = None,
    schema: Optional[dict] = None,
) -> ModelingRule:
    """Creating an modeling_rule object with altered fields from a default modeling_rule yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The modeling_rule object.
    """
    yml_content = load_yaml("modeling_rule.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    pack.create_modeling_rule(yml=yml_content, rules=rules, schema=schema)
    return cast(ModelingRule, BaseContent.from_path(Path(pack.modeling_rules[0].path)))


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
    yml_content = load_yaml("ps_integration.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    integration = pack.create_integration(yml=yml_content)
    integration.code = File(
        Path(f"{integration.path}/integration_0.ps1"), integration.repo_path
    )
    integration.code.write(r". $PSScriptRoot\CommonServerPowerShell.ps1")
    return cast(Integration, BaseContent.from_path(Path(integration.path)))


def create_script_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
    readme_content: Optional[str] = None,
    name: Optional[str] = None,
    code: Optional[str] = None,
    test_code: Optional[str] = None,
) -> Script:
    """Creating an script object with altered fields from a default script yml structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        pack_name (str): The name of the pack that the script will be inside of

    Returns:
        The script object.
    """
    additional_params = {}
    if name is not None:
        additional_params["name"] = name

    yml_content = load_yaml("script.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    if pack_info:
        pack.set_data(**pack_info)
    if readme_content is not None:
        additional_params["readme"] = readme_content

    script = pack.create_script(yml=yml_content, **additional_params)
    code = code or "from MicrosoftApiModule import *"
    script.code.write(code)
    if test_code:
        script.test.write(test_code)
    return cast(Script, BaseContent.from_path(Path(script.path)))


def create_pack_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    fields_to_delete: Optional[List[str]] = None,
    readme_text: str = "",
    image: Optional[str] = None,
    playbooks: int = 0,
    name: Optional[str] = None,
    release_note_content: Optional[str] = None,
    bc_release_note_content: Optional[dict] = None,
    version_config: Optional[dict] = None,
) -> Pack:
    """Creating an pack object with altered fields from a default pack_metadata json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The pack_metadata object.
    """
    json_content = load_json("pack_metadata.json")
    update_keys(json_content, paths, values)
    remove_fields_from_dict(json_content, fields_to_delete)
    pack = REPO.create_pack(name)
    pack_path = Path(pack.path)

    if release_note_content is not None:
        if (version := Version(json_content.get("currentVersion", "1.0.0"))) == Version(
            "1.0.0"
        ):
            raise ValueError(
                "Can't write release notes for v1.0.0, set version to another value"
            )
        # Writes the release notes
        (
            pack_path / RELEASE_NOTES_DIR / (str(version).replace(".", "_") + ".md")
        ).write_text(release_note_content)

    if bc_release_note_content is not None:
        if (version := Version(json_content.get("currentVersion", "1.0.0"))) == Version(
            "1.0.0"
        ):
            raise ValueError(
                "Can't write release notes for v1.0.0, set version to another value"
            )
        json_object = json.dumps(bc_release_note_content, indent=4)

        with open(
            pack_path / RELEASE_NOTES_DIR / (str(version).replace(".", "_") + ".json"),
            "w",
        ) as outfile:
            outfile.write(json_object)

    if version_config:
        pack.version_config.write_json(version_config)

    PackParser.parse_ignored_errors = MagicMock(return_value={})
    pack.pack_metadata.write_json(json_content)
    pack.readme.write_text(readme_text)

    if image is not None:
        pack.author_image.write(image)
    if playbooks:
        for _ in range(playbooks):
            pack.create_playbook()

    return cast(Pack, BaseContent.from_path(pack_path))


def remove_fields_from_dict(
    json_content: dict, fields_to_delete: Optional[List[str]] = None
):
    if fields_to_delete:
        for field in fields_to_delete:
            del json_content[field]


def create_classifier_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Classifier:
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
    return cast(Classifier, BaseContent.from_path(Path(pack.classifiers[0].path)))


def create_list_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> ListObject:
    """Creating an list object with altered fields from a default list json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The list object.
    """
    json_content = load_json("list.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_list(name="list", content=json_content)
    return cast(ListObject, BaseContent.from_path(Path(pack.lists[0].path)))


def create_job_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Job:
    """Creating an job object with altered fields from a default job json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The job object.
    """
    json_content = {}
    pack = REPO.create_pack()
    pack.create_job(name="job", is_feed=True)
    if paths and values:
        with open(pack.jobs[0].path) as f:
            json_content = json.load(f)
            update_keys(json_content, paths, values)
        with open(pack.jobs[0].path, "w") as fp:
            json.dump(json_content, fp)
    return cast(Job, BaseContent.from_path(Path(pack.jobs[0].path)))


def create_dashboard_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Dashboard:
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
    return cast(Dashboard, BaseContent.from_path(Path(pack.dashboards[0].path)))


def create_incident_type_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> IncidentType:
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
    return cast(IncidentType, BaseContent.from_path(Path(pack.incident_types[0].path)))


def create_incident_field_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
) -> IncidentField:
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
    if pack_info:
        pack.set_data(**pack_info)
    pack.create_incident_field(name="incident_field", content=json_content)
    return cast(
        IncidentField, BaseContent.from_path(Path(pack.incident_fields[0].path))
    )


def create_report_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Report:
    """Creating an report object with altered fields from a default report json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The report object.
    """
    json_content = load_json("report.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_report(name="report", content=json_content)
    return cast(Report, BaseContent.from_path(Path(pack.reports[0].path)))


def create_xsiam_report_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> XSIAMReport:
    """Creating an xsiam_report object with altered fields from a default xsiam_report json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The xsiam_report object.
    """
    json_content = load_json("xsiam_report.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_xsiam_report(name="xsiam_report", content=json_content)
    return cast(XSIAMReport, BaseContent.from_path(Path(pack.xsiam_reports[0].path)))


def create_xsiam_dashboard_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> XSIAMDashboard:
    """Creating an xsiam_dashboard object with altered fields from a default xsiam_dashboard json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The xsiam_dashboard object.
    """
    json_content = load_json("xsiam_dashboard.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_xsiam_dashboard(name="xsiam_dashboard", content=json_content)
    return cast(
        XSIAMDashboard, BaseContent.from_path(Path(pack.xsiam_dashboards[0].path))
    )


def create_xdrc_template_object(
    json_paths: Optional[List[str]] = None,
    json_values: Optional[List[Any]] = None,
    yml_paths: Optional[List[str]] = None,
    yml_values: Optional[List[Any]] = None,
) -> XDRCTemplate:
    """Creating an xdrc_template object with altered fields from a default xdrc_template json and yml structures.

    Args:
        json_paths (Optional[List[str]]): The keys to update for the json file.
        json_values (Optional[List[Any]]): The values to update for the json file.
        yml_paths (Optional[List[str]]): The keys to update for the yml file.
        yml_values (Optional[List[Any]]): The values to update for the yml file.

    Returns:
        The xdrc_template object.
    """
    json_content = load_json("xdrc_template.json")
    update_keys(json_content, json_paths, json_values)
    yml_content = load_yaml("xdrc_template.yml")
    update_keys(json_content, yml_paths, yml_values)
    pack = REPO.create_pack()
    pack.create_xdrc_template(
        name="xdrc_template", json_content=json_content, yaml_content=yml_content
    )
    return cast(XDRCTemplate, BaseContent.from_path(Path(pack.xdrc_templates[0].path)))


def create_assets_modeling_rule_object(
    json_paths: Optional[List[str]] = None,
    json_values: Optional[List[Any]] = None,
    yml_paths: Optional[List[str]] = None,
    yml_values: Optional[List[Any]] = None,
) -> AssetsModelingRule:
    """Creating an assets_modeling_rule object with altered fields from a default assets_modeling_rule json and yml structures.

    Args:
        json_paths (Optional[List[str]]): The keys to update for the json file.
        json_values (Optional[List[Any]]): The values to update for the json file.
        yml_paths (Optional[List[str]]): The keys to update for the yml file.
        yml_values (Optional[List[Any]]): The values to update for the yml file.

    Returns:
        The assets_modeling_rule object.
    """
    json_content = load_json("assets_modeling_rule.json")
    update_keys(json_content, json_paths, json_values)
    yml_content = load_yaml("assets_modeling_rule.yml")
    update_keys(json_content, yml_paths, yml_values)
    pack = REPO.create_pack()
    pack.create_assets_modeling_rule(
        name="assets_modeling_rule", schema=json_content, yml=yml_content
    )
    return cast(
        AssetsModelingRule,
        BaseContent.from_path(Path(pack.assets_modeling_rules[0].path)),
    )


def create_trigger_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    file_name: str = "trigger",
) -> Trigger:
    """Creating an trigger object with altered fields from a default trigger json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        file_name (str): the file name.

    Returns:
        The trigger object.
    """
    json_content = load_json("trigger.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_trigger(name=file_name, content=json_content)
    return cast(Trigger, BaseContent.from_path(Path(pack.triggers[0].path)))


def create_layout_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    file_path: Optional[str] = None,
) -> Layout:
    """Creating an layout object with altered fields from a default layout json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        file_path: Optional[str]: For creating layout object from specific json file.

    Returns:
        The layout object.
    """
    if file_path:
        json_content = load_json(file_path)
        pack = REPO.create_pack()
        pack.create_layout(name="layout", content=json_content)
        return cast(Layout, BaseContent.from_path(Path(pack.layouts[0].path)))

    json_content = load_json("layoutscontainer.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_layout(name="layout", content=json_content)
    return cast(Layout, BaseContent.from_path(Path(pack.layouts[0].path)))


def create_widget_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Widget:
    """Creating an widget object with altered fields from a default widget json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The widget object.
    """
    json_content = load_json("widget.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_widget(name="widget", content=json_content)
    return cast(Widget, BaseContent.from_path(Path(pack.widgets[0].path)))


def create_indicator_field_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> IndicatorField:
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
    return cast(
        IndicatorField, BaseContent.from_path(Path(pack.indicator_fields[0].path))
    )


def create_wizard_object(dict_to_update: Optional[Any] = None) -> Wizard:
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
    return cast(Wizard, BaseContent.from_path(Path(pack.wizards[0].path)))


def create_generic_definition_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> GenericDefinition:
    """Creating an generic_definition object with altered fields from a default generic_definition json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The generic_definition object.
    """
    json_content = load_json("generic_definition.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_generic_definition(name="generic_definition", content=json_content)
    return cast(
        GenericDefinition, BaseContent.from_path(Path(pack.generic_definitions[0].path))
    )


def create_generic_field_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> GenericField:
    """Creating an generic_field object with altered fields from a default generic_field json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The generic_field object.
    """
    json_content = load_json("generic_field.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_generic_field(name="generic_field", content=json_content)
    return cast(GenericField, BaseContent.from_path(Path(pack.generic_fields[0].path)))


def create_generic_type_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> GenericType:
    """Creating an generic_type object with altered fields from a default generic_type json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The generic_type object.
    """
    json_content = load_json("generic_type.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_generic_type(name="generic_type", content=json_content)
    return cast(GenericType, BaseContent.from_path(Path(pack.generic_types[0].path)))


def create_generic_module_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> GenericModule:
    """Creating an generic_module object with altered fields from a default generic_module json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The generic_module object.
    """
    json_content = load_json("generic_module.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_generic_module(name="generic_module", content=json_content)
    return cast(
        GenericModule, BaseContent.from_path(Path(pack.generic_modules[0].path))
    )


def create_incoming_mapper_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> Mapper:
    """Creating an incoming_mapper object with altered fields from a default incoming_mapper json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The incoming_mapper object.
    """
    json_content = load_json("incoming_mapper.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_mapper(name="incoming_mapper", content=json_content)
    return cast(Mapper, BaseContent.from_path(Path(pack.mappers[0].path)))


def create_outgoing_mapper_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
):
    """Creating an outgoing_mapper object with altered fields from a default outgoing_mapper json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The outgoing_mapper object.
    """
    json_content = load_json("outgoing_mapper.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_mapper(name="outgoing_mapper", content=json_content)
    return BaseContent.from_path(Path(pack.mappers[0].path))


def create_indicator_type_object(
    paths: Optional[List[str]] = None, values: Optional[List[Any]] = None
) -> IndicatorType:
    """Creating an indicator_type object with altered fields from a default indicator_type json structure.

    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.

    Returns:
        The indicator_type object.
    """
    json_content = load_json("indicator_type.json")
    update_keys(json_content, paths, values)
    pack = REPO.create_pack()
    pack.create_indicator_type(name="indicator_type", content=json_content)
    return cast(
        IndicatorType, BaseContent.from_path(Path(pack.indicator_types[0].path))
    )


def create_old_file_pointers(content_items, old_content_items) -> None:
    """Given two iterables of content_items and their old_content_items, assign each content_item its matching old_content_item.

    Args:
        content_items (Iterable): Iterables object of content_items.
        old_content_items (Iterable): Iterables object of olf_content_items.
    """
    for content_item, old_content_item in zip(content_items, old_content_items):
        content_item.old_base_content_object = old_content_item


def update_keys(dict_obj, paths, values):
    if paths and values:
        for path, value in zip(paths, values):
            set_value(dict_obj, path, value)


def create_agentix_action_object(
    paths: Optional[List[str]] = None,
    values: Optional[List[Any]] = None,
    pack_info: Optional[Dict[str, Any]] = None,
    file_name: Optional[str] = None,
) -> AgentixAction:
    """Creating a playbook object with altered fields from a default playbook yml structure.
    Args:
        paths (Optional[List[str]]): The keys to update.
        values (Optional[List[Any]]): The values to update.
        pack_info (Optional[List[str]]): The actions's pack name.
        file_name (Optional[List[Any]]): The action's file name.
    Returns:
        The playbook object.
    """
    yml_content = load_yaml("agentix_action.yml")
    update_keys(yml_content, paths, values)
    pack = REPO.create_pack()
    if pack_info:
        pack.set_data(**pack_info)
    additional_params = {}
    if file_name:
        additional_params["name"] = file_name

    agentix_action = pack.create_agentix_action(**additional_params)
    agentix_action.create_default_agentix_action("sample")
    agentix_action.yml.update(yml_content)
    parser = AgentixActionParser(
        Path(agentix_action.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    return AgentixAction.from_orm(parser)
