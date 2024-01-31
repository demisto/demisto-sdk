from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.SC_validators import (
    SC109_script_name_is_not_unique_validator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator import (
    DuplicatedScriptNameValidator,
)
from TestSuite.repo import Repo

MP_XSOAR = [MarketplaceVersions.XSOAR.value]
MP_V2 = [MarketplaceVersions.MarketplaceV2.value]
MP_XSOAR_AND_V2 = [
    MarketplaceVersions.XSOAR.value,
    MarketplaceVersions.MarketplaceV2.value,
]


def test_DuplicatedScriptNameValidator_is_valid(mocker, graph_repo: Repo):
    """
    Given
        - A content repo with 8 scripts:
        - 2 scripts (test_alert1, test_incident1) supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert2, test_incident2) not supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert3, test_incident3) supported by MP V2 with SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert4, test_incident4) where only one is supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
    When
        - running DuplicatedScriptNameValidator is_valid function.
    Then
        - Validate that only the first pair of scripts appear in the results, and the rest of the scripts is valid.
    """
    mocker.patch.object(
        SC109_script_name_is_not_unique_validator, "CONTENT_PATH", new=graph_repo.path
    )

    pack = graph_repo.create_pack()

    pack.create_script("test_incident_1").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_1").set_data(marketplaces=MP_XSOAR_AND_V2)

    pack.create_script("test_incident_2").set_data(marketplaces=MP_XSOAR)
    pack.create_script("test_alert_2").set_data(marketplaces=MP_XSOAR)

    pack.create_script("test_incident_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )
    pack.create_script("test_alert_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )

    pack.create_script("test_incident_4").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_4").set_data(marketplaces=MP_XSOAR)

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = DuplicatedScriptNameValidator().is_valid(
        [script.object for script in pack.scripts]
    )

    assert len(results) == 1
    assert "test_alert_1.yml" == results[0].content_object.path.name
