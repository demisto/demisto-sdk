import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import set_value
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from TestSuite.file import File
from TestSuite.test_suite_base import TestSuiteBase
from TestSuite.test_tools import suite_join_path
from TestSuite.yml import YAML

yaml = YAML_Handler()


class Integration(TestSuiteBase):
    def __init__(
        self,
        tmpdir: Path,
        name,
        repo,
        create_unified: Optional[bool] = False,
        _type: str = "python",
        unit_test_name: Optional[str] = None,
    ):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.prefix = "integration"
        # Create paths
        self._tmpdir_integration_path = tmpdir / f"{self.name}"
        self._tmpdir_integration_path.mkdir()

        # if creating a unified yaml
        self.create_unified = create_unified

        self.path = str(self._tmpdir_integration_path)
        self.type = _type
        if self.type == "python":
            self.code = File(
                self._tmpdir_integration_path / f"{self.name}.py", self._repo.path
            )
        else:
            self.code = File(
                self._tmpdir_integration_path / f"{self.name}.js", self._repo.path
            )
        self.test = File(
            self._tmpdir_integration_path / f"{unit_test_name or self.name}_test.py",
            self._repo.path,
        )
        self.yml = YAML(
            self._tmpdir_integration_path / f"{self.name}.yml", self._repo.path
        )
        self.readme = File(self._tmpdir_integration_path / "README.md", self._repo.path)
        self.description = File(
            self._tmpdir_integration_path / f"{self.name}_description.md",
            self._repo.path,
        )
        self.changelog = File(
            self._tmpdir_integration_path / "CHANGELOG.md", self._repo.path
        )
        self.image = File(
            self._tmpdir_integration_path / f"{self.name}_image.png", self._repo.path
        )
        self.commands_txt = File(
            self._tmpdir_integration_path / "commands.txt", self._repo.path
        )
        super().__init__(self._tmpdir_integration_path)

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
        """Writes not None objects to files."""
        # DIAGNOSTIC LOGGING: Track build process to debug race conditions
        print(  # noqa: T201
            f"[DIAGNOSTIC] Integration.build() called for: {self.path}",
            file=sys.stderr,
        )
        print(  # noqa: T201
            f"[DIAGNOSTIC] Directory exists: {os.path.exists(self.path)}",
            file=sys.stderr,
        )
        
        if code is not None:
            self.code.write(code)
        else:
            if self.type == "python":
                self.code.write("from CommonServerPython import *\n\n\n")
            else:  # javascript
                self.code.write("console.log('Hello World');")

        self.test.write("from CommonServerPython import *\n\n\n")

        if yml is None:
            yml = {}

        self.yml.write_dict(yml)
        if readme is not None:
            self.readme.write(readme)
        if description is not None:
            self.description.write(description)
        if changelog is not None:
            self.changelog.write(changelog)
        if image is not None:
            # DIAGNOSTIC LOGGING: Track image write
            print(  # noqa: T201
                f"[DIAGNOSTIC] About to write image to: {self.image.path}",
                file=sys.stderr,
            )
            print(  # noqa: T201
                f"[DIAGNOSTIC] Parent dir exists: {os.path.exists(os.path.dirname(self.image.path))}",
                file=sys.stderr,
            )
            self.image.write_bytes(image)
            print(  # noqa: T201
                f"[DIAGNOSTIC] Image written successfully to: {self.image.path}",
                file=sys.stderr,
            )
        if commands_txt is not None:
            self.commands_txt.write(commands_txt)
        if test is not None:
            self.test.write(test)

        if self.create_unified:
            output_yml_path = Path(self.path).with_name(
                f"{self.prefix}-{self.name}.yml"
            )
            self.yml = YAML(
                output_yml_path,
                self._repo.path,
                IntegrationScriptUnifier.unify(Path(self.yml.path), yml),
            )
            self.readme = File(
                output_yml_path.with_name(
                    output_yml_path.name.replace(".yml", "_README.md")
                ),
                self._repo.path,
            )
            self.path = str(output_yml_path)
            shutil.rmtree(self._tmpdir_integration_path)

    def create_default_integration(
        self, name: str = "Sample", commands: List[str] = None
    ):
        """Creates a new integration with basic data

        Args:
            name: The name and ID of the new integration, default is "Sample".
            commands: List of additional commands to add to the integration.

        """
        default_integration_dir = "assets/default_integration"

        with open(suite_join_path(default_integration_dir, "sample.py")) as code_file:
            code = str(code_file.read())
        with open(suite_join_path(default_integration_dir, "sample.yml")) as yml_file:
            yml = yaml.load(yml_file)
            yml["name"] = yml["commonfields"]["id"] = name
            if commands:
                for command in commands:
                    yml["script"]["commands"].append(
                        {"name": command, "description": f"{command}-description"}
                    )
        with open(
            suite_join_path(default_integration_dir, "sample_image.png"), "rb"
        ) as image_file:
            image = image_file.read()
        with open(
            suite_join_path(default_integration_dir, "CHANGELOG.md")
        ) as changelog_file:
            changelog = str(changelog_file.read())
        with open(
            suite_join_path(default_integration_dir, "sample_description.md")
        ) as description_file:
            description = str(description_file.read())

        self.build(
            code=code,
            yml=yml,
            image=image,
            changelog=changelog,
            description=description,
        )

    def set_data(self, **key_path_to_val):
        yml_contents = self.yml.read_dict()
        for key_path, val in key_path_to_val.items():
            set_value(yml_contents, key_path, val)
        self.yml.write_dict(yml_contents)
        self.clear_from_path_cache()

    def set_commands(self, commands: List[str]):
        commands_data = [
            {"name": command, "description": f"{command}-description"}
            for command in commands
        ]
        self.set_data(**{"script.commands": commands_data})
