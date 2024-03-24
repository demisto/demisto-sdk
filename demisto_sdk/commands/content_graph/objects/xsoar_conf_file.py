import typing
from abc import ABC

from pydantic import BaseModel, Extra, Field


class StrictBaseModel(BaseModel, ABC):
    class Config:
        extra = Extra.forbid


class BasePack(StrictBaseModel, ABC):
    id_: str = Field(..., alias="id", description="ID of the pack to install")


class CustomPack(BasePack):
    url: str = Field(..., description="URL of the pack to install")


class MarketplacePack(BasePack):
    version: str = Field(..., description="version of the pack to install")


class List(StrictBaseModel):
    name: str = Field(..., description="Name of the list to configure")
    value: str = Field(..., description="Value of the list to configure")


class Job(BaseModel):  # Not strict, unlike the others
    type_: str = Field(..., alias="type", description="Type of incident to be created")
    name: str = Field(..., description="Name of the job to configure")
    playbook_id: str = Field(
        ...,
        alias="playbookId",
        description="ID of the playbook to be configured in the job",
    )
    scheduled: bool = Field(..., description="Whether to configure as a scheduled job")
    recurrent: bool = Field(..., description="Whether to configure as a recurrent job")
    cron_view: bool = Field(
        ...,
        alias="cronView",
        description="Whether to configure the recurrent time as a cron string",
    )
    cron: str = Field(
        ...,
        description="Cron string to represent the recurrence of the job",
    )
    start_date: str = Field(
        ...,
        alias="startDate",
        description="ISO format start datetime string (YYYY-mm-ddTHH:MM:SS.fffZ)",
    )
    end_date: str = Field(
        ...,
        alias="endingDate",
        description="ISO format end datetime string (YYYY-mm-ddTHH:MM:SS.fffZ)",
    )
    should_trigger_new: bool = Field(
        ...,
        alias="shouldTriggerNew",
        description="Whether to trigger new job instance when a previous job instance is still active",
    )
    close_previous_run: bool = Field(
        ...,
        alias="closePrevRun",
        description="Whether to cancel the previous job run when one is still active",
    )


class XSOAR_Configuration(StrictBaseModel):
    custom_packs: typing.List[CustomPack]
    marketplace_packs: typing.List[MarketplacePack]
    lists: typing.List[List]
    jobs: typing.List[Job]
