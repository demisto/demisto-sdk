import glob
import os

import pytest

from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.description import (
    DescriptionValidator,
)
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from TestSuite.test_tools import ChangeCWD


@pytest.mark.parametrize(
    "integration_obj",
    [
        ({"script": {"script": "Here Comes The Script"}, "category": "ok"}),
        ({"deprecated": True, "category": "ok"}),
    ],
)
def test_is_duplicate_description_unified_deprecated_integration(
    mocker, tmp_path, integration_obj
):
    """
    Given:
        - Case A: Content pack with unified integration
        - Case B: Content pack with deprecated integration

    When:
        - Running detailed description validator on the integration

    Then:
        - Ensure validation passes
        - Ensure no warning is printed
    """
    mocker.patch.object(DescriptionValidator, "handle_error")
    integration_dir = (
        tmp_path / "Packs" / "SomePack" / "Integrations" / "SomeIntegration"
    )
    integration_dir.mkdir(parents=True)
    unified_integration_yml = integration_dir / "SomeIntegration.yml"
    yaml.dump(integration_obj, unified_integration_yml.open("w"))
    description_validator = DescriptionValidator(str(unified_integration_yml))
    assert description_validator.is_duplicate_description()
    assert not DescriptionValidator.handle_error.called


def test_is_duplicate_description_given(pack, mocker):
    """
    Given:
        - Description file path

    When:
        - Running detailed description validator on the integration.

    Then:
        - Ensure validation passes
        - Ensure handle error is not called.
    """
    mocker.patch.object(DescriptionValidator, "handle_error")
    integration = pack.create_integration()
    integration.create_default_integration()
    description_validator = DescriptionValidator(integration.description.path)
    assert description_validator.is_duplicate_description()
    assert not DescriptionValidator.handle_error.called


@pytest.mark.parametrize(
    "file_input, result",
    [
        ("### Community Contributed Integration\n### OtherSection", False),
        ("### partner Contributed Integration", False),
        # ("\n### Other section\n- No space", False), TODO reenable after validations enabled
        ("\n### Other section\n", True),
        # ("\n###Other section\n", False),TODO reenable after validations enabled
    ],
)
def test_is_valid_file(integration, file_input, result):
    """
    Given
        - Description file with Contribution details or not
    When
        - Run validate on Description file
    Then
        - Ensure no Contribution details in the file
    """

    with ReadMeValidator.start_mdx_server():
        integration.description.write(file_input)
        description_path = integration.description.path
        with ChangeCWD(integration.repo_path):
            description_validator = DescriptionValidator(description_path)
            answer = description_validator.is_valid_file()

        assert answer == result
        assert description_validator._is_valid == answer


def test_is_valid_description_name(repo):
    """
    Given
        - An integration description with a valid name

    When
        - Validating the integration description name

    Then
        - Ensure that description validator for integration passes.
    """

    pack = repo.create_pack("PackName")

    integration = pack.create_integration("IntName")
    integration.create_default_integration()

    description_validator = DescriptionValidator(integration.description.path)

    assert description_validator.is_valid_description_name()


def test_is_invalid_description_name(repo):
    """
    Given
        - An integration description with invalid name
    When
        - Validating the integration description name
    Then
        - Ensure that description validator for integration failed.
    """

    pack = repo.create_pack("PackName")

    integration = pack.create_integration("IntName")

    description_path = glob.glob(
        os.path.join(os.path.dirname(integration.yml.path), "*_description.md")
    )
    new_name = f'{description_path[0].rsplit("/", 1)[0]}/IntName_desc.md'

    os.rename(description_path[0], new_name)
    with ChangeCWD(repo.path):
        description_validator = DescriptionValidator(integration.description.path)

        assert not description_validator.is_valid_description_name()


def test_is_invalid_description_integration_name(repo):
    """
    Given
        - An integration description with invalid integration name
    When
        - Validating the integration description name
    Then
        - Ensure that description validator for integration failed.
    """

    pack = repo.create_pack("PackName")

    integration = pack.create_integration("IntName")
    new_name = (
        f'{integration.description.path.rsplit("/", 1)[0]}/IntNameTest_description.md'
    )

    os.rename(integration.description.path, new_name)
    with ChangeCWD(repo.path):
        description_validator = DescriptionValidator(new_name)

        assert not description_validator.is_valid_description_name()


def test_demisto_in_description(repo):
    """
    Given
        - An integration description with the word 'Demisto'.

    When
        - Running verify_demisto_in_description_content.

    Then
        - Ensure that the validation fails.
    """

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("IntName")
    integration.create_default_integration()
    integration.description.write(
        "This checks if we have the word Demisto in the description."
    )

    with ChangeCWD(repo.path):
        description_validator = DescriptionValidator(integration.yml.path)

        assert not description_validator.verify_demisto_in_description_content()

        description_validator = DescriptionValidator(integration.description.path)

        assert not description_validator.verify_demisto_in_description_content()


def test_demisto_not_in_description(repo):
    """
    Given
        - An integration description without the word 'Demisto'.

    When
        - Running verify_demisto_in_description_content.

    Then
        - Ensure that the validation passes.
    """

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("IntName")
    integration.create_default_integration()
    integration.description.write(
        "This checks if we have the word XSOAR in the description."
    )

    with ChangeCWD(repo.path):
        description_validator = DescriptionValidator(integration.yml.path)

        assert description_validator.verify_demisto_in_description_content()

        description_validator = DescriptionValidator(integration.description.path)

        assert description_validator.verify_demisto_in_description_content()
