import glob
from os.path import join
from typing import List


class FileFinder:
    class Extension:
        YML = '.yml'
        PYTHON = '.py'
        JSON = '.json'

    @staticmethod
    def get_files_with_extension_in_dir(dir_path: str, extension: str, recursive: bool = False) -> List[str]:
        """Return all files in directory, absolute path.

        Args:
            dir_path: path to files in
            extension: files that ends with this term
            recursive: Should find files in subdirectories

        Returns:
            A list of all files in the path.
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        if recursive:
            glob_search = join(dir_path, '**', f'*{extension}')
        else:
            glob_search = join(dir_path, f'*{extension}')

        return glob.glob(glob_search, recursive=recursive)

    @classmethod
    def get_yml_files_in_dir(cls, dir_path: str, recursive: bool = False) -> List[str]:
        """Return all files in directory, absolute path.

        Args:
            dir_path: path to find yml files in
            recursive: Find in file in subdirectories.

        Returns:
            A list of all files in the path.
        """
        return cls.get_files_with_extension_in_dir(dir_path, cls.Extension.YML, recursive=recursive)

    @classmethod
    def get_json_files_in_dir(cls, dir_path: str, recursive: bool = False) -> List[str]:
        """Return all files in directory, absolute path.

        Args:
            dir_path: path to find json files in
            recursive: Find in file in subdirectories.

        Returns:
            A list of all files in the path.
        """
        return cls.get_files_with_extension_in_dir(dir_path, cls.Extension.JSON, recursive=recursive)

    @classmethod
    def get_python_files_in_dir(cls, dir_path: str, recursive: bool = False) -> List[str]:
        """Return all files in directory, absolute path.

        Args:
            dir_path: path to find python files in
            recursive: Find in file in subdirectories.

        Returns:
            A list of all files in the path.
        """
        return cls.get_files_with_extension_in_dir(dir_path, cls.Extension.PYTHON, recursive=recursive)
