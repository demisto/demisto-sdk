from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from TestSuite.test_tools import ChangeCWD

VALIDATE_CMD = "validate"
TEST_FILES_PATH = join(git_path(), "demisto_sdk/tests/test_files")
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzure")
AZURE_FEED_INVALID_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzureab")
VALID_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzureValid")
CONF_JSON_MOCK = {
    "tests": [
        {
            "integrations": "AzureFeed",
            "playbookID": "AzureFeed - Test"
        }
    ]
}

OLD_CLASSIFIER = {
    "brandName": "test",
    "custom": True,
    "defaultIncidentType": "",
    "id": "test classifier",
    "keyTypeMap": {
        "test": "test1"
    },
    "mapping": {
        "Logz.io Alert": {
            "dontMapEventToLabels": False,
            "internalMapping": {
                "test Alert ID": {
                    "complex": None,
                    "simple": "alertId"
                },
                "details": {
                    "complex": None,
                    "simple": "description"
                }
            }
        }
    },
    "transformer": {
        "complex": None,
        "simple": "test"
    },
    "unclassifiedCases": {},
    "version": -1,
    "fromVersion": "5.0.0",
    "toVersion": "5.9.9"
}

NEW_CLASSIFIER = {
    "defaultIncidentType": "test",
    "id": "testing",
    "type": "classification",
    "name": "test Classifier",
    "description": "Classifies test.",
    "keyTypeMap": {
        "test": "test1"
    },
    "transformer": {
        "complex": None,
        "simple": "test"
    },
    "version": -1,
    "fromVersion": "6.0.0",
    "toVersion": "6.0.5"
}

MAPPER = {
    "defaultIncidentType": "test",
    "id": "testing",
    "type": "mapping-incoming",
    "name": "test Mapper",
    "description": "Mapper test",
    "mapping": {
        "test": {
            "dontMapEventToLabels": False,
            "internalMapping": {
                "test Alert ID": {
                    "complex": None,
                    "simple": "alertId"
                }
            }
        }
    },
    "version": -1,
    "fromVersion": "6.0.0",
    "toVersion": "6.0.5"
}


def assert_positive(file_path, result):
    """
    Series of asserts every positive test should do
    :param file_path: path to the file
    :param result: result object as returned from runner.invoke
    """
    assert result.exit_code == 0
    assert "Starting validating files structure" in result.stdout
    assert f"Validating {file_path}" in result.stdout
    assert "The files are valid" in result.stdout
    assert result.stderr == ""


class TestIncidentField:
    def test_positive(self):
        """
        Given
        - Valid `city` incident field.

        When
        - Running validation on it.

        Then
        - Ensure validation passes.
        - Ensure success validation message is printed.
        """
        pack_incident_field_path = join(AZURE_FEED_PACK_PATH, "IncidentFields/incidentfield-city.json")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", pack_incident_field_path, "--no-conf-json"])
        assert_positive(pack_incident_field_path, result)


class TestIntegration:
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
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {pack_integration_path}" in result.stdout
        assert "The docker image tag is not the latest, please update it" in result.stdout
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
        result = runner.invoke(main, [VALIDATE_CMD, "-p", integration_path, "--no-conf-json"])
        assert result.exit_code == 1
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {integration_path}" in result.stdout
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
        result = runner.invoke(main, [VALIDATE_CMD, "-p", integration_path, "--no-conf-json"])
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {integration_path}" in result.stdout
        assert "can't be hidden. Please remove this field" not in result.stdout
        assert result.stderr == ""


class TestPack:
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
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", VALID_PACK_PATH, "--no-conf-json"])
        assert "Starting validating files structure" in result.output
        assert f"{VALID_PACK_PATH} unique pack files" in result.output
        assert f"Validating {VALID_PACK_PATH}" in result.output
        assert f"{VALID_PACK_PATH}/Integrations/FeedAzureValid/FeedAzureValid.yml" in result.output
        assert f"{VALID_PACK_PATH}/IncidentFields/incidentfield-city.json" in result.output
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
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_PACK_PATH, "--no-conf-json"])
        assert "Starting validating files structure" in result.output

        assert f'{AZURE_FEED_PACK_PATH}' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/IncidentFields/incidentfield-city.json' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/Integrations/FeedAzure/FeedAzure.yml' in result.output
        assert 'Playbook conditional task with id:15 has unhandled condition: MAYBE' in result.output
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


