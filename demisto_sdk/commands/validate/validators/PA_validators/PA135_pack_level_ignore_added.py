from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class PackLevelIgnoreAddedValidator(BaseValidator[ContentTypes]):
    error_code = "PA135"
    description = (
        "Validate that no new pack-level ignored validations were added to the "
        "[pack] section of the .pack-ignore file."
    )
    rationale = (
        "Ignoring validations for an entire pack is not recommended, as it "
        "could lead to unintended consequences. Therefore this requires a force-merge approved by a manager."
    )
    error_message = (
        "New pack-level ignored validation(s) were added to the [pack] section "
        "of .pack-ignore: {0}. Ignoring validations at the pack level is not "
        "recommended and requires a "
        "force merge. Please remove the additions or request a force merge."
    )
    related_field = "pack_ignore"
    is_auto_fixable = False
    # `expected_git_statuses` is left as None on purpose (i.e. "run on any git
    # status"). Here's why restricting it would break this validator:
    #
    # A change to `.pack-ignore` is not collected as its own item; validate
    # attributes it to the pack's main file, `pack_metadata.json`. The Pack
    # object's `git_status` therefore reflects the *metadata* file, not the
    # `.pack-ignore` file:
    #   - If only `.pack-ignore` changed (metadata untouched), the pack is still
    #     collected, but its `git_status` is None.
    #   - If the metadata also changed, `git_status` is MODIFIED/ADDED/RENAMED.
    #
    # So restricting to [ADDED, MODIFIED, RENAMED] would skip the pack whenever
    # ONLY `.pack-ignore` changed - which is the exact case this validator exists
    # to catch. We run on every pack instead and let `_added_pack_level_codes`
    # make the real decision by diffing the [pack] section against prev_ver:
    #   - no [pack] section now                -> nothing added -> pass
    #   - [pack] section exists                -> nothing added -> pass
    #   - codes added to [pack] section        -> fail
    expected_git_statuses = None
    related_file_type = [RelatedFileType.PACK_IGNORE]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for pack in content_items:
            added = self._added_pack_level_codes(pack)
            if added:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(", ".join(sorted(added))),
                        content_object=pack,
                    )
                )
        return results

    def _added_pack_level_codes(self, pack: ContentTypes) -> Set[str]:
        """Return the [pack] error codes that are new compared to prev_ver.

        Removing codes is allowed, so only additions (new minus old) are
        returned. A first-time [pack] section yields all of its codes as
        additions; a brand-new pack has no previous version, so all current
        codes count as additions.

        The "before" ref is `old_base_content_object.git_sha`. The validate
        initializer always sets this to the run's `prev_ver` (e.g. origin/master)
        whenever an old object exists - including the pack-ignore-only case,
        where the pack is collected via its unchanged `pack_metadata.json` but
        the old object is still built from `prev_ver`. When there is no old
        object at all (a brand-new pack), there is nothing to diff against, so
        every current code counts as an addition.
        """
        new_codes = set(pack.pack_level_ignored_errors)
        if not new_codes:
            return set()  # nothing in [pack] now -> nothing was added
        old_object = (
            pack.old_base_content_object
        )  # the same pack from prev_ver (e.g. origin/master)
        prev_ver = old_object.git_sha if old_object else None
        old_codes = set(pack.old_pack_level_ignored_errors(prev_ver))
        return new_codes - old_codes
