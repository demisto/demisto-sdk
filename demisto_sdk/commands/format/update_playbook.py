import os
import uuid
from typing import Tuple, Union

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    PLAYBOOK,
    FileType,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_yaml,
    is_string_uuid,
    remove_copy_and_dev_suffixes_from_str,
    write_dict,
)
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SCHEMAS_PATH,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class BasePlaybookYMLFormat(BaseUpdateYML):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        assume_answer: Union[bool, None] = None,
        deprecate: bool = False,
        add_tests: bool = False,
        interactive: bool = True,
        clear_cache: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            assume_answer=assume_answer,
            deprecate=deprecate,
            add_tests=add_tests,
            interactive=interactive,
            clear_cache=clear_cache,
        )

    def add_description(self):
        """Add empty description to playbook and tasks."""
        logger.debug("Adding descriptions for the playbook and to relevant tasks")
        if "description" not in set(self.data.keys()):
            logger.info(
                "<red>No description is specified for this playbook, would you like to add a description? [Y/n]</red>"
            )
            user_answer = (
                "y"
                if self.assume_answer
                else "n"
                if self.assume_answer is False
                else ""
            )
            while not user_answer:
                user_answer = input()
                if user_answer in ["n", "N", "no", "No"]:
                    user_description = ""
                    self.data["description"] = user_description
                elif user_answer in ["y", "Y", "yes", "Yes"]:
                    if self.interactive:
                        user_description = input("Please enter the description\n")
                    else:
                        user_description = ""
                    self.data["description"] = user_description
                else:
                    logger.info(
                        "<red>Invalid input, would you like to add a description? [Y/n]</red>"
                    )
                    user_answer = ""

        for task_id, task in self.data.get("tasks", {}).items():
            if not task["task"].get("description") and task["type"] in [
                "title",
                "start",
                "playbook",
            ]:
                task["task"].update({"description": ""})

    def update_task_uuid(self):
        """If taskid field and the id under the task field are not from uuid type, generate uuid instead"""
        for task_key, task in self.data.get("tasks", {}).items():
            taskid = str(task.get("taskid", ""))
            task_id_under_task = str(task.get("task", {}).get("id", ""))
            if not is_string_uuid(taskid) or not is_string_uuid(task_id_under_task):
                logger.debug(
                    f"Taskid field and the id under task field must be from uuid format. Generating uuid "
                    f"for those fields under task key: {task_key}"
                )
                generated_uuid = str(uuid.uuid4())
                task["taskid"] = generated_uuid
                task["task"]["id"] = generated_uuid

    def run_format(self) -> int:
        self.update_playbook_usages()
        super().update_yml(
            default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION[FileType.PLAYBOOK],
            file_type=PLAYBOOK,
        )
        self.add_description()
        self.update_task_uuid()
        self.save_yml_to_destination_file()
        return SUCCESS_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the playbook YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def update_playbook_usages(self) -> None:
        """Check if the current playbook is used as a sub-playbook in other changed playbooks.
        Change the playbook's id in the tasks id needed.
        """
        current_playbook_id = str(self.data.get("id"))
        new_playbook_id = str(self.data.get("name"))

        # if the id and name are the same - there is no need for this format.
        if current_playbook_id == new_playbook_id:
            return

        # gather all the changed files - if the formatted playbook was
        # modified then any additional playbook changes were changed alongside it -
        # we would use git to gather all other changed playbooks
        try:
            git_util = GitUtil()
            modified_files = git_util.modified_files(include_untracked=True)
            added_files = git_util.added_files(include_untracked=True)
            renamed_files = git_util.renamed_files(
                include_untracked=True, get_only_current_file_names=True
            )

            all_changed_files = modified_files.union(added_files).union(renamed_files)  # type: ignore[arg-type]

        except (InvalidGitRepositoryError, TypeError) as e:
            logger.info("Unable to connect to git - skipping sub-playbook checks")
            logger.debug(f"The error: {e}")
            return

        for file_path in all_changed_files:
            self.check_for_subplaybook_usages(
                str(file_path), current_playbook_id, new_playbook_id
            )

    def check_for_subplaybook_usages(
        self, file_path: str, current_playbook_id: str, new_playbook_id: str
    ) -> None:
        """Check if the current_playbook_id appears in the file's playbook type tasks and change it if needed.

        Arguments:
            file_path (str): The file path to check.
            current_playbook_id (str): The current playbook ID.
            new_playbook_id (str): The new playbook ID.
        """
        updated_tasks = []
        # if the changed file is a playbook get it's data
        if find_type(file_path) in [FileType.PLAYBOOK, FileType.TEST_PLAYBOOK]:
            playbook_data = get_yaml(file_path)
            # go through all the tasks
            for task_id, task_data in playbook_data.get("tasks").items():
                # if a task is of playbook type
                if task_data.get("type") == "playbook":
                    id_key = (
                        "playbookId"
                        if "playbookId" in task_data.get("task")
                        else "playbookName"
                    )
                    # make sure the playbookId or playbookName use the new id and not the old
                    if task_data.get("task", {}).get(id_key) == current_playbook_id:
                        playbook_data["tasks"][task_id]["task"][id_key] = (
                            new_playbook_id
                        )
                        updated_tasks.append(task_id)

            # if any tasks were changed re-write the playbook
            if updated_tasks:
                logger.debug(
                    f"Found usage of playbook in {file_path} tasks: "
                    f'{" ".join(updated_tasks)} - Updating playbookId'
                )
                write_dict(file_path, playbook_data)


