from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    CONNECTION, DASHBOARD, INCIDENT_FIELD, INCIDENT_TYPE, INDICATOR_FIELD,
    LAYOUT, LAYOUTS_CONTAINER, MAPPER, NEW_CLASSIFIER, OLD_CLASSIFIER, REPORT,
    REPUTATION, WIDGET)
from TestSuite.test_tools import ChangeCWD

VALIDATE_CMD = "validate"
TEST_FILES_PATH = join(git_path(), 'demisto_sdk', 'tests', 'test_files')
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, 'content_repo_example', 'Packs', 'FeedAzure')
AZURE_FEED_INVALID_PACK_PATH = join(TEST_FILES_PATH, 'content_repo_example', 'Packs', 'FeedAzureab')
VALID_PACK_PATH = join(TEST_FILES_PATH, 'content_repo_example', 'Packs', 'FeedAzureValid')
VALID_PLAYBOOK_FILE_PATH = join(TEST_FILES_PATH, 'Packs', 'CortexXDR', 'Playbooks', 'Cortex_XDR_Incident_Handling.yml')
INVALID_PLAYBOOK_FILE_PATH = join(TEST_FILES_PATH, 'Packs', 'CortexXDR', 'Playbooks',
                                  'Cortex_XDR_Incident_Handling_invalid.yml')
VALID_SCRIPT_PATH = join(TEST_FILES_PATH, 'Packs', 'CortexXDR', 'Scripts', 'EntryWidgetNumberHostsXDR',
                         'EntryWidgetNumberHostsXDR.yml')

CONF_JSON_MOCK = {
    "tests": [
        {
            "integrations": "AzureFeed",
            "playbookID": "AzureFeed - Test"
        }
    ]
}


class TestIncidentFieldValidation:
    def test_valid_incident_field(self, mocker, repo):
        """
        Given
        - Valid `city` incident field.

        When
        - Running validation on it.

        Then
        - Ensure validation passes.
        - Ensure success validation message is printed.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        pack.create_incident_field("incident-field", INCIDENT_FIELD)
        incident_field_path = pack.incident_fields[0].path
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', incident_field_path], catch_exceptions=False)
        assert f'Validating {incident_field_path} as incidentfield' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_incident_field(self, mocker, repo):
        """
        Given
        - invalid incident field - system field set to true.

        When
        - Running validation on it.

        Then
        - Ensure validation fails on IF102 - wrong system field value.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        incident_field_copy = INCIDENT_FIELD.copy()
        incident_field_copy['system'] = True
        pack.create_incident_field("incident-field", incident_field_copy)
        incident_field_path = pack.incident_fields[0].path
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', incident_field_path], catch_exceptions=False)
        assert result.exit_code == 1
        assert f"Validating {incident_field_path} as incidentfield" in result.stdout
        assert 'IF102' in result.stdout
        assert "The system key must be set to False" in result.stdout


class TestIntegrationValidation:
    def test_valid_integration(self, mocker, repo):
        """
        Given
        - a valid Integration.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as an integration.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        valid_integration_yml = get_yaml(pack_integration_path)
        integration = pack.create_integration(yml=valid_integration_yml)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', integration.yml_path, '--no-docker-checks'],
                                   catch_exceptions=False)
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_integration(self, mocker, repo):
        """
        Given
        - an invalid Integration - no fromversion though it is a feed.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on IN119 - wrong fromversion in feed integration.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        pack = repo.create_pack('PackName')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        invalid_integration_yml = get_yaml(pack_integration_path)
        del invalid_integration_yml['fromversion']
        integration = pack.create_integration(yml=invalid_integration_yml)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', integration.yml_path, '--no-docker-checks'],
                                   catch_exceptions=False)
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert 'IN119' in result.stdout
        assert 'This is a feed and has wrong fromversion.' in result.stdout
        assert result.exit_code == 1

    def test_negative__non_latest_docker_image(self):
        """
        Given
        - FeedAzure integration with non-latest docker image.

        When
        - Running validation on it.

        Then
        - Ensure validation fails.
        - Ensure failure message on non-latest docker image.
        """
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", pack_integration_path, "--no-conf-json"])

        assert result.exit_code == 1
        assert f"Validating {pack_integration_path} as integration" in result.stdout
        assert "The docker image tag is not the latest numeric tag, please update it" in result.stdout
        assert "You can check for the most updated version of demisto/python3 here:" in result.stdout
        assert result.stderr == ""

    def test_negative__hidden_param(self):
        """
        Given
        - Integration with not allowed hidden params: ["server", "credentials"].

        When
        - Running validation on it.

        Then
        - Ensure validation fails.
        - Ensure failure message on hidden params.
        """
        integration_path = join(TEST_FILES_PATH, 'integration-invalid-no-hidden-params.yml')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", integration_path, "--no-conf-json"])
        assert result.exit_code == 1
        assert f"Validating {integration_path} as integration" in result.stdout
        assert "can't be hidden. Please remove this field" in result.stdout
        assert result.stderr == ""

    def test_positive__hidden_param(self):
        """
        Given
        - Integration with allowed hidden param: "longRunning".

        When
        - Running validation on it.

        Then
        - Ensure validation succeeds.
        """
        integration_path = join(TEST_FILES_PATH, 'integration-valid-no-unallowed-hidden-params.yml')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", integration_path, "--no-conf-json"])
        assert f"Validating {integration_path} as integration" in result.stdout
        assert "can't be hidden. Please remove this field" not in result.stdout
        assert result.stderr == ""


