from pathlib import Path


def create_temp_file(tmp_path, file_content, filename='file.txt'):
    file_like = tmp_path / filename
    file_like.write_text(file_content)
    return str(Path(file_like))
