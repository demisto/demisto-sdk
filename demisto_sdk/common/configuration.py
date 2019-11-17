import sys
import os
import logging


class Configuration:
    def __init__(self, default_env_dir=None, log_verbose=False, logging_level=logging.INFO):
        logging.basicConfig(level=logging_level)
        self.log_verbose = log_verbose
        if not default_env_dir:
            self.env_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.env_dir = default_env_dir
        self.envs_dirs_base = '{}/dev_envs/default_python'.format(self.env_dir)
        self.config_dir = '{}/configs/'.format(self.env_dir)


class ValidationConfiguration(Configuration):
    def __init__(self, default_env_dir=None, is_backward_check=True, prev_ver='origin/master', is_forked=False,
                 is_circle=False, print_ignored_files=False, validate_conf_json=True, validate_id_set=False,
                 use_git=False):
        """

        :param is_backward_check:
        :param prev_ver:
        :param is_forked:
        :param is_circle (bool): whether we are running on circle or local env.
        :param print_ignored_files (bool): should print ignored files when iterating over changed files.
        """
        super().__init__(default_env_dir=default_env_dir, logging_level=logging.CRITICAL)
        self.content_dir = os.path.abspath(self.env_dir + '/../..')
        self.is_backward_check = is_backward_check
        self.prev_ver = prev_ver
        self.is_forked = is_forked
        self.is_circle = is_circle
        self.print_ignored_files = print_ignored_files
        self.validate_conf_json = validate_conf_json
        self.validate_id_set = validate_id_set
        self.use_git = use_git

    def append_sys_path(self):
        sys.path.append(self.content_dir)

    @staticmethod
    def create(**kwargs):
        return ValidationConfiguration(**kwargs)
