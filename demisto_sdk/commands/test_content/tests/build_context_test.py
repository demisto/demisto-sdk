from typing import Union

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.TestContentClasses import BuildContext
from demisto_sdk.commands.test_content.tests.DemistoClientMock import DemistoClientMock


def generate_test_configuration(
    playbook_id: str,
    integrations: list = None,
    instance_names: list = None,
    nightly: bool = None,
    fromversion: str = "",
    toversion: str = "",
    timeout: int = None,
    memory_threshold: int = None,
    pid_threshold: int = None,
    runnable_on_docker_only: bool = None,
    marketplaces: Union[list, str] = None,
) -> dict:
    playbook_config = {
        "playbookID": playbook_id,
    }
    if integrations:
        playbook_config["integrations"] = integrations
    if instance_names:
        playbook_config["instance_names"] = instance_names
    if nightly is not None:
        playbook_config["nightly"] = nightly
    if fromversion:
        playbook_config["fromversion"] = fromversion
    if toversion:
        playbook_config["toversion"] = toversion
    if timeout:
        playbook_config["timeout"] = timeout
    if memory_threshold:
        playbook_config["memory_threshold"] = memory_threshold
    if pid_threshold:
        playbook_config["pid_threshold"] = pid_threshold
    if runnable_on_docker_only is not None:
        playbook_config["runnable_on_docker_only"] = runnable_on_docker_only
    if marketplaces:
        playbook_config["marketplaces"] = marketplaces
    return playbook_config


def generate_content_conf_json(
    tests: list = None,
    skipped_tests: dict = None,
    skipped_integrations: dict = None,
    parallel_integrations: list = None,
    docker_thresholds_images: dict = None,
) -> dict:
    """
    Generates a replica of the content conf.json file according to parameters
    Args:
        tests: A dict with a test playbook configuration
        skipped_tests: A dict containing playbook IDs as keys and the reason why it was skipped as value
        skipped_integrations: A list containing integration IDs
        parallel_integrations: A list containing integration IDs
        docker_thresholds_images: A dict containing image name as key and a dict containing docker limitations as value
    Returns:
        A replica of the content conf.json file according to parameters
    """
    return {
        "testTimeout": 160,
        "testInterval": 20,
        "tests": tests or [],
        "skipped_tests": skipped_tests or {},
        "skipped_integrations": skipped_integrations or {},
        "parallel_integrations": parallel_integrations or [],
        "docker_thresholds": {"images": docker_thresholds_images or {}},
    }


