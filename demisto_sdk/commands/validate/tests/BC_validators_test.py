import pytest

from demisto_sdk.commands.common.constants import GitStatuses, MarketplaceVersions
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
    create_metadata_object,
    create_old_file_pointers,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC100_breaking_backwards_subtype import (
    BreakingBackwardsSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC105_id_changed import (
    IdChangedValidator,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC108_was_marketplace_modified import (
    WasMarketplaceModifiedValidator,
)
from TestSuite.repo import ChangeCWD

ALL_MARKETPLACES = list(MarketplaceVersions)
XSIAM_MARKETPLACE = [ALL_MARKETPLACES[1]]
ALL_MARKETPLACES_FOR_IN_PACK = [marketplace.value for marketplace in ALL_MARKETPLACES]
XSIAM_MARKETPLACE_FOR_IN_PACK = [ALL_MARKETPLACES_FOR_IN_PACK[1]]
XSOAR_MARKETPLACE = [ALL_MARKETPLACES[0]]
XSOAR_MARKETPLACE_FOR_IN_PACK = [ALL_MARKETPLACES_FOR_IN_PACK[0]]


@pytest.mark.parametrize(
    "content_items, old_content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_integration_object(),
            ],
            [create_integration_object(), create_integration_object()],
            1,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo."
            ],
        ),
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_script_object(),
            ],
            [create_integration_object(), create_script_object()],
            1,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo."
            ],
        ),
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_script_object(paths=["subtype"], values=["python2"]),
            ],
            [create_integration_object(), create_script_object()],
            2,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo.",
                "Possible backwards compatibility break, You've changed the Script subtype from python3 to python2, please undo.",
            ],
        ),
        (
            [create_integration_object(), create_script_object()],
            [create_integration_object(), create_script_object()],
            0,
            [],
        ),
    ],
)
def test_BreakingBackwardsSubtypeValidator_is_valid(
    content_items, old_content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items and old_content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has its subtype altered, and two integration with no changes in old_content_items.
        - Case 2: content_items with 1 integration where the first one has its subtype altered and one script with no subtype altered, and old_content_items with one script and integration with no changes.
        - Case 3: content_items with 1 integration where the first one has its subtype altered and 1 script where that has its subtype altered, and old_content_items with one script and integration with no changes.
        - Case 4: content_items and old_content_items with 1 integration and 1 script both with no changes
    When
    - Calling the BreakingBackwardsSubtypeValidator is valid function.
    Then
        - Make sure the right amount of failures return and that the right message is returned.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 integration.
        - Case 3: Should fail both the integration and the script
        - Case 4: Shouldn't fail any content item.
    """
    create_old_file_pointers(content_items, old_content_items)
    results = BreakingBackwardsSubtypeValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_subtype, expected_fix_msg",
    [
        (
            create_integration_object(paths=["script.subtype"], values=["python2"]),
            "python3",
            "Changing subtype back to (python3).",
        ),
        (
            create_script_object(paths=["subtype"], values=["python2"]),
            "python3",
            "Changing subtype back to (python3).",
        ),
    ],
)
def test_BreakingBackwardsSubtypeValidator_fix(
    content_item, expected_subtype, expected_fix_msg
):
    """
    Given
        - content_item.
        - Case 1: an Integration content item where the subtype is different from the subtype of the old_content_item.
        - Case 2: a Script content item where the subtype is different from the subtype of the old_content_item.
    When
    - Calling the BreakingBackwardsSubtypeValidator fix function.
    Then
        - Make sure the the object subtype was changed to match the old_content_item subtype, and that the right fix msg is returned.
    """
    validator = BreakingBackwardsSubtypeValidator()
    validator.old_subtype[content_item.name] = "python3"
    assert validator.fix(content_item).message == expected_fix_msg
    assert content_item.subtype == expected_subtype


@pytest.mark.parametrize(
    "content_items, old_content_items, expected_number_of_failures, old_id, expected_msgs",
    [
        (
            [
                create_integration_object(paths=["commonfields.id"], values=["id_2"]),
                create_integration_object(),
            ],
            [
                create_integration_object(paths=["commonfields.id"], values=["id_1"]),
                create_integration_object(),
            ],
            1,
            {"TestIntegration": "id_1"},
            [
                "ID of content item was changed from id_1 to id_2, please undo.",
            ],
        ),
        (
            [
                create_script_object(paths=["commonfields.id"], values=["id_2"]),
                create_integration_object(),
            ],
            [
                create_script_object(paths=["commonfields.id"], values=["id_1"]),
                create_integration_object(),
            ],
            1,
            {"myScript": "id_1"},
            [
                "ID of content item was changed from id_1 to id_2, please undo.",
            ],
        ),
        (
            [
                create_integration_object(paths=["commonfields.id"], values=["id_2"]),
                create_script_object(paths=["commonfields.id"], values=["id_4"]),
            ],
            [
                create_integration_object(paths=["commonfields.id"], values=["id_1"]),
                create_script_object(paths=["commonfields.id"], values=["id_3"]),
            ],
            2,
            {"TestIntegration": "id_1", "myScript": "id_3"},
            [
                "ID of content item was changed from id_1 to id_2, please undo.",
                "ID of content item was changed from id_3 to id_4, please undo.",
            ],
        ),
        (
            [
                create_integration_object(),
                create_script_object(),
            ],
            [
                create_integration_object(),
                create_script_object(),
            ],
            0,
            {},
            [],
        ),
    ],
)
def test_IdChangedValidator(
    content_items, old_content_items, expected_number_of_failures, old_id, expected_msgs
):
    """
    Given
    content_items and old_content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has its id changed.
        - Case 2: content_items with 1 integration that has its id changed, and one script with no id changed.
        - Case 3: content_items with 1 integration that has its id changed, and one script that has its id changed.
        - Case 4: content_items with 1 integration and 1 script, both with no changes.
    When
    - Calling the IdChangedValidator is valid function.
    Then
        - Make sure the right amount of failures and messages are returned, and that we construct the "old_id" object correctly.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 script.
        - Case 3: Should fail both the integration and the script
        - Case 4: Shouldn't fail any content item.
    """
    create_old_file_pointers(content_items, old_content_items)
    validator = IdChangedValidator()
    results = validator.is_valid(content_items)
    assert validator.old_id == old_id
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_id, expected_fix_msg",
    [
        (
            create_integration_object(paths=["commonfields.id"], values=["id_2"]),
            "id_1",
            "Changing ID back to id_1.",
        ),
        (
            create_script_object(paths=["commonfields.id"], values=["id_2"]),
            "id_1",
            "Changing ID back to id_1.",
        ),
    ],
)
def test_IdChangedValidator_fix(content_item, expected_id, expected_fix_msg):
    """
    Given
        - content_item.
        - Case 1: an Integration content item where its id has changed.
        - Case 2: a Script content item where its id has changed.
    When
    - Calling the IdChangedValidator fix function.
    Then
        - Make sure the the id was changed to match the old_content_item id, and that the right fix message is returned.
    """
    validator = IdChangedValidator()
    validator.old_id[content_item.name] = expected_id
    assert validator.fix(content_item).message == expected_fix_msg
    assert content_item.object_id == expected_id


@pytest.mark.parametrize(
    "old_marketplaces, in_pack_marketplaces",
    [
        (ALL_MARKETPLACES, XSIAM_MARKETPLACE_FOR_IN_PACK),
        (XSIAM_MARKETPLACE, ALL_MARKETPLACES_FOR_IN_PACK),
        (XSIAM_MARKETPLACE, XSIAM_MARKETPLACE_FOR_IN_PACK),
    ],
)
def test_WasMarketplaceModifiedValidator__modified_item_has_only_one_marketplace__passes(
    old_marketplaces, in_pack_marketplaces
):
    """
    Given:
        - Modified `Integration` and `Script` and Old `Integration` and `Script` iterables, each within a pack.
        - Modified `Integration` and `Script` have only `XSIAM` in their level.
        - Case 1: Old `Integration` and `Script` have all marketplaces in their level, and the pack has only `XSIAM`.
        - Case 2: Old `Integration` and `Script` have only `XSIAM`, and the pack has all marketplaces.
        - Case 3: Old `Integration` and `Script` have only `XSIAM`, and the pack has only one marketplace (`XSIAM`).

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should pass the validation since although the user defined only `XSIAM`, the content item will be used only in the `XSIAM` marketplace as defined in the pack level.
        - Case 2: Should pass the validation since the user did not remove any marketplace.
        - Case 3: Should pass the validation since the user did not remove any marketplace.
    """
    modified_content_items = [
        create_integration_object(pack_info={"marketplaces": in_pack_marketplaces}),
        create_script_object(pack_info={"marketplaces": in_pack_marketplaces}),
    ]
    old_content_items = [create_integration_object(), create_script_object()]

    modified_content_items[0].marketplaces = modified_content_items[
        1
    ].marketplaces = XSIAM_MARKETPLACE
    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = old_marketplaces
    create_old_file_pointers(modified_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        assert WasMarketplaceModifiedValidator().is_valid(modified_content_items) == []


@pytest.mark.parametrize(
    "old_marketplaces, in_pack_marketplaces",
    [
        (ALL_MARKETPLACES, ALL_MARKETPLACES_FOR_IN_PACK),
        (XSOAR_MARKETPLACE, ALL_MARKETPLACES_FOR_IN_PACK),
    ],
)
def test_WasMarketplaceModifiedValidator__modified_item_has_only_one_marketplace__fails(
    old_marketplaces, in_pack_marketplaces
):
    """
    Given:
        - Modified `Integration` and `Script` and Old `Integration` and `Script` iterables, each within a pack.
        - Modified `Integration` and `Script` have only `XSIAM` in their level.
        - Case 1: Old `Integration` and `Script` have all marketplaces in their level, and the pack has all marketplaces.
        - Case 2: Old `Integration` and `Script` have only `XSOAR`, and the pack has all marketplaces.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should fail the validation since the user removed marketplaces.
        - Case 2: Should fail the validation since the user replaced one marketplace with a different one.
    """
    modified_content_items = [
        create_integration_object(pack_info={"marketplaces": in_pack_marketplaces}),
        create_script_object(pack_info={"marketplaces": in_pack_marketplaces}),
    ]
    old_content_items = [create_integration_object(), create_script_object()]

    modified_content_items[0].marketplaces = modified_content_items[
        1
    ].marketplaces = XSIAM_MARKETPLACE
    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = old_marketplaces
    create_old_file_pointers(modified_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        results = WasMarketplaceModifiedValidator().is_valid(modified_content_items)
        assert (
            results[0].message
            == "You can't delete current marketplaces or add new ones if doing so will remove existing ones. Please undo the change or request a forced merge."
        )
        assert len(results) == 2


@pytest.mark.parametrize(
    "modified_marketplaces, in_pack_marketplaces",
    [
        (ALL_MARKETPLACES, XSIAM_MARKETPLACE_FOR_IN_PACK),
        (ALL_MARKETPLACES, ALL_MARKETPLACES_FOR_IN_PACK),
    ],
)
def test_WasMarketplaceModifiedValidator__old_item_has_only_one_marketplace__passes(
    modified_marketplaces, in_pack_marketplaces
):
    """
    Given:
        - Modified `Integration` and `Script` and Old `Integration` and `Script` iterables, each within a pack.
        - Old `Integration` and `Script` have only `XSIAM` in their level.
        - Case 1: Modified `Integration` and `Script` have all marketplaces in their level, and the pack has only `XSIAM`.
        - Case 2: Modified `Integration` and `Script` have all marketplaces in their level, and the pack has all marketplaces.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should pass the validation since the user added marketplaces or removed all marketplaces which is equal to adding all marketplaces.
        - Case 2: Should pass the validation since the user added marketplaces or removed all marketplaces which is equal to adding all marketplaces.
    """
    modified_content_items = [
        create_integration_object(pack_info={"marketplaces": in_pack_marketplaces}),
        create_script_object(pack_info={"marketplaces": in_pack_marketplaces}),
    ]
    old_content_items = [create_integration_object(), create_script_object()]

    modified_content_items[0].marketplaces = modified_content_items[
        1
    ].marketplaces = modified_marketplaces
    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = XSIAM_MARKETPLACE
    create_old_file_pointers(modified_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        assert WasMarketplaceModifiedValidator().is_valid(modified_content_items) == []


def test_WasMarketplaceModifiedValidator__old_item_has_only_one_marketplace__fails():
    """
    Given:
        - Modified `Integration` and `Script` and Old `Integration` and `Script` iterables, each within a pack.
        - Old `Integration` and `Script` have only `XSIAM` in their level.
        - Modified `Integration` and `Script` have only `XSOAR`, and the pack has all marketplaces.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Should fail the validation since the user replaced one marketplace with a different one.

    """
    modified_marketplaces = XSOAR_MARKETPLACE
    in_pack_marketplaces = ALL_MARKETPLACES_FOR_IN_PACK

    modified_content_items = [
        create_integration_object(pack_info={"marketplaces": in_pack_marketplaces}),
        create_script_object(pack_info={"marketplaces": in_pack_marketplaces}),
    ]
    old_content_items = [create_integration_object(), create_script_object()]

    modified_content_items[0].marketplaces = modified_content_items[
        1
    ].marketplaces = modified_marketplaces
    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = XSIAM_MARKETPLACE
    create_old_file_pointers(modified_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        results = WasMarketplaceModifiedValidator().is_valid(modified_content_items)
        assert (
            results[0].message
            == "You can't delete current marketplaces or add new ones if doing so will remove existing ones. Please undo the change or request a forced merge."
        )
        assert len(results) == 2


@pytest.mark.parametrize(
    "in_pack_marketplaces",
    [
        (XSIAM_MARKETPLACE_FOR_IN_PACK),
        (ALL_MARKETPLACES_FOR_IN_PACK),
    ],
)
def test_WasMarketplaceModifiedValidator__old_and_modified_items_have_all_marketplace(
    in_pack_marketplaces,
):
    """
    Given:
        - Modified `Integration` and `Script` and Old `Integration` and `Script` iterables, each within a pack.
        - Modified `Integration` and `Script` have all marketplaces in their level.
        - Old `Integration` and `Script` have all marketplaces in their level.
        - Case 1: Pack has only `XSIAM`.
        - Case 2: Pack has all marketplaces.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should pass the validation since the user added marketplaces or removed all marketplaces which is equal to adding all marketplaces.
        - Case 2: Should pass the validation since the user didn't change anything or removed all marketplaces which is equal to adding all marketplaces.
    """

    modified_content_items = [
        create_integration_object(pack_info={"marketplaces": in_pack_marketplaces}),
        create_script_object(pack_info={"marketplaces": in_pack_marketplaces}),
    ]
    old_content_items = [create_integration_object(), create_script_object()]

    create_old_file_pointers(modified_content_items, old_content_items)
    with ChangeCWD(REPO.path):
        assert WasMarketplaceModifiedValidator().is_valid(modified_content_items) == []


@pytest.mark.parametrize(
    "modified_pack, old_pack",
    [
        (ALL_MARKETPLACES, ALL_MARKETPLACES),
        (ALL_MARKETPLACES, XSIAM_MARKETPLACE),
        (XSIAM_MARKETPLACE, XSIAM_MARKETPLACE),
    ],
)
def test_WasMarketplaceModifiedValidator__a_pack_is_modified__passes(
    modified_pack, old_pack
):
    """
    Given:
        - Modified `Pack` and Old `Pack` iterables.
        - Case 1: Modified `Pack` and Old `Pack` have all marketplaces.
        - Case 2: Modified `Pack` has all marketplaces and Old `Pack` has only `XSIAM`.
        - Case 3: Modified `Pack` and Old `Pack` have only `XSIAM`.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should pass the validation since the user didn't change anything or removed all marketplaces which is equal to adding all marketplaces.
        - Case 2: Should pass the validation since the user added marketplaces or removed all marketplaces which is equal to adding all marketplaces.
        - Case 3: Should pass the validation since the user didn't change anything or removed all marketplaces which is equal to adding all marketplaces.
    """
    modified_content_item = [create_metadata_object()]
    old_content_item = [create_metadata_object()]
    modified_content_item[0].marketplaces = modified_pack
    old_content_item[0].marketplaces = old_pack

    create_old_file_pointers(modified_content_item, old_content_item)
    assert WasMarketplaceModifiedValidator().is_valid(modified_content_item) == []


@pytest.mark.parametrize(
    "modified_pack, old_pack",
    [(XSIAM_MARKETPLACE, ALL_MARKETPLACES), (XSIAM_MARKETPLACE, XSOAR_MARKETPLACE)],
)
def test_WasMarketplaceModifiedValidator__a_pack_is_modified__fails(
    modified_pack, old_pack
):
    """
    Given:
        - Modified `Pack` and Old `Pack` iterables.
        - Case 1: Modified `Pack` has only `XSIAM` and Old `Pack` has all marketplaces.
        - Case 2: Modified `Pack` has only `XSIAM` and Old `Pack` has only `XSOAR`.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Case 1: Should fail the validation since the user removed marketplaces.
        - Case 2: Should fail the validation since the user replaced one marketplace with a different one.
    """
    modified_content_item = [create_metadata_object()]
    old_content_item = [create_metadata_object()]
    modified_content_item[0].marketplaces = modified_pack
    old_content_item[0].marketplaces = old_pack

    create_old_file_pointers(modified_content_item, old_content_item)
    results = WasMarketplaceModifiedValidator().is_valid(modified_content_item)
    assert (
        results[0].message
        == "You can't delete current marketplaces or add new ones if doing so will remove existing ones. Please undo the change or request a forced merge."
    )


def test_WasMarketplaceModifiedValidator__renamed__fails():
    """
    Given:
        - Renamed `Integration` and `Script` iterables, each moved into a new pack.
        - Old host-pack hade only `XSOAR` in pack level.
        - renamed host-pack has all marketplaces in pack level.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Should fail the validation since moving to a different pack with less marketplaces is not allowed.

    """
    renamed_content_items = [
        create_integration_object(pack_info={"marketplaces": XSOAR_MARKETPLACE}),
        create_script_object(pack_info={"marketplaces": XSOAR_MARKETPLACE}),
    ]
    renamed_content_items[0].git_status = renamed_content_items[
        1
    ].git_status = GitStatuses.RENAMED
    old_content_items = [create_integration_object(), create_script_object()]

    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = ALL_MARKETPLACES_FOR_IN_PACK
    create_old_file_pointers(renamed_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        results = WasMarketplaceModifiedValidator().is_valid(renamed_content_items)
        assert (
            results[0].message
            == "You can't delete current marketplaces or add new ones if doing so will remove existing ones. Please undo the change or request a forced merge."
        )
        assert len(results) == 2


def test_WasMarketplaceModifiedValidator__renamed__passes():
    """
    Given:
        - Renamed `Integration` and `Script` iterables, each moved into a new pack.
        - Renamed host-pack hade only `XSOAR` in pack level.
        - old host-pack has all marketplaces in pack level.

    When:
        - Calling the `WasMarketplaceModifiedValidator` function.

    Then:
        - The results should be as expected.
        - Should pass the validation since the new host has all marketplaces in pack level.

    """
    renamed_content_items = [
        create_integration_object(
            pack_info={"marketplaces": ALL_MARKETPLACES_FOR_IN_PACK}
        ),
        create_script_object(pack_info={"marketplaces": ALL_MARKETPLACES_FOR_IN_PACK}),
    ]
    renamed_content_items[0].git_status = renamed_content_items[
        1
    ].git_status = GitStatuses.RENAMED
    old_content_items = [create_integration_object(), create_script_object()]

    old_content_items[0].marketplaces = old_content_items[
        1
    ].marketplaces = XSOAR_MARKETPLACE
    create_old_file_pointers(renamed_content_items, old_content_items)

    with ChangeCWD(REPO.path):
        assert WasMarketplaceModifiedValidator().is_valid(renamed_content_items) == []
