from pathlib import Path

from _pytest import tmpdir


def create_temp_file(tmp_path: tmpdir.tmp_path, file_content: str, filename: str = 'file.txt') -> str:
    """ Creates a temporary file with contents

    Args:
        tmp_path: tmp_path object
        file_content: Contents of a file
        filename: name of the file (default `file.txt`)

    Returns:
        path to the temporary file
    """
    file_like = tmp_path / filename
    file_like.write_text(file_content)
    return str(Path(file_like))
