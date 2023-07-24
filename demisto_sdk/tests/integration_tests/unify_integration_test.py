import logging
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.constants import ENV_DEMISTO_SDK_MARKETPLACE
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    DASHBOARD,
    GENERIC_MODULE,
    UNIFIED_GENERIC_MODULE,
)
from TestSuite.test_tools import ChangeCWD

UNIFY_CMD = "unify"


class TestGenericModuleUnifier:
    def test_unify_generic_module(self, mocker, repo):
        """
        Given
        - A pack with a valid generic module, and a dashboard that it's id matches a dashboard in the generic module.

        When
        - Running unify on it.
        - Passing mp flag with marketplacev2

        Then
        - Ensure the module was unified successfully (i.e contains the dashboard's content) and saved successfully
         in the output path.
        - Ensure env was modified to use marketplacev2
        """
        pack = repo.create_pack("PackName")
        pack.create_generic_module("generic-module", GENERIC_MODULE)
        generic_module_path = pack.generic_modules[0].path
        dashboard_copy = DASHBOARD.copy()
        dashboard_copy["id"] = "asset_dashboard"
        pack.create_dashboard("dashboard_1", dashboard_copy)
        saving_path = os.path.join(
            pack._generic_modules_path,
            f'{pack.generic_modules[0].name.rstrip(".json")}_unified.json',
        )
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                main,
                [UNIFY_CMD, "-i", generic_module_path, "-mp", "marketplacev2"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert os.getenv(ENV_DEMISTO_SDK_MARKETPLACE) == "marketplacev2"
        assert os.path.isfile(saving_path)
        with open(saving_path) as f:
            saved_generic_module = json.load(f)
        assert saved_generic_module == UNIFIED_GENERIC_MODULE


class TestParsingRuleUnifier:
    def test_unify_parsing_rule(self, repo, tmpdir):
        """
        Given
        - Content Pack which contains a parsing rule

        When
        - Running unify on it.

        Then
        - Ensure the command runs successfully
        - Ensure the rules are written to the unified YAML as expected
        """
        pack = repo.create_pack()
        pack.create_parsing_rule()

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main,
            [UNIFY_CMD, "-i", pack.parsing_rules[0].path, "-o", tmpdir],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        with open(
            os.path.join(tmpdir, "parsingrule-parsingrule_0.yml")
        ) as unified_rule_file:
            unified_rule = yaml.load(unified_rule_file)
            with open(pack.parsing_rules[0].rules.path) as rules_xif_file:
                assert unified_rule["rules"] == rules_xif_file.read()

    def test_unify_parsing_rule_with_samples(self, repo, tmpdir):
        """
        Given
        - Content Pack which contains a parsing rule and samples

        When
        - Running unify on it.

        Then
        - Ensure the command runs successfully
        - Ensure the rules are written to the unified YAML as expected
        - Ensure the samples are written to the unified YAML as expected
        """
        rule_id = "rule-with-samples"
        sample = {
            "vendor": "somevendor",
            "product": "someproduct",
            "rules": [rule_id],
            "samples": [{"field": "value"}],
        }
        pack = repo.create_pack()
        pack.create_parsing_rule(
            yml={"name": rule_id, "id": rule_id, "rules": "", "samples": ""},
            samples=[sample],
        )

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main,
            [UNIFY_CMD, "-i", pack.parsing_rules[0].path, "-o", tmpdir],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        with open(
            os.path.join(tmpdir, "parsingrule-parsingrule_0.yml")
        ) as unified_rule_file:
            unified_rule = yaml.load(unified_rule_file)
            assert json.loads(unified_rule["samples"]) == {
                f'{sample["vendor"]}_{sample["product"]}': sample["samples"]
            }


class TestModelingRuleUnifier:
    def test_unify_modeling_rule(self, repo, tmpdir):
        """
        Given
        - Content Pack which contains a modeling rule

        When
        - Running unify on it.

        Then
        - Ensure the command runs successfully
        - Ensure the rules are written to the unified YAML as expected
        """
        pack = repo.create_pack()
        pack.create_modeling_rule()

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main,
            [UNIFY_CMD, "-i", pack.modeling_rules[0].path, "-o", tmpdir],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        with open(
            os.path.join(tmpdir, "modelingrule-modelingrule_0.yml")
        ) as unified_rule_file:
            unified_rule = yaml.load(unified_rule_file)
            with open(pack.modeling_rules[0].rules.path) as rules_xif_file:
                assert unified_rule["rules"] == rules_xif_file.read()


class TestIntegrationScriptUnifier:
    @pytest.mark.parametrize("flag", [True, False])
    def test_add_custom_section_flag_integration(self, repo, flag):
        """
        Given:
            - An integration with a name of sample(yml)

        When:
            - Running the Unify command
            first run with -c flag on
            second run without -c flag

        Then:
            - Check that the 'Test' label was added or not to the unified yml
            - make sure the nativeImage was key was added with the native-images.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("dummy-integration")
        integration.create_default_integration()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            if flag:
                runner.invoke(
                    main, [UNIFY_CMD, "-i", f"{integration.path}", "-c", "Test"]
                )
            else:
                runner.invoke(main, [UNIFY_CMD, "-i", f"{integration.path}"])

            with open(
                os.path.join(integration.path, "integration-dummy-integration.yml")
            ) as unified_yml:
                unified_yml_data = yaml.load(unified_yml)
                if flag:
                    assert unified_yml_data.get("name") == "Sample - Test"
                else:
                    assert unified_yml_data.get("name") == "Sample"
                assert unified_yml_data.get("script").get("nativeimage") == [
                    "8.1",
                    "8.2",
                ]

    def test_add_custom_section_flag(self, repo):
        """
        Given:
            - A script with the name sample_script(yml)

        When:
            - running the Unify command with the -c flag

        Then:
            - check that the 'Test' label was appended to the name of the script
            in the unified yml
            - make sure the nativeimage was key was added with the native-images.
        """
        pack = repo.create_pack("PackName")
        script = pack.create_script("dummy-script", "script-code")
        script.create_default_script()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            runner.invoke(main, [UNIFY_CMD, "-i", f"{script.path}", "-c", "Test"])
            with open(
                os.path.join(script.path, "script-dummy-script.yml")
            ) as unified_yml:
                unified_yml_data = yaml.load(unified_yml)
                assert unified_yml_data.get("name") == "sample_scriptTest"
                assert unified_yml_data.get("nativeimage") == ["8.1", "8.2"]

    def test_ignore_native_image_integration(self, repo):
        """
        Given:
            - integration that can use native-images

        When:
            - running the Unify command along with -ini flag

        Then:
            - make sure the nativeimage key is not added to the integration unified yml.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("dummy-integration")
        integration.create_default_integration()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            runner.invoke(main, [UNIFY_CMD, "-i", f"{integration.path}", "-ini"])

            with open(
                os.path.join(integration.path, "integration-dummy-integration.yml")
            ) as unified_yml:
                unified_yml_data = yaml.load(unified_yml)
                assert "nativeimage" not in unified_yml_data.get("script")

    def test_ignore_native_image_script(self, repo):
        """
        Given:
            - script that can use native-images

        When:
            - running the Unify command along with -ini flag

        Then:
            - make sure the nativeImage key is not added to the script unified yml.
        """
        pack = repo.create_pack("PackName")
        script = pack.create_script("dummy-script", "script-code")
        script.create_default_script()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            runner.invoke(main, [UNIFY_CMD, "-i", f"{script.path}", "-ini"])
            with open(
                os.path.join(script.path, "script-dummy-script.yml")
            ) as unified_yml:
                unified_yml_data = yaml.load(unified_yml)
                assert "nativeimage" not in unified_yml_data


class TestLayoutUnifer:
    def test_layout_unify(self, repo, mocker, monkeypatch):
        """
        Given:
            - layout that has 'fromVersion' field and 'toVersion' filed.

        When:
            - running the Unify command along with -ini flag on the layout.

        Then:
            - make sure the 'fromServerVersion' was added
            - make sure the 'toServerVersion' was added
            - make sure the 'fromVersion' was not deleted.
            - make sure the 'toVersion' was not deleted.
            - make sure the 'fromServerVersion' and 'fromVersion' are the same.
            - make sure the 'toVersion' and 'toServerVersion' are the same.
        """
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        pack = repo.create_pack("test")
        layout = pack.create_layoutcontainer(
            name="test",
            content=json.load(
                open(
                    f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/layoutscontainer-test.json"
                )
            ),
        )

        output = "test.json"

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                main, [UNIFY_CMD, "-i", f"{layout.path}", "-o", output]
            )

            assert result.exit_code == 0
            assert not result.exception

            assert logger_warning.call_count == 0
            assert logger_error.call_count == 0

            with open(Path(output).name) as updated_layout:
                layout_data = json.load(updated_layout)
            assert "fromVersion" in layout_data
            assert "fromServerVersion" in layout_data
            assert "toVersion" in layout_data
            assert "toServerVersion" in layout_data

            assert layout_data["fromVersion"] == layout_data["fromServerVersion"]
            assert layout_data["toVersion"] == layout_data["toServerVersion"]
