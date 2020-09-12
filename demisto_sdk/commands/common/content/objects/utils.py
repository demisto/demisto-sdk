

def normalize_file_name(file_name: str, file_prefix: str) -> str:
    """Add prefix to file name if not exists.

    Examples:
        1. "hello-world.yml" -> "<prefix>-hello-world.yml"

    Returns:
        str: Normalize file name.
    """
    if file_prefix and not file_name.startswith(f'{file_prefix}-'):
        file_name = f'{file_prefix}-{file_name}'

    return file_name
