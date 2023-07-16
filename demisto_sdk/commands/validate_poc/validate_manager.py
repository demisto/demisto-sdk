import toml

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate_poc.validators.base_validator import BaseValidator


class ValidateManager:
    def __init__(
        self,
        use_git=False,
        validate_all=False,
        file_path=None,
    ):
        self.files_to_run = self.gather_files_to_run(file_path, use_git, validate_all)
        self.validation_codes, self.run_using_select = self.gather_validations_to_run(use_git, validate_all)

    def run(self):
        results = []
        # gather validator from validate_poc package
        validators = BaseValidator.__subclasses__()
        for validator in validators:
            # if error in validation_codes the left = True if run_using_select = True then we get get True
            # if error in validation_codes the left = True if run_using_select = False then we get get False
            # if error in validation_codes the left = False if run_using_select = True then we get get False
            # if error in validation_codes the left = False if run_using_select = False then we get get True
            if (validator.error_code in self.validation_codes) == self.run_using_select:
                for content_item in self.files_to_run:
                    pack = content_item if isinstance(content_item, Pack) else content_item.in_pack
                    # if content item name is in pack ignore list, skip
                    if validator.should_run(content_item):
                        results.append(validator.is_valid(content_item))
            self.post_results(results)

    def gather_files_to_run(self, file_path, use_git, validate_all):
        # gather all files to run on (will be based on the given flag)
        files_to_run = ["test_data/test.yml"]
        return [BaseContent.from_path(file_to_run) for file_to_run in files_to_run]
        # if file_path:
            # get_all_files_in_path
        # elif validate_all:
            # gather all files
        # else:
            # gather all changed files
    
    def gather_validations_to_run(self, use_git, validate_all):
        flag = "use_git" if use_git else "validate_all"
        config: dict = toml.load("validation_conf.toml")
        if select := config.get(flag, {}).get("select"):
            validation_codes, run_using_select = select, True
        else:
            validation_codes, run_using_select = config.get(flag, {}).get("ignore"), False
        return validation_codes, run_using_select

    def post_results(self, results):
        pass
