from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
    SEPARATOR,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class MarketplaceKeysHaveDefaultValidator(BaseValidator[ContentTypes]):
    error_code = "PB127"
    description = "Ensure that any yml keys that are marketplace only have a default non-marketplace counterpart."
    rationale = "To ensure the required yml keys, we have to have a default value for any marketplace only keys."
    error_message = (
        "The following playbook yml keys only do not have a default option: {}. Please remove these keys or add "
        "another default option to each key."
    )
    fix_message = "Added default value to the following playbook keys: {0}."
    marketplace_suffixes = [
        marketplace for marketplace in MarketplaceVersions.__members__.values()
    ]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
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

        return validation_results

    def check_recursively(self, datum, path="root", bad_keys=[], fix=False) -> list:
        # If the datum is a list, iterate over its values and check recursively.
        if isinstance(datum, list):
            for index, item in enumerate(datum):
                bad_inner_keys = self.check_recursively(
                    item, path=f"{path}.[{index}]", bad_keys=bad_keys, fix=fix
                )
                bad_keys.extend(
                    bad_key for bad_key in bad_inner_keys if bad_key not in bad_keys
                )
            return bad_keys

        # If the datum is a dictionary, iterate over its keys.
        elif isinstance(datum, dict):
            for key in datum.keys():
                value = datum[key]
                if isinstance(value, (list, dict)):
                    # If the value is a list or a dictionary recursively check.
                    bad_inner_keys = self.check_recursively(
                        value, path=f"{path}.{key}", bad_keys=bad_keys, fix=fix
                    )
                    bad_keys.extend(
                        bad_key for bad_key in bad_inner_keys if bad_key not in bad_keys
                    )
                if isinstance(key, str) and SEPARATOR in str(key):
                    for suffix in self.marketplace_suffixes:
                        if key.casefold().endswith(suffix):
                            # Construct the default key without the suffix and check if it exists in the datum.
                            clean_key = key[: -(len(suffix) + len(SEPARATOR))]
                            if (
                                clean_key not in datum
                                and f"{path}.{key}" not in bad_keys
                            ):
                                bad_keys.append(f"{path}.{key}")
                            # No need to keep matching marketplaces to the suffix once one is found.
                            break

        return bad_keys
