import logging
from pathlib import Path


class Configuration:
    """Configuration was designed to make sure we have the necessary configuration to run SDK commands.

    Attributes:
        log_verbose (bool): whether the log should be verbose or not. default is False.
        sdk_env_dir (dict): SDK environment directory.
        env_dir (set): Current environment directory.
        envs_dirs_base (set): Environment directory base.
    """

    def __init__(self, log_verbose=False, logging_level=logging.INFO):
        logging.basicConfig(level=logging_level)
        self.log_verbose = log_verbose
        # refers to "demisto_sdk/commands" dir
        self.sdk_env_dir = str(Path(__file__).parent.parent)
        self.env_dir = str(Path().cwd())
        self.envs_dirs_base = str(
            Path(self.sdk_env_dir) / "lint" / "resources" / "pipfile_python"
        )
