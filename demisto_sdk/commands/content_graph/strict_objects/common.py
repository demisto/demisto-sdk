from abc import ABC
from typing import Any, Dict, Optional, Sequence

import pydantic
from pydantic import BaseModel, Extra, validator
from pydantic.fields import FieldInfo

from demisto_sdk.commands.common.constants import MarketplaceVersions

marketplace_suffixes = tuple((marketplace.value for marketplace in MarketplaceVersions))


class BaseStrictModel(BaseModel, ABC):
    class Config:
        """
        This is the definition of not allowing extra fields except those defined by the schema.
        """

        extra = Extra.forbid

    @validator("*", pre=True)
    def prevent_none(cls, value, field):
        """
        Validator ensures no None value is entered in a field.
        There is a difference between an empty and missing field.
        Optional means a field can be left out of the schema, but if it does exist, it has to have a value - not None.
        """
        # There is currently an exclusion for all fields which failed this validation on the Content repository
        if field.name not in {
            "default_value",
            "defaultvalue",
            "additional_info",
            "additionalinfo",
            "defaultValue",
            "default",
            "detailed_description",
            "image",
            "default_classifier",
            "display",
            "outputs",
            "predefined",
            "select_values",
            "columns",
            "default_rows",
            "system_associated_types",
            "associated_types",
            "propagation_labels",
            "sort_values",
            "playbook_id",
            "query",
            "playbook_input_query",
            "suppression_duration",  # correlation rules
            "suppression_fields",  # correlation rules
            "user_defined_category",  # correlation rules
            "user_defined_severity",  # correlation rules
            "investigation_query_link",  # correlation rules
            "cron_tab",  # correlation rules
            "search_window",  # correlation rules
            "sort",  # widget
            "params",  # widget
            "cache",  # widget
            "tags",  # modeling rule
            "to_value",  # report
            "from_value",  # report
            "description",  # xsiam_dashboard
            "default_mapping",  # indicator_type
            "manual_mapping",  # indicator_type
            "file_hashes_priority",  # indicator_type
            "legacy_names",  # indicator_type
            "default_template_id",  # xsiam-report
            "breaking_changes_notes",  # release-notes-config
        }:
            # The assertion is caught by pydantic and converted to a pydantic.ValidationError
            assert (
                value is not None
            ), f"The field {field.alias or field.name} is not required, but should not be None if it exists"
        return value


def create_model(model_name: str, base_models: tuple, **kwargs) -> BaseModel:
    """
    Wrapper for pydantic.create_model so type:ignore[call-overload] appears only once.
    """
    return pydantic.create_model(
        __model_name=model_name, __base__=base_models, **kwargs
    )  # type:ignore[call-overload]


def create_dynamic_model(
    field_name: str,
    type_: Any,
    default: Any = ...,
    suffixes: Sequence[str] = marketplace_suffixes,
    alias: Optional[str] = None,
    include_without_suffix: bool = False,
    description: Optional[str] = None,
) -> BaseModel:
    """
    This function creates a sub-model for avoiding duplicate lines of parsing arguments with different suffix.
    (we have fields that are almost identical, except for the suffix.
     for example: description:xsoar, description:marketplacev2, description:xpanse etc.)
    Then the strict models inherit it, thus adding those fields to the root.

    This is a better way than declaring on those fields manually in the root object, in this way:
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    """
    fields = {
        f"{field_name}_{suffix}": (
            type_,
            FieldInfo(
                default,
                alias=f"{alias or field_name}:{suffix}",
                description=description,
            ),
        )
        for suffix in suffixes
    }
    if include_without_suffix:
        fields[field_name] = (
            type_,
            FieldInfo(default, alias=alias or field_name, description=description),
        )

    return create_model(
        model_name=f"Dynamic{field_name.title()}Model",
        base_models=(BaseStrictModel,),
        **fields,
    )


