import git

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.format.format_module import format_manager
from TestSuite.repo import Repo

yaml = YAML_Handler()


class TestIDUpdates:
    REPO_NAME = 'example_repo'

    def make_git_content_repo(self, tmp_path):
        # create local git repo
        repo_path = tmp_path / self.REPO_NAME
        git_repo = git.Repo.init(repo_path)
        git_repo.git.config('user.email', 'automatic@example.com')
        git_repo.git.config('user.name', 'AutomaticTest')
        content_repo = Repo(repo_path)
        return git_repo, content_repo

    def test_new_id_is_modified(self, tmp_path):
        git_repo, content_repo = self.make_git_content_repo(tmp_path)
        pack = content_repo.create_pack('PackName')

        name = 'new_name'
        yml = {
            'commonfields': {'id': f'not_{name}', 'version': -1},
            'name': name,
            'display': name,
            'description': f'this is an integration {name}',
            'script': {
                'type': 'python',
                'subtype': 'python3',
                'script': '',
                'commands': [],
            },
        }

        integration = pack.integrations.create_integration(name=name, yml=yml)
        git_repo.git.commit('-m', 'test_commit', '-a')
        result = format_manager(None, None, no_validate=True, verbose=True, use_git=True)
        assert result == 0
        new_yml_dict = integration.yml.read_dict()
        assert new_yml_dict['commonfields']['id'] == new_yml_dict['name']
        assert new_yml_dict['commonfields']['id'] == name

    def test_old_ids_are_not_modified(self, repo):
        pass
