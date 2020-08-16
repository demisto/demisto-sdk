import os

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from TestSuite.test_tools import ChangeCWD

FIND_DEPENDENCIES_CMD = "find-dependencies"

EMPTY_ID_SET = {
    'scripts': [],
    'integrations': [],
    'playbooks': [],
    'TestPlaybooks': [],
    'Classifiers': [],
    'Dashboards': [],
    'IncidentFields': [],
    'IncidentTypes': [],
    'IndicatorFields': [],
    'IndicatorTypes': [],
    'Layouts': [],
    'Reports': [],
    'Widgets': [],
    'Mappers': [],
}


def test_integration_find_dependencies__sanity(mocker, repo):
    """
    Given
    - Valid pack folder

    When
    - Running find-dependencies on it.
    -

    Then
    - Ensure find-dependencies passes.
    - Ensure no error occurs.
    - Ensure debug file is created.
    """
    pack = repo.create_pack('FindDependencyPack')
    integration = pack.create_integration('integration')
    mocker.patch(
        "demisto_sdk.commands.find_dependencies.find_dependencies.update_pack_metadata_with_dependencies",
    )

    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        # Circle froze on 3.7 dut to high usage of processing power.
        # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
        # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
        # and not the maximum amount.
        import demisto_sdk.commands.common.update_id_set as uis
        mocker.patch.object(uis, 'cpu_count', return_value=1)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FIND_DEPENDENCIES_CMD,
                                      '-p', os.path.basename(repo.packs[0].path),
                                      '-v', os.path.join(repo.path, 'debug.md'),
                                      ])
    assert 'Found dependencies result for FindDependencyPack pack:' in result.output
    assert "{}" in result.output
    assert result.exit_code == 0
    assert result.stderr == ""
    assert os.path.isfile(os.path.join(repo.path, 'debug.md'))


def test_integration_find_dependencies__sanity_with_id_set(repo):
    """
    Given
    - Valid pack folder

    When
    - Running find-dependencies on it.

    Then
    - Ensure find-dependencies passes.
    - Ensure no error occurs.
    """
    pack = repo.create_pack('FindDependencyPack')
    integration = pack.create_integration('integration')
    id_set = EMPTY_ID_SET.copy()
    id_set['integrations'].append({
        'integration': {
            'name': integration.name,
            'file_path': integration.path,
            'commands': [
                'test-command',
            ],
            'pack': 'FindDependencyPack',
        }
    })

    repo.id_set.write_json(id_set)

    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FIND_DEPENDENCIES_CMD,
                                      '-p', os.path.basename(repo.packs[0].path),
                                      '-i', repo.id_set.path,
                                      '--no-update',
                                      ])
    assert 'Found dependencies result for FindDependencyPack pack:' in result.output
    assert "{}" in result.output
    assert result.exit_code == 0
    assert result.stderr == ""


def test_integration_find_dependencies__not_a_pack(repo):
    """
    Given
    - Valid pack folder

    When
    - Running find-dependencies on it.

    Then
    - Ensure find-dependencies passes.
    - Ensure no error occurs.
    """
    pack = repo.create_pack('FindDependencyPack')
    integration = pack.create_integration('integration')
    id_set = EMPTY_ID_SET.copy()
    id_set['integrations'].append({
        'integration': {
            'name': integration.name,
            'file_path': integration.path,
            'commands': [
                'test-command',
            ],
            'pack': 'FindDependencyPack',
        }
    })

    repo.id_set.write_json(id_set)

    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FIND_DEPENDENCIES_CMD,
                                      '-p', 'NotValidPack',
                                      '-i', repo.id_set.path,
                                      '--no-update',
                                      ])
    assert "Couldn't find any items for pack" in result.output
    assert result.exit_code == 0
    assert result.stderr == ""


def test_integration_find_dependencies__with_dependency(repo):
    """
    Given
    - Valid repo with 2 pack folders where pack2 (script) depends on pack1 (integration).

    When
    - Running find-dependencies on it.

    Then
    - Ensure find-dependencies passes.
    - Ensure dependency is printed.
    """
    pack1 = repo.create_pack('FindDependencyPack1')
    integration = pack1.create_integration('integration1')
    integration.create_default_integration()
    pack2 = repo.create_pack('FindDependencyPack2')
    script = pack2.create_script('script1')
    script.create_default_script()
    id_set = EMPTY_ID_SET.copy()
    id_set['scripts'].append({
        'Script1': {
            "name": script.name,
            'file_path': script.path,
            'deprecated': False,
            'depends_on': [
                'test-command'
            ],
            'pack': 'FindDependencyPack2',
        }
    })
    id_set['integrations'].append({
        'integration1': {
            'name': integration.name,
            'file_path': integration.path,
            'commands': [
                'test-command',
            ],
            'pack': 'FindDependencyPack1',
        }
    })

    repo.id_set.write_json(id_set)

    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FIND_DEPENDENCIES_CMD,
                                      '-p', os.path.basename(pack2.path),
                                      '-i', repo.id_set.path,
                                      '--no-update',
                                      ])
    assert 'Found dependencies result for FindDependencyPack2 pack:' in result.output
    assert '"display_name": "FindDependencyPack1"' in result.output
    assert result.exit_code == 0
    assert result.stderr == ""
