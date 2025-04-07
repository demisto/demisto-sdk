from functools import cached_property
from typing import Callable, Dict, List, Optional, Set

import demisto_client
from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
    PlaybookTaskType,
)
from demisto_sdk.commands.common.tools import remove_nulls_from_dictionary, write_dict
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers.related_files import (
    ImageRelatedFile,
    ReadmeRelatedFile,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)


class Task(BaseModel):
    id: str
    version: Optional[int] = None
    name: Optional[str] = None
    name_x2: Optional[str] = None
    playbookName: Optional[str] = None
    playbookName_x2: Optional[str] = None
    playbookId: Optional[str] = None
    playbookId_x2: Optional[str] = None
    description: Optional[str] = None
    description_x2: Optional[str] = None
    scriptName: Optional[str] = None
    scriptName_x2: Optional[str] = None
    script: Optional[str] = None
    script_x2: Optional[str] = None
    tags: Optional[List[str]] = None
    type: Optional[PlaybookTaskType] = None
    iscommand: Optional[bool] = None
    elasticcommonfields: Optional[Dict[str, str]] = None
    brand: Optional[str] = None
    issystemtask: Optional[bool] = None
    clonedfrom: Optional[str] = None
    name_xsoar: Optional[str] = None
    name_marketplacev2: Optional[str] = None
    name_xpanse: Optional[str] = None
    name_xsoar_saas: Optional[str] = None
    name_xsoar_on_prem: Optional[str] = None
    description_xsoar: Optional[str] = None
    description_marketplacev2: Optional[str] = None
    description_xpanse: Optional[str] = None
    description_xsoar_saas: Optional[str] = None
    description_xsoar_on_prem: Optional[str] = None

    @property
    def to_raw_dict(self) -> Dict:
        """Generate a dict representation of the Task object.

        Returns:
            Dict: The dict representation of the Task object.
        """
        task = {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "name_x2": self.name_x2,
            "playbookName": self.playbookName,
            "playbookName_x2": self.playbookName_x2,
            "playbookId": self.playbookId,
            "playbookId_x2": self.playbookId_x2,
            "description": self.description,
            "description_x2": self.description_x2,
            "scriptName": self.scriptName,
            "scriptName_x2": self.scriptName_x2,
            "script": self.script,
            "script_x2": self.script_x2,
            "tags": self.tags,
            "type": self.type.value if self.type else None,
            "iscommand": self.iscommand,
            "elasticcommonfields": self.elasticcommonfields,
            "brand": self.brand,
            "issystemtask": self.issystemtask,
            "clonedfrom": self.clonedfrom,
            "name_xsoar": self.name_xsoar,
            "name_marketplacev2": self.name_marketplacev2,
            "name_xpanse": self.name_xpanse,
            "name_xsoar_saas": self.name_xsoar_saas,
            "name_xsoar_on_prem": self.name_xsoar_on_prem,
            "description_xsoar": self.description_xsoar,
            "description_marketplacev2": self.description_marketplacev2,
            "description_xpanse": self.description_xpanse,
            "description_xsoar_saas": self.description_xsoar_saas,
            "description_xsoar_on_prem": self.description_xsoar_on_prem,
        }
        remove_nulls_from_dictionary(task)
        return task


class TaskConfig(BaseModel):
    id: str
    taskid: str
    type: Optional[PlaybookTaskType] = None
    form: Optional[Dict] = None
    message: Optional[Dict] = None
    defaultassigneecomplex: Optional[Dict] = None
    sla: Optional[Dict] = None
    slareminder: Optional[Dict] = None
    quietmode: Optional[int] = None
    restrictedcompletion: Optional[bool] = None
    scriptarguments: Optional[Dict] = None
    timertriggers: Optional[List] = None
    ignoreworker: Optional[bool] = None
    skipunavailable: Optional[bool] = None
    isoversize: Optional[bool] = None
    isautoswitchedtoquietmode: Optional[bool] = None
    quiet: Optional[bool] = None
    evidencedata: Optional[dict] = None
    task: Task
    note: Optional[bool] = None
    nexttasks: Optional[Dict[str, List[str]]] = None
    loop: Optional[Dict] = None
    conditions: Optional[List[dict]] = None
    view: Optional[str] = None
    results: Optional[List[str]] = None
    continueonerror: Optional[bool] = None
    continueonerrortype: Optional[str] = None
    reputationcalc: Optional[int] = None
    separatecontext: Optional[bool] = None
    fieldMapping: Optional[List] = None

    @property
    def to_raw_dict(self) -> Dict:
        """Generate a dict representation of the TaskConfig object.

        Returns:
            Dict: The dict representation of the TaskConfig object.
        """
        task_config = {
            "id": self.id,
            "taskid": self.taskid,
            "type": self.type.value if self.type else None,
            "form": self.form,
            "message": self.message,
            "defaultassigneecomplex": self.defaultassigneecomplex,
            "sla": self.sla,
            "slareminder": self.slareminder,
            "quietmode": self.quietmode,
            "restrictedcompletion": self.restrictedcompletion,
            "scriptarguments": self.scriptarguments,
            "timertriggers": self.timertriggers,
            "ignoreworker": self.ignoreworker,
            "skipunavailable": self.skipunavailable,
            "isoversize": self.isoversize,
            "isautoswitchedtoquietmode": self.isautoswitchedtoquietmode,
            "quiet": self.quiet,
            "evidencedata": self.evidencedata,
            "task": self.task.to_raw_dict,
            "note": self.note,
            "nexttasks": self.nexttasks,
            "loop": self.loop,
            "conditions": self.conditions,
            "view": self.view,
            "results": self.results,
            "continueonerror": self.continueonerror,
            "continueonerrortype": self.continueonerrortype,
            "reputationcalc": self.reputationcalc,
            "separatecontext": self.separatecontext,
            "fieldMapping": self.fieldMapping,
        }
        remove_nulls_from_dictionary(task_config)
        return task_config


class BasePlaybook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    version: Optional[int] = 0
    tasks: Dict[str, TaskConfig] = Field([], exclude=True)
    quiet: bool = Field(False)
    tags: List[str] = Field([])

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)
        return MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            self,
            data,
            current_marketplace=current_marketplace,
            supported_marketplaces=self.marketplaces,
        )

    def is_incident_to_alert(self, marketplace: MarketplaceVersions) -> bool:
        """
        Checks whether the playbook needs the preparation
        of an `incident to alert`,
        and this affects the `metadata.json` and the `dump` process of the playbook.

        Args:
            marketplace (MarketplaceVersions): the destination marketplace.

        Returns:
            bool: True if the given MP is MPV2
        """
        return marketplace == MarketplaceVersions.MarketplaceV2

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_playbook

    def save(self):
        super().save(fields_to_exclude=["tasks"])
        data = self.data
        data["tasks"] = {
            task_id: task_config.to_raw_dict
            for task_id, task_config in self.tasks.items()
        }
        write_dict(self.path, data, indent=4)

    @cached_property
    def readme(self) -> ReadmeRelatedFile:
        return ReadmeRelatedFile(self.path, is_pack_readme=False, git_sha=self.git_sha)

    @cached_property
    def image(self) -> ImageRelatedFile:
        return ImageRelatedFile(self.path, git_sha=self.git_sha)

    def metadata_fields(self) -> Set[str]:
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "tags",
                }
            )
        )