class TestPackValidation:
    def test_integration_validate_pack_positive(self, mocker):
        """
        Given
        - FeedAzure integration valid Pack.

        When
        - Running validation on the pack.

        Then
        - See that the validation succeed.
        """
        mocker.patch.object(ContentEntityValidator, '_load_conf_file', return_value=CONF_JSON_MOCK)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", VALID_PACK_PATH, "--no-conf-json"])
        assert f"{VALID_PACK_PATH} unique pack files" in result.stdout
        assert f"Validating pack {VALID_PACK_PATH}" in result.stdout
        assert f"{VALID_PACK_PATH}/Integrations/FeedAzureValid/FeedAzureValid.yml" in result.stdout
        assert f"{VALID_PACK_PATH}/IncidentFields/incidentfield-city.json" in result.stdout
        assert "The files are valid" in result.stdout
        assert result.stderr == ""

    def test_integration_validate_pack_negative(self, mocker):
        """
        Given
        - FeedAzure integration invalid Pack with invalid playbook that has unhandled conditional task.

        When
        - Running validation on the pack.

        Then
        - Ensure validation fails.
        - Ensure error message regarding unhandled conditional task in playbook.
        """
        mocker.patch.object(ContentEntityValidator, '_load_conf_file', return_value=CONF_JSON_MOCK)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_PACK_PATH, "--no-conf-json"])

        assert f'{AZURE_FEED_PACK_PATH}' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/IncidentFields/incidentfield-city.json' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/Integrations/FeedAzure/FeedAzure.yml' in result.output
        assert 'Playbook conditional task with id:15 has an unhandled condition: MAYBE' in result.output
        assert "The files were found as invalid, the exact error message can be located above" in result.stdout
        assert result.stderr == ""

    def test_integration_validate_invalid_pack_path(self):
        """
        Given
        - FeedAzure integration invalid Pack path.

        When
        - Running validation on the pack.

        Then
        - See that the validation failed.
        """
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_INVALID_PACK_PATH])
        assert result.exit_code == 1
        assert f'{AZURE_FEED_INVALID_PACK_PATH} was not found' in result.output
        assert result.stderr == ""


