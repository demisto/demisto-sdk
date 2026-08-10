#  ConnectUs Manifest Validations \- temp

## Table of Contents

- [Overview](#overview)  
- [Code numbering scheme](#code-numbering-scheme)  
- [Legend — "Applies To" classification](#legend--applies-to-classification)  
- [connector.yaml (CO100–CO106)](#connectoryaml)  
- [capabilities.yaml (CO107–CO117)](#capabilitiesyaml)  
- [connection.yaml (CO118–CO128)](#connectionyaml)  
- [configurations.yaml (CO129–CO145)](#configurationsyaml)  
- [summary.yaml (CO146–CO147)](#summaryyaml)  
- [triggers.yaml (CO148–CO152)](#triggersyaml)  
- [handler.yaml (CO153–CO170)](#handleryaml)  
- [serializer.yaml (CO171–CO173)](#serializeryaml)  
- [CODEOWNERS (CO174)](#codeowners)  
- [Breaking-Change Guards (CO175–CO187)](#breaking-change-guards)  
- [Whole-Connector Schema (CO188–CO189)](#whole-connector-schema)  
- [Integration-Side (XSOAR YML) (CO190–CO192)](#integration-side-xsoar-yml)  
- [Customer-Facing / Terminology (CO193)](#customer-facing--terminology)  
- [Notes & edge cases](#notes--edge-cases)

## Overview

We’ll utilize the existing demisto-sdk validate infrastructure with minor modifications to run validations both on the Connectus repository and the content repository together.

We’ll add a \--run-connectors-validation flag that triggers a slightly different Initializer flow

We’ll utilize the graph during the parsing time (initializer) to find connections between the given integrations and connectors (or the non-given if only one side is provided)

We’ll add a new section to the validations\_config file that includes all the error codes that need to run on connectors

We’ll add a connector object (and all sub-objects) to the Pydantic structures to ensure schema validations, easy O(1) access to fields during validations, and add the connector to the graph.

Summarize: All the modifications mentioned above allow us to simply trigger

```shell
demisto-sdk validate -g --config-path validation_config.toml --category-to-run connectors_use_git --run-connectors-validation
```

And utilize the existing mechanism to create integration\<-\>connector connected objects and run validation on them.

Proposed validations:

## Code numbering scheme

Validators are grouped by **Category** . Every code follows the format `CO<NNN>`, where:

- `CO` is the product prefix (**CO**nnector).  
- `<NNN>` is a 3-digit sequential number that **follows a global continuous sequence** starting from 100\. Because the codes are global, adding a validator increments the global sequence without renumbering other categories.

Category codes and their bands:

- `connector.yaml` → CO100–CO106  
- `capabilities.yaml` → CO107–CO117  
- `connection.yaml` → CO118–CO128  
- `configurations.yaml` → CO129–CO145  
- `summary.yaml` → CO146–CO147  
- `triggers.yaml` → CO148–CO152  
- `handler.yaml` → CO153–CO170  
- `serializer.yaml` → CO171–CO173  
- CODEOWNERS → CO174  
- Breaking-Change Guards → CO175–CO187  
- Whole-Connector Schema → CO188–CO189  
- Integration-Side (XSOAR YML) → CO190–CO192  
- Customer-Facing / Terminology → CO193

## Legend — "Applies To" classification

ConnectUs connectors come in two forms:

- **Grouped** (`settings.grouped: true`): multiple integrations/handlers per vendor; uses `view_groups` registries, `profiles[].view_group` bindings, per-`view_group` `integrationLogLevel`, and collision-prefixed field ids. Handlers subscribe to sub-capabilities.  
- **Standard** (non-grouped): a single handler/integration, a single implicit tile, `integrationLogLevel` with no `view_group`, and no `view_groups` registry.

Every validator is classified with an **"Applies To"** value so grouped-only checks can short-circuit early. The four values are:

- **Both** — runs unconditionally on every connector (the default).  
- **Grouped only** — depends on grouped-only constructs (`view_groups`, `profiles[].view_group`, per-`view_group` `integrationLogLevel`, collision-prefixed ids). Implementation short-circuits with `if not grouped: pass`.  
- **Standard only** — only meaningful for single-handler / non-grouped connectors.  
- **Both (integration-side)** — runs on the XSOAR integration YML side (not the connector manifest), independent of grouping.

## connector.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO100 | IsConnectorOwnershipFieldsAlign | Both | Since we assume that if the connector was collected, it has an XSOAR handler, we just need to validate that `metadata.ownership.maintainers` contains `@xsoar-content` | Done |
| CO101 | IsAuthorImagePresent | Both | `metadata.author_image` is present and non-empty. From a pure connector POV an icon is optional, but from the XSOAR content POV it is HARD-REQUIRED — every migrated connector must ship an icon (§3.3 sources it from the integration folder). (Filename pattern \+ on-disk existence \+ max-1-icon are already enforced by schema/OPA; this adds the presence requirement.) | Done |
| CO102 | IsPublisherValid | Both | `metadata.publisher == "Palo Alto Networks"` (§3.3). | Done |
| CO103 | IsConnectorIdTitleAligned | Both | `id` (lowercase-dashes slug) and `metadata.title` (Title Case) encode the same name — i.e. slugify(title) \== id  | Done |
| CO104 | IsVendorMatchesProvider | Both | `metadata.vendor` matches the linked integration(s)' `provider` field; flag if providers differ across handlers  | Done |
| CO105 | IsCategoriesUnionSupersetOfPacks | Both  | `metadata.categories` equals the deduplicated union of the linked parent packs' categories (§3.3). Cross-repo check via the graph. WARNING-level (curated categories may legitimately differ).\* contained in | Done |
| CO106 | IsTagsUnionSupersetOfPacks | Both | metadata.tags equals the deduplicated union of the linked parent packs' tags WARNING-level (curated tags may legitimately differ).\* contained in | Done |

## capabilities.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO107 | `IsValidCapabilitiesMetadata` | Both | `metadata.title` must equal "Capabilities"; `metadata.description` must equal "Name and configure the instance capabilities"; `metadata.help` must be omitted If the connector is a grouped connector | Done |
| CO108 | `IsValidGeneralConfigDescription` | Both | `general_configurations.description` must equal "General configurations for all capabilities". | Done |
| CO109 | `IsInstanceNameTemplateValid` | Both | `general_configurations.configurations` must include the verbatim `instance_name` field template. | Done |
| CO110 | `IsCapabilityNameValid` | Both | For XSOAR-owned capabilities/sub-capabilities only (ownership determined via the handler `module: xsoar` field), the capability `id` must be one of the 6 allowed capability ids (automation-and-remediation, log-collection, fetch-issues, fetch-assets-and-vulnerabilities, threat-intelligence-and-enrichment, fetch-secrets). Non-XSOAR capabilities are skipped entirely. | Done |
| CO111 | `groupedConnectorXSOAROnlyCapabilities` | Grouped only | A grouped connector may only contain XSOAR-owned capabilities/handlers (ownership determined via the handler `module: xsoar` field); any non-XSOAR handler/capability is an error, since only XSOAR is permitted to use grouped connectors. | Done |
| CO112 | `HasSubCapability` | Grouped only | Each capability must declare at least one sub-capability | Done |
| CO113 | `IsSubCapabilityIdDerived` | Grouped only | Sub-capability id must follow the pattern `<capability_id>_<normalized_integration_id>`. Note: Only to be checked on new connectors, as we dont want to edit IDs of existing connectors.  | Done |
| CO114 | `IsMatchingLicense` | Both | For each capability and sub-capability check which handlers subscribe to them.  Then using that integration, check that the required\_licenses on the cap/sub-cap is a subset of the integrations supportedModules.  Notes: If the integration YML doesnt have the supportedModuled field, take from the parent pack metadata.  If the pack metadata also doesnt have the supportedModules, then it supports all platform ones. If the capability/sub-capability does not have required\_licenses, then it means it supports all licenses, and the assertion should be done on that  | Done |
| CO115 | `IsCapabilityUsed` | Both | Every declared capability/sub-capability must be subscribed by at least one handler; unused declarations are flagged. Note: A capability is allowed to have no subscribers if it has sub-capabilities A sub-capability always must have a subscriber | Will be covered by UCP. see ticket: https://jira-dc.paloaltonetworks.com/browse/CRTX-270320 |
| CO116 | IsConnectorMatchesIntegrationFlags | Both | Cross-validate connector capabilities against integration flags. E.g., if the connector declares `Log Collection` capability but the linked integration has `script.isfetchevents: false` / `script.isfetchevents:platform: false`. | Done |
| CO117 | IsCapabilityTitleValid | Both | Each capability's `title` must be the exact Title Case of its `id` (e.g., fetch-issues → "Fetch Issues", automation-and-remediation → "Automation and Remediation", log-collection → "Log Collection", fetch-assets-and-vulnerabilities → "Fetch Assets and Vulnerabilities", threat-intelligence-and-enrichment → "Threat Intelligence and Enrichment", fetch-secrets → "Fetch Secrets")  | Done |
| CO194 | IsSubCapabilityTitleDerivedValidator | Grouped Only | "Validates that each sub-capability in a grouped connector has a "         "title equal to the linked integration's display name. Runs on all "         "grouped connectors, not only newly added ones." | Done |

## connection.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO118 | `IsValidConnectionMetadata` | Both | `metadata.title` must equal "Connection"; `metadata.description` must equal "Enter the credentials to securely authorize the connection"; ~~`metadata.help` must be present (flag if empty).~~ | Done |
| CO119 | `NoConnectionGeneralConfigurations` | Grouped only | Grouped connectors must NOT declare `general_configurations` in connection.yam. | Done |
| CO120 | `IsGeneralParamsExist` | Both | Ensure the existence and correct configuration of general params: Proxy — one of \[proxy, useproxy, use\_proxy\] — if it appears in the integration yml, it should appear in each of the handler's auth options. Insecure — one of \[insecure, unsecure, verify, secure, trust\] — if it appears in integration yml, should appear in each of the handler's auth options. Engine — should appear in each of the handler's auth options. Use Joey list to skip irrelevant integrations. Log level, "Do not use in CLI by default" — should appear in general\_configuration, serialized per handler. |  |
| CO121 | `IsValidInterpolation` | Both | Ensures that each auth profile that supports interpolations has a valid interpolation\_mapping — left side exists as an id under the auth profile (serialized or deserialized), right side exists in integration, only type 9 is split between .identifier/.password. Additionally, the interpolation\_mapping left-side keys must be auth-field metadata.auth.parameter values only — never engine, engine\_group, proxy, or insecure (§2.6.2). |  |
| CO122 | `IsValidViewgroup` | Grouped only | Grouped-only. For each XSOAR handler, `connection.yaml` MUST declare a view_group whose `id` matches `handler.related_integration.object_id` after alphanumeric-only normalization (lowercased, every non-alphanumeric character stripped — view_group ids are developer-facing so any stylistic drift is tolerated) AND whose `label` equals the integration's `display_name` **verbatim** (the label is customer-facing tile heading). Unresolved handlers are errors, not silent skips. `view_groups` only exist when grouped; implementation short-circuits with `if not grouped: pass`. | Done |
| CO123 | `IsProfileFieldsCovered` | Both | Ensures that for each auth profile that supports interpolation, all the non-interpolated params have publish \= true (except for engine\_mode). |  |
| CO124 | `IsValidGroupedConnectorAuth` | Grouped only | Every `ConnectionProfile` in a grouped connector MUST declare a non-empty `metadata.xsoar.interpolation_mapping` string. Missing key, `null`, empty string, and whitespace-only are all rejected. No per-profile ownership check — grouped connectors are XSOAR-only by CO111. Complements CO121 which validates mapping contents. Short-circuits `if not grouped: pass`. | Done |
| CO125 | `IsAuthProfileHasEngine` | Both | Ensures the engine triplet (`engine_mode`, `engine`, `engine_group`/`engineGroup`) is present. Grouped: checked per profile inside `profile.configurations`. Standard: checked once at `connection.general_configurations`. Integrations on the Appendix G engine/proxy exclusion list are skipped (CO127 validates the opposite direction). | Done |
| CO126 | `IsValidEngineParams` | Both | Conformance of the engine triplet: `engine_mode` is `radio` + `options.orientation: horizontal` + `options.values` keys = `{no_engine, engine, engineGroup}`; all 3 engine fields live in the same `FieldGroup`; `engine` and `engineGroup` are `select` + `metadata.xsoar.config_type: backend`; their `metadata.dynamic_values.provider == "xsoar"` with trigger containing both `on_create` and `on_edit`; `params.integrationID` matches the owning XSOAR handler's integration id; `params.dynamicField` is `"engine"` or `"engine-group"`. Grouped connectors are resolved through the handler's `serializer.yaml` before lookup. Appendix G integrations skipped; Appendix H integrations skip the options-key-set check (CO128 handles their 2-key shape). Static `hidden` defaults and `advanced` intentionally NOT enforced (CO148 triggers own runtime engine/engineGroup visibility). | Done |
| CO127 | IsEngineExclusionRespected | Both | Integrations on the Appendix G engine/proxy exclusion list (EDL, ExportIndicators, PingCastle, Publish List, Simple API Proxy, Syslog v2, TAXII Server, TAXII2 Server, Web File Repository, Workday\_IAM\_Event\_Generator, XSOAR-Web-Server, Microsoft Teams, AWS-SNS-Listener) must emit NO `engine_mode`, `engine`, `engine_group`, or `proxy` fields at all. |  |
| CO128 | IsSingleEngineRespected | Both | Integrations on the Appendix H single-engine list (saml, slack, sharedagent, syslog, mattermost, duo) must emit `engine_mode` with only 2 options (`no_engine` \+ `engine`) and the `engine` dropdown, and MUST NOT emit `engine_group`. |  |

## configurations.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO129 | `IsValidConfigurationsMetadata` | Both | `metadata.title` must equal "Configuration"; `metadata.description` must equal "Adjust and refine your configuration settings" (§3.7). Description enforced to the de-facto disk value (with trailing "settings") used by 328/356 XSOAR-owned connectors, rather than the shorter manifest wording, to minimize churn. | Done |
| CO130 | `IsValidFetch` | Both | Every XSOAR handler subscribing to the `fetch-issues` capability MUST (a) emit `isFetch: true` via its `serializer.yaml` `computed_fields` gated by a capability condition (§3.9.1), AND (b) have a `configurations[]` entry with `id == <capability-id>` (bare or namespaced grouped variant) containing all four required fields with the correct field-shape (§3.7): `incidentType` (`select`, `dynamicField: incident-type`), `incidentFetchInterval` (`duration`), `incomingMapperId` (`select`, `dynamicField: mapper-incoming`), `mappingId` (`select`, `dynamicField: classifier`). | Done |
| CO131 | IsValidFeed | Both | Ensure that if the connector has the feed capability, it includes all related params as well (reputation, reliability, expiration interval, etc) and that they're configured correctly. Params to validate: feed, feedFetchInterval, feedReputation, feedReliability, feedExpirationPolicy, feedExpirationInterval, feedBypassExclusionList. |  |
| CO132 | IsValidFetchAssets | Both | Ensure that if the connector has the fetch-assets capability, it includes all related params as well. Params to validate: isFetchAssets, assetsFetchInterval. |  |
| CO133 | IsValidFetchEvents | Both | Ensure that if the connector has the fetch-events capability, it includes all related params as well. Params to validate: isFetchEvents, eventFetchInterval. |  |
| CO134 | IsValidFetchCredentials | Both | Ensure that if the connector has the fetch-credentials capability, it includes all related params as well. Params to validate: isFetchCredentials. |  |
| CO135 | IsValidLongRunning | Both | Ensure that if the connector has the long-running capability, it includes all related params as well (long-running port, long-running checkbox). |  |
| CO136 | `IsValidAutomationCapability` | Both | Every XSOAR handler subscribing to the `automation-and-remediation` capability (bare id or grouped-namespaced variant like `automation-and-remediation_qualysv2`) MUST have a `configurations[]` entry with `id == <capability-id>` containing a `defaultIgnore` field (§3.7 rule 4, Appendix J) with `field_type: checkbox` and `metadata.xsoar.config_type: backend`. Grouped-connector namespaced ids (e.g. `xsoar-qualys_fim_defaultIgnore`) are canonicalized via the handler's `serializer.yaml` `field_mappings` before the check — same resolution pattern as CO120. | Done |
| CO137 | `IsValidDurationTypeParam` | Both | Every field with `field_type: duration` (anywhere in `connection.yaml` or `configurations.yaml` — top-level `general_configurations`, profile `configurations`, and per-capability `configurations`) MUST expose `options.units == ["days","hours","minutes"]` (exact list, mandatory order), `options.output_format == "minutes"`, and per-unit `default_value` caps `hours <= 23` + `minutes <= 59` (§2.11 + Appendix A row 19). All sub-rule failures aggregate into a single ValidationResult per connector. | Done |
| CO138 | IsParamConfigTypeValid | Both | The following fields — and **only** these fields — MUST carry a `metadata.xsoar: { config_type: "backend" }` field: engine (per connection profile), engine\_group (per connection profile), mappingId (configurations.yaml under fetch capability Incoming), mapperId (configurations.yaml under fetch capability), defaultIgnore (configurations.yaml under automation capability), integrationLogLevel (configurations.yaml under general\_configurations). For all other params, ensure they don’t have config\_type \= backend. Note: must use serializer to find the params. |  |
| CO139 | `IsHandlerContainLoglevel` | Both | Every XSOAR handler must be reachable by an `integrationLogLevel` field (§3.7 rule "Canonical integrationLogLevel block" + Appendix J) under `configurations.yaml` `general_configurations.configurations[]`. **Standard connectors:** the union of `required_for_capabilities` across all field-group entries containing `integrationLogLevel` MUST cover every capability id XSOAR handlers subscribe to. **Grouped connectors:** each XSOAR handler's `view_group` id is matched against `handler.related_integration.object_id` using the same alphanumeric-only normalization as CO122 (lowercased, every non-alphanumeric character stripped — view_group ids are developer-facing so stylistic drift is tolerated), and the matching entry MUST carry `advanced: true` plus the field. **Field-shape sub-checks (both):** `field_type: select`, `metadata.xsoar.config_type: backend`, `options.searchable: true`, `options.clearable: true`, `options.values` keys include `Off`, `Debug`, `Verbose`. Namespaced field ids (e.g. `xsoar-qualys_fim_integrationLogLevel`) are canonicalized via serializer `field_mappings` before matching (same resolution pattern as CO120/CO136). Skip only if no XSOAR handlers OR no `configurations.yaml`; a missing field with XSOAR handlers present is a hard failure. | Done |
| CO140 | IsValidAdvancedMaaping | Both | Ensures that each advanced param in the integration yml contains the advanced: true field in the connector. |  |
| CO141 | `IsMirroringOmitted` | Both | Mirroring is out of scope on Platform — `outgoingMapperId`, `defaultMapperOut`, and any other mirroring params MUST NOT be emitted in the connector (§3.2, §3.7). |  |
| CO142 | `OneFieldPerFieldsBlock` | Grouped only | Each `configurations[].fields[]` block (and each `general_configurations.configurations[].fields[]` block) MUST contain exactly one field — one field per UI row — with the sole exception of a `checkbox_group`'s inner `fields[]` items  | TBD if we should do. May be noisy |
| CO143 | `IsSelectSearchableClearable` | Grouped only | Every `select` and `multi_select` field MUST set `options.searchable: true` and `options.clearable: true` (§3.7 field rule 9). |  |
| CO144 | `IsConfigOnSubCapability` | Grouped only | In grouped connectors, every `configurations.yaml` `configurations[]` entry's `id` MUST be a sub-capability id (declared under `capabilities.yaml` `capabilities[*].sub_capabilities[*].id`), never a bare parent capability id (§3.7 configurations rule 3). Additionally, every declared sub-capability MUST have a matching `configurations[]` entry — even an empty one carrying only its `view_group` and `configurations: []` — so the tile is still emitted (§3.7 configurations rule 4). Findings (bare-parent-id use, unknown ids, missing sub-cap coverage) aggregate into a single `ValidationResult` per connector. Short-circuits with `if not grouped: pass`. | Done |
| CO145 | NoImpliedFetchCheckbox | Both | The implied fetch checkbox for a declared collection capability MUST be omitted — choosing the capability implies it. Forbid emitting `isFetch`, `feed`, `isFetchEvents`, `isFetchAssets`, or `isFetchCredentials` as user fields (§3.4 note 5, §3.7). |  |

## summary.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO146 | `IsSummaryPresentAndValidMetadata` (merges CO146+CO147) | Both | Every migrated connector MUST ship a `summary.yaml` file AND its `metadata.title` must equal "Summary" and `metadata.description` must equal "Review your instance configuration". Merged into a single validator because both rules operate on the same file with a natural dependency (contents can only be checked if the file exists). Missing-file case aborts early; when the file exists, missing/invalid title and description aggregate into a single `ValidationResult` per connector. Path pinned to `summary.yaml`. | Done |
| ~~CO147~~ | ~~`IsValidSummaryMetadata`~~ | — | **Merged into CO146** — see `IsSummaryPresentAndValidMetadata` above. | Done (merged) |

## triggers.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO148 | `IsValidEngineTriggers` | Both | For every `<prefix>engine_mode` field id declared in `connection.yaml` (bare `engine_mode` for standard; profile-namespaced ids like `plain_jira_v3_engine_mode` for grouped), the `triggers.yaml` file MUST contain three canonical engine triggers: (1) hide `<prefix>engine` when `<prefix>engine_mode != "engine"` — `conditions: { id: <prefix>engine_mode, behavior: value, operator: neq, value: engine }` + `effects: [{ id: <prefix>engine, action: { hidden: true } }]`; (2) same shape but `value: engineGroup` on `<prefix>engineGroup`; (3) unlock `<prefix>proxy` (`read_only: false`) once either engine or engineGroup is set — `conditions: { operator: OR, children: [{ id: <prefix>engine, behavior: value, operator: is_not_empty }, { id: <prefix>engineGroup, behavior: value, operator: is_not_empty }] }` + `effects: [{ id: <prefix>proxy, action: { read_only: false } }]` (§3.7 engine triggers). Discovery scans raw connection.yaml ids matching `(.*)engine_mode$` (no serializer resolution — triggers.yaml uses raw ids). Skip when no `engine_mode` field is present (Appendix G integrations). Missing `triggers.yaml` + at least one engine_mode = hard fail. All findings aggregate into a single `ValidationResult` per connector. | Done |
| ~~CO149~~ | ~~`IsFetchMutexTriggers`~~ | ~~Both~~ | ~~For any handler (integration) whose `serializer.yaml` `computed_fields` emits ≥2 of the 5 fetch flags (`isFetch`, `feed`, `isFetchEvents`, `isFetchAssets`, `isFetchCredentials`) gated by capability conditions, the `triggers.yaml` file MUST contain the `n × (n-1)` canonical mutex triggers among those capability ids. Each mutex trigger: `conditions: { id: <Fi>, behavior: selected, operator: eq, value: true }` + `effects: [{ id: <Fj>, action: { read_only: true }, message: "Select only one fetch option." }]` (§3.4 note 6, §3.5). Discovery is data-driven from serializer computed_fields (no hard-coded capability whitelist) — grouped-namespaced ids (`fetch-issues_akamai-waf-siem` etc.) are naturally scoped per handler. Missing `triggers.yaml` while any handler requires mutex triggers = hard fail. All findings aggregate into a single `ValidationResult` per connector.~~ | **Removed (revisit later)** — the strict N×(N-1) flat single-condition shape (`conditions: { id, behavior: selected, operator: eq, value: true }`) rejects the equivalent OR-collapsed shape (`conditions: { operator: OR, children: [...] }` with a shared `read_only: true` effect) used today by connectors such as `crowdstrike`. Validator file and its `TestCO149IsFetchMutexTriggers` suite deleted; recover from git history when re-introducing. Decide between (a) relaxing the validator to accept the OR-collapsed form, or (b) reshaping connector triggers to the canonical singles before re-enable. |
| CO150 | `IsCollectionAutoEnablesAutomation` | Both | For each handler whose `serializer.yaml` `computed_fields` emits ≥1 fetch flag (same 5-flag whitelist as CO149) AND whose derived `automation-and-remediation<_suffix>` cap is declared on the connector, `triggers.yaml` MUST contain exactly ONE canonical auto-enable trigger with: `conditions: { operator: OR, children: [{ id: <Fi>, behavior: selected, operator: eq, value: true }, ...] }` (one child per fetch cap of THIS handler; extras or omissions fail) + `effects: [{ id: <automation_cap_id>, action: { read_only: true, enabled: true } (strict), message: "A selected capability enables this setting. Clear the active dependency to disable it" }]`. Discovery is data-driven from serializer computed_fields; automation cap id derived by suffix substitution (`fetch-issues_akamai-waf-siem` → `automation-and-remediation_akamai-waf-siem`; bare `fetch-issues` → bare `automation-and-remediation`). Skip when handler has no fetch caps or the derived automation cap isn't declared on the connector. Missing `triggers.yaml` while any handler needs one = hard fail. All findings aggregate into one `ValidationResult` per connector. | Done |
| CO151 | `IsFeedExpirationIntervalGated` | Both | If `feedExpirationInterval` is emitted, a trigger must make it visible only when the `threat-intelligence-and-enrichment` (feed) capability is on AND `feedExpirationPolicy == "interval"` |  |
| CO152 | `IsLongRunningPortGated` | Both | If `longRunningPort` is emitted, a trigger must make it visible only when `longRunning == true` AND no engine/engine group is selected (§3.5). |  |

## handler.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO153 | IsHandlerFolderNameMatchesId | Both | The handler folder name under components/handlers/ must equal the handler `id`. Not enforced by schema/OPA. |  |
| CO154 | IsHandlerIdXsoarPrefixed | Both | For XSOAR handlers (module: xsoar), `id` must equal `xsoar-<normalized-integration-id>` (integration commonfields.id lowercased, spaces→dashes). |  |
| CO155 | IsHandlerModuleXsoar | Both | XSOAR handlers must set `metadata.module: xsoar` (schema does not require module presence). A handler is considered "XSOAR" via `HandlerData.is_xsoar` — OR of `module=="xsoar"`, `team=="xsoar"`, or `@xsoar-content` in `maintainers`. This validator enforces that the canonical self-declaring signal (`metadata.module`) is present and equals `xsoar`. Emits one result per offending handler; path points at the handler.yaml. | `Done` |
| CO156 | IsHandlerOwnershipFieldsAlign | Both | Handler `metadata.ownership` must align: `team == "xsoar"` AND `"@xsoar-content"` in `maintainers` (contains-check, mirroring CO100 at handler granularity; co-maintainers permitted). Applies to every handler where `HandlerData.is_xsoar` is True. Emits one aggregated result per offending handler with both problems joined; path points at the handler.yaml. | `Done` |
| ~~CO157~~ | ~~IsHandlerDescriptionTemplated~~ | Both | ~~`metadata.description` must follow the template `"XSOAR handler for <name> integration"`.~~ | `Removed - too strict / not useful. Deleted per team decision.` |
| ~~CO158~~ | ~~IsHandlerTriggeringLabelsPresent~~ | Both | ~~`triggering.labels` must include `xsoar-integration-id` and `xsoar-pack-id`.~~ | `Removed - subsumed by CO164 (xsoar-integration-id presence + resolution) and CO165 (xsoar-pack-id presence + resolution). No net loss of coverage.` |
| CO159 | IsHandlerHasValidTestConnection | Both | Every XSOAR handler must declare both `test_connection` AND `test_connection_metro`, each equal to exactly `{type: service, service: xsoar, endpoint: /settings/integration/connector/verification}` with no extra fields (`host`/`headers` must be omitted). `test_connection_metro` is `Optional` at the model layer but mandatory per policy — a missing block is flagged. Aggregated per-handler result covering both blocks; path points at the handler.yaml. | `Done` |
| CO160 | IsHandlerIDUnique | Both | Handler `id` must be unique across all handlers in the connector.  | To be done by UCP: https://jira-dc.paloaltonetworks.com/browse/CRTX-270338 |
| CO161 | IsFetchCapabilitiesContainActions | Both | Every fetch-family capability subscribed by the handler must declare its required reset-state action in `capabilities[].actions[].type`. Base id → required action: `fetch-issues` → `reset_incidents_last_run`; `log-collection` → `reset_events_last_run`; `fetch-assets-and-vulnerabilities` → `reset_assets_last_run`; `threat-intelligence-and-enrichment` → `reset_feed_last_run`. `fetch-secrets` is stateless and has no required action. `automation-and-remediation` is not a fetch capability and is not required to declare any action (handlers may still declare optional actions on it — CO161 only enforces required ones). Namespaced ids (`<base>_<suffix>`) are stripped to their base for the lookup. Aggregated per-handler result; path → handler.yaml. | `Done` |
| CO162 | IsValidWorkloads | Both | For every XSOAR handler, each `capabilities[].auth_options[].workloads` list must equal the canonical set `{xsoar-automationhub-runner, xsoar-pod}` (order-insensitive; missing/empty lists fail). Additionally, the anonymous capability-level shape (`capabilities[].workloads` without auth_options) must NOT be used by XSOAR handlers (its presence is a hard fail). Aggregated per-handler result; path → handler.yaml. | `Done` |
| CO163 | handlerOnlySubscribedToSubCapabilities | Grouped only | Grouped handlers must subscribe to SUB-capabilities only, never bare capabilities (§3.8 rule 3). Short-circuits (pass) for non-grouped connectors. |  |
| CO164 | `IsMatchingIntegrationExist` | Both | Every XSOAR handler MUST (1) declare an `xsoar-integration-id` triggering label, (2) resolve to a real integration in the content graph, AND (3) the label MUST equal the resolved integration's YML `object_id` verbatim (case-sensitive, no slugification). Rule (3) is the invariant that lets CO122/CO139 compare `view_group.id` against `integration.object_id` verbatim - if this validator passes, `xsoar-integration-id` and `integration.object_id` are interchangeable. Fails when: label is missing, integration is unresolved, or label drifts from YML id (e.g. slugified handler label vs. spaced YML id). | Done |
| CO165 | IsHandlerMatchingPackExist | Both | Every XSOAR handler must declare `xsoar-pack-id` in `triggering.labels`, and the label must match the pack that owns the handler's referenced integration (`handler.related_integration.pack_id`). Consistency-based (uses already-resolved graph data; no additional queries). Fails on: missing label, unresolvable integration, or pack-id mismatch. Emits one result per offending handler; path points at the handler.yaml. | `Done` |
| CO166 | NoOrphanedHandlerFiles | Both | Scans the connector directory for handler-\*.yaml files. For each file, verify it's referenced by at least one capability's handler\_id mapping.Unless the handler is “disabled”, then its allowed  |  |
| CO167 | IsServerStyleCredentialPinned | Both | Appendix I server-style integrations that carry a type-9 `credentials` param must set `triggering.labels.xsoar-long-running-credentials-profile-id` to the id of the connection profile that supplies those credentials. If the integration has no type-9 `credentials` param, flag as a migration blocker. |  |
| CO168 | IsActionOnSubCapability | Both | Handler `capabilities[].actions[]` must be declared only on sub-capability entries, never on a bare parent capability (§3.8 "Actions per sub-capability"). |  |
| CO169 | IsNoDuplicateHandlerIntegration | Both | No two handlers may point to the same integration — handler==integration is 1:1. Enforce that `triggering.labels.xsoar-integration-id` is unique across all handlers in the connector |  |
| CO170 | IsHandlerMigrationConstants | Both | Every XSOAR handler must set `triggering.type: "PUB_SUB"` (per §3.8). Per-handler validation; path→handler.yaml. **Scoped down**: `enabled: true` and `metadata.version: "1.0.0"` deferred to a later expansion. | Done |

## serializer.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO171 | `IsCollectionSubCapabilityFetchFlagValid` | Both | **Forward direction**: For every collection sub-capability the handler subscribes to (`fetch-issues`, `log-collection`, `fetch-assets-and-vulnerabilities`, `fetch-secrets`, `threat-intelligence-and-enrichment`), the handler's `serializer.yaml` must exist and its `computed_fields` block must contain a rule that (a) outputs the correctly-mapped flag id (`isFetch`, `isFetchEvents`, `isFetchAssets`, `isFetchCredentials`, `feed` respectively) with a truthy value (`true`/`"true"`/`"on"`), AND (b) is gated on a `type: capability` condition whose `options.capability_id` equals the subscribed cap id (bare or grouped-namespaced) with `options.value == "on"`. Base id derived by splitting on first `_`. Per-handler aggregated result; path→serializer.yaml. | Done |
| CO172 | `IsFetchFlagGatedOnOwnSubCapability` | Both | **Reverse direction**: Every fetch-flag emission (isFetch, isFetchEvents, isFetchAssets, isFetchCredentials, feed) in an XSOAR handler's `serializer.yaml` must be gated on a `type: capability` condition targeting a cap that (a) appears in `handler.capabilities[].id` (this handler subscribes to it), AND (b) whose base id matches the emitted flag per the canonical mapping. Per-handler aggregated result; path→serializer.yaml. **Subsumes CO173**: `automation-and-remediation` is not in the mapping, so any fetch flag gated on it fails clause (b). | Done |
| ~~CO173~~ | ~~`NoFetchFlagForAutomationRemediation`~~ | ~~Both~~ | ~~The `automation-and-remediation` sub-capability must NOT emit any fetch flag, since it is not a collection capability. Negative rule.~~ | **Removed** — subsumed by CO172 (any fetch flag gated on `automation-and-remediation` fails CO172's mapping-family check). |

## CODEOWNERS

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO174 | IsConnectorInCodeowners | Both | Every new connector must have a `/connectors/<connector-name>/**` entry in the repo-root CODEOWNERS file, and that entry must list at least one owner (user handle). (§3.11) |  |

## Breaking-Change Guards

These are diff-based guards that run in git mode (`demisto-sdk validate -g`), comparing the connector against its previously committed version. They fail when a change would break already-deployed customer instances or the FE/BE contract.

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO175 | `NoRemovedConnectorParams` | Both | **Breaking Change Check:** For every XSOAR handler that exists in both the prior and the new version (matched by `handler.id`), no `connector_param_name` from the prior version's `handler.resolved_params` may be missing in the new version. The resolved-params set is XSOAR-relevant only (connection.yaml general_configurations, the profiles the handler authenticates against, capabilities.yaml general_configurations, and configurations.yaml entries for the handler's capabilities — as computed by `ConnectorParser._build_resolved_params`). Additions are allowed; newly-added handlers are skipped. Per-handler aggregated result; path→handler.yaml. `expected_git_statuses = [MODIFIED, RENAMED]`. | Done |
| CO176 | `NoChangeConnectorIDs` | Both | **Breaking Change Check:** Any-change guard for the 6 id families: `connector_id` (top-level), `handler_id` (`connector.handlers[].id`), `capability_id` (`connector.capabilities[].id`), `sub_capability_id` (`connector.capabilities[].sub_capabilities[].id`), `profile_id` (`connector.connection.profiles[].id`), `view_group_id` (`connector.connection.view_groups[].id`). For each family, the prior version's id set must be a subset of the new version's set (renames and removals both fail, additions are allowed). One aggregated result per connector; path→connector root. `expected_git_statuses = [MODIFIED, RENAMED]`. Subsumes CO177 (`capability_id` + `sub_capability_id`), CO180 (`profile_id`), CO182 (`view_group_id` — non-grouped connectors have an empty view_groups list so the family is a no-op for them), and CO184 (`handler_id` — deleting a handler folder removes its `handler.yaml` so the parser drops its `HandlerData` and its id disappears from the new set). | Done |
| ~~CO177~~ | ~~`NoRemovedCapabilities`~~ | ~~Both~~ | ~~**Breaking Change Check:** A capability or sub-capability present in the prior version must not be removed; existing enabled instances would lose functionality.~~ | **Removed** — subsumed by CO176 (its `capability_id` + `sub_capability_id` families cover both removal and rename cases). |
| CO178 | NoParamTypeChanged | Both | **Breaking Change Check:** An existing field's `type` must not change (e.g., shortText→encrypted, single→checkbox\_group); it breaks stored values and FE rendering. |  |
| CO179 | `NoParamRequiredTightened` | Both | **Breaking Change Check:** For each XSOAR handler, no field id present in BOTH the prior and new version may have `options.create_modifiers.required` OR `options.edit_modifiers.required` transition from false/unset to `true`. The XSOAR-visible field surface per handler is built from: (1) `connection.yaml` `general_configurations`, (2) `connection.yaml` `profiles[]` referenced via `handler.capabilities[].auth_options[].id`, (3) `capabilities.yaml` `general_configurations`, and (4) the per-capability configurations unified onto `CapabilityData.configurations` for the handler's declared `capabilities[].id`. Missing modifier blocks / missing `required` keys count as false, so an explicit `true` on a previously-implicit-false modifier still fails. Newly-added fields and existing required→optional relaxations are allowed. One aggregated result per offending handler; path→handler.yaml. `expected_git_statuses = [MODIFIED, RENAMED]`. | Done |
| ~~CO180~~ | ~~`NoRemovedProfile`~~ | ~~Both~~ | ~~**Breaking Change Check:** A connection profile (`profiles[].id`) present in the prior version must not be removed; instances bound to it would break.~~ | **Removed** — subsumed by CO176 (its `profile_id` family covers both removal and rename of `connection.profiles[].id`). |
| CO181 | `NoRemovedAuthOption` | Both | **Breaking Change Check:** For each XSOAR handler present in both versions (matched by `handler.id`): (1) per `(handler_id, capability_id)`, the prior set of `auth_options[].id` must be a subset of the new set (removals and renames both fail); (2) per `(handler_id, capability_id, auth_option_id)` for auth_options that survived (1), the prior set of method ids (from `auth_options[].methods[]`, normalizing the `str | {id, scopes}` union) must be a subset of the new set. Capability additions and handler additions are allowed. Whole-capability removals are already covered by CO176's `capability_id` family and are not re-reported here. One aggregated result per offending handler; path→handler.yaml. `expected_git_statuses = [MODIFIED, RENAMED]`. | Done |
| ~~CO182~~ | ~~`NoChangedViewGroupId`~~ | ~~Grouped only~~ | ~~**Breaking Change Check:** A `view_groups[].id` must not change or be removed; grouped-connector field bindings would break. Short-circuits (pass) for non-grouped connectors.~~ | **Removed** — subsumed by CO176's new `view_group_id` family (non-grouped connectors have an empty view_groups list, so the family is a natural no-op for them and no explicit grouped-only gate is needed). |
| CO183 | `NoGroupedFlagFlipped` | Both | **Breaking Change Check:** `settings.grouped` must not change value (`true` ↔ `false`) between versions. The flag drives connector shape (single service vs multi-service view-group registry) and id-namespacing conventions; flipping it corrupts every enabled instance's expectations. Missing `settings` block defaults to `False` (matches the model default), so first-time serializations don't false-flag when a prior version omitted the block entirely. One result per connector; path→connector root. `expected_git_statuses = [MODIFIED, RENAMED]`. | Done |
| ~~CO184~~ | ~~`NoRemovedHandler`~~ | ~~Both~~ | ~~**Breaking Change Check:** A handler folder present in the prior version must not be deleted; its integration's instances would break.~~ | **Removed** — subsumed by CO176's `handler_id` family. Deleting a handler folder removes its `handler.yaml`, so the parser drops its `HandlerData`, so its id disappears from the new set and CO176 flags the missing `handler_id` with the same removal semantics. |
| CO185 | NoChangedFetchFlagMapping | Both | **Breaking Change Check:** A serializer fetch-flag `computed_fields` mapping (output flag id or gating `capability_id`) for an existing collection sub-capability must not change; BE fetch would break. |  |
| CO186 | NoChangedHandlerModule | Both | **Breaking Change Check:** A handler's `metadata.module` must not change. |  |
| CO187 | NoChangedHandlerTriggeringLabels | Both | **Breaking Change Check:** A handler's `triggering.labels.xsoar-integration-id` and `triggering.labels.xsoar-pack-id` must not change. |  |

## Whole-Connector Schema

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO188 | IsValidConnectorYamlSchema | Both | Validate the connector YAML conforms to the Pydantic schema (all required fields present, types correct, nested structures valid). |  |
| CO189 | NoHiddenParamInConnector | Both | Ensure that all params being used in the connector are not hidden: true or hidden: \-platform in the corresponding integration yml. |  |

## Integration-Side (XSOAR YML)

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO190 | NoReservedParamNames | Both (integration-side) | Runs only on integrations; ensure no param is called engine/engine\_mode/instance\_name/engine\_group. | Done |
| CO191 | IsEventcollectorCapabilityMapped | Both (integration-side) | §3.4 note 1 eventcollector carve-out: an integration whose name/id contains `eventcollector` (case-insensitive) gets a `log-collection` sub-capability ONLY, UNLESS it has ≥3 commands OR ≥1 command whose name does not contain `get-events` — in which case it ALSO gets an `automation-and-remediation` sub-capability. Validate the capability mapping matches this rule. |  |

## Customer-Facing / Terminology

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO193 | NoIntegrationInCustomerFacingDocs | Both | Ensures the word incidents is not being exposed to customers, it should be "issues" instead. |  |

---

## Notes & edge cases

- **`capabilities.yaml` vs `connector.yaml`:** CO102 (IsInstanceNameTemplateValid) and CO100 (IsValidCapabilitiesMetadata) target `capabilities.yaml` — the `instance_name` param and the metadata block are defined there, not in `connector.yaml`.  
- **`connection.yaml` / `configurations.yaml` overlap:** Some `connection.yaml` validators (CO102 IsGeneralParamsExist, CO103 IsValidInterpolation) may also touch `configurations.yaml`; they are categorized by their primary file.  
- **Grouped-only short-circuit:** CO104 (IsValidViewgroup) and CO106 (IsValidGroupedConnectorAuth) depend on grouped-only constructs and short-circuit with `if not grouped: pass`. CO115 (IsConfigOnSubCapability) is another grouped-only short-circuit.  
- **`connector.yaml` additive scope:** connector.yaml validators CO101–CO106 are additive to the unified-connectors JSON schema \+ OPA policies, which already enforce structural/shape rules (id minLength, semver format, required fields, author\_image pattern & on-disk existence, folder-name==id, grouped↔view\_groups). The CO validators here cover value/policy/cross-repo rules not expressible in schema/OPA.
