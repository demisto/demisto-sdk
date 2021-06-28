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

    def create_default_script(self, name: str = None):
        """Creates a new script with basic data.

        Args:
            name: The name and ID of the new script, default is "sample_script".

        """

        default_script_dir = 'assets/default_script'

        with open(suite_join_path(default_script_dir, 'sample_script.py')) as code_file:
            code = str(code_file.read())
        with open(suite_join_path(default_script_dir, 'sample_script.yml')) as yml_file:
            yml = yaml.load(yml_file, Loader=yaml.FullLoader)
            if name:
                yml['name'] = yml['commonfields']['id'] = name
        with open(suite_join_path(default_script_dir, 'sample_script_image.png'), 'rb') as image_file:
            image = image_file.read()
        with open(suite_join_path(default_script_dir, 'CHANGELOG.md')) as changelog_file:
            changelog = str(changelog_file.read())
        with open(suite_join_path(default_script_dir, 'sample_script_description.md')) as description_file:
            description = str(description_file.read())

        self.build(
            code=code,
            yml=yml,
            image=image,
            changelog=changelog,
            description=description
        )

        if self.create_unified:
            unifier = Unifier(input=self.path, output=os.path.dirname(self._tmpdir_integration_path))
            unifier.merge_script_package_to_yml()
            shutil.rmtree(self._tmpdir_integration_path)
