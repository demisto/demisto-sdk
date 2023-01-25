from typing import Union


def change_incident_to_alert(data: dict) -> dict:
    """
    Changes internal {name: 'Related Incidents', ... }, into {name: 'Related Alerts', ... }, see the condition below.
    """
    if not isinstance(data, dict):
        raise TypeError(f"expected dictionary, got {type(data)}")

    def fix_recursively(datum: Union[list, dict]) -> Union[list, dict]:
        if isinstance(datum, dict):
            if (
                datum.get("id") == "relatedIncidents"
                and datum.get("name") == "Related Incidents"
                and datum.get("name_x2") is None
            ):  # the kind of dictionary we want to fix
                datum["name"] = "Related Alerts"
                return datum
            else:  # not the atomic dictionary that we fix, use recursion instead.
                return {key: fix_recursively(value) for key, value in datum.items()}

        elif isinstance(datum, list):
            return [fix_recursively(item) for item in datum]

        else:
            return datum  # nothing to change

    if not isinstance(result := fix_recursively(data), dict):
        """
        the inner function returns a value of the same type as its input,
        so a dict input should never return a non-dict. this part is just for safety (mypy).
        """
        raise ValueError(f"unexpected type for a fixed-dictionary output {type(data)}")

    return result
