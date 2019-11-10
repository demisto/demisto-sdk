import os


class Configuration:
    def __init__(self, default_env_dir=None, log_verbose=False):
        self.log_verbose = log_verbose
        if not default_env_dir:
            self.env_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.env_dir = default_env_dir
        self.envs_dirs_base = '{}/dev_envs/default_python'.format(self.env_dir)
        self.config_dir = '{}/configs/'.format(self.env_dir)
