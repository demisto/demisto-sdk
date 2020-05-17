def is_v2_file(current_file):
    """Check if the specific integration of script is a v2
    Returns:
        bool. Whether the file is a v2 file
    """
    name = current_file.get('name', '')
    suffix = str(name[-2:].lower())
    if suffix != "v2":
        return False
    return True
