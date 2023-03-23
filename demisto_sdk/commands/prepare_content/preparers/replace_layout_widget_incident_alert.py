from typing import Union


def replace_layout_widget_incident_alert(data: dict) -> dict:
    """
    Changes {"name": "Related/Linked/Chiled Incidents", ... }
         to {"name": "Related/Linked/Chiled Alerts", ... }
    """

    if not isinstance(data, dict):
        raise TypeError(f"expected dictionary, got {type(data)}")

    def fix_recursively(datum: Union[list, dict]) -> Union[list, dict]:
        if isinstance(datum, dict):
            if datum.get("name_x2") is not None:
                # already has a xsiam name, then we have nothing to do
                return datum
            if (name := datum.get("name", ""), datum.get("type")) in {
                ("Child Incidents", "childInv"),
                ("Linked Incidents", "linkedIncidents"),
                ("Related Incidents", "relatedIncidents"),
            }:
                datum["name"] = name.replace("Incident", "Alert")
                return datum
            else:  # not the atomic dictionary that we intend to fix, use recursion instead.
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
