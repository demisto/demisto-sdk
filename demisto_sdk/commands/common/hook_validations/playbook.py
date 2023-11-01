import re
from typing import Dict, Set

from demisto_sdk.commands.common.constants import (
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import is_string_uuid


class PlaybookValidator(ContentEntityValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def __init__(
        self,
        structure_validator,
        ignored_errors=None,
        json_file_path=None,
        validate_all=False,
        deprecation_validator=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
        )
        self.validate_all = validate_all
        self.deprecation_validator = deprecation_validator

    def is_valid_playbook(
        self, validate_rn: bool = True, id_set_file=None, is_modified: bool = False
    ) -> bool:
        """Check whether the playbook is valid or not.

         Args:
            this will also determine whether a new id_set can be created by validate.
            validate_rn (bool):  whether we need to validate release notes or not
            is_modified (bool): Wether the given files are modified or not.
            id_set_file (dict): id_set.json file if exists, None otherwise

        Returns:
            bool. Whether the playbook is valid or not
        """
        if "TestPlaybooks" in self.file_path:
            logger.info(
                f"[yellow]Skipping validation for Test Playbook {self.file_path}[/yellow]"
            )
            return True
        playbook_checks = [
            super().is_valid_file(validate_rn),
            self.validate_readme_exists(self.validate_all),
            self.is_valid_version(),
            self.is_id_equals_name(),
            self.is_no_rolename(),
            self.is_root_connected_to_all_tasks(),
            self.is_using_instance(),
            self.is_condition_branches_handled(),
            self.are_default_conditions_valid(),
            self.is_delete_context_all_in_playbook(),
            self.are_tests_configured(),
            self.is_script_id_valid(id_set_file),
            self._is_id_uuid(),
            self._is_taskid_equals_id(),
            self._is_correct_value_references_interface(),
            self.name_not_contain_the_type(),
            self.is_valid_with_indicators_input(),
            self.inputs_in_use_check(is_modified),
            self.is_playbook_deprecated_and_used(),
        ]
        answers = all(playbook_checks)

        return answers

    def are_tests_configured(self) -> bool:
        """
        Checks if the playbook has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        file_type = self.structure_validator.scheme_name
        if not isinstance(file_type, str):
            file_type = file_type.value  # type: ignore

        tests = self.current_file.get("tests", [])
        return self.yml_has_test_key(tests, file_type)

    def is_id_equals_name(self) -> bool:
        """Check whether the playbook ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name("playbook")

    def is_valid_version(self) -> bool:
        """Check whether the playbook version is equal to DEFAULT_VERSION (see base_validator class)

        Return:
            bool. whether the version is valid or not
        """
        return self._is_valid_version()

    def collect_all_inputs_in_use(self) -> Set[str]:
        """

        Returns: Set of all inputs used in playbook.

        """
        result: set = set()
        with open(self.file_path) as f:
            playbook_text = f.read()
        all_inputs_occurrences = re.findall(r"inputs\.[-\w ?!():]+", playbook_text)
        for input in all_inputs_occurrences:
            input = input.strip()
            splitted = input.split(".")
            if len(splitted) > 1 and splitted[1] and not splitted[1].startswith(" "):
                result.add(splitted[1])
        return result

    def collect_all_inputs_from_inputs_section(self) -> Set[str]:
        """

        Returns: A set of all inputs defined in the 'inputs' section of playbook.

        """
        inputs: Dict = self.current_file.get("inputs", {})
        inputs_keys = []
        for input in inputs:
            if input["key"]:
                inputs_keys.append(input["key"].strip())
        return set(inputs_keys)

    def inputs_in_use_check(self, is_modified: bool) -> bool:
        """

        Args:
            is_modified: Wether the given files are modified or not.

        Returns:
            True if both directions for input use in playbook passes.

        """
        if not is_modified:
            return True
        inputs_in_use: set = self.collect_all_inputs_in_use()
        inputs_in_section: set = self.collect_all_inputs_from_inputs_section()
        all_inputs_in_use = self.are_all_inputs_in_use(inputs_in_use, inputs_in_section)
        are_all_used_inputs_in_inputs_section = (
            self.are_all_used_inputs_in_inputs_section(inputs_in_use, inputs_in_section)
        )
        return all_inputs_in_use and are_all_used_inputs_in_inputs_section

    @error_codes("PB118")
    def are_all_inputs_in_use(self, inputs_in_use: set, inputs_in_section: set) -> bool:
        """Check whether the playbook inputs are in use in any of the tasks

        Return:
            bool. if the Playbook inputs are in use.
        """

        inputs_not_in_use = inputs_in_section.difference(inputs_in_use)

        if inputs_not_in_use:
            playbook_name = self.current_file.get("name", "")
            error_message, error_code = Errors.input_key_not_in_tasks(
                playbook_name, sorted(inputs_not_in_use)
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

    @error_codes("PB119")
    def are_all_used_inputs_in_inputs_section(
        self, inputs_in_use: set, inputs_in_section: set
    ) -> bool:
        """Check whether the playbook inputs that in use appear in the input section.

        Return:
            bool. if the Playbook inputs appear in inputs section.
        """

        inputs_not_in_section = inputs_in_use.difference(inputs_in_section)

        if inputs_not_in_section:
            playbook_name = self.current_file.get("name", "")
            error_message, error_code = Errors.input_used_not_in_input_section(
                playbook_name, sorted(inputs_not_in_section)
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

    @error_codes("PB100")
    def is_no_rolename(self) -> bool:
        """Check whether the playbook has a rolename

        Return:
            bool. if the Playbook has a rolename it is not valid.
        """
        rolename = self.current_file.get("rolename", None)
        if rolename:
            error_message, error_code = Errors.playbook_cant_have_rolename()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_condition_branches_handled(self) -> bool:
        """Check whether the playbook conditional tasks has all optional branches handled

        Return:
            bool. if the Playbook handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        tasks: Dict = self.current_file.get("tasks", {})
        for task in tasks.values():
            if task.get("type") == "condition":
                # builtin conditional task
                if task.get("conditions"):
                    is_all_condition_branches_handled = (
                        self.is_builtin_condition_task_branches_handled(task)
                        and is_all_condition_branches_handled
                    )
                # ask conditional task
                elif task.get("message"):
                    is_all_condition_branches_handled = (
                        self.is_ask_condition_branches_handled(task)
                        and is_all_condition_branches_handled
                    )
                # script conditional task
                elif task.get("scriptName"):
                    is_all_condition_branches_handled = (
                        self.is_script_condition_branches_handled(task)
                        and is_all_condition_branches_handled
                    )
        return is_all_condition_branches_handled

    @error_codes("PB122")
    def is_builtin_condition_task_branches_handled(self, task: Dict) -> bool:
        """Checks whether a builtin conditional task branches are handled properly
        NOTE: The function uses str.upper() on branches to be case insensitive

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        # ADD all possible conditions to task_condition_labels (UPPER)
        # #default# condition should always exist in a builtin condition
        task_condition_labels = set()
        for condition in task.get("conditions", []):
            label = condition.get("label")
            if label:
                # Need to cast it to string because otherwise it's parsed as boolean
                task_condition_labels.add(str(label).upper())

        # REMOVE all used condition branches from task_condition_labels (UPPER)
        next_tasks: Dict = task.get("nexttasks", {})
        for next_task_branch in next_tasks.keys():
            try:
                if next_task_branch:
                    # Need to cast it to string because otherwise it's parsed as boolean
                    task_condition_labels.remove(str(next_task_branch).upper())
            except KeyError as e:
                # else doesn't have a path, skip error
                if "#DEFAULT#" == e.args[0]:
                    continue
                error_message, error_code = Errors.playbook_unhandled_task_branches(
                    task.get("id"), next_task_branch
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = is_all_condition_branches_handled = False

        # if there are task_condition_labels left then not all branches are handled
        if task_condition_labels:
            error_message, error_code = Errors.playbook_unhandled_task_branches(
                task.get("id"), task_condition_labels
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False

        return is_all_condition_branches_handled

    @error_codes("PB101,PB123")
    def is_ask_condition_branches_handled(self, task: Dict) -> bool:
        """Checks whether a builtin conditional task branches are handled properly
        NOTE: The function uses str.upper() on branches to be case insensitive

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get("nexttasks", {})

        # ADD all replyOptions to unhandled_reply_options (UPPER)
        unhandled_reply_options = set(
            map(str.upper, task.get("message", {}).get("replyOptions", []))
        )

        # Rename the keys in dictionary to upper case
        next_tasks_upper = {k.upper(): v for k, v in next_tasks.items()}

        mapper_dict = {
            "YES": ["YES", "TRUE POSITIVE"],
            "TRUE POSITIVE": ["YES", "TRUE POSITIVE"],
            "NO": ["NO", "FALSE POSITIVE"],
            "FALSE POSITIVE": ["NO", "FALSE POSITIVE"],
        }

        # Remove all nexttasks from unhandled_reply_options (UPPER)
        for next_task_branch, next_task_id in next_tasks_upper.items():
            key_to_remove = None
            if next_task_id and next_task_branch != "#DEFAULT#":
                for mapping in mapper_dict.get(next_task_branch, [next_task_branch]):
                    if mapping in unhandled_reply_options:
                        key_to_remove = mapping
                if key_to_remove:
                    unhandled_reply_options.remove(key_to_remove)
                else:
                    error_message, error_code = Errors.playbook_unreachable_condition(
                        task.get("id"), next_task_branch
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        self.is_valid = is_all_condition_branches_handled = False

        if unhandled_reply_options:
            # if there's only one unhandled_reply_options and there's a #default#
            # then all good.
            # Otherwise - Error
            if not (
                len(unhandled_reply_options) == 1 and "#DEFAULT#" in next_tasks_upper
            ):
                error_message, error_code = Errors.playbook_unhandled_reply_options(
                    task.get("id"), unhandled_reply_options
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = is_all_condition_branches_handled = False
        return is_all_condition_branches_handled

    @error_codes("PB124")
    def is_script_condition_branches_handled(self, task: Dict) -> bool:
        """Checks whether a script conditional task branches are handled properly

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get("nexttasks", {})

        if len(next_tasks) < 2:
            # there should be at least 2 next tasks, we don't know what condition is missing, but we know it's missing
            (
                error_message,
                error_code,
            ) = Errors.playbook_unhandled_script_condition_branches(task.get("id"), {})
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False

        return is_all_condition_branches_handled

    def are_default_conditions_valid(self) -> bool:
        """Check whether the playbook conditional tasks' default options are valid

        Return:
            bool. if the Playbook's handles all condition default options correctly.
        """
        default_conditions_valid: bool = True
        tasks: Dict = self.current_file.get("tasks", {})
        for task in tasks.values():
            if task.get("type") == "condition":
                # builtin conditional task
                if task.get("nexttasks"):
                    default_conditions_valid = (
                        self.is_default_not_only_condition(task)
                        and default_conditions_valid
                    )
                # ask conditional task
                if task.get("message") and task.get("message").get("replyOptions"):
                    default_conditions_valid = (
                        self.is_default_not_only_reply_option(task)
                        and default_conditions_valid
                    )
        return default_conditions_valid

    @error_codes("PB125")
    def is_default_not_only_condition(self, task: Dict) -> bool:
        """Checks whether the #default# is the only branch

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task's next tasks have more than just the default option.
        """
        is_default_not_only_condition_res: bool = True
        next_tasks: Dict = task.get("nexttasks", {})

        # Rename the keys in dictionary to upper case
        next_tasks_upper = {k.upper(): v for k, v in next_tasks.items()}
        default_upper = "#default#".upper()
        found_non_default_next_task = False
        for current_next_task_upper in next_tasks_upper:
            if default_upper != current_next_task_upper:
                found_non_default_next_task = True

        if not found_non_default_next_task:
            error_message, error_code = Errors.playbook_only_default_next(
                task.get("id")
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_default_not_only_condition_res = False

        return is_default_not_only_condition_res

    @error_codes("PB126")
    def is_default_not_only_reply_option(self, task: Dict) -> bool:
        """Checks whether #default# is the only reply option

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task reply options have more than just the default option.
        """
        is_default_not_only_reply_option_res: bool = True

        reply_options = set(
            map(str.upper, task.get("message", {}).get("replyOptions", []))
        )

        if len(reply_options) == 1 and "#default#".upper() in reply_options:
            error_message, error_code = Errors.playbook_only_default_reply_option(
                task.get("id")
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_default_not_only_reply_option_res = False

        return is_default_not_only_reply_option_res

    @error_codes("PB103")
    def is_root_connected_to_all_tasks(self) -> bool:
        """Check whether the playbook root is connected to all tasks

        Return:
            bool. if the Playbook has root is connected to all tasks.
        """
        start_task_id = self.current_file.get("starttaskid")
        tasks = self.current_file.get("tasks", {})
        tasks_bucket = set()
        next_tasks_bucket = set()
        for task_id, task in tasks.items():
            if task_id != start_task_id:
                tasks_bucket.add(task_id)
            next_tasks = task.get("nexttasks", {})
            for next_task_ids in next_tasks.values():
                if next_task_ids:
                    next_tasks_bucket.update(next_task_ids)
        orphan_tasks = tasks_bucket.difference(next_tasks_bucket)
        if orphan_tasks:
            error_message, error_code = Errors.playbook_unconnected_tasks(orphan_tasks)
            if not self.handle_error(
                error_message, error_code, file_path=self.file_path
            ):
                return False

        return tasks_bucket.issubset(next_tasks_bucket)

    @error_codes("PB104")
    def is_valid_as_deprecated(self) -> bool:
        is_deprecated = self.current_file.get("deprecated", False)
        description = self.current_file.get("description", "")

        if is_deprecated and not any(
            (
                re.search(DEPRECATED_DESC_REGEX, description),
                re.search(DEPRECATED_NO_REPLACE_DESC_REGEX, description),
            )
        ):
            error_message, error_code = Errors.invalid_deprecated_playbook()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("PB105")
    def is_delete_context_all_in_playbook(self) -> bool:
        """
        Check if delete context all=yes exist in playbook.
        Returns:
            True if delete context exists else False.
        """
        tasks: Dict = self.current_file.get("tasks", {})
        for task in tasks.values():
            curr_task = task.get("task", {})
            scriptargs = task.get("scriptarguments", {})
            if (
                curr_task
                and scriptargs
                and curr_task.get("scriptName", "") == "DeleteContext"
                and scriptargs.get("all", {}).get("simple", "") == "yes"
            ):
                (
                    error_message,
                    error_code,
                ) = Errors.playbook_cant_have_deletecontext_all()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = False
                    return False
        return True

    @error_codes("PB106")
    def is_using_instance(self) -> bool:
        """
        Check if there is an existing task that uses specific instance.
        Returns:
            True if using specific instance exists else False.
        """
        tasks: Dict = self.current_file.get("tasks", {})
        for task in tasks.values():
            scriptargs = task.get("scriptarguments", {})
            if scriptargs and scriptargs.get("using", {}):
                error_message, error_code = Errors.using_instance_in_playbook()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = False
                    return False
        return True

    @error_codes("PB107")
    def is_script_id_valid(self, id_set_file):
        """Checks whether a script id is valid (i.e id exists in set_id)
        Args:
            id_set_file (dict): id_set.json file
            this will also determine whether a new id_set can be created by validate.

        Return:
            bool. if all scripts ids of this playbook are valid.
        """

        if not id_set_file:
            logger.info(
                "[yellow]Skipping playbook script id validation. Could not read id_set.json.[/yellow]"
            )
            return True

        id_set_scripts = id_set_file.get("scripts")
        id_set_integrations = id_set_file.get("integrations")
        pb_tasks = self.current_file.get("tasks", {})
        for id, task_dict in pb_tasks.items():
            is_valid = True
            pb_task = task_dict.get("task", {})
            script_id_used_in_task = pb_task.get("script")
            task_script_name = pb_task.get("scriptName")
            script_entry_to_check = (
                script_id_used_in_task if script_id_used_in_task else task_script_name
            )
            integration_script_flag = "|||"
            if script_id_used_in_task:
                if (
                    integration_script_flag not in script_id_used_in_task
                ):  # Checking script
                    is_valid &= self.check_script_id(
                        script_id_used_in_task, id_set_scripts
                    )
                else:  # Checking integration command
                    is_valid &= self.check_integration_command(
                        script_id_used_in_task, id_set_integrations
                    )
            if task_script_name and integration_script_flag not in task_script_name:
                # if there is 'scriptName' and it is not integration
                is_valid &= self.check_script_name(task_script_name, id_set_scripts)

            if not is_valid:
                error_message, error_code = Errors.invalid_script_id(
                    script_entry_to_check, pb_task
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    def check_script_id(self, script_id_used_in_task, id_set_scripts):
        """
        Checks if script id exists in at least one of id_set's dicts
        Args:
            script_id_used_in_task (str):  script id from playbook
            id_set_scripts (list): all scripts of id_set
        Returns:
            True if script_used_in_task exists in id_set
        """
        return any(
            [script_id_used_in_task in id_set_dict for id_set_dict in id_set_scripts]
        )

    def check_integration_command(
        self,
        integration_id_used_in_task,
        id_set_integrations,
        command_without_brand=True,
    ):
        """
        Checks if integration id and command exists in at least one of id_set's dicts
        Args:
            integration_id_used_in_task (str):  integration id from playbook
            id_set_integrations (list): all integrations of id_set
            command_without_brand (bool): Whether the case that the command does not include the
            brand/integration name is legal.
             i.e.: |||Command is legal or not. true - legal, false - not
        Returns:
            True if integration_id and integration_command exist in id_set
        """
        integration_id, integration_command = integration_id_used_in_task.split("|||")
        if integration_id == "Builtin":  # skipping Builtin
            return True
        for id_integration_dict in id_set_integrations:
            id_integration_id = list(id_integration_dict.keys())[0]
            if (
                command_without_brand and not integration_id
            ) or id_integration_id == integration_id:
                commands = id_integration_dict.get(id_integration_id, {}).get(
                    "commands", []
                )
                if integration_command in commands:
                    return True
        return False

    def check_script_name(self, pb_script_name, id_set_scripts):
        """
        Checks if script name exists in at least one of id_set's dicts as value of the key 'name'
        Args:
            pb_script_name (str):  script name from playbook
            id_set_scripts (list): all scripts of id_set
        Returns:
            True if pb_script_name exists in id_set
        """
        return any(
            [
                pb_script_name == id_set_dict[key].get("name")
                for id_set_dict in id_set_scripts
                for key in id_set_dict
            ]
        )

    def _is_else_path_in_condition_task(self, task):
        next_tasks: Dict = task.get("nexttasks", {})
        return "#default#" in next_tasks

    @error_codes("PB108")
    def _is_id_uuid(self):
        """
        Check that the taskid field and the id field under the task field are both on from uuid format
        Returns: True if the ids are uuid
        """
        is_valid = True
        tasks: dict = self.current_file.get("tasks", {})
        for task_key, task in tasks.items():
            taskid = str(task.get("taskid", ""))
            inner_id = str(task.get("task", {}).get("id", ""))
            is_valid_task = is_string_uuid(taskid) and is_string_uuid(inner_id)

            if not is_valid_task:
                is_valid = is_valid_task
                error_message, error_code = Errors.invalid_uuid(
                    task_key, taskid, inner_id
                )
                self.handle_error(
                    error_message, error_code, file_path=self.file_path
                )  # Does not break after one
                # invalid task in order to raise error for all the invalid tasks at the file

        return is_valid

    @error_codes("PB109")
    def _is_taskid_equals_id(self):
        """
        Check that taskid field and id field under task field contains equal values
        Returns: True if the values are equal

        """
        is_valid = True
        tasks: dict = self.current_file.get("tasks", {})
        for task_key, task in tasks.items():
            taskid = task.get("taskid", "")
            inner_id = task.get("task", {}).get("id", "")
            is_valid_task = taskid == inner_id

            if not is_valid_task:
                is_valid = is_valid_task
                error_message, error_code = Errors.taskid_different_from_id(
                    task_key, taskid, inner_id
                )
                self.handle_error(
                    error_message, error_code, file_path=self.file_path
                )  # Does not break after one
                # invalid task in order to raise error for all the invalid tasks at the file

        return is_valid

    @error_codes("PB121")
    def _is_correct_value_references_interface(self):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>}
        Returns: True if the references are correct
        """
        answers = []
        tasks: dict = self.current_file.get("tasks", {})
        for task_id, task in tasks.items():
            task_name = task.get("task", {}).get("name", "")
            tasks_check = [
                self.handle_condition_task(task, task_id, task_name),
                self.handle_regular_task(task, task_id, task_name),
                self.handle_data_collection(task, task_id, task_name),
            ]
            answers.extend(tasks_check)

        answers.append(self.handle_playbook_inputs(self.current_file.get("inputs", [])))
        return all(answers)

    def handle_condition_task(self, task, task_id, task_name):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a condition task
        Returns: True if the references are correct
        """
        is_valid = True
        if task.get("type") == "condition":
            for conditions in task.get("conditions", []):
                for condition in conditions.get("condition"):
                    for condition_info in condition:
                        if (
                            value := condition_info.get("left", {})
                            .get("value", {})
                            .get("simple", "")
                        ):
                            if not self.handle_incorrect_reference_value(
                                task_id,
                                value,
                                task_name,
                                "condition",
                                condition_info.get("left", {}),
                            ):
                                is_valid = False

                        elif (
                            value := condition_info.get("left", {})
                            .get("value", {})
                            .get("complex", {})
                        ):
                            if not self.handle_transformers_and_filters(
                                value, task_id, task_name, "condition"
                            ):
                                is_valid = False

                        if (
                            value := condition_info.get("right", {})
                            .get("value", {})
                            .get("simple", "")
                        ):
                            if not self.handle_incorrect_reference_value(
                                task_id,
                                value,
                                task_name,
                                "condition",
                                condition_info.get("right", {}),
                            ):
                                is_valid = False

                        elif (
                            value := condition_info.get("right", {})
                            .get("value", {})
                            .get("complex", {})
                        ):
                            if not self.handle_transformers_and_filters(
                                value, task_id, task_name, "condition"
                            ):
                                is_valid = False

            for message_key, message_value in task.get("message", {}).items():
                if not self.handle_message_value(
                    message_key, message_value, task_id, task_name
                ):
                    is_valid = False

            for script_argument in task.get("scriptarguments", {}).values():
                if not self.handle_script_arguments(
                    script_argument, task_id, task_name
                ):
                    is_valid = False

        return is_valid

    def handle_regular_task(self, task, task_id, task_name):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a regular task
        Returns: True if the references are correct
        """
        is_valid = True
        if task.get("type") == "regular":
            if default_assignee := task.get("defaultassigneecomplex", {}).get(
                "simple", ""
            ):
                if not self.handle_incorrect_reference_value(
                    task_id, default_assignee, task_name, "default assignee"
                ):
                    is_valid = False

            elif default_assignee := task.get("defaultassigneecomplex", {}).get(
                "complex", {}
            ):
                if not self.handle_transformers_and_filters(
                    default_assignee, task_id, task_name, "default assignee"
                ):
                    is_valid = False

            for script_argument in task.get("scriptarguments", {}).values():
                if not self.handle_script_arguments(
                    script_argument, task_id, task_name
                ):
                    is_valid = False

            for incident_field in task.get("fieldMapping", []):
                field_output = incident_field.get("output", {}).get("complex", {})
                if not self.handle_transformers_and_filters(
                    field_output, task_id, task_name, "field mapping"
                ):
                    is_valid = False

        return is_valid

    def handle_data_collection(self, task, task_id, task_name):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a data collection task
        Returns: True if the references are correct
        """
        is_valid = True
        if task.get("type") == "collection":
            for script_argument in task.get("scriptarguments", {}).values():
                if not self.handle_script_arguments(
                    script_argument, task_id, task_name
                ):
                    is_valid = False

        for message_key, message_value in task.get("message", {}).items():
            if not self.handle_message_value(
                message_key, message_value, task_id, task_name
            ):
                is_valid = False

        for form_question in task.get("form", {}).get("questions", []):
            if form_question.get("labelarg"):
                if value := form_question.get("labelarg", {}).get("simple", ""):
                    if not self.handle_incorrect_reference_value(
                        task_id, value, task_name, "form question", form_question
                    ):
                        is_valid = False

                elif value := form_question.get("labelarg", {}).get("complex", {}):
                    if not self.handle_transformers_and_filters(
                        value, "inputs", task_name, "form question"
                    ):
                        is_valid = False

        return is_valid

    def handle_playbook_inputs(self, inputs):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in the inputs section
        Returns: True if the references are correct
        """
        is_valid = True
        for playbook_input in inputs:
            if value := playbook_input.get("value", {}).get("simple", ""):
                if not self.handle_incorrect_reference_value(
                    "inputs", value, "inputs", "playbook inputs", playbook_input
                ):
                    is_valid = False

            elif complex_value := playbook_input.get("value", {}).get("complex", {}):
                if not self.handle_transformers_and_filters(
                    complex_value, "inputs", "inputs", "playbook inputs"
                ):
                    is_valid = False

        return is_valid

    def handle_transformers_and_filters(
        self, field_output: dict, task_id, task_name, section_name
    ):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a transformers and filters section.
        Returns: True if the references are correct
        """
        is_valid = True
        filters = field_output.get("filters", [])
        for incident_filter in filters:
            for filter_info in incident_filter:
                if (
                    value := filter_info.get("left", {})
                    .get("value", {})
                    .get("simple", "")
                ):
                    if not self.handle_incorrect_reference_value(
                        task_id,
                        value,
                        task_name,
                        section_name,
                        filter_info.get("left", {}),
                    ):
                        is_valid = False

                if (
                    value := filter_info.get("right", {})
                    .get("value", {})
                    .get("simple", "")
                ):
                    if not self.handle_incorrect_reference_value(
                        task_id,
                        value,
                        task_name,
                        section_name,
                        filter_info.get("right", {}),
                    ):
                        is_valid = False

        for transformer in field_output.get("transformers", []):
            for _, arg_info in transformer.get("args", {}).items():
                if value := arg_info.get("value", {}).get("simple", ""):
                    if not self.handle_incorrect_reference_value(
                        task_id, value, task_name, section_name, arg_info
                    ):
                        is_valid = False

        return is_valid

    def handle_script_arguments(self, script_argument: dict, task_id, task_name):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a script arguments section.
        Returns: True if the references are correct
        """
        is_valid = True
        if arg_value := script_argument.get("simple", ""):
            if not self.handle_incorrect_reference_value(
                task_id, arg_value, task_name, "script arguments"
            ):
                is_valid = False

        elif arg_value := script_argument.get("complex", {}):
            if not self.handle_transformers_and_filters(
                arg_value, task_id, task_name, "script arguments"
            ):
                is_valid = False

        return is_valid

    def handle_message_value(self, message_key, message_value, task_id, task_name):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a message section.
        Returns: True if the references are correct
        """
        is_valid = True
        if message_key and message_value:
            if isinstance(message_value, dict):
                if value := message_value.get("simple", ""):
                    if not self.handle_incorrect_reference_value(
                        task_id, value, task_name, "message"
                    ):
                        is_valid = False

                elif value := message_value.get("complex", {}):
                    if not self.handle_transformers_and_filters(
                        value, task_id, task_name, "message"
                    ):
                        is_valid = False

        return is_valid

    def handle_incorrect_reference_value(
        self, task_id, values, task_name, section_name, value_info: dict = {}
    ):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        Returns: True if the references are correct
        """
        is_valid = True
        split_values = values.split(",") if isinstance(values, str) else ()
        for value in split_values:
            if value.startswith("incident.") or value.startswith("inputs."):
                if not value_info.get("iscontext", ""):
                    error_message, error_code = Errors.incorrect_value_references(
                        task_id, value, task_name, section_name
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        self.is_valid = False
                        is_valid = False

        return is_valid

    @error_codes("BA110")
    def name_not_contain_the_type(self):
        """
        Check that the entity name does not contain the entity type
        Returns: True if the name is valid
        """

        name = self.current_file.get("name", "")
        if "playbook" in name.lower():
            error_message, error_code = Errors.field_contain_forbidden_word(
                field_names=["name"], word="playbook"
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

    def is_valid_with_indicators_input(self):
        input_data = self.current_file.get("inputs", [])
        for item in input_data:
            entity = (
                item["playbookInputQuery"].get("queryEntity", "")
                if item.get("playbookInputQuery", None)
                else None
            )
            if entity == "indicators":
                answer = [
                    self.is_playbook_quiet_mode(),
                    self.is_tasks_quiet_mode(),
                    self.is_stopping_on_error(),
                ]
                return all(answer)
        return True

    @error_codes("PB114")
    def is_playbook_quiet_mode(self):
        if not self.current_file.get("quiet", False):
            error_message, error_code = Errors.playbook_not_quiet_mode()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("PB115")
    def is_tasks_quiet_mode(self):
        not_quiet = []
        tasks: dict = self.current_file.get("tasks", {})
        for task_key, task in tasks.items():
            if task.get("quietmode", 0) == 2:
                not_quiet.append(task_key)
        if not_quiet:
            error_message, error_code = Errors.playbook_tasks_not_quiet_mode(not_quiet)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("PB116")
    def is_stopping_on_error(self):
        continue_tasks = []
        tasks: dict = self.current_file.get("tasks", {})
        for task_key, task in tasks.items():
            if task.get("continueonerror", False):
                continue_tasks.append(task_key)
        if continue_tasks:
            error_message, error_code = Errors.playbook_tasks_continue_on_error(
                continue_tasks
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("PB120")
    def is_playbook_deprecated_and_used(self):
        """
        Checks if the playbook is deprecated and is used in other none-deprcated playbooks.

        Return:
            bool: True if the playbook isn't deprecated
            or if the playbook is deprecated but isn't used in any non-deprecated playbooks.
            False if the playbook is deprecated and used in a non-deprecated playbook.
        """
        is_valid = True

        if self.current_file.get("deprecated"):
            used_files_list = self.deprecation_validator.validate_playbook_deprecation(
                self.current_file.get("name")
            )
            if used_files_list:
                error_message, error_code = Errors.playbook_is_deprecated_and_used(
                    self.current_file.get("name"), used_files_list
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    is_valid = False

        return is_valid