class TestClassifier:

    def test_valid_new_classifier(self, mocker, repo):
        """
        Given
        - Valid new classifier

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
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
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        NEW_CLASSIFIER['fromVersion'] = '5.0.0'
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'fromVersion field in new classifiers needs to be higher or equal to 6.0.0' in result.stdout

    def test_invalid_to_version_in_new_classifiers(self, mocker, repo):
        """
        Given
        - New classifier with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        NEW_CLASSIFIER['toVersion'] = '5.0.0'
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'toVersion field in new classifiers needs to be higher than 6.0.0' in result.stdout

    def test_classifier_from_version_higher_to_version(self, mocker, repo):
        """
        Given
        - New classifier with from version field higher than to version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        NEW_CLASSIFIER['toVersion'] = '6.0.2'
        NEW_CLASSIFIER['fromVersion'] = '6.0.5'
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'fromVersion field can not be higher than toVersion field' in result.stdout

    def test_missing_mandatory_field_in_new_classifier(self, mocker, repo):
        """
        Given
        - New classifier with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        del NEW_CLASSIFIER['id']
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'Missing id in root' in result.stdout

    def test_missing_fromversion_field_in_new_classifier(self, mocker, repo):
        """
        Given
        - New classifier with missing from version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        del NEW_CLASSIFIER['fromVersion']
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
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
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        NEW_CLASSIFIER['type'] = 'test'
        classifier = pack.create_classifier('new_classifier', NEW_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'Classifiers type must be classification' in result.stdout

    def test_valid_old_classifier(self, mocker, repo):
        """
        Given
        - Valid old classifier

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
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
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        OLD_CLASSIFIER['fromVersion'] = '6.0.0'
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
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
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        OLD_CLASSIFIER['toVersion'] = '6.0.0'
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'toVersion field in old classifiers needs to be lower than 6.0.0' in result.stdout

    def test_missing_mandatory_field_in_old_classifier(self, mocker, repo):
        """
        Given
        - Old classifier with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        del OLD_CLASSIFIER['id']
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'Missing id in root' in result.stdout

    def test_missing_toversion_field_in_old_classifier(self, mocker, repo):
        """
        Given
        - Old classifier with missing from version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        del OLD_CLASSIFIER['toVersion']
        classifier = pack.create_classifier('old_classifier', OLD_CLASSIFIER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', classifier.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {classifier.path}" in result.stdout
        assert 'Must have toVersion field in old classifiers' in result.stdout


class TestMapper:

    def test_valid_mapper(self, mocker, repo):
        """
        Given
        - Valid mapper

        When
        - Running validate on it.

        Then
        - Ensure validate passes.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        print(result.stdout)
        assert 'The files are valid' in result.stdout

    def test_invalid_from_version_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with invalid from version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        MAPPER['fromVersion'] = '5.0.0'
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        assert 'fromVersion field in mapper needs to be higher or equal to 6.0.0' in result.stdout

    def test_invalid_to_version_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with invalid to version

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        MAPPER['toVersion'] = '5.0.0'
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        assert 'toVersion field in mapper needs to be higher than 6.0.0' in result.stdout

    def test_missing_mandatory_field_in_mapper(self, mocker, repo):
        """
        Given
        - Mapper with missing mandatory field (id).

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        del MAPPER['id']
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        assert 'Missing id in root' in result.stdout

    def test_mapper_from_version_higher_to_version(self, mocker, repo):
        """
        Given
        - Mapper with from version field higher than to version field.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        MAPPER['toVersion'] = '6.0.2'
        MAPPER['fromVersion'] = '6.0.5'
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        assert 'fromVersion field can not be higher than toVersion field' in result.stdout

    def test_invalid_mapper_type(self, mocker, repo):
        """
        Given
        - Mapper with invalid type.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_private_repository', return_value=True)
        pack = repo.create_pack('PackName')
        MAPPER['type'] = 'test'
        mapper = pack.create_mapper('mapper', MAPPER)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', mapper.path], catch_exceptions=False)
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {mapper.path}" in result.stdout
        assert 'Mappers type must be mapping-incoming or mapping-outgoing' in result.stdout
