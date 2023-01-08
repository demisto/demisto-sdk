from pathlib import Path

from typer.testing import CliRunner

from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData

ONE_MODEL_RULE_TEXT = """
[MODEL: dataset=fake_fakerson_raw]
alter
    xdm.session_context_id = externalId,
    xdm.observer.action = act,
    xdm.event.outcome = outcome,
    xdm.event.outcome_reason = reason,
    xdm.network.http.method = requestMethod,
    xdm.network.http.url = request,
    xdm.source.host.hostname = devicehostname,
    xdm.source.host.ipv4_addresses = arraycreate(coalesce(src, "")),
    xdm.target.host.ipv4_addresses = arraycreate(coalesce(dst, "")),
    xdm.network.application_protocol_category = cat,
    xdm.network.protocol_layers = arraycreate(coalesce(app, "")),
    xdm.source.user.username = suser,
    xdm.source.zone = spriv,
    xdm.network.http.domain = dhost,
    xdm.network.http.response_code = outcome,
    xdm.target.sent_bytes = to_integer(out),
    xdm.network.http.url_category = cs2,
    xdm.network.http.content_type = contenttype,
    xdm.alert.category = cs4,
    xdm.alert.name = cs5,
    xdm.alert.severity = to_string(cn1),
    xdm.observer.name = _reporting_device_name,
    xdm.source.user_agent = requestClientApplication,
    xdm.target.interface = destinationServiceName,
    xdm.source.ipv4 = sourceTranslatedAddress,
    xdm.event.type = FakeFakersonURLClass,
    xdm.observer.product = _product,
    xdm.observer.vendor = _vendor,
    xdm.target.process.executable.file_type = fileType;
"""
DEFAULT_MODELING_RULE_NAME = "TestModelingRule"
DEFAULT_MODELING_RULE_NAME_2 = "TestModelingRule2"


def test_init_test_data_create(pack):
    """
    Given:
        - A path to a directory of a modeling rule.
        - The number of events to initialize the test data file for.
    When:
        - The test data file does not exist.
    Then:
        - Ensure the test data file is created.
        - Ensure the test data file contains the correct number of events.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
        app as init_test_data_app,
    )

    runner = CliRunner()
    mr = pack.create_modeling_rule(
        DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT
    )
    mr.testdata._file_path.unlink()
    mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
    test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
    assert test_data_file.exists() is False
    count = 1
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count


def test_init_test_data_update_with_unchanged_modeling_rule(pack):
    """
    Given:
        - A path to a directory of a modeling rule.
        - The number of events to initialize the test data file for is greater than what already
            exists in the test data file.
    When:
        - The test data file exists.
    Then:
        - Ensure the test data file contains the correct number of events.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
        app as init_test_data_app,
    )

    runner = CliRunner()
    pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
    mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
    test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
    count = 1
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count
    count = 2
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count