def generate_secret_conf_json(integrations: list = None):
    return {
        "username": "username",
        "userPassword": "password",
        "integrations": integrations or [],
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
    integration_config = {"name": name, "params": params or {}}
    if instance_name:
        integration_config["instance_name"] = instance_name
    if byoi is not None:
        integration_config["byoi"] = byoi
    if validate_test is not None:
        integration_config["validate_test"] = validate_test
    return integration_config


def generate_env_results_content(
    number_of_instances: int = 1,
    role: str = "Server Master",
):
    role_to_ami_name_mapping = {
        "Server Master": "Demisto-Marketplace-Content-AMI-Master-612266-2021-01-03",
        "Server 6.0": "Demisto-Marketplace-Content-AMI-GA_6_0-86106-2021-01-03",
        "Server 5.5": "Demisto-Circle-CI-Content-AMI-PreGA-5.5-87835-2021-01-03",
        "Server 5.0": "Demisto-Circle-CI-Content-AMI-GA-5.0-62071-2021-01-03",
    }
    env_results = [
        {
            "AmiName": role_to_ami_name_mapping[role],
            "Role": role,
            "InstanceDNS": "1.1.1.1",
            "TunnelPort": 4445,
        }
        for _ in range(number_of_instances)
    ]
    return env_results


def generate_xsiam_servers_data():
    return {
        "qa2-test-111111": {
            "ui_url": "https://xsiam1.paloaltonetworks.com/",
            "instance_name": "qa2-test-111111",
            "base_url": "https://api1.paloaltonetworks.com/",
            "xsiam_version": "3.2.0",
            "demisto_version": "99.99.98",
        },
        "qa2-test-222222": {
            "ui_url": "https://xsoar-content-2.xdr-qa2-uat.us.paloaltonetworks.com/",
            "instance_name": "qa2-test-222222",
            "base_url": "https://api-xsoar-content-2.xdr-qa2-uat.us.paloaltonetworks.com",
            "xsiam_version": "3.2.0",
            "demisto_version": "99.99.98",
        },
    }


def generate_xsoar_sass_servers_data():
    return {
        "qa2-test-111111": {
            "ui_url": "https://xsoar1.paloaltonetworks.com/",
            "instance_name": "qa2-test-111111",
            "base_url": "https://api1.paloaltonetworks.com/",
            "xsoar_version": "8.2.0",
            "demisto_version": "99.99.98",
        },
        "qa2-test-222222": {
            "ui_url": "https://xsoar-content-2.xdr-qa2-uat.us.paloaltonetworks.com/",
            "instance_name": "qa2-test-222222",
            "base_url": "https://api-xsoar-content-2.xdr-qa2-uat.us.paloaltonetworks.com",
            "xsoar_version": "8.2.0",
            "demisto_version": "99.99.98",
        },
    }


def get_mocked_build_context(
    mocker,
    tmp_file,
    content_conf_json: dict = None,
    secret_conf_json: dict = None,
    env_results_content: dict = None,
    machine_assignment_content: dict = None,
    nightly: bool = False,
    server_version: str = "Server Master",
) -> BuildContext:
    """
    Generates a BuildContext instance with mocked data.
    Args:
        mocker: The mocker instance used in the unittest
        tmp_file: the path in which the log should be written
        content_conf_json: The contents of conf.json to load in the BuildContext instance
        secret_conf_json: The contents of content-test-conf conf.json to load in the BuildContext instance
        env_results_content: The contents of env_results.json to load in the BuildContext instance
        machine_assignment_content: The contents of machine_assignment.json to load in the BuildContext instance
        nightly: Indicates whether this build is a nightly build
        server_version: The server version to run the instance on
    """
    logging_manager = ParallelLoggingManager(tmp_file / "log_file.log")
    mocked_demisto_client = DemistoClientMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.demisto_client",
        mocked_demisto_client,
    )
    conf_path = tmp_file / "conf_path"
    conf_path.write_text(json.dumps(content_conf_json or generate_content_conf_json()))

    secret_conf_path = tmp_file / "secret_conf_path"
    secret_conf_path.write_text(
        json.dumps(secret_conf_json or generate_secret_conf_json())
    )

    env_results_path = tmp_file / "env_results_path"
    env_results_path.write_text(
        json.dumps(env_results_content or generate_env_results_content())
    )
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ENV_RESULTS_PATH",
        str(env_results_path),
    )

    machine_assignment_path = tmp_file / "machine_assignment.json"
    machine_assignment_path.write_text(
        json.dumps(machine_assignment_content or {}) or "{}"
    )

    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ServerContext._get_all_integration_config",
        return_value=[],
    )
    kwargs = {
        "api_key": "api_key",
        "server": None,
        "conf": conf_path,
        "secret": secret_conf_path,
        "slack": "slack_token",
        "nightly": nightly,
        "is_ami": True,
        "circleci": "circle_token",
        "build_number": "11111",
        "branch_name": "branch",
        "server_version": server_version,
        "mem_check": False,
        "server_type": "XSOAR",
        "artifacts_path": tmp_file,
        "product_type": "xsoar",
        "service_account": "test",
        "artifacts_bucket": "test",
        "machine_assignment": machine_assignment_path,
        "cloud_machine_ids": "qa2-test-222222,qa2-test-111111",
    }
    return BuildContext(kwargs, logging_manager)


