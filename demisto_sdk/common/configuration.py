import os
import logging


class Configuration:
    def __init__(self, env_dir=None, log_verbose=False, logging_level=logging.INFO):
        logging.basicConfig(level=logging_level)
        self.log_verbose = log_verbose
        self.sdk_env_dir = os.path.dirname(os.path.dirname(os.path.join(__file__)))
        if not env_dir:
            self.env_dir = os.getcwd()
        else:
            self.env_dir = env_dir
        self.envs_dirs_base = os.path.join(self.sdk_env_dir, 'common', 'dev_envs', 'default_python')
