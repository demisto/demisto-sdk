from enum import Enum


def to_dict(obj):
    if isinstance(obj, Enum):
        return obj.name

    if not hasattr(obj, '__dict__'):
        return obj

    result = {}
    for key, val in obj.__dict__.items():
        if key.startswith("_"):
            continue

        element = []
        if isinstance(val, list):
            for item in val:
                element.append(to_dict(item))
        else:
            element = to_dict(val)
        result[key] = element

    return result
