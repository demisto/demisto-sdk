import os
import shutil
from pathlib import Path

import yaml
from demisto_sdk.commands.unify.unifier import Unifier
from TestSuite.integration import Integration
from TestSuite.test_tools import suite_join_path


class Script(Integration):
    # Im here just to have one!!!
    def __init__(self, tmpdir: Path, name, repo, create_unified=False):
        super().__init__(tmpdir, name, repo, create_unified)

    def create_default_script(self):
        default_script_dir = 'assets/default_script'
        code = open(suite_join_path(default_script_dir, 'sample_script.py'))
        yml = open(suite_join_path(default_script_dir, 'sample_script.yml'))
        image = open(suite_join_path(default_script_dir, 'sample_script_image.png'), 'rb')
        changelog = open(suite_join_path(default_script_dir, 'CHANGELOG.md'))
        description = open(suite_join_path(default_script_dir, 'sample_script_description.md'))
        self.build(
            code=str(code.read()),
            yml=yaml.load(yml, Loader=yaml.FullLoader),
            image=image.read(),
            changelog=str(changelog.read()),
            description=str(description.read())
        )
        yml.close()
        image.close()
        changelog.close()
        description.close()
        code.close()
        if self.create_unified:
            unifier = Unifier(input=self.path, output=os.path.dirname(self._tmpdir_integration_path))
            unifier.merge_script_package_to_yml()
            shutil.rmtree(self._tmpdir_integration_path)