class PlaybookYMLFormat(BasePlaybookYMLFormat):
    """PlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
    """

    def delete_sourceplaybookid(self):
        """Delete the not needed sourceplaybookid fields"""
        logger.debug("Removing sourceplaybookid field from playbook")
        if "sourceplaybookid" in self.data:
            self.data.pop("sourceplaybookid", None)

    def remove_copy_and_dev_suffixes_from_subplaybook(self):
        for task_id, task in self.data.get("tasks", {}).items():
            if task["task"].get("playbookName"):
                task["task"]["playbookName"] = remove_copy_and_dev_suffixes_from_str(
                    task["task"].get("playbookName")
                )

                task["task"]["name"] = remove_copy_and_dev_suffixes_from_str(
                    task["task"].get("name")
                )

    def remove_copy_and_dev_suffixes_from_subscripts(self):
        for task_id, task in self.data.get("tasks", {}).items():
            if task["task"].get("scriptName"):
                task["task"]["scriptName"] = remove_copy_and_dev_suffixes_from_str(
                    task["task"].get("scriptName")
                )

    def remove_empty_fields_from_scripts(self):
        """Removes unnecessary empty fields from SetIncident, SetIndicator, CreateNewIncident, CreateNewIndicator
        scripts"""

        scripts = [
            "setIncident",
            "setIndicator",
            "createNewIncident",
            "createNewIndicator",
        ]
        for task_id, task in self.data.get("tasks", {}).items():
            current_task_script = task.get("task", {}).get("script", "")
            if any(script in current_task_script for script in scripts):
                script_args = task.get("scriptarguments", {})
                for key in list(script_args):
                    if not script_args[key]:  # if value is empty
                        script_args.pop(key)

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n<blue>================= Updating file {self.source_file} =================</blue>"
            )
            self.update_tests()
            self.remove_copy_and_dev_suffixes_from_subplaybook()
            self.remove_copy_and_dev_suffixes_from_subscripts()
            self.update_conf_json("playbook")
            self.delete_sourceplaybookid()
            self.remove_empty_fields_from_scripts()
            super().run_format()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
            )
            return ERROR_RETURN_CODE


class TestPlaybookYMLFormat(BasePlaybookYMLFormat):
    """TestPlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(self, *args, **kwargs):
        kwargs["path"] = os.path.normpath(
            os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, "playbook.yml")
        )
        super().__init__(*args, **kwargs)

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n<blue>================= Updating file {self.source_file} =================</blue>"
            )
            return super().run_format()
        except Exception as err:
            logger.info(
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
            )
            return ERROR_RETURN_CODE
