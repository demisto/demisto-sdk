from __future__ import annotations

from typing import Iterable, List, Tuple, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    SEPARATOR,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class MarketplaceKeysHaveDefaultValidator(BaseValidator[ContentTypes]):
    error_code = "PB127"
    description = "Ensure that any yml keys that are marketplace only have a default non-marketplace counterpart."
    rationale = (
        "To be able to validate the existence of required yml keys, "
        "we need to make sure that in addition to a specific marketplace key (say mykey:xsoar) "
        "there is also a basic key with no specific marketplace (for example: mykey)."
    )
    error_message = (
        "The following playbook yml keys only do not have a default option: {}. "
        "Please remove these keys or add another default option to each key."
    )
    fix_message = "Added default value to the following playbook keys:\n{0}"
    marketplace_suffixes = [
        marketplace for marketplace in MarketplaceVersions.__members__.values()
    ]
    bad_paths_dict: dict = dict()
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []

        for content_item in content_items:
            marketplace_keys_with_no_default = self.check_recursively(
                content_item.data, bad_keys=[]
            )
            if marketplace_keys_with_no_default:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            marketplace_keys_with_no_default
                        ),
                        content_object=content_item,
                    )
                )
                self.bad_paths_dict[content_item.name] = (
                    marketplace_keys_with_no_default
                )

        return validation_results

    def check_recursively(self, datum, path="root", bad_keys=[]) -> list:
        """If marketplace suffix is encountered in the data, check for default value. Do

        Args:
            datum (dict or list): The root data node to check.
            path (str): The path to the current data node.
            bad_keys (list): The bad keys that are already known.

        Return:
            (list) All data paths with no default value.
        """
        # If the datum is a list, iterate over its values and check recursively.
        if isinstance(datum, list):
            for index, item in enumerate(datum):
                bad_keys = self.check_recursively(
                    item,
                    path=f"{path}.[{index}]",
                    bad_keys=bad_keys,
                )
            return bad_keys

        # If the datum is a dictionary, iterate over its keys.
        elif isinstance(datum, dict):
            for key, value in datum.items():
                if isinstance(value, (list, dict)):
                    # If the value is a list or a dictionary recursively check.
                    bad_keys = self.check_recursively(
                        value,
                        path=f"{path}.{key}",
                        bad_keys=bad_keys,
                    )
                if isinstance(key, str) and SEPARATOR in str(key):
                    for suffix in self.marketplace_suffixes:
                        if key.casefold().endswith(suffix):
                            # Construct the default key without the suffix and check if it exists in the datum.
                            clean_key = key.split(SEPARATOR)[0]
                            if (
                                clean_key not in datum
                                and f"{path}.{clean_key}" not in bad_keys
                            ):
                                bad_keys.append(f"{path}.{clean_key}")
                            # No need to keep matching marketplaces to the suffix once one is found.
                            break

        return bad_keys

    @staticmethod
    def get_parent_path_from_data(
        data: Union[list, dict], key_path: str
    ) -> Tuple[dict, str]:
        """Return the parent path and the last key from the dataset given.

        Args:
            data (list | dict): The data to search in.
            key_path (str): The path to obtain. For example: "root.inputs.[0].description".

        Return:
            (dict, str): The parent node, the last key name.
        """
        keys: list = key_path.split(".")
        last_key: str = keys[-1]
        keys = keys[1:-1]  # No root and no last key
        data_node: Union[list, dict] = data
        for key_index, key in enumerate(keys):
            if (
                key.startswith("[")
                and key.endswith("]")
                and isinstance(data_node, list)
            ):
                # If it is a list node, the key is numerical
                key = int(key[1:-1])  # type: ignore[assignment]
            data_node = data_node[key]

        # During the iteration data_node can be a list.
        # If the key with a suffix is found, the parent can only be a dict.
        # Therefor the iteration will end with a dict and a string.
        return data_node, last_key  # type: ignore[return-value]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """Add default value to keys with marketplace suffix. Add the first one encountered.

        Args:
            content_item (ContentTypes): The content item to fix.

        Return:
            (FixResult) The relevant fix result.
        """
        new_content_data = content_item.data
        # Go to the longest, nested paths first.
        bad_paths = sorted(self.bad_paths_dict[content_item.name], key=len)[::-1]
        default_paths_used = {}
        for bad_path in bad_paths:
            parent_datum, last_key = self.get_parent_path_from_data(
                new_content_data, bad_path
            )
            # Go over the available suffixes and find the first match.
            for suffix in self.marketplace_suffixes:
                key_with_suffix = f"{last_key}{SEPARATOR}{suffix}"
                if key_with_suffix in parent_datum.keys():
                    new_default_value = parent_datum[key_with_suffix]
                    parent_datum[last_key] = new_default_value
                    default_paths_used[bad_path] = key_with_suffix
                    # No need to continue looking after a match is found
                    break

        return FixResult(
            validator=self,
            message=self.fix_message.format(
                "\n".join(
                    [
                        f"For {bad_path} used {key_used}."
                        for bad_path, key_used in default_paths_used.items()
                    ]
                )
            ),
            content_object=content_item,
        )
