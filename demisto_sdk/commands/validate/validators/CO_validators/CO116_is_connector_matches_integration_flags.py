from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


@dataclass(frozen=True)
class CollectionFlag:
    """Describes where/how a collection capability's backing flag is declared
    on the integration YAML.

    Two source shapes are supported:

    * ``source="script"`` - the flag is a top-level boolean under the YAML's
      ``script:`` block (e.g. ``script.isfetch``, ``script.isfetchevents``).
      For these, ``attr_name`` is the Pydantic field on
      :class:`Integration` that mirrors the flag (already resolved by the
      content-graph parser), and ``yaml_key`` is the raw YAML key used in
      user-facing error messages.

    * ``source="param"`` - the flag is expressed as a configuration
      parameter of type ``8`` (checkbox) whose ``name`` matches
      ``param_name`` (case-insensitively). This is the XSOAR convention
      for credential-fetching integrations: they do NOT declare
      ``script.isfetchcredentials: true``; instead they expose a checkbox
      configuration parameter named ``isFetchCredentials`` that the
      platform reads to route credential-fetch calls.
    """

    source: str  # "script" or "param"
    yaml_key: str  # human-readable label in error messages
    attr_name: Optional[str] = None  # Integration field name (script source)
    param_name: Optional[str] = None  # configuration parameter name (param source)


# Maps a collection capability id (the segment before the "_<integration>"
# suffix on a sub-capability, or the bare capability id) to the flag
# declaration on the backing integration.
COLLECTION_CAPABILITY_TO_FLAG: Dict[str, CollectionFlag] = {
    "fetch-issues": CollectionFlag(
        source="script", attr_name="is_fetch", yaml_key="isfetch"
    ),
    "log-collection": CollectionFlag(
        source="script", attr_name="is_fetch_events", yaml_key="isfetchevents"
    ),
    "fetch-assets-and-vulnerabilities": CollectionFlag(
        source="script", attr_name="is_fetch_assets", yaml_key="isfetchassets"
    ),
    "threat-intelligence-and-enrichment": CollectionFlag(
        source="script", attr_name="is_feed", yaml_key="feed"
    ),
    # Credential-fetching integrations declare themselves via a
    # ``configuration:`` checkbox parameter named ``isFetchCredentials``,
    # not via a ``script.isfetchcredentials`` boolean. No integration in
    # the content repo uses the script-level form. See CO116 validator
    # docstring for details.
    "fetch-secrets": CollectionFlag(
        source="param",
        param_name="isFetchCredentials",
        yaml_key="configuration parameter 'isFetchCredentials'",
    ),
}


class IsConnectorMatchesIntegrationFlagsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO116"
    description = (
        "Validates that when a connector declares a collection "
        "capability/sub-capability (fetch-issues, log-collection, "
        "fetch-assets-and-vulnerabilities, fetch-secrets, "
        "threat-intelligence-and-enrichment), the backing integration has the "
        "corresponding fetch flag enabled. Most flags live on the integration "
        "YAML under ``script:`` (e.g. log-collection requires "
        "``script.isfetchevents: true``); the ``fetch-secrets`` capability is "
        "the exception and is signaled by a configuration parameter named "
        "``isFetchCredentials`` (type 8 checkbox)."
    )
    rationale = (
        "A collection capability promises the platform that the integration "
        "collects that data. If the integration's matching fetch flag is off, "
        "the connector advertises collection functionality the integration "
        "cannot perform."
    )
    error_message = (
        "Connector '{connector_id}' declares collection capabilities that are "
        "not backed by the integration's flags: {details}."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            details: List[str] = []

            for capability in connector.capabilities:
                if capability.sub_capabilities:
                    # A parent capability with sub-capabilities is checked
                    # through its sub-capabilities (each carries the
                    # "<capability-id>_<integration>" form).
                    for sub_capability in capability.sub_capabilities:
                        details.extend(self._check_entry(connector, sub_capability.id))
                else:
                    details.extend(self._check_entry(connector, capability.id))

            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details="; ".join(details),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

    def _check_entry(
        self,
        connector: ContentTypes,
        entry_id: str,
    ) -> List[str]:
        """Check one capability/sub-capability against its handlers' integrations.

        Only collection capabilities are checked. For every handler subscribing
        to a collection entry, the backing integration must have the mapped
        fetch flag enabled. A subscribing handler whose integration cannot be
        resolved is flagged (never silently skipped).
        """
        details: List[str] = []

        flag = self._collection_flag_for(entry_id)
        if flag is None:
            # Not a collection capability - nothing to check.
            return details

        handler_ids = self._subscribing_handler_ids(connector, entry_id)
        for handler_id in handler_ids:
            handler = next((h for h in connector.handlers if h.id == handler_id), None)
            if handler is None:
                continue

            integration = handler.related_integration
            if integration is None:
                details.append(
                    f"'{entry_id}' cannot be verified: the subscribing handler "
                    f"'{handler_id}' references integration "
                    f"'{handler.xsoar_integration_id}' which was not resolved "
                    f"(ensure the content graph is built)"
                )
                continue

            if not self._integration_has_flag(integration, flag):
                details.append(
                    f"'{entry_id}' requires integration "
                    f"'{handler.xsoar_integration_id}' to have "
                    f"'{flag.yaml_key}' enabled, but it is disabled"
                )

        return details

    @staticmethod
    def _collection_flag_for(entry_id: str) -> Optional[CollectionFlag]:
        """Resolve the collection flag mapping for a capability/sub-capability id.

        Sub-capability ids take the form ``<capability-id>_<integration>``; the
        capability id is the segment before the first underscore. Bare
        capability ids are matched directly.
        """
        prefix = entry_id.split("_", 1)[0]
        return COLLECTION_CAPABILITY_TO_FLAG.get(prefix)

    @staticmethod
    def _integration_has_flag(integration: Integration, flag: CollectionFlag) -> bool:
        """Return True iff the backing integration expresses ``flag`` as enabled.

        Dispatches on ``flag.source``:

        * ``"script"`` - reads the ``attr_name`` boolean field on the
          :class:`Integration` object (populated by the content-graph parser
          from ``script.<yaml_key>``).
        * ``"param"`` - scans ``integration.params`` for a checkbox
          parameter (type 8) whose ``name`` matches ``param_name``
          (case-insensitively, since YAML keys like ``isFetchCredentials``
          use camelCase but users may write them differently). The
          parameter's ``defaultvalue`` is intentionally NOT inspected: the
          platform treats the mere presence of the checkbox as the enabling
          signal (matching how the content repo's credential-fetch
          integrations are shaped).
        """
        if flag.source == "script":
            assert flag.attr_name is not None
            return bool(getattr(integration, flag.attr_name, False))

        if flag.source == "param":
            assert flag.param_name is not None
            target = flag.param_name.casefold()
            for param in integration.params or []:
                if (
                    getattr(param, "name", "").casefold() == target
                    and getattr(param, "type", None) == 8
                ):
                    return True
            return False

        # Defensive: unknown source shape - fail closed so misconfigured
        # mappings surface rather than silently passing.
        return False

    @staticmethod
    def _subscribing_handler_ids(connector: ContentTypes, entry_id: str) -> List[str]:
        """Return the handler ids subscribing to the capability/sub-capability."""
        mapping = connector.capability_handler_map.get(entry_id)
        if not mapping:
            return []
        return list(mapping.handler_ids)
