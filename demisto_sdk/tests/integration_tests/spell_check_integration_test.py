from click.testing import CliRunner
from demisto_sdk.__main__ import main
from TestSuite.test_tools import ChangeCWD

SPELL_CHECK = 'spell-check'


def test_spell_integration_dir_valid(repo):
    pack = repo.create_pack('my_pack')
    integration = pack.create_integration('myint')
    integration.create_default_integration()

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SPELL_CHECK, '-i', integration.path], catch_exceptions=False)
        assert 'No misspelled words found ' in result.stdout
        print(result.stdout)
        assert 'Words that might be misspelled were found in' not in result.stdout


def test_spell_integration_invalid(repo):
    pack = repo.create_pack('my_pack')
    integration = pack.create_integration('myint')
    integration.create_default_integration()
    yml_content = integration.yml.read_dict()
    yml_content['display'] = 'legal words kfawh and some are not'
    yml_content['description'] = 'ggghghgh'
    integration.yml.write_dict(yml_content)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SPELL_CHECK, '-i', integration.yml.path], catch_exceptions=False)
        assert 'No misspelled words found ' not in result.stdout
        assert 'Words that might be misspelled were found in' in result.stdout
        assert 'kfawh' in result.stdout
        assert 'ggghghgh' in result.stdout


def test_spell_script_invalid(repo):
    pack = repo.create_pack('my_pack')
    script = pack.create_script('myscr')
    script.create_default_script()
    yml_content = script.yml.read_dict()
    yml_content['comment'] = 'legal words kfawh and some are not'
    arg_description = yml_content['args'][0].get('description') + ' some more ddddddd words '
    yml_content['args'][0]['description'] = arg_description
    script.yml.write_dict(yml_content)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SPELL_CHECK, '-i', script.yml.path], catch_exceptions=False)
        assert 'No misspelled words found ' not in result.stdout
        assert 'Words that might be misspelled were found in' in result.stdout
        assert 'kfawh' in result.stdout
        assert 'ddddddd' in result.stdout


def test_spell_playbook_invalid(repo):
    pack = repo.create_pack('my_pack')
    playbook = pack.create_playbook('myplaybook')
    playbook.create_default_playbook()
    yml_content = playbook.yml.read_dict()
    yml_content['description'] = 'legal words kfawh and some are not'
    task_description = yml_content['tasks']['0']['task'].get('description') + ' some more ddddddd words '
    yml_content['tasks']['0']['task']['description'] = task_description
    playbook.yml.write_dict(yml_content)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SPELL_CHECK, '-i', playbook.yml.path], catch_exceptions=False)
        assert 'No misspelled words found ' not in result.stdout
        assert 'Words that might be misspelled were found in' in result.stdout
        assert 'kfawh' in result.stdout
        assert 'ddddddd' in result.stdout


def test_spell_readme_invalid(repo):
    pack = repo.create_pack('my_pack')
    integration = pack.create_integration('myint')
    integration.create_default_integration()
    integration.readme.write("some weird readme which is not really a word. "
                             "and should be noted bellow - also hghghghgh\n"
                             "GoodCase stillGoodCase notGidCase")

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SPELL_CHECK, '-i', integration.readme.path,
                                      '--expand-dictionary'], catch_exceptions=False)
        assert 'No misspelled words found ' not in result.stdout
        assert 'Words that might be misspelled were found in' in result.stdout
        assert 'readme' in result.stdout
        assert 'hghghghgh' in result.stdout
        assert 'notGidCase' in result.stdout
        assert 'GoodCase' not in result.stdout
        assert 'stillGoodCase' not in result.stdout
