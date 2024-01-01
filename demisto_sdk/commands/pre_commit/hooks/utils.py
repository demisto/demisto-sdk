def get_property(hook: dict, mode: str, name: str, default=None):
    """
    Will get the given property from the base hook, taking mode into account
    Args:
        hook: the hook dict
        mode: the mode to use
        name: the key to get from the config
        default: the default value to return
    Returns: The value from the base hook
    """
    ret = None
    if mode:
        ret = hook.get(f"{name}:{mode}")
    return ret or hook.get(name, default)