def create_xsiam_build(
    mocker,
    tmp_file,
    content_conf_json: dict = None,
    machine_assignment_content: dict = None,
):
    mocked_demisto_client = DemistoClientMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.demisto_client",
        mocked_demisto_client,
    )
    logging_manager = ParallelLoggingManager(tmp_file / "log_file.log")
    conf_path = tmp_file / "conf_path"
    conf_path.write_text(json.dumps(content_conf_json or generate_content_conf_json()))

    secret_conf_path = tmp_file / "secret_conf_path"
    secret_conf_path.write_text(json.dumps(generate_secret_conf_json()))

    cloud_servers_path = tmp_file / "xsiam_servers_path.json"
    cloud_servers_path.write_text(json.dumps(generate_xsiam_servers_data()))

    xsiam_api_keys_path = tmp_file / "xsiam_api_keys_path.json"
    xsiam_api_keys_path.write_text(
        json.dumps(
            {
                "qa2-test-111111": {"api-key": "api_key", "x-xdr-auth-id": 1},
                "qa2-test-222222": {"api-key": "api_key", "x-xdr-auth-id": 1},
            }
        )
    )

    env_results_path = tmp_file / "env_results_path"
    env_results_path.write_text(json.dumps(generate_env_results_content()))
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ENV_RESULTS_PATH",
        str(env_results_path),
    )

    machine_assignment_path = tmp_file / "machine_assignment.json"
    machine_assignment_path.write_text(
        json.dumps(machine_assignment_content or {}) or "{}"
    )

    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ServerContext._get_all_integration_config",
        return_value=[],
    )
    kwargs = {
        "api_key": "api_key",
        "server": None,
        "conf": conf_path,
        "secret": secret_conf_path,
        "slack": "slack_token",
        "nightly": False,
        "is_ami": True,
        "circleci": "circle_token",
        "build_number": "11111",
        "branch_name": "branch",
        "server_version": "XSIAM Master",
        "mem_check": False,
        "server_type": "XSIAM",
        "cloud_servers_path": cloud_servers_path,
        "cloud_machine_ids": "qa2-test-111111",
        "cloud_servers_api_keys": xsiam_api_keys_path,
        "artifacts_path": tmp_file,
        "product_type": "xsoar",
        "service_account": "test",
        "artifacts_bucket": "test",
        "machine_assignment": machine_assignment_path,
    }
    return BuildContext(kwargs, logging_manager)


def create_xsoar_saas_build(
    mocker,
    tmp_file,
    content_conf_json: dict = None,
    machine_assignment_content: dict = None,
):
    mocked_demisto_client = DemistoClientMock()
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.demisto_client",
        mocked_demisto_client,
    )
    logging_manager = ParallelLoggingManager(tmp_file / "log_file.log")
    conf_path = tmp_file / "conf_path"
    conf_path.write_text(json.dumps(content_conf_json or generate_content_conf_json()))

    secret_conf_path = tmp_file / "secret_conf_path"
    secret_conf_path.write_text(json.dumps(generate_secret_conf_json()))

    cloud_servers_path = tmp_file / "xsoar_saas_servers_path.json"
    cloud_servers_path.write_text(json.dumps(generate_xsoar_sass_servers_data()))

    xsiam_api_keys_path = tmp_file / "xsoar_saas_api_keys_path.json"
    xsiam_api_keys_path.write_text(
        json.dumps(
            {
                "qa2-test-111111": {"api-key": "api_key", "x-xdr-auth-id": 1},
                "qa2-test-222222": {"api-key": "api_key", "x-xdr-auth-id": 1},
            }
        )
    )

    env_results_path = tmp_file / "env_results_path"
    env_results_path.write_text(json.dumps(generate_env_results_content()))
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ENV_RESULTS_PATH",
        str(env_results_path),
    )

    machine_assignment_path = tmp_file / "machine_assignment.json"
    machine_assignment_path.write_text(
        json.dumps(machine_assignment_content or {}) or "{}"
    )

    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.ServerContext._get_all_integration_config",
        return_value=[],
    )
    kwargs = {
        "api_key": "api_key",
        "server": None,
        "conf": conf_path,
        "secret": secret_conf_path,
        "slack": "slack_token",
        "nightly": False,
        "is_ami": True,
        "circleci": "circle_token",
        "build_number": "11111",
        "branch_name": "branch",
        "server_version": "XSOAR SAAS Master",
        "mem_check": False,
        "server_type": "XSOAR SAAS",
        "cloud_servers_path": cloud_servers_path,
        "cloud_machine_ids": "qa2-test-111111",
        "cloud_servers_api_keys": xsiam_api_keys_path,
        "artifacts_path": tmp_file,
        "product_type": "xsoar",
        "service_account": "test",
        "artifacts_bucket": "test",
        "machine_assignment": machine_assignment_path,
    }
    return BuildContext(kwargs, logging_manager)


