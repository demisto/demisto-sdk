import toml

CONFIG_FILE_PATH = "/Users/yhayun/dev/demisto/demisto-sdk/demisto_sdk/commands/validate_poc/validation_conf.toml"
USE_GIT = "use_git"
VALIDATE_ALL = "validate_all"
class ConfigReader:
    def __init__(self, config_file_path, category_to_run):
        if not config_file_path:
            config_file_path = CONFIG_FILE_PATH
        self.config_file_path = config_file_path
        self.config_file_content: dict = toml.load(self.config_file_path)
        self.category_to_run = category_to_run

    def gather_validations_to_run(self, use_git):
        flag = self.category_to_run or USE_GIT if use_git else VALIDATE_ALL
        section = self.config_file_content.get(flag, {})
        return (
            section.get("select"),
            section.get("ignore"),
            section.get("warning"),
            section.get("ignorable_errors"),
            self.config_file_content.get("support_level", {})
            
        )
