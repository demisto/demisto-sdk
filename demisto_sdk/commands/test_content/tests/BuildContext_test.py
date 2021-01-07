from demisto_sdk.commands.test_content.ParallelLoggingManager import \
    ParallelLoggingManager
from demisto_sdk.commands.test_content.TestContentClasses import (BuildContext,
                                                                  Conf,
                                                                  SecretConf)


def generate_test_configuration(playbook_id: str,
                                integrations: list = None,
                                instance_names: list = None,
                                nightly: bool = None,
                                fromversion: str = '',
                                toversion: str = '',
                                timeout: int = None,
                                memory_threshold: int = None,
                                pid_threshold: int = None
                                ) -> dict:
    playbook_config = {
        'playbookID': playbook_id,
    }
    if integrations:
        playbook_config['integrations'] = integrations
    if instance_names:
        playbook_config['instance_names'] = instance_names
    if nightly is not None:
        playbook_config['nightly'] = nightly
    if fromversion:
        playbook_config['fromversion'] = fromversion
    if toversion:
        playbook_config['toversion'] = toversion
    if timeout:
        playbook_config['timeout'] = timeout
    if memory_threshold:
        playbook_config['memory_threshold'] = memory_threshold
    if pid_threshold:
        playbook_config['pid_threshold'] = pid_threshold
    return playbook_config


def generate_content_conf_json(
        tests: list = None,
        skipped_tests: dict = None,
        skipped_integrations: dict = None,
        nightly_integrations: list = None,
        unmockable_integrations: dict = None,
        parallel_integrations: list = None,
        docker_thresholds_images: dict = None
) -> dict:
    """
    Generates a replica of the content conf.json file according to parameters
    Args:
        tests: A dict with a test playbook configuration
        skipped_tests: A dict containing playbook IDs as keys and the reason why it was skipped as value
        skipped_integrations: A list containing integration IDs
        nightly_integrations: A list containing integration IDs
        unmockable_integrations: A dict containing integration IDs as keys and the reason why it's unmockable as value
        parallel_integrations: A list containing integration IDs
        docker_thresholds_images: A dict containing image name as key and a dict containing docker limitations as value
    Returns:
        A replica of the content conf.json file according to parameters
    """
    return {
        'testTimeout': 160,
        'testInterval': 20,
        'tests': tests or [],
        'skipped_tests': skipped_tests or {},
        'skipped_integrations': skipped_integrations or {},
        'nightly_integrations': nightly_integrations or [],
        'unmockable_integrations': unmockable_integrations or {},
        'parallel_integrations': parallel_integrations or [],
        'docker_thresholds': {
            'images': docker_thresholds_images or {}
        }
    }


def generate_secret_conf_json(
        integrations: list = None
):
    return {
        'username': 'username',
        'userPassword': 'password',
        'integrations': integrations or []
    }


def generate_integration_configuration(
        name: str,
        params: dict = None,
        instance_name: str = None,
        byoi: bool = None,
        validate_test: bool = None,
) -> dict:
    """
    Generates an integration configuration according to params
    Args:
        name: The name of the integration
        params: A dict containing the params of the integration
        instance_name: the name of the instance that should be used
        byoi: is byoi integration
        validate_test: should the build validate the test-module before configuring
    """
    integration_config = {
        'name': name,
        'params': params or {}
    }
    if instance_name:
        integration_config['instance_name'] = instance_name
    if byoi is not None:
        integration_config['byoi'] = byoi
    if validate_test is not None:
        integration_config['validate_test'] = validate_test
    return integration_config


def generate_env_results_content(
        number_of_instances: int = 1,
        role: str = 'Server Master',
):
    role_to_ami_name_mapping = {
        'Server Master': 'Demisto-Marketplace-Content-AMI-Master-612266-2021-01-03',
        'Server 6.0': 'Demisto-Marketplace-Content-AMI-GA_6_0-86106-2021-01-03',
        'Server 5.5': 'Demisto-Circle-CI-Content-AMI-PreGA-5.5-87835-2021-01-03',
        'Server 5.0': 'Demisto-Circle-CI-Content-AMI-GA-5.0-62071-2021-01-03'
    }
    env_results = [{'AmiName': role_to_ami_name_mapping[role],
                    'Role': role} for _ in range(number_of_instances)]
    return env_results


