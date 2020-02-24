
def is_v2_file(current_file):
    """Check if the file is a v2 file
    Returns:
        bool. Whether the file is a v2 file
    """
    name = current_file.get('name', '')
    namePref = str(name[-2:].lower())
    if namePref != "v2":
        return False
    return True