class TestClassifierValidation:

    def test_valid_new_classifier(self, mocker, repo):
        """
        Given
        - Valid new classifier

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert result.exit_code == 0
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'The files are valid' in result.stdout

    def test_invalid_from_version_in_new_classifiers(self, mocker, repo):
        """
        Given
        - New classifier with invalid from version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        new_classifier_copy['fromVersion'] = '5.0.0'

        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'fromVersion field in new classifiers needs to be higher or equal to 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_invalid_to_version_in_new_classifiers(self, mocker, repo):
        """
        Given
        - New classifier with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        new_classifier_copy['toVersion'] = '5.0.0'
        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'toVersion field in new classifiers needs to be higher than 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_classifier_from_version_higher_to_version(self, mocker, repo):
        """
        Given
        - New classifier with from version field higher than to version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        new_classifier_copy['toVersion'] = '6.0.2'
        new_classifier_copy['fromVersion'] = '6.0.5'
        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'fromVersion field can not be higher than toVersion field' in result.stdout
        assert result.exit_code == 1

    def test_missing_mandatory_field_in_new_classifier(self, mocker, repo):
        """
        Given
        - New classifier with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        del new_classifier_copy['id']
        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'Missing id in root' in result.stdout
        assert result.exit_code == 1

    def test_missing_fromversion_field_in_new_classifier(self, mocker, repo):
        """
        Given
        - New classifier with missing from version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        del new_classifier_copy['fromVersion']
        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'Must have fromVersion field in new classifiers' in result.stdout

    def test_invalid_type_in_new_classifier(self, mocker, repo):
        """
        Given
        - New classifier with invalid type field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        new_classifier_copy = NEW_CLASSIFIER.copy()
        new_classifier_copy['type'] = 'test'
        classifier = pack.create_classifier('new_classifier', new_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier" in result.stdout
        assert 'Classifiers type must be classification' in result.stdout
        assert result.exit_code == 1

    def test_valid_old_classifier(self, mocker, repo):
        """
        Given
        - Valid old classifier

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert result.exit_code == 0
        assert f"Validating {classifier.path} as classifier_5_9_9" in result.stdout
        assert 'The files are valid' in result.stdout

    def test_invalid_from_version_in_old_classifiers(self, mocker, repo):
        """
        Given
        - Old classifier with invalid from version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        old_classifier_copy = OLD_CLASSIFIER.copy()
        old_classifier_copy['fromVersion'] = '6.0.0'
        classifier = pack.create_classifier('old_classifier', old_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier_5_9_9" in result.stdout
        assert 'fromVersion field in old classifiers needs to be lower than 6.0.0' in result.stdout

    def test_invalid_to_version_in_old_classifiers(self, mocker, repo):
        """
        Given
        - Old classifier with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        old_classifier_copy = OLD_CLASSIFIER.copy()
        old_classifier_copy['toVersion'] = '6.0.0'
        classifier = pack.create_classifier('old_classifier', old_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier_5_9_9" in result.stdout
        assert 'toVersion field in old classifiers needs to be lower than 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_missing_mandatory_field_in_old_classifier(self, mocker, repo):
        """
        Given
        - Old classifier with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        old_classifier_copy = OLD_CLASSIFIER.copy()
        del old_classifier_copy['id']
        classifier = pack.create_classifier('old_classifier', old_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier_5_9_9" in result.stdout
        assert 'Missing id in root' in result.stdout
        assert result.exit_code == 1

    def test_missing_toversion_field_in_old_classifier(self, mocker, repo):
        """
        Given
        - Old classifier with missing from version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        old_classifier_copy = OLD_CLASSIFIER.copy()
        del old_classifier_copy['toVersion']
        classifier = pack.create_classifier('old_classifier', old_classifier_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert f"Validating {classifier.path} as classifier_5_9_9" in result.stdout
        assert 'Must have toVersion field in old classifiers' in result.stdout
        assert result.exit_code == 1


class TestMapperValidation:

    def test_valid_mapper(self, mocker, repo):
        """
        Given
        - Valid mapper

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_from_version_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with invalid from version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper_copy = MAPPER.copy()
        mapper_copy['fromVersion'] = '5.0.0'
        mapper = pack.create_mapper('mapper', mapper_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'fromVersion field in mapper needs to be higher or equal to 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_invalid_to_version_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper_copy = MAPPER.copy()
        mapper_copy['toVersion'] = '5.0.0'
        mapper = pack.create_mapper('mapper', mapper_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'toVersion field in mapper needs to be higher than 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_missing_mandatory_field_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper_copy = MAPPER.copy()
        del mapper_copy['id']
        mapper = pack.create_mapper('mapper', mapper_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'Missing id in root' in result.stdout
        assert result.exit_code == 1

    def test_mapper_from_version_higher_to_version(self, mocker, repo):
        """
        Given
        - Mapper with from version field higher than to version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper_copy = MAPPER.copy()
        mapper_copy['toVersion'] = '6.0.2'
        mapper_copy['fromVersion'] = '6.0.5'
        mapper = pack.create_mapper('mapper', mapper_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'fromVersion field can not be higher than toVersion field' in result.stdout
        assert result.exit_code == 1

    def test_invalid_mapper_type(self, mocker, repo):
        """
        Given
        - Mapper with invalid type.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper_copy = MAPPER.copy()
        mapper_copy['type'] = 'test'
        mapper = pack.create_mapper('mapper', mapper_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert f"Validating {mapper.path} as mapper" in result.stdout
        assert 'Mappers type must be mapping-incoming or mapping-outgoing' in result.stdout
        assert result.exit_code == 1


class TestDashboardValidation:
    def test_valid_dashboard(self, mocker, repo):
        """
        Given
        - a valid Dashboard.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a dashboard.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        dashboard = pack.create_dashboard('dashboard', DASHBOARD)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', dashboard.path], catch_exceptions=False)
        assert f'Validating {dashboard.path} as dashboard' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_dashboard(self, mocker, repo):
        """
        Given
        - an invalid dashboard (wrong version).

        When
        - Running validate on it.

        Then
        - Ensure validate fails on - BA100 wrong version error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        dashboard_copy = DASHBOARD.copy()
        dashboard_copy['version'] = 1
        dashboard = pack.create_dashboard('dashboard', dashboard_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', dashboard.path], catch_exceptions=False)
        assert f'Validating {dashboard.path} as dashboard' in result.stdout
        assert 'BA100' in result.stdout
        assert "The version for our files should always be -1, please update the file." in result.stdout
        assert result.exit_code == 1


class TestConnectionValidation:
    def test_valid_connection(self, mocker, repo):
        """
        Given
        - a valid Connection.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a connection.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        connection = pack._create_json_based(name='connection', prefix='', content=CONNECTION)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', connection.path], catch_exceptions=False)
        assert f'Validating {connection.path} as canvas-context-connections' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_connection(self, mocker, repo):
        """
        Given
        - an invalid Connection - no contextKey1 in a connection.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on missing contextKey1.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        connection_copy = CONNECTION.copy()
        del connection_copy['canvasContextConnections'][0]['contextKey1']
        connection = pack._create_json_based(name='connection', prefix='', content=connection_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', connection.path], catch_exceptions=False)
        assert f'Validating {connection.path} as canvas-context-connections' in result.stdout
        assert 'Missing contextKey1' in result.stdout
        assert result.exit_code == 1


class TestIndicatorFieldValidation:
    def test_valid_indicator_field(self, mocker, repo):
        """
        Given
        - a valid Indicator Field.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as an indicator field.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        pack.create_indicator_field("indicator-field", INDICATOR_FIELD)
        indicator_field_path = pack.indicator_fields[0].path
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', indicator_field_path], catch_exceptions=False)
        assert f'Validating {indicator_field_path} as indicatorfield' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_indicator_field(self, mocker, repo):
        """
        Given
        - an invalid Indicator Field - content key set to False.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on IF101 wrong content key value error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        indicator_field_copy = INDICATOR_FIELD.copy()
        indicator_field_copy['content'] = False
        pack.create_indicator_field("indicator-field", indicator_field_copy)
        indicator_field_path = pack.indicator_fields[0].path
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', indicator_field_path], catch_exceptions=False)
        assert f'Validating {indicator_field_path} as indicatorfield' in result.stdout
        assert 'IF101' in result.stdout
        assert 'The content key must be set to True.' in result.stdout
        assert result.exit_code == 1


class TestIncidentTypeValidation:
    def test_valid_incident_type(self, mocker, repo):
        """
        Given
        - a valid Incident Type.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as an incident type.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        incident_type = pack.create_incident_type('incident_type', INCIDENT_TYPE)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', incident_type.path], catch_exceptions=False)
        assert f'Validating {incident_type.path} as incidenttype' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_incident_type(self, mocker, repo):
        """
        Given
        - an invalid Incident Type - days field has a negative number in it.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on IT100 wrong integer value in field.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        incident_type_copy = INCIDENT_TYPE.copy()
        incident_type_copy['days'] = -1
        incident_type = pack.create_incident_type('incident_type', incident_type_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', incident_type.path], catch_exceptions=False)
        assert f'Validating {incident_type.path} as incidenttype' in result.stdout
        assert 'IT100' in result.stdout
        assert 'The field days needs to be a positive integer' in result.stdout
        assert result.exit_code == 1


class TestLayoutValidation:
    def test_valid_layout(self, mocker, repo):
        """
        Given
        - a valid Layout.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a layout.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layout = pack._create_json_based(name='layout', prefix='', content=LAYOUT)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layout.path], catch_exceptions=False)
        assert f'Validating {layout.path} as layout' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_layout(self, mocker, repo):
        """
        Given
        - an invalid layout (wrong version).

        When
        - Running validate on it.

        Then
        - Ensure validate fails on - BA100 wrong version error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layout_copy = LAYOUT.copy()
        layout_copy['version'] = 2
        layout = pack._create_json_based(name='layout', prefix='', content=layout_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layout.path], catch_exceptions=False)
        assert f'Validating {layout.path} as layout' in result.stdout
        assert 'BA100' in result.stdout
        assert 'The version for our files should always be -1, please update the file.' in result.stdout
        assert result.exit_code == 1

    def test_valid_layoutscontainer(self, mocker, repo):
        """
        Given
        - a valid Layout_Container.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a layout.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layout = pack._create_json_based(name='layoutscontainer', prefix='', content=LAYOUTS_CONTAINER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layout.path], catch_exceptions=False)
        assert f'Validating {layout.path} as layoutscontainer' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_layoutscontainer(self, mocker, repo):
        """
        Given
        - an invalid Layout_Container (wrong version).

        When
        - Running validate on it.

        Then
        - Ensure validate fails on - BA100 wrong version error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layout_copy = LAYOUTS_CONTAINER.copy()
        layout_copy['version'] = 2
        layout = pack._create_json_based(name='layoutscontainer', prefix='', content=layout_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layout.path], catch_exceptions=False)
        assert f'Validating {layout.path} as layoutscontainer' in result.stdout
        assert 'BA100' in result.stdout
        assert 'The version for our files should always be -1, please update the file.' in result.stdout
        assert result.exit_code == 1

    def test_invalid_from_version_in_layoutscontaier(self, mocker, repo):
        """
        Given
        - Layout_container with invalid from version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layoutscontainer_copy = LAYOUTS_CONTAINER.copy()
        layoutscontainer_copy['fromVersion'] = '5.0.0'

        layoutscontainer = pack._create_json_based(name='layoutscontainer', prefix='', content=layoutscontainer_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layoutscontainer.path], catch_exceptions=False)
        assert f"Validating {layoutscontainer.path} as layoutscontainer" in result.stdout
        assert 'fromVersion field in layoutscontainer needs to be higher or equal to 6.0.0' in result.stdout
        assert result.exit_code == 1

    def test_invalid_to_version_in_layout(self, mocker, repo):
        """
        Given
        - Layout_container with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        layout_copy = LAYOUT.copy()
        layout_copy['toVersion'] = '6.0.0'

        layout = pack._create_json_based(name='layout', prefix='', content=layout_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', layout.path], catch_exceptions=False)
        assert f"Validating {layout.path} as layout" in result.stdout
        assert 'toVersion field in layout needs to be lower than 6.0.0' in result.stdout
        assert result.exit_code == 1


class TestPlaybookValidation:
    def test_valid_playbook(self, mocker):
        """
        Given
        - a valid Playbook.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a playbook.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, '-i', VALID_PLAYBOOK_FILE_PATH], catch_exceptions=False)
        assert f'Validating {VALID_PLAYBOOK_FILE_PATH} as playbook' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_playbook(self, mocker):
        """
        Given
        - an invalid Playbook - root task is disconnected from next task.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on PB103 - unconnected tasks error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, '-i', INVALID_PLAYBOOK_FILE_PATH], catch_exceptions=False)
        assert f'Validating {INVALID_PLAYBOOK_FILE_PATH} as playbook' in result.stdout
        assert 'PB103' in result.stdout
        assert 'The following tasks ids have no previous tasks: {\'5\'}' in result.stdout
        assert result.exit_code == 1


class TestReportValidation:
    def test_valid_report(self, mocker, repo):
        """
        Given
        - a valid Report.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a report.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        report = pack._create_json_based(name='report', prefix='', content=REPORT)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', report.path], catch_exceptions=False)
        assert f'Validating {report.path} as report' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_report(self, mocker, repo):
        """
        Given
        - an invalid Report - illegal value in orientation field.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on wrong orientation value.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        report_copy = REPORT.copy()
        report_copy['orientation'] = 'bla'
        report = pack._create_json_based(name='report', prefix='', content=report_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', report.path], catch_exceptions=False)
        assert f'Validating {report.path} as report' in result.stdout
        assert 'Enum \'bla\' does not exist. Path: \'/orientation\'' in result.stdout
        assert result.exit_code == 1


class TestReputationValidation:
    def test_valid_reputation(self, mocker, repo):
        """
        Given
        - a valid Reputation.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a reputation.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        reputation = pack._create_json_based(name='reputation', prefix='', content=REPUTATION)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', reputation.path], catch_exceptions=False)
        assert f'Validating {reputation.path} as reputation' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_reputation(self, mocker, repo):
        """
        Given
        - an invalid Reputation - negative integer in expiration field.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on RP101 - wrong value in expiration field.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        reputation_copy = REPUTATION.copy()
        reputation_copy['expiration'] = -1
        reputation = pack._create_json_based(name='reputation', prefix='', content=reputation_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', reputation.path], catch_exceptions=False)
        assert f'Validating {reputation.path} as reputation' in result.stdout
        assert 'RP101' in result.stdout
        assert 'Expiration field should have a positive numeric value.' in result.stdout
        assert result.exit_code == 1


class TestScriptValidation:
    def test_valid_script(self, mocker, repo):
        """
        Given
        - a valid Script.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a script.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        valid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        script = pack.create_script(yml=valid_script_yml)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', script.yml_path, '--no-docker-checks'],
                                   catch_exceptions=False)
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_script(self, mocker, repo):
        """
        Given
        - an invalid Script - v2 in name instead  of V2.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on SC100 wrong v2 format in name.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        pack = repo.create_pack('PackName')
        invalid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        invalid_script_yml['name'] = invalid_script_yml['name'] + "_v2"
        script = pack.create_script(yml=invalid_script_yml)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', script.yml_path, '--no-docker-checks'],
                                   catch_exceptions=False)
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'SC100' in result.stdout
        assert 'The name of this v2 script is incorrect' in result.stdout
        assert result.exit_code == 1


class TestWidgetValidation:
    def test_valid_widget(self, mocker, repo):
        """
        Given
        - a valid Widget.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as a widget.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        widget = pack._create_json_based(name='widget', prefix='', content=WIDGET)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', widget.path], catch_exceptions=False)
        assert f'Validating {widget.path} as widget' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_widget(self, mocker, repo):
        """
        Given
        - an invalid widget (wrong version).

        When
        - Running validate on it.

        Then
        - Ensure validate fails on - BA100 wrong version error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        widget_copy = WIDGET.copy()
        widget_copy['version'] = 1
        widget = pack._create_json_based(name='widget', prefix='', content=widget_copy)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', widget.path], catch_exceptions=False)
        assert f'Validating {widget.path} as widget' in result.stdout
        assert 'BA100' in result.stdout
        assert 'The version for our files should always be -1, please update the file.' in result.stdout
        assert result.exit_code == 1


class TestImageValidation:
    def test_valid_image(self, mocker, repo):
        """
        Given
        - a valid Image.

        When
        - Running validate on it.

        Then
        - Ensure validate passes and identifies the file as an image.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        pack = repo.create_pack('PackName')
        integration = pack.create_integration()
        image_path = integration.image.path
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', image_path], catch_exceptions=False)
        assert f'Validating {image_path} as image' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_invalid_image(self, mocker, repo):
        """
        Given
        - The default image.

        When
        - Running validate on it.

        Then
        - Ensure validate fails on error IM106 - default image error.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        pack = repo.create_pack('PackName')
        integration = pack.create_integration()
        image_path = integration.image.path
        mocker.patch.object(ImageValidator, 'load_image', return_value=DEFAULT_IMAGE_BASE64)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', image_path], catch_exceptions=False)
        assert f'Validating {image_path} as image' in result.stdout
        assert 'IM106' in result.stdout
        assert 'This is the default image, please change to the integration image.' in result.stdout
        assert result.exit_code == 1


class TestAllFilesValidator:
    def test_all_files_valid(self, mocker, repo):
        """
        Given
        - A valid repo.

        When
        - Running validate on it.

        Then
        - Ensure validate passes on all files.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_unique_files', return_value='')
        mocker.patch.object(ValidateManager, 'validate_readme', return_value=True)
        pack1 = repo.create_pack('PackName1')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        valid_integration_yml = get_yaml(pack_integration_path)
        integration = pack1.create_integration(yml=valid_integration_yml)
        incident_field = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        dashboard = pack1.create_dashboard('dashboard', content=DASHBOARD)

        valid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        pack2 = repo.create_pack('PackName2')
        script = pack2.create_script(yml=valid_script_yml)

        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-a', '--no-docker-checks', '--no-conf-json'],
                                   catch_exceptions=False)

        assert 'Validating all files' in result.stdout
        assert 'Validating Packs/PackName1 unique pack files' in result.stdout
        assert 'Validating Packs/PackName2 unique pack files' in result.stdout
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert f'Validating {incident_field.get_path_from_pack()} as incidentfield' in result.stdout
        assert f'Validating {dashboard.get_path_from_pack()} as dashboard' in result.stdout
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_not_all_files_valid(self, mocker, repo):
        """
        Given
        - An invalid repo.

        When
        - Running validate on it.

        Then
        - Ensure validate fails.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_unique_files', return_value='')
        mocker.patch.object(ValidateManager, 'validate_readme', return_value=True)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        pack1 = repo.create_pack('PackName1')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        valid_integration_yml = get_yaml(pack_integration_path)
        integration = pack1.create_integration(yml=valid_integration_yml)
        incident_field_copy = INCIDENT_FIELD.copy()
        incident_field_copy['content'] = False
        incident_field = pack1.create_incident_field('incident-field', content=incident_field_copy)
        dashboard = pack1.create_dashboard('dashboard', content=DASHBOARD)

        invalid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        invalid_script_yml['name'] = invalid_script_yml['name'] + "_v2"
        pack2 = repo.create_pack('PackName2')
        script = pack2.create_script(yml=invalid_script_yml)

        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-a', '--no-docker-checks', '--no-conf-json'],
                                   catch_exceptions=False)

        assert 'Validating all files' in result.stdout
        assert 'Validating Packs/PackName1 unique pack files' in result.stdout
        assert 'Validating Packs/PackName2 unique pack files' in result.stdout
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert f'Validating {incident_field.get_path_from_pack()} as incidentfield' in result.stdout
        assert f'Validating {dashboard.get_path_from_pack()} as dashboard' in result.stdout
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'IF101' in result.stdout
        assert 'The content key must be set to True.' in result.stdout
        assert 'SC100' in result.stdout
        assert 'The name of this v2 script is incorrect' in result.stdout
        assert result.exit_code == 1


class TestValidationUsingGit:
    def test_passing_validation_using_git(self, mocker, repo):
        """
        Given
        - A valid repo.

        When
        - Running validate using git on it.

        Then
        - Ensure validate passes on all files.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_unique_files', return_value='')
        pack1 = repo.create_pack('PackName1')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        valid_integration_yml = get_yaml(pack_integration_path)
        integration = pack1.create_integration(yml=valid_integration_yml)
        incident_field = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        dashboard = pack1.create_dashboard('dashboard', content=DASHBOARD)

        valid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        pack2 = repo.create_pack('PackName2')
        script = pack2.create_script(yml=valid_script_yml)

        modified_files = {integration.yml_path, incident_field.get_path_from_pack()}
        added_files = {dashboard.get_path_from_pack(), script.yml_path}
        mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
        mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, added_files,
                                                                                           set(), set(), set()))

        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-g', '--no-docker-checks', '--no-conf-json',
                                          '--skip-pack-release-notes'],
                                   catch_exceptions=False)
        assert 'Running validation on branch' in result.stdout
        assert 'Running validation on modified files' in result.stdout
        assert 'Running validation on newly added files' in result.stdout
        assert 'Running validation on changed pack unique files' in result.stdout
        assert 'Validating Packs/PackName1 unique pack files' in result.stdout
        assert 'Validating Packs/PackName2 unique pack files' in result.stdout
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert f'Validating {incident_field.get_path_from_pack()} as incidentfield' in result.stdout
        assert f'Validating {dashboard.get_path_from_pack()} as dashboard' in result.stdout
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'The files are valid' in result.stdout
        assert result.exit_code == 0

    def test_failing_validation_using_git(self, mocker, repo):
        """
        Given
        - An invalid repo.

        When
        - Running validate using git on it.

        Then
        - Ensure validate fails.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_unique_files', return_value='')
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        pack1 = repo.create_pack('PackName1')
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        valid_integration_yml = get_yaml(pack_integration_path)
        integration = pack1.create_integration(yml=valid_integration_yml)
        incident_field_copy = INCIDENT_FIELD.copy()
        incident_field_copy['content'] = False
        incident_field = pack1.create_incident_field('incident-field', content=incident_field_copy)
        dashboard = pack1.create_dashboard('dashboard', content=DASHBOARD)

        invalid_script_yml = get_yaml(VALID_SCRIPT_PATH)
        invalid_script_yml['name'] = invalid_script_yml['name'] + "_v2"
        pack2 = repo.create_pack('PackName2')
        script = pack2.create_script(yml=invalid_script_yml)

        modified_files = {integration.yml_path, incident_field.get_path_from_pack()}
        added_files = {dashboard.get_path_from_pack(), script.yml_path}
        mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
        mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, added_files,
                                                                                           set(), set(), set()))

        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-g', '--no-docker-checks', '--no-conf-json',
                                          '--skip-pack-release-notes'],
                                   catch_exceptions=False)

        assert 'Running validation on branch' in result.stdout
        assert 'Running validation on modified files' in result.stdout
        assert 'Running validation on newly added files' in result.stdout
        assert 'Running validation on changed pack unique files' in result.stdout
        assert 'Validating Packs/PackName1 unique pack files' in result.stdout
        assert 'Validating Packs/PackName2 unique pack files' in result.stdout
        assert f'Validating {integration.yml_path} as integration' in result.stdout
        assert f'Validating {incident_field.get_path_from_pack()} as incidentfield' in result.stdout
        assert f'Validating {dashboard.get_path_from_pack()} as dashboard' in result.stdout
        assert f'Validating {script.yml_path} as script' in result.stdout
        assert 'IF101' in result.stdout
        assert 'The content key must be set to True.' in result.stdout
        assert 'SC100' in result.stdout
        assert 'The name of this v2 script is incorrect' in result.stdout
        assert result.exit_code == 1

    def test_validation_using_git_without_pack_dependencies(self, mocker, repo):
        """
        Given
        - An invalid repo.

        When
        - Running validate using git on it with --skip-pack-dependencies flag.

        Then
        - Ensure validate fails.
        - Ensure pack dependencies check doesnt happen.
        """
        pack = repo.create_pack('FeedAzure')
        integration = pack.create_integration(name='FeedAzure',
                                              yml=join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml"))
        modified_files = {integration.yml.rel_path}
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(BaseValidator, 'update_checked_flags_by_support_level', return_value=None)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_meta_file', return_value=True)
        mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
        mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, set(),
                                                                                           set(), set(), set()))

        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-g', '--no-docker-checks', '--no-conf-json',
                                          '--skip-pack-release-notes', '--skip-pack-dependencies'],
                                   catch_exceptions=False)
        assert 'Running validation on branch' in result.stdout
        assert 'Running validation on modified files' in result.stdout
        assert 'Running validation on newly added files' in result.stdout
        assert 'Running validation on changed pack unique files' in result.stdout
        assert 'Validating Packs/FeedAzure unique pack files' in result.stdout
        assert 'Running pack dependencies validation on' not in result.stdout
        assert result.exit_code == 1

    def test_validation_using_git_with_pack_dependencies(self, mocker, repo):
        """
        Given
        - An invalid repo.

        When
        - Running validate using git on it with --skip-pack-dependencies flag.

        Then
        - Ensure validate fails.
        - Ensure pack dependencies check happens.
        """
        pack = repo.create_pack('FeedAzure')
        integration = pack.create_integration(name='FeedAzure',
                                              yml=join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml"))
        modified_files = {integration.yml.rel_path}
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
        mocker.patch.object(PackDependencies, 'find_dependencies', return_value={})
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_meta_file', return_value=True)
        mocker.patch.object(BaseValidator, 'update_checked_flags_by_support_level', return_value=None)
        mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, set(),
                                                                                           set(), set(), set()))
        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-g', '--no-docker-checks', '--no-conf-json',
                                          '--skip-pack-release-notes'], catch_exceptions=False)
        assert 'Running pack dependencies validation on' in result.stdout
        assert result.exit_code == 1
