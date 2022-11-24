from demisto_sdk.commands.common.hook_validations.content_entity_validator import ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.correlation_rule import CorrelationRuleValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml

GIT_ROOT = git_path()


def test_is_hyphen_exists():
    """
    Given: A modeling rule with mismatch between dataset name of the schema and xif files.
    When: running is_dataset_name_similar.
    Then: Validate that the modeling rule is invalid.
    """
    invalid_correlation_file = f'{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/invalid_correlation_rule.yml'
    invalid_correlation_yaml = get_yaml(invalid_correlation_file)
    structure_validator = StructureValidator(invalid_correlation_file)
    structure_validator.current_file = invalid_correlation_yaml
    content_validator = ContentEntityValidator(structure_validator)
    correlation_rule_validator = CorrelationRuleValidator(content_validator)

    assert not correlation_rule_validator.is_hyphen_exists()
