from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List, Set

from demisto_sdk.commands.common.tools import get_content_item_supported_modules
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.upload.constants import (
    CONTENT_TYPES_EXCLUDED_FROM_UPLOAD,
    CONTENT_TYPES_NOT_SUPPORTED_IN_UPLOAD,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack

# Content types that are never individually uploaded and should not count
# toward module coverage (same sets used by the upload flow).
_SKIP_CONTENT_TYPES = (
    CONTENT_TYPES_EXCLUDED_FROM_UPLOAD | CONTENT_TYPES_NOT_SUPPORTED_IN_UPLOAD
)


class PackSupportedModulesCoverageValidator(BaseValidator[ContentTypes]):
    error_code = "PA134"
    description = (
        "Validate that every supported module declared in the pack metadata is covered "
        "by at least one individually-uploadable content item."
    )
    rationale = (
        "If a module is declared in the pack's supportedModules but no individually-uploadable "
        "content item supports it, tenants licensed only for that module will receive an empty pack."
    )
    error_message = (
        "The following supported modules declared in the pack metadata are not covered by any "
        "individually-uploadable content item: {0}. "
        "A tenant licensed only for these modules will receive an empty pack."
    )
    fix_message = (
        "Removed the following uncovered modules from the pack's supportedModules: {0}."
    )
    related_field = "supportedModules"
    is_auto_fixable = True

    # Stores the uncovered modules per pack name so the fix() method can use them
    # without re-computing.
    _uncovered_modules_cache: ClassVar[Dict[str, Set[str]]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for pack in content_items:
            uncovered = self._get_uncovered_modules(pack)
            if uncovered:
                self._uncovered_modules_cache[pack.name] = uncovered
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(", ".join(sorted(uncovered))),
                        content_object=pack,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        uncovered = self._uncovered_modules_cache.get(content_item.name, set())
        content_item.supportedModules = [
            m for m in (content_item.supportedModules or []) if m not in uncovered
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(sorted(uncovered))),
            content_object=content_item,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_uncovered_modules(self, pack: ContentTypes) -> Set[str]:
        """Return the set of modules declared in the pack but not covered by
        any individually-uploadable content item.

        Returns an empty set when the pack is valid (or when the check is
        not applicable).
        """
        pack_modules = get_content_item_supported_modules(pack)
        if not pack_modules:
            # No explicit supportedModules declaration — nothing to validate.
            return set()

        uploadable_items = [
            item
            for item in pack.content_items
            if item.content_type not in _SKIP_CONTENT_TYPES
        ]

        union_of_item_modules: Set[str] = set()
        for item in uploadable_items:
            union_of_item_modules.update(get_content_item_supported_modules(item))

        return pack_modules - union_of_item_modules