def test_init_test_data_update_with_reduced_modeling_rule(pack):
    """
    Given:
        - A path to a directory of a modeling rule.
        - The number of events to initialize the test data file for is greater than what already
            exists in the test data file.
        - A field have been removed from the modeling rule.
    When:
        - The test data file exists.
        - The modeling rule has changed.
    Then:
        - Ensure fields that no longer exist in the modeling rule are removed from the keys of
            the expected values dictionary for the previously existing events.
        - Ensure the test data file contains the correct number of events.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
        app as init_test_data_app,
    )

    runner = CliRunner()
    pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT)
    mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
    test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
    count = 1
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count

    # verify field exists in the expected values dictionary for test data event 0
    field_to_remove = "xdm.source.user.username"
    assert (
        test_data.data[0].expected_values
        and field_to_remove in test_data.data[0].expected_values
    )
    updated_rule_text = ONE_MODEL_RULE_TEXT.replace(
        f"\n    {field_to_remove} = suser,", ""
    )

    # update the modeling rule with the updated rule text
    with open(mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}.xif", "w") as f:
        f.write(updated_rule_text)

    count = 2
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count
    for test_data_event in test_data.data:
        assert (
            test_data_event.expected_values
            and field_to_remove not in test_data_event.expected_values
        )


def test_init_test_data_update_with_extended_modeling_rule(pack):
    """
    Given:
        - A path to a directory of a modeling rule.
        - The number of events to initialize the test data file for is greater than what already
            exists in the test data file.
        - A field have been added to the modeling rule.
    When:
        - The test data file exists.
        - The modeling rule has changed.
    Then:
        - Ensure the test data file contains the correct number of events.
        - Ensure the new field is added to the expected values dictionary for the previously existing
            events.
    """
    from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
        app as init_test_data_app,
    )

    runner = CliRunner()

    field_to_add = "xdm.source.user.username"
    reduced_rule_text = ONE_MODEL_RULE_TEXT.replace(
        f"\n    {field_to_add} = suser,", ""
    )

    pack.create_modeling_rule(DEFAULT_MODELING_RULE_NAME, rules=reduced_rule_text)
    mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
    test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
    count = 1
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count

    # verify field does not exist in the expected values dictionary for test data event 0
    assert (
        test_data.data[0].expected_values
        and field_to_add not in test_data.data[0].expected_values
    )

    # update the modeling rule with the updated rule text
    with open(mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}.xif", "w") as f:
        f.write(ONE_MODEL_RULE_TEXT)

    count = 2
    result = runner.invoke(
        init_test_data_app, [mrule_dir.as_posix(), f"--count={count}"]
    )
    assert result.exit_code == 0
    assert test_data_file.exists() is True
    test_data = TestData.parse_file(test_data_file.as_posix())
    assert len(test_data.data) == count
    for test_data_event in test_data.data:
        assert (
            test_data_event.expected_values
            and field_to_add in test_data_event.expected_values
        )


class TestInitTestDataMultiInput:
    """Test different multi input scenarios for init test data command."""

    def test_init_test_data_multi_input_all_valid(self, pack):
        """
        Given:
            - Paths to directories of two modeling rules.
            - The number of events to initialize the test data files for.
        When:
            - The test data files do not exist.
            - Both modeling rule directories are valid path inputs.
        Then:
            - Ensure the test data files are created.
            - Ensure the test data files contain the correct number of events.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
            app as init_test_data_app,
        )

        runner = CliRunner()
        mr_1 = pack.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT
        )
        mr_2 = pack.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME_2, rules=ONE_MODEL_RULE_TEXT
        )
        mr_1.testdata._file_path.unlink()
        mr_2.testdata._file_path.unlink()
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        mrule_dir_2 = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME_2)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        test_data_file_2 = mrule_dir_2 / f"{DEFAULT_MODELING_RULE_NAME_2}_testdata.json"
        count = 1
        result = runner.invoke(
            init_test_data_app,
            [mrule_dir.as_posix(), mrule_dir_2.as_posix(), f"--count={count}"],
        )
        assert result.exit_code == 0
        assert test_data_file.exists() is True
        assert test_data_file_2.exists() is True
        test_data = TestData.parse_file(test_data_file.as_posix())
        test_data_2 = TestData.parse_file(test_data_file_2.as_posix())
        assert len(test_data.data) == count
        assert len(test_data_2.data) == count

    def test_init_test_data_multi_input_some_invalid(self, pack):
        """
        Given:
            - Paths to directories of two modeling rules.
            - The number of events to initialize the test data files for.
        When:
            - The test data files do not exist.
            - The first modeling rule directory is an invalid path input.
            - The second modeling rule directory is a valid path input.
        Then:
            - Ensure the test data file for the second modeling rule directory is created.
            - Ensure the test data file contain the correct number of events.
            - Ensure the command returns a non-zero exit code.
        """
        from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
            app as init_test_data_app,
        )

        runner = CliRunner()
        mr_1 = pack.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME, rules=ONE_MODEL_RULE_TEXT
        )
        mr_2 = pack.create_modeling_rule(
            DEFAULT_MODELING_RULE_NAME_2, rules=ONE_MODEL_RULE_TEXT
        )
        mr_1.testdata._file_path.unlink()
        mr_2.testdata._file_path.unlink()
        mrule_dir = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME)
        mrule_dir_2 = Path(pack._modeling_rules_path / DEFAULT_MODELING_RULE_NAME_2)
        test_data_file = mrule_dir / f"{DEFAULT_MODELING_RULE_NAME}_testdata.json"
        test_data_file_2 = mrule_dir_2 / f"{DEFAULT_MODELING_RULE_NAME_2}_testdata.json"
        count = 1
        result = runner.invoke(
            init_test_data_app, [pack.path, mrule_dir.as_posix(), f"--count={count}"]
        )
        assert result.exit_code != 0
        assert test_data_file.exists() is True
        assert test_data_file_2.exists() is False
        test_data = TestData.parse_file(test_data_file.as_posix())
        assert len(test_data.data) == count