def test_build_creation(mocker, tmp_path):
    """
    Given:
        - A build context for xsiam run
    When:
        - Running test-content command and creating xsiam build context
    Then:
        - All xsiam build  parameters created as expected
    """
    machine_assignment_content_xsiam = {
        "qa2-test-111111": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: []},
        }
    }
    build_contex = create_xsiam_build(
        mocker, tmp_path, machine_assignment_content=machine_assignment_content_xsiam
    )
    assert build_contex.is_saas_server_type
    assert build_contex.servers


def test_non_filtered_tests_are_skipped(mocker, tmp_path):
    """
    Given:
        - A build context with one test in filtered tests list
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that all tests that are not in filtered tests are skipped
        - Ensure that the test that was in filtered tests is not skipped
    """
    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["test_that_should_run"]},
        }
    }
    tests = [
        generate_test_configuration(playbook_id="test_that_should_run"),
        generate_test_configuration(playbook_id="test_that_should_be_skipped"),
    ]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )

    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
    )
    assert (
        "test_that_should_be_skipped" in build_context.tests_data_keeper.skipped_tests
    )
    assert "test_that_should_run" not in build_context.tests_data_keeper.skipped_tests


def test_no_tests_are_executed_when_filtered_tests_is_empty(mocker, tmp_path):
    """
    Given:
        - A build context with empty filtered tests list
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that all tests that are skipped
    """
    tests = [generate_test_configuration(playbook_id="test_that_should_be_skipped")]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content={"xsoar-machine": {"packs_to_install": ["TEST"]}},
    )
    assert (
        "test_that_should_be_skipped" in build_context.tests_data_keeper.skipped_tests
    )


def test_playbook_with_skipped_integrations_is_skipped(mocker, tmp_path):
    """
    Given:
        - A build context with one test in filtered tests list that has a skipped integration

    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with the skipped integrations is skipped
    """
    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["test_with_skipped_integrations"]},
        }
    }

    tests = [
        generate_test_configuration(
            playbook_id="test_with_skipped_integrations",
            integrations=["skipped_integration"],
        )
    ]
    content_conf_json = generate_content_conf_json(
        tests=tests, skipped_integrations={"skipped_integration": ""}
    )
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
    )
    assert (
        "test_with_skipped_integrations"
        in build_context.tests_data_keeper.skipped_tests
    )


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
    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["nightly_playbook"]},
        }
    }

    tests = [generate_test_configuration(playbook_id="nightly_playbook", nightly=True)]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
    )
    assert "nightly_playbook" in build_context.tests_data_keeper.skipped_tests

    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
        nightly=True,
    )
    assert "nightly_playbook" not in build_context.tests_data_keeper.skipped_tests


def test_playbook_with_integration(mocker, tmp_path):
    """
    Given:
        - A build context with playbook that has an integration
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with the integration is not skipped on nightly build
    """
    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["playbook_with_integration"]},
        }
    }

    tests = [
        generate_test_configuration(
            playbook_id="playbook_with_integration", integrations=["integration"]
        )
    ]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
        nightly=True,
    )
    assert (
        "playbook_with_integration" not in build_context.tests_data_keeper.skipped_tests
    )