def get_mocked_build_context(
        mocker,
        tmp_file,
        content_conf_json: dict = None,
        secret_conf_json: dict = None,
        env_results_content: dict = None,
        filtered_tests_content: list = None,
        nightly: bool = False,
        server_version: str = 'Server Master'
) -> BuildContext:
    """
    Generates a BuildContext instance with mocked data.
    Args:
        mocker: The mocker instance used in the unittest
        tmp_file: the path in which the log should be written
        content_conf_json: The contents of conf.json to load in the BuildContext instance
        secret_conf_json: The contents of content-test-conf conf.json to load in the BuildContext instance
        env_results_content: The contents of env_results.json to load in the BuildContext instance
        filtered_tests_content: The contents of filtered_tests to load in the BuildContext instance
        nightly: Indicates whether this build is a nightly build
        server_version: The server version to run the instance on
    """
    logging_manager = ParallelLoggingManager(tmp_file / 'log_file.log')
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.BuildContext._load_conf_files',
                 return_value=(Conf(content_conf_json or generate_content_conf_json()),
                               SecretConf(secret_conf_json or generate_secret_conf_json()),))
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.BuildContext._load_env_results_json',
                 return_value=env_results_content or generate_env_results_content())
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.BuildContext._extract_filtered_tests',
                 return_value=filtered_tests_content or [])
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.BuildContext._retrieve_slack_user_id',
                 return_value='some_user_id')
    mocker.patch('demisto_sdk.commands.test_content.TestContentClasses.BuildContext._get_all_integration_config',
                 return_value=[])
    kwargs = {
        'api_key': 'api_key',
        'server': None,
        'conf': 'conf_path',
        'secret': 'secret_conf_path',
        'slack': 'slack_token',
        'nightly': nightly,
        'is_ami': True,
        'circleci': 'circle_token',
        'build_number': '11111',
        'branch_name': 'branch',
        'server_version': server_version,
        'mem_check': False
    }
    return BuildContext(kwargs, logging_manager)


def test_non_filtered_tests_are_skipped(mocker, tmp_path):
    """
    Given:
        - A build context with one test in filtered tests list
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that all tests that are not in filtered tests are skipped
        - Ensure that the test that was in  filtered tests is not skipped
    """
    filtered_tests = ['test_that_should_run']
    tests = [generate_test_configuration(playbook_id='test_that_should_run'),
             generate_test_configuration(playbook_id='test_that_should_be_skipped')]
    content_conf_json = generate_content_conf_json(tests=tests)
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    assert 'test_that_should_be_skipped' in build_context.tests_data_keeper.skipped_tests
    assert 'test_that_should_run' not in build_context.tests_data_keeper.skipped_tests


def test_playbook_with_skipped_integrations_is_skipped(mocker, tmp_path):
    """
    Given:
        - A build context with one test in filtered tests list that has a skipped integration

    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with the skipped integrations is skipped
    """
    filtered_tests = ['test_with_skipped_integrations']
    tests = [generate_test_configuration(playbook_id='test_with_skipped_integrations',
                                         integrations=['skipped_integration'])]
    content_conf_json = generate_content_conf_json(tests=tests,
                                                   skipped_integrations={'skipped_integration': ''})
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    assert 'test_with_skipped_integrations' in build_context.tests_data_keeper.skipped_tests


def test_nightly_playbook_skipping(mocker, tmp_path):
    """
    Given:
        - A build context with one nightly playbook
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the nightly playbook is skipped on non nightly build
        - Ensure that the nightly playbook is not skipped on nightly build
    """
    filtered_tests = ['nightly_playbook']
    tests = [generate_test_configuration(playbook_id='nightly_playbook', nightly=True)]
    content_conf_json = generate_content_conf_json(tests=tests)
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    assert 'nightly_playbook' in build_context.tests_data_keeper.skipped_tests
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests,
                                             nightly=True)
    assert 'nightly_playbook' not in build_context.tests_data_keeper.skipped_tests


def test_playbook_with_nightly_integration_skipping(mocker, tmp_path):
    """
    Given:
        - A build context with playbook that has a nightly integration
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with nightly integration is skipped on non nightly build
        - Ensure that the playbook with nightly integration is not skipped on nightly build
    """
    filtered_tests = ['playbook_with_nightly_integration']
    tests = [generate_test_configuration(playbook_id='playbook_with_nightly_integration',
                                         integrations=['nightly_integration'])]
    content_conf_json = generate_content_conf_json(tests=tests,
                                                   nightly_integrations=['nightly_integration'])
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    assert 'playbook_with_nightly_integration' in build_context.tests_data_keeper.skipped_tests
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests,
                                             nightly=True)
    assert 'playbook_with_nightly_integration' not in build_context.tests_data_keeper.skipped_tests


def test_playbook_with_version_mismatch_is_skipped(mocker, tmp_path):
    """
    Given:
        - A build context for a version that does not match the playbook version
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with version mismatch is skipped
    """
    filtered_tests = ['playbook_with_version_mismatch']
    tests = [generate_test_configuration(playbook_id='playbook_with_version_mismatch',
                                         toversion='6.0.0')]
    content_conf_json = generate_content_conf_json(tests=tests)
    build_context = get_mocked_build_context(mocker,
                                             tmp_path,
                                             content_conf_json=content_conf_json,
                                             filtered_tests_content=filtered_tests)
    assert 'playbook_with_version_mismatch' in build_context.tests_data_keeper.skipped_tests
