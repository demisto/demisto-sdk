from typing import Any, Mapping

import pytest
from pydantic import ValidationError

from demisto_sdk.commands.common.constants import PlatformSupportedModules
from demisto_sdk.commands.content_graph.strict_objects.integration import Configuration
from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
    StrictPackMetadata,
)

ALL_MODULES = [module.value for module in PlatformSupportedModules]

MINIMAL_PACK_METADATA = {
    "name": "TestPack",
    "support": "xsoar",
    "author": "Cortex XSOAR",
}

MINIMAL_PARAM = {"name": "param", "type": 0, "display": "Param"}


def pack_metadata(**overrides):
    return {**MINIMAL_PACK_METADATA, **overrides}


def build_param(**overrides):
    """Build an integration configuration parameter.

    ``Configuration`` is assembled at runtime by ``create_model``, so mypy sees a
    plain ``BaseModel`` and cannot tell it is instantiable. The call is kept in
    this single helper so the resulting ignore is not repeated in every test.
    """
    return Configuration(**{**MINIMAL_PARAM, **overrides})  # type:ignore[operator]


def first_error(exc_info) -> Mapping[str, Any]:
    """Return the first error of a caught pydantic ``ValidationError``."""
    validation_error: ValidationError = exc_info.value
    return validation_error.errors()[0]


class TestPackMetadataSupportedModules:
    """``supportedModules`` in pack_metadata.json must hold PlatformSupportedModules values.

    Before this was enforced, the field was a plain ``List[str]``, so a typo or a
    retired module name was written to the metadata unnoticed. Since content items
    inherit the pack's modules when they declare none of their own, a bad value
    there silently propagated to the whole pack.
    """

    def test_field_is_optional(self):
        """An omitted field means "all modules are supported" and stays valid."""
        assert StrictPackMetadata(**pack_metadata()).supportedModules is None

    @pytest.mark.parametrize(
        "modules",
        (
            pytest.param(["xsiam"], id="single"),
            pytest.param(["xsiam", "agentix"], id="subset"),
            pytest.param(ALL_MODULES, id="every_module"),
        ),
    )
    def test_valid_modules_are_accepted(self, modules):
        """Any combination of real module values is accepted, up to the full set."""
        parsed = StrictPackMetadata(**pack_metadata(supportedModules=modules))
        assert [module.value for module in parsed.supportedModules or []] == modules

    @pytest.mark.parametrize(
        "module",
        (
            pytest.param("X1", id="retired_name"),
            pytest.param("ENT_PLUS", id="legacy_license_tier"),
            pytest.param("not_a_module", id="nonexistent"),
            pytest.param("XSIAM", id="wrong_case"),
        ),
    )
    def test_unknown_module_is_rejected(self, module):
        """A value outside PlatformSupportedModules fails, naming the bad entry."""
        with pytest.raises(ValidationError) as exc_info:
            StrictPackMetadata(**pack_metadata(supportedModules=[module]))

        error = first_error(exc_info)
        assert error["loc"] == ("supportedModules", 0)
        assert "not a valid enumeration member" in error["msg"]

    def test_empty_list_is_left_to_st113(self):
        """``[]`` passes the schema on purpose: ST113 reports it with a clearer message.

        Declaring a lower bound here too would surface the same mistake twice.
        """
        assert (
            StrictPackMetadata(**pack_metadata(supportedModules=[])).supportedModules
            == []
        )


class TestIntegrationParamSupportedModules:
    """``supportedModules`` on an integration parameter shares the pack's constraints.

    The field used to carry a hardcoded ``max_length=7`` while the enum has since
    grown past it. That bound never took effect anyway: ``max_length`` is the
    pydantic v2 spelling and this project runs pydantic v1, which ignores it on
    list fields. Only the item type is enforced now.
    """

    def test_accepts_more_than_seven_modules(self):
        """Regression: a count above the old hardcoded limit is valid."""
        modules = ALL_MODULES[:8]
        parsed = build_param(supportedModules=modules)
        assert [module.value for module in parsed.supportedModules] == modules

    def test_accepts_every_module(self):
        """The full set of modules is accepted."""
        parsed = build_param(supportedModules=ALL_MODULES)
        assert len(parsed.supportedModules) == len(PlatformSupportedModules)

    def test_duplicates_are_not_rejected(self):
        """Repeated values pass: nothing here deduplicates or bounds the length.

        Documents a deliberate gap rather than an intended guarantee. A list can
        therefore be longer than the enum. Deduplication is left to the
        validators, which report it with a message aimed at content authors.
        """
        parsed = build_param(supportedModules=["xsiam"] * 3)
        assert len(parsed.supportedModules) == 3

    def test_unknown_module_is_rejected(self):
        """A parameter is held to the same set of values as the pack."""
        with pytest.raises(ValidationError) as exc_info:
            build_param(supportedModules=["not_a_module"])

        assert "not a valid enumeration member" in first_error(exc_info)["msg"]

    def test_empty_list_is_left_to_st113(self):
        """As with the pack, an empty list is reported by ST113 rather than the schema."""
        assert build_param(supportedModules=[]).supportedModules == []
