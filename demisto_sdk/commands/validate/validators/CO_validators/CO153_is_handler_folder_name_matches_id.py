"""CO153 - IsHandlerFolderNameMatchesIdValidator.

Per §3.8 handler-layout rules, every handler's on-disk folder name
under ``components/handlers/`` MUST equal its ``handler.id``
**verbatim, case-sensitive** — no normalization, no dash/underscore
substitution, no whitespace tolerance.

Rationale
---------
The folder path is the identifier used by:
- Build/packaging scripts that copy/rename handler bundles.
- Migration fixtures that map old-integration paths to new-handler
  paths.
- ``.connector-ignore`` chains keyed on
  ``<handler-folder>/handler.yaml`` — a drifted folder name means
  every per-file ignore silently misses.

Even a case difference or a `_` vs `-` swap breaks all of the above
because filesystems are byte-exact and the tooling never
"normalizes" first. So the rule is strict verbatim.

Scope
-----
Runs on every handler in every connector (ownership-agnostic — the
tooling breakage applies whether the handler is XSOAR or not). One
``ValidationResult`` per handler with a mismatch. Handlers whose
``file_path`` is unresolvable (constructed in memory / stub) are
skipped.

Path routing: the finding's ``path`` points at the handler's
``handler.yaml`` so ``[file:<folder>/handler.yaml]`` in
``.connector-ignore`` resolves; folder-name refactors are then
authored as a per-file ignore during the transitional migration
period if ever needed.
"""

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsHandlerFolderNameMatchesIdValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO153"
    description = (
        "Every handler's on-disk folder name under "
        "`components/handlers/` MUST equal `handler.id` verbatim "
        "(case-sensitive, no normalization)."
    )
    rationale = (
        "Filesystem paths are the identifier used by build scripts, "
        "migration fixtures, and `.connector-ignore` resolution. "
        "Any drift between id and folder name — case, "
        "dash-vs-underscore, trailing whitespace — silently breaks "
        "tooling and per-file ignores. Strict verbatim equality "
        "keeps the invariant crystal-clear."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': folder "
        "name '{folder_name}' does not match handler id "
        "'{handler_id}' verbatim. Rename the folder to "
        "'{handler_id}' (case-sensitive, no normalization). "
        "Filesystem / tooling breaks otherwise."
    )
    related_field = "id"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.handlers:
                folder_name = self._folder_name(handler)
                if folder_name is None:
                    # Handler constructed without a file_path (stub /
                    # in-memory). Nothing to compare against.
                    continue
                if folder_name == handler.id:
                    continue
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            folder_name=folder_name,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    @staticmethod
    def _folder_name(handler: HandlerData):
        """Return the handler's on-disk folder name, or ``None`` if
        the handler has no resolvable file path."""
        fp = handler.file_path
        if fp is None:
            return None
        # ``handler.file_path`` layout is
        # ``<connector>/components/handlers/<folder>/handler.yaml``.
        return fp.parent.name
