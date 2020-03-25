import os
import logging


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
        self.sdk_env_dir = os.path.dirname(os.path.dirname(os.path.join(__file__)))
        self.env_dir = os.getcwd()
        self.envs_dirs_base = os.path.join(self.sdk_env_dir, 'lint', 'dev_envs', 'default_python')
