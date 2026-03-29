"""
get-schema command: returns the JSON schema of a content item's strict (pydantic) model.
"""

import json
from typing import Dict, Optional, Type

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    AgentixAction,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_action_test import (
    StrictAgentixActionTest,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_agent import (
    AgentixAgent,
)
from demisto_sdk.commands.content_graph.strict_objects.asset_modeling_rule import (
    StrictAssetsModelingRule,
)
from demisto_sdk.commands.content_graph.strict_objects.case_field import StrictCaseField
from demisto_sdk.commands.content_graph.strict_objects.case_layout import (
    StrictCaseLayout,
)
from demisto_sdk.commands.content_graph.strict_objects.case_layout_rule import (
    StrictCaseLayoutRule,
)
from demisto_sdk.commands.content_graph.strict_objects.classifier import (
    StrictClassifier,
)
from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel
from demisto_sdk.commands.content_graph.strict_objects.correlation_rule import (
    StrictCorrelationRule,
)
from demisto_sdk.commands.content_graph.strict_objects.dashboard import StrictDashboard
from demisto_sdk.commands.content_graph.strict_objects.generic_definition import (
    StrictGenericDefinition,
)
from demisto_sdk.commands.content_graph.strict_objects.generic_field import (
    StrictGenericField,
)
from demisto_sdk.commands.content_graph.strict_objects.generic_module import (
    StrictGenericModule,
)
from demisto_sdk.commands.content_graph.strict_objects.generic_type import (
    StrictGenericType,
)
from demisto_sdk.commands.content_graph.strict_objects.incident_field import (
    StrictIncidentField,
)
from demisto_sdk.commands.content_graph.strict_objects.incident_type import (
    StrictIncidentType,
)
from demisto_sdk.commands.content_graph.strict_objects.indicator_field import (
    StrictIndicatorField,
)
from demisto_sdk.commands.content_graph.strict_objects.indicator_type import (
    StrictIndicatorType,
)
from demisto_sdk.commands.content_graph.strict_objects.integration import (
    StrictIntegration,
)
from demisto_sdk.commands.content_graph.strict_objects.job import StrictJob
from demisto_sdk.commands.content_graph.strict_objects.layout import StrictLayout
from demisto_sdk.commands.content_graph.strict_objects.layout_rule import (
    StrictLayoutRule,
)
from demisto_sdk.commands.content_graph.strict_objects.list import StrictList
from demisto_sdk.commands.content_graph.strict_objects.mapper import StrictMapper
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule import (
    StrictModelingRule,
)
from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
    StrictPackMetadata,
)
from demisto_sdk.commands.content_graph.strict_objects.parsing_rule import (
    StrictParsingRule,
)
from demisto_sdk.commands.content_graph.strict_objects.playbook import StrictPlaybook
from demisto_sdk.commands.content_graph.strict_objects.pre_process_rule import (
    StrictPreProcessRule,
)
from demisto_sdk.commands.content_graph.strict_objects.report import StrictReport
from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript
from demisto_sdk.commands.content_graph.strict_objects.trigger import StrictTrigger
from demisto_sdk.commands.content_graph.strict_objects.widget import StrictWidget
from demisto_sdk.commands.content_graph.strict_objects.wizard import StrictWizard
from demisto_sdk.commands.content_graph.strict_objects.xdrc_template import (
    StrictXDRCTemplate,
)
from demisto_sdk.commands.content_graph.strict_objects.xsiam_dashboard import (
    StrictXSIAMDashboard,
)
from demisto_sdk.commands.content_graph.strict_objects.xsiam_report import (
    StrictXSIAMReport,
)

