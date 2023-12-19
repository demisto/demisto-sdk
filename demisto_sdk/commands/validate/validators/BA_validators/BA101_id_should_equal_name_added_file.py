from __future__ import annotations

from typing import Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator

ContentTypes = Union[
    Dashboard,
    IncidentType,
    Classifier,
]


class IDNameAddedFileValidator(IDNameValidator, BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.ADDED]