DESCRIPTION_DYNAMIC_MODEL = create_dynamic_model(
    field_name="description",
    type_=Optional[str],
    default=None,
    description="Marketplace-specific description override for this content item. Overrides the base description field for the specified marketplace.",
)
NAME_DYNAMIC_MODEL = create_dynamic_model(
    field_name="name",
    type_=Optional[str],
    default=None,
    description="Marketplace-specific name override for this content item. Overrides the base name field for the specified marketplace.",
)
DEPRECATED_DYNAMIC_MODEL = deprecated_dynamic_model = create_dynamic_model(
    field_name="deprecated",
    type_=Optional[bool],
    default=None,
    description="Marketplace-specific deprecated flag. When True, marks this content item as deprecated for the specified marketplace.",
)
REQUIRED_DYNAMIC_MODEL = create_dynamic_model(
    field_name="required",
    type_=Optional[bool],
    default=None,
    description="Marketplace-specific required flag. When True, this field is required for the specified marketplace.",
)
DEFAULT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="defaultValue",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific default value override. Overrides the base defaultValue for the specified marketplace.",
)
DEFAULT_DYNAMIC_MODEL_LOWER_CASE = create_dynamic_model(
    # field name here defaultvalue vs defaultValue
    field_name="defaultvalue",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific default value override (lowercase variant). Overrides the base defaultvalue for the specified marketplace.",
)
ID_DYNAMIC_MODEL = create_dynamic_model(
    field_name="id",
    type_=Optional[Any],
    default=None,
    include_without_suffix=True,
    description="Unique identifier of this content item. The marketplace-suffixed variants allow different IDs per marketplace.",
)
KEY_DYNAMIC_MODEL = create_dynamic_model(
    field_name="key",
    type_=Optional[str],
    default=None,
    description="Marketplace-specific key override for this field.",
)
VALUE_DYNAMIC_MODEL = create_dynamic_model(
    field_name="value",
    type_=Optional[Any],
    default=None,
    description="Marketplace-specific value override for this field.",
)
PLAYBOOK_INPUT_QUERY_DYNAMIC_MODEL = create_dynamic_model(
    field_name="playbookInputQuery",
    type_=Optional[Any],
    default=None,
    description="Marketplace-specific playbook input query override.",
)
FORM_DYNAMIC_MODEL = create_dynamic_model(
    field_name="form",
    type_=Optional[Dict],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific form configuration override.",
)
MESSAGE_DYNAMIC_MODEL = create_dynamic_model(
    field_name="message",
    type_=Optional[Dict],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific message configuration override.",
)
SCRIPT_ARGUMENTS_LOWER_CASE_DYNAMIC_MODEL = create_dynamic_model(
    field_name="scriptarguments",
    type_=Optional[Dict],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific script arguments override (lowercase variant). Key-value pairs passed to the script.",
)
SCRIPT_ARGUMENTS_UPPER_CASE_DYNAMIC_MODEL = create_dynamic_model(
    field_name="scriptArguments",
    type_=Optional[Dict],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific script arguments override (camelCase variant). Key-value pairs passed to the script.",
)
SCRIPT_ID_DYNAMIC_MODEL = create_dynamic_model(
    field_name="scriptId",
    type_=Optional[str],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific script ID override. References the script to execute for this task.",
)
IS_CONTEXT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="iscontext",
    type_=Optional[bool],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific isContext flag. When True, the value is read from the XSOAR context rather than used as a literal.",
)

QUICK_ACTION_DYNAMIC_MODEL = create_dynamic_model(
    field_name="quickaction",
    type_=Optional[bool],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific quick action flag. When True, this command appears as a quick action in the UI.",
)

HIDDEN_DYNAMIC_MODEL = create_dynamic_model(
    field_name="hidden",
    type_=Optional[bool],
    default=None,
    include_without_suffix=True,
    description="Marketplace-specific hidden flag. When True, this command/field is hidden from the UI for the specified marketplace.",
)


class _LeftOrRight(BaseStrictModel):
    value: Any  # VALUE_DYNAMIC_MODEL doesn't have the raw 'value', only its variations


LeftOrRight = create_model(
    model_name="LeftOrRight",
    base_models=(_LeftOrRight, VALUE_DYNAMIC_MODEL, IS_CONTEXT_DYNAMIC_MODEL),
)

LEFT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="left",
    type_=Optional[LeftOrRight],
    default=None,
    include_without_suffix=True,
)

RIGHT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="right",
    type_=Optional[LeftOrRight],
    default=None,
    include_without_suffix=True,
)

SUFFIXED_ID_DYNAMIC_MODEL = create_dynamic_model(
    # creating here with include_without_suffix == False
    field_name="id",
    type_=Optional[str],
    default=None,
)
