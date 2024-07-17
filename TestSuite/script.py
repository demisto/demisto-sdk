import shutil
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.integration import Integration
from TestSuite.test_tools import suite_join_path

yaml = YAML_Handler()


class Script(Integration):
    # Im here just to have one!!!
    def __init__(
        self, tmpdir: Path, name, repo, create_unified=False, _type: str = "python"
    ):
        super().__init__(tmpdir, name, repo, create_unified, _type)
        self.prefix = "script"

    def create_default_script(self, name: str = "sample_script"):
        """Creates a new script with basic data.

        Args:
            name: The name and ID of the new script, default is "sample_script".

        """

        default_script_dir = "assets/default_script"

        with open(suite_join_path(default_script_dir, "sample_script.py")) as code_file:
            code = str(code_file.read())
        with open(suite_join_path(default_script_dir, "sample_script.yml")) as yml_file:
            yml = yaml.load(yml_file)
            yml["name"] = yml["commonfields"]["id"] = name
        with open(
            suite_join_path(default_script_dir, "sample_script_image.png"), "rb"
        ) as image_file:
            image = image_file.read()
        with open(
            suite_join_path(default_script_dir, "CHANGELOG.md")
        ) as changelog_file:
            changelog = str(changelog_file.read())
        with open(
            suite_join_path(default_script_dir, "sample_script_description.md")
        ) as description_file:
            description = str(description_file.read())

        self.build(
            code=code,
            yml=yml,
            image=image,
            changelog=changelog,
            description=description,
        )

    def build(
        self,
        code: Optional[str] = None,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[str] = None,
        image: Optional[bytes] = None,
        commands_txt: Optional[str] = None,
        test: Optional[str] = None,
    ):
        super().build(
            code, yml, readme, description, changelog, image, commands_txt, test
        )
        if self.create_unified:
            script_yml_path = Path(self.path).with_name(
                Path(self.path).name.replace("integration-", "script-")
            )
            readme_path = Path(self.readme.path).with_name(
                Path(self.readme.path).name.replace("integration-", "script-")
            )
            shutil.move(self.yml.path, script_yml_path)
            shutil.move(self.readme.path, readme_path)
            self.yml.path = str(script_yml_path)
            self.path = str(script_yml_path)
            self.readme.path = str(readme_path)