# Mapping from content item name (case-insensitive) to its strict pydantic model.
# Both underscore-separated and concatenated variants are registered so that
# e.g. both "agentix_action" and "agentixaction" resolve correctly.
CONTENT_ITEM_NAME_TO_STRICT_OBJECT: Dict[str, Type[BaseStrictModel]] = {
    "integration": StrictIntegration,
    "script": StrictScript,
    "playbook": StrictPlaybook,
    "testplaybook": StrictPlaybook,
    "test_playbook": StrictPlaybook,
    "classifier": StrictClassifier,
    "mapper": StrictMapper,
    "incidentfield": StrictIncidentField,
    "incident_field": StrictIncidentField,
    "indicatorfield": StrictIndicatorField,
    "indicator_field": StrictIndicatorField,
    "incidenttype": StrictIncidentType,
    "incident_type": StrictIncidentType,
    "indicatortype": StrictIndicatorType,
    "indicator_type": StrictIndicatorType,
    "layout": StrictLayout,
    "layoutrule": StrictLayoutRule,
    "layout_rule": StrictLayoutRule,
    "dashboard": StrictDashboard,
    "report": StrictReport,
    "widget": StrictWidget,
    "job": StrictJob,
    "list": StrictList,
    "genericdefinition": StrictGenericDefinition,
    "generic_definition": StrictGenericDefinition,
    "genericfield": StrictGenericField,
    "generic_field": StrictGenericField,
    "genericmodule": StrictGenericModule,
    "generic_module": StrictGenericModule,
    "generictype": StrictGenericType,
    "generic_type": StrictGenericType,
    "correlationrule": StrictCorrelationRule,
    "correlation_rule": StrictCorrelationRule,
    "modelingrule": StrictModelingRule,
    "modeling_rule": StrictModelingRule,
    "assetsmodelrule": StrictAssetsModelingRule,
    "assetsmodellingrule": StrictAssetsModelingRule,
    "assets_modeling_rule": StrictAssetsModelingRule,
    "parsingrule": StrictParsingRule,
    "parsing_rule": StrictParsingRule,
    "preprocessrule": StrictPreProcessRule,
    "preprocess_rule": StrictPreProcessRule,
    "pre_process_rule": StrictPreProcessRule,
    "trigger": StrictTrigger,
    "wizard": StrictWizard,
    "xsiamdashboard": StrictXSIAMDashboard,
    "xsiam_dashboard": StrictXSIAMDashboard,
    "xsiamreport": StrictXSIAMReport,
    "xsiam_report": StrictXSIAMReport,
    "xdrctemplate": StrictXDRCTemplate,
    "xdrc_template": StrictXDRCTemplate,
    "casefield": StrictCaseField,
    "case_field": StrictCaseField,
    "caselayout": StrictCaseLayout,
    "case_layout": StrictCaseLayout,
    "caselayoutrule": StrictCaseLayoutRule,
    "case_layout_rule": StrictCaseLayoutRule,
    "agentixaction": AgentixAction,
    "agentix_action": AgentixAction,
    "agentixactiontest": StrictAgentixActionTest,
    "agentix_action_test": StrictAgentixActionTest,
    "agentixagent": AgentixAgent,
    "agentix_agent": AgentixAgent,
    "pack": StrictPackMetadata,
    "pack_metadata": StrictPackMetadata,
    "packmetadata": StrictPackMetadata,
}


def get_content_item_schema(content_item_name: str) -> Optional[dict]:
    """
    Returns the JSON schema of the strict pydantic model for the given content item name.

    Args:
        content_item_name: The name of the content item type (e.g. 'integration', 'script').

    Returns:
        A dict representing the JSON schema, or None if the content item name is not recognized.
    """
    # Normalise: lower-case, replace hyphens/spaces with underscores.
    normalized = content_item_name.strip().lower().replace("-", "_").replace(" ", "_")
    strict_model = CONTENT_ITEM_NAME_TO_STRICT_OBJECT.get(normalized)
    if strict_model is None:
        return None
    return strict_model.schema()


def print_schema(content_item_name: str, output_file: Optional[str] = None) -> int:
    """
    Retrieves and prints (or writes) the JSON schema for the given content item name.

    Args:
        content_item_name: The name of the content item type.
        output_file: Optional path to write the schema JSON to. If None, prints to stdout.

    Returns:
        0 on success, 1 on failure.
    """
    schema = get_content_item_schema(content_item_name)
    if schema is None:
        available = sorted(
            {
                k
                for k in CONTENT_ITEM_NAME_TO_STRICT_OBJECT
                if "_" not in k
                or k.replace("_", "") not in CONTENT_ITEM_NAME_TO_STRICT_OBJECT
            }
        )
        logger.error(
            f"Unknown content item type: '{content_item_name}'.\n"
            f"Available content item types: {', '.join(available)}"
        )
        return 1

    schema_json = json.dumps(schema, indent=2)

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(schema_json)
            logger.info(f"Schema written to {output_file}")
        except OSError as e:
            logger.error(f"Failed to write schema to '{output_file}': {e}")
            return 1
    else:
        print(schema_json)

    return 0
