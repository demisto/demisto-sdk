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
        "Ignoring validations for an entire pack is a significant decision. In "
        "the demisto/content repo, this requires a force-merge approved by a "
        "manager."
    )
    error_message = (
        "New pack-level ignored validation(s) were added to the [pack] section "
        "of .pack-ignore: {0}. Ignoring validations at the pack level requires a "
        "force merge. Please remove the additions or request a force merge."
    )
    related_field = "pack_ignore"
    is_auto_fixable = False
    # NOTE: intentionally NOT restricted by `expected_git_statuses`.
    # A `.pack-ignore` change maps to the pack's `pack_metadata.json`, but the
    # metadata file itself is often unchanged. In that case the collected Pack
    # has `git_status is None` (it was pulled in via the changed related file),
    # so gating on [ADDED, MODIFIED, RENAMED] would skip PA135 exactly for the
    # pack-ignore-only change we need to catch. Instead we run on every pack and
    # let `_added_pack_level_codes` decide via the git diff (no [pack] -> pass;
    # unchanged -> pass; new/added codes -> fail).
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

        The previous ref is taken from `old_base_content_object.git_sha`, which
        the initializer sets to the run's `prev_ver`. It can be missing in two
        cases that both mean "no previous version to diff against" (so every
        current code is an addition):
          - a brand-new pack (ADDED), which has no `old_base_content_object`;
          - a pack-ignore-only change where the metadata baseline was not
            git-resolved, leaving `git_sha` empty. Falling back to the pack's
            own `git_sha` keeps the comparison anchored to the run's prev_ver
            instead of silently reading the working tree.
        """
        new_codes = set(pack.pack_level_ignored_errors)
        if not new_codes:
            return set()  # nothing in [pack] now -> nothing was added
        old_object = pack.old_base_content_object
        prev_ver = old_object.git_sha if old_object else None
        if not prev_ver and old_object is not None:
            # old object exists but its ref was not populated; fall back to the
            # pack's own recorded ref so we still diff against git, not the WT.
            prev_ver = pack.git_sha
        old_codes = set(pack.old_pack_level_ignored_errors(prev_ver))
        return new_codes - old_codes
