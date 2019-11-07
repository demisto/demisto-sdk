import os


class Configuration:
    def __init__(self, script_dir=None, log_verbose=False):
        self.log_verbose = log_verbose
        if not script_dir:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.script_dir = script_dir
        self.envs_dirs_base = '{}/dev_envs/default_python'.format(self.script_dir)
