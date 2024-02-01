from typing import Callable, Optional, List, Dict, Any

import demisto_client
from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)

class TimerTriggerSchema(BaseModel):
    fieldname: str
    action: str


class EvidenceDataDescription(BaseModel):
    simple: Optional[str]

class EvidenceDataOccurred(BaseModel):
    simple: Optional[str]

class EvidenceDataTags(BaseModel):
    simple: Optional[str]

class EvidenceData(BaseModel):
    description: Optional[EvidenceDataDescription]
    customfields: Optional[EvidenceDataOccurred]
    occurred: Optional[Dict]
    tags: Optional[EvidenceDataTags]


class Task(BaseModel):
    id: str
    version: int
    name: str
    name_x2: Optional[str]
    playbookName: Optional[str]
    playbookName_x2: Optional[str]
    playbookId: Optional[str]
    playbookId_x2: Optional[str]
    description: Optional[str]
    description_x2: Optional[str]
    scriptName: Optional[str]
    scriptName_x2: Optional[str]
    script: Optional[str]
    script_x2: Optional[str]
    tags: Optional[List[str]]
    type: Optional[str]
    iscommand: bool
    elasticcommonfields: Optional[Dict[str, str]]
    brand: str
    issystemtask: Optional[bool]
    clonedfrom: Optional[str]
    name_xsoar: Optional[str]
    name_marketplacev2: Optional[str]
    name_xpanse: Optional[str]
    name_xsoar_saas: Optional[str]
    name_xsoar_on_prem: Optional[str]
    description_xsoar: Optional[str]
    description_marketplacev2: Optional[str]
    description_xpanse: Optional[str]
    description_xsoar_saas: Optional[str]
    description_xsoar_on_prem: Optional[str]

class ArgFilterSchema(BaseModel):
    operator: str
    ignorecase: Optional[bool]
    left: Dict[str, Any]
    right: Optional[Dict[str, Any]]

class Loop(BaseModel):
    iscommand: Optional[bool]
    builtincondition: Optional[List[List[ArgFilterSchema]]]
    scriptId: Optional[str]
    scriptId_x2: Optional[str]
    scriptArguments: Optional[Dict]
    exitCondition: Optional[str]
    max: Optional[int]
    wait: Optional[int]
    forEach: Optional[bool]

class ConditionSchema(BaseModel):
    # Define the fields in condition_schema
    # You might need to adjust the field types based on the actual structure
    label: str
    condition: Optional[List[list]]

class TaskConfig(BaseModel):
    id: str
    taskid: str
    type: str
    form: Optional[Dict] = None
    message: Optional[Dict] = None
    defaultassigneecomplex: Optional[Dict] = None
    sla: Optional[Dict] = None
    slareminder: Optional[Dict] = None
    quietmode: Optional[int]
    restrictedcompletion: Optional[bool]
    scriptarguments: Optional[Dict] = None
    timertriggers: Optional[List[TimerTriggerSchema]] = None
    ignoreworker: Optional[bool]
    skipunavailable: Optional[bool]
    isoversize: Optional[bool]
    isautoswitchedtoquietmode: Optional[bool]
    quiet: Optional[bool]
    evidencedata: Optional[EvidenceData]
    task: Task
    note: Optional[bool]
    nexttasks: Optional[Dict[str, List[str]]]
    loop: Optional[Loop]
    conditions: Optional[List[ConditionSchema]]
    view: str
    results: Optional[List[str]]
    continueonerror: Optional[bool]
    continueonerrortype: Optional[str]
    reputationcalc: Optional[int]
    separatecontext: Optional[bool]
    fieldMapping: Optional[List]


class BasePlaybook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]

    tasks: Dict[str, TaskConfig] = Field([], exclude=True)

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        # taking the description from the data after preparing the playbook to upload
        # this might be different when replacing incident to alert in the description for marketplacev2
        summary["description"] = self.data.get("description") or ""
        return summary

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)
        return MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            self,
            data,
            current_marketplace=current_marketplace,
            supported_marketplaces=self.marketplaces,
        )

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_playbook

    def save(self, output_path: str = ""):
        super().save(output_path)  # type: ignore