def test_playbook_with_version_mismatch_is_skipped(mocker, tmp_path):
    """
    Given:
        - A build context for a version that does not match the playbook version
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with version mismatch is skipped
    """
    machine_assignment_content = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["playbook_with_version_mismatch"]},
        }
    }

    tests = [
        generate_test_configuration(
            playbook_id="playbook_with_version_mismatch", toversion="6.0.0"
        )
    ]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content,
    )
    assert (
        "playbook_with_version_mismatch"
        in build_context.tests_data_keeper.skipped_tests
    )


def test_playbook_with_marketplaces(mocker, tmp_path):
    """
    Given:
        - A build context for a server type that matches and that does not match the playbook marketplaces
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the playbook with marketplaces mismatch is skipped
        - Ensure that the playbook with the marketplaces match is not skipped
    """
    machine_assignment_content_xsiam = {
        "qa2-test-111111": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["xsiam_playbook_with_marketplaces_mismatch"]},
        }
    }
    machine_assignment_content_xsoar = {
        "xsoar-machine": {
            "packs_to_install": ["TEST"],
            "tests": {TEST_PLAYBOOKS: ["xsoar_playbook_with_marketplaces_mismatch"]},
        }
    }
    machine_assignment_content_xsoar_saas = {
        "qa2-test-111111": {
            "packs_to_install": ["TEST"],
            "tests": {
                TEST_PLAYBOOKS: [
                    "xsoar_saas_playbook_with_marketplaces_mismatch",
                    "xsoar_playbook_with_marketplaces_mismatch",
                ]
            },
        }
    }

    tests = [
        generate_test_configuration(
            playbook_id="xsiam_playbook_with_marketplaces_mismatch",
            marketplaces="marketplacev2",
        ),
        generate_test_configuration(
            playbook_id="xsoar_playbook_with_marketplaces_mismatch",
            marketplaces="xsoar",
        ),
        generate_test_configuration(
            playbook_id="xsoar_saas_playbook_with_marketplaces_mismatch",
            marketplaces="xsoar_on_prem",
        ),
    ]
    content_conf_json = generate_content_conf_json(tests=tests)
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    xsoar_build_context = get_mocked_build_context(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content_xsoar,
    )
    assert (
        "xsiam_playbook_with_marketplaces_mismatch"
        in xsoar_build_context.tests_data_keeper.skipped_tests
    )
    assert (
        "xsoar_playbook_with_marketplaces_mismatch"
        not in xsoar_build_context.tests_data_keeper.skipped_tests
    )

    xsiam_build_context = create_xsiam_build(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content_xsiam,
    )
    assert (
        "xsiam_playbook_with_marketplaces_mismatch"
        not in xsiam_build_context.tests_data_keeper.skipped_tests
    )
    assert (
        "xsoar_playbook_with_marketplaces_mismatch"
        in xsiam_build_context.tests_data_keeper.skipped_tests
    )

    xsoar_saas_build_context = create_xsoar_saas_build(
        mocker,
        tmp_path,
        content_conf_json=content_conf_json,
        machine_assignment_content=machine_assignment_content_xsoar_saas,
    )
    assert (
        "xsoar_saas_playbook_with_marketplaces_mismatch"
        in xsoar_saas_build_context.tests_data_keeper.skipped_tests
    )
    assert (
        "xsiam_playbook_with_marketplaces_mismatch"
        in xsoar_saas_build_context.tests_data_keeper.skipped_tests
    )
    assert (
        "xsoar_playbook_with_marketplaces_mismatch"
        not in xsoar_saas_build_context.tests_data_keeper.skipped_tests
    )


def test_get_instances_ips(mocker, tmp_path):
    """
    Given:
        - A build context
    When:
        - Initializing the BuildContext instance
    Then:
        - Ensure that the instance ips are returnd.
    """
    mocker.patch(
        "demisto_sdk.commands.test_content.TestContentClasses.is_redhat_instance",
        return_value=False,
    )
    build_context = get_mocked_build_context(mocker, tmp_path)
    assert build_context.instances_ips == ["1.1.1.1"]
