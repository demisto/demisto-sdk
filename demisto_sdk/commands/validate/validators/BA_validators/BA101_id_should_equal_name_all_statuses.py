from __future__ import annotations

from typing import Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.job import Job
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)

ContentTypes = Union[Integration, Layout, Mapper, Playbook, Script, Wizard, Job]


class IDNameAllStatusesValidator(IDNameValidator, BaseValidator[ContentTypes]):
    """
    This class is for cases where the IDNameValidator need to run on all cases (no matter what git status)
    """
