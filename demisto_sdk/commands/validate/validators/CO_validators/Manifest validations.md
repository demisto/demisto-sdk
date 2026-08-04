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
| CO122 | `IsValidViewgroup` | Grouped only | Ensure that each XSOAR handler has a view group with id matching the handler's integration id. `view_groups` only exist when grouped; implementation short-circuits with `if not grouped: pass`. |  |
| CO123 | `IsProfileFieldsCovered` | Both | Ensures that for each auth profile that supports interpolation, all the non-interpolated params have publish \= true (except for engine\_mode). |  |
| CO124 | `IsValidGroupedConnectorAuth` | Grouped only | Every `ConnectionProfile` in a grouped connector MUST declare a non-empty `metadata.xsoar.interpolation_mapping` string. Missing key, `null`, empty string, and whitespace-only are all rejected. No per-profile ownership check — grouped connectors are XSOAR-only by CO111. Complements CO121 which validates mapping contents. Short-circuits `if not grouped: pass`. | Done |
| CO125 | `IsAuthProfileHasEngine` | Both | Ensures the engine triplet (`engine_mode`, `engine`, `engine_group`/`engineGroup`) is present. Grouped: checked per profile inside `profile.configurations`. Standard: checked once at `connection.general_configurations`. Integrations on the Appendix G engine/proxy exclusion list are skipped (CO127 validates the opposite direction). | Done |
| CO126 | `IsValidEngineParams` | Both | Ensure that there's an engine\_mode radio\_button; the engine\_mode has horizontal view; the options must be "no engine", "engine", "engine-group"; all 3 engine params appear under the same field; engine and engine\_group must be defined as config\_type: backend; engine and engine\_group must be defined as type "select" with dynamic value with the proper payload; engine and engine\_group must be triggered on create and edit; engine and engine\_group need to be hidden by default; all 3 need to be advanced. |  |
| CO127 | IsEngineExclusionRespected | Both | Integrations on the Appendix G engine/proxy exclusion list (EDL, ExportIndicators, PingCastle, Publish List, Simple API Proxy, Syslog v2, TAXII Server, TAXII2 Server, Web File Repository, Workday\_IAM\_Event\_Generator, XSOAR-Web-Server, Microsoft Teams, AWS-SNS-Listener) must emit NO `engine_mode`, `engine`, `engine_group`, or `proxy` fields at all. |  |
| CO128 | IsSingleEngineRespected | Both | Integrations on the Appendix H single-engine list (saml, slack, sharedagent, syslog, mattermost, duo) must emit `engine_mode` with only 2 options (`no_engine` \+ `engine`) and the `engine` dropdown, and MUST NOT emit `engine_group`. |  |

## configurations.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO129 | `IsValidConfigurationsMetadata` | Both | `metadata.title` must equal "Configuration"; `metadata.description` must equal "Adjust and refine your configuration" (§3.7). |  |
| CO130 | IsValidFetch | Both | Ensure that if the connector has the “Fetch Issues” capability, it includes all related params existing and configured correctly — isFetch, incidentType, incidentFetchInterval, Mapper-in, classifier. |  |
| CO131 | IsValidFeed | Both | Ensure that if the connector has the feed capability, it includes all related params as well (reputation, reliability, expiration interval, etc) and that they're configured correctly. Params to validate: feed, feedFetchInterval, feedReputation, feedReliability, feedExpirationPolicy, feedExpirationInterval, feedBypassExclusionList. |  |
| CO132 | IsValidFetchAssets | Both | Ensure that if the connector has the fetch-assets capability, it includes all related params as well. Params to validate: isFetchAssets, assetsFetchInterval. |  |
| CO133 | IsValidFetchEvents | Both | Ensure that if the connector has the fetch-events capability, it includes all related params as well. Params to validate: isFetchEvents, eventFetchInterval. |  |
| CO134 | IsValidFetchCredentials | Both | Ensure that if the connector has the fetch-credentials capability, it includes all related params as well. Params to validate: isFetchCredentials. |  |
| CO135 | IsValidLongRunning | Both | Ensure that if the connector has the long-running capability, it includes all related params as well (long-running port, long-running checkbox). |  |
| CO136 | IsValidAutomationCapability | Both | Ensure that automation capability has DefaultIgnore param. |  |
| CO137 | IsValidDurationTypeParam | Both | Ensures that minutes \< 60, hours \< 24; we need a validator to make sure we always do output\_format: "minutes" and units: \["days", "hours", "minutes"\]. |  |
| CO138 | IsParamConfigTypeValid | Both | The following fields — and **only** these fields — MUST carry a `metadata.xsoar: { config_type: "backend" }` field: engine (per connection profile), engine\_group (per connection profile), mappingId (configurations.yaml under fetch capability Incoming), mapperId (configurations.yaml under fetch capability), defaultIgnore (configurations.yaml under automation capability), integrationLogLevel (configurations.yaml under general\_configurations). For all other params, ensure they don’t have config\_type \= backend. Note: must use serializer to find the params. |  |
| CO139 | IsHandlerContainLoglevel | Both | Ensures that each XSOAR-supported handler has a valid integrationloglevel param under general\_configurations. Log level needs to be advanced. Needs to be in correct template.  Note: must use serializer to find the param |  |
| CO140 | IsValidAdvancedMaaping | Both | Ensures that each advanced param in the integration yml contains the advanced: true field in the connector. |  |
| CO141 | `IsMirroringOmitted` | Both | Mirroring is out of scope on Platform — `outgoingMapperId`, `defaultMapperOut`, and any other mirroring params MUST NOT be emitted in the connector (§3.2, §3.7). |  |
| CO142 | `OneFieldPerFieldsBlock` | Grouped only | Each `configurations[].fields[]` block (and each `general_configurations.configurations[].fields[]` block) MUST contain exactly one field — one field per UI row — with the sole exception of a `checkbox_group`'s inner `fields[]` items  | TBD if we should do. May be noisy |
| CO143 | `IsSelectSearchableClearable` | Grouped only | Every `select` and `multi_select` field MUST set `options.searchable: true` and `options.clearable: true` (§3.7 field rule 9). |  |
| CO144 | `IsConfigOnSubCapability` | Grouped only | In grouped connectors, config params and `view_group` live on the SUB-capability (each `configurations[]` entry `id` is a sub-capability id), never on a bare parent capability; an empty sub-capability still emits a `configurations[]` entry carrying its `view_group` with `configurations: []` (§3.7 configurations 3 & 4). Short-circuits with `if not grouped: pass`. |  |
| CO145 | NoImpliedFetchCheckbox | Both | The implied fetch checkbox for a declared collection capability MUST be omitted — choosing the capability implies it. Forbid emitting `isFetch`, `feed`, `isFetchEvents`, `isFetchAssets`, or `isFetchCredentials` as user fields (§3.4 note 5, §3.7). |  |

## summary.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO146 | `IsSummaryPresent` | Both | Every migrated connector MUST ship a `summary.yaml` file. From a pure connector POV it is optional, but from the XSOAR content POV it is required. |  |
| CO147 | `IsValidSummaryMetadata` | Both | `summary.yaml` `metadata.title` must equal "Summary" and `metadata.description` must equal "Review your instance configuration". |  |

## triggers.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO148 | `IsValidEngineTriggers` | Both | For each auth profile that emits the engine fields, ensure the required engine `triggers.yaml` entries exist and are correct: (1) a trigger hides `engine` when `engine_mode != "engine"`; (2) a trigger hides `engine_group` when `engine_mode != "engine_group"`; (3) a trigger locks `proxy` (`read_only: true`) while `engine_mode == "no_engine"` and unlocks it once an engine or engine group is selected (§3.7). |  |
| CO149 | `IsFetchMutexTriggers` | Both | For any integration that contributes ≥2 fetch sub-capabilities, the `n × (n-1)` mutual-exclusion triggers must exist: each fetch sub-capability, when selected, sets the other fetch sub-capabilities of the SAME integration to `read_only: true` with the message "Select only one fetch option" (§3.4 note 6, §3.5). |  |
| CO150 | `IsCollectionAutoEnablesAutomation` | Both | For each collection (fetch) sub-capability an integration contributes, a trigger must exist that — when that sub-capability is selected — auto-enables and locks the integration's `automation-and-remediation` sub-capability (`action: { read_only: true, enabled: true }`) with the message "A selected capability enables this setting. Clear the active dependency to disable it"  Ensure there is a single trigger with all fetch types and OR between them. For example:- conditions:    operator: OR    children:    \- id: fetch-issues\_akamai-waf-siem      behavior: selected      operator: eq      value: true    \- id: log-collection\_akamai-waf-siem      behavior: selected      operator: eq      value: true  effects:  \- id: automation-and-remediation\_akamai-waf-siem    action:      read\_only: true      enabled: true    message: A selected capability enables this setting. Clear the active dependency      to disable it |  |
| CO151 | `IsFeedExpirationIntervalGated` | Both | If `feedExpirationInterval` is emitted, a trigger must make it visible only when the `threat-intelligence-and-enrichment` (feed) capability is on AND `feedExpirationPolicy == "interval"` |  |
| CO152 | `IsLongRunningPortGated` | Both | If `longRunningPort` is emitted, a trigger must make it visible only when `longRunning == true` AND no engine/engine group is selected (§3.5). |  |

## handler.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO153 | IsHandlerFolderNameMatchesId | Both | The handler folder name under components/handlers/ must equal the handler `id`. Not enforced by schema/OPA. |  |
| CO154 | IsHandlerIdXsoarPrefixed | Both | For XSOAR handlers (module: xsoar), `id` must equal `xsoar-<normalized-integration-id>` (integration commonfields.id lowercased, spaces→dashes). |  |
| CO155 | IsHandlerModuleXsoar | Both | XSOAR handlers must set `metadata.module: xsoar` (schema does not require module presence). |  |
| CO156 | IsHandlerOwnershipFieldsAlign | Both | Handler `metadata.ownership` must align: `team: xsoar` and `maintainers: [@xsoar-content]`. |  |
| CO157 | IsHandlerDescriptionTemplated | Both | `metadata.description` must follow the template `"XSOAR handler for <name> integration"`. | `Done` |
| CO158 | IsHandlerTriggeringLabelsPresent | Both | `triggering.labels` must include `xsoar-integration-id` and `xsoar-pack-id`. |  |
| CO159 | IsHandlerHasValidTestConnection | Both | Both `test_connection` AND `test_connection_metro` must each equal `{type: service, service: xsoar, endpoint: /settings/integration/connector/verification}`. |  |
| CO160 | IsHandlerIDUnique | Both | Handler `id` must be unique across all handlers in the connector.  | To be done by UCP: https://jira-dc.paloaltonetworks.com/browse/CRTX-270338 |
| CO161 | IsFetchCapbailitiesContainActions | Both | Fetch-type sub-capabilities subscribed by the handler must contain their required actions. |  |
| CO162 | IsValidWorkloads | Both | `workloads` must always equal `["xsoar-automationhub-runner", "xsoar-pod"]`. |  |
| CO163 | handlerOnlySubscribedToSubCapabilities | Grouped only | Grouped handlers must subscribe to SUB-capabilities only, never bare capabilities (§3.8 rule 3). Short-circuits (pass) for non-grouped connectors. |  |
| CO164 | IsHandlerMatchingIntegrationExist | Both | Ensure that the handler's matching integration ID exists. And is supported on platform marketplace. | Done |
| CO165 | IsHandlerMatchingPackExist | Both | Ensure that the handler's matching pack ID exists. |  |
| CO166 | NoOrphanedHandlerFiles | Both | Scans the connector directory for handler-\*.yaml files. For each file, verify it's referenced by at least one capability's handler\_id mapping.Unless the handler is “disabled”, then its allowed  |  |
| CO167 | IsServerStyleCredentialPinned | Both | Appendix I server-style integrations that carry a type-9 `credentials` param must set `triggering.labels.xsoar-long-running-credentials-profile-id` to the id of the connection profile that supplies those credentials. If the integration has no type-9 `credentials` param, flag as a migration blocker. |  |
| CO168 | IsActionOnSubCapability | Both | Handler `capabilities[].actions[]` must be declared only on sub-capability entries, never on a bare parent capability (§3.8 "Actions per sub-capability"). |  |
| CO169 | IsNoDuplicateHandlerIntegration | Both | No two handlers may point to the same integration — handler==integration is 1:1. Enforce that `triggering.labels.xsoar-integration-id` is unique across all handlers in the connector |  |
| CO170 | IsHandlerMigrationConstants | Both | Migrated XSOAR handlers must set the fixed migration constants: `enabled: true`, `metadata.version: "1.0.0"`, and `triggering.type: "PUB_SUB"` (§3.8). |  |

## serializer.yaml

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO171 | `IsCollectionSubCapabilityFetchFlagValid` | Both | For every collection sub-capability the handler subscribes to (`fetch-issues`, `log-collection`, `fetch-assets-and-vulnerabilities`, `fetch-secrets`, `threat-intelligence-and-enrichment`), the handler's serializer.yaml must exist and emit a `computed_fields` block that (a) is present, (b) outputs the correctly-mapped flag id (fetch-issues→`isFetch`, log-collection→`isFetchEvents`, fetch-assets-and-vulnerabilities→`isFetchAssets`, fetch-secrets→`isFetchCredentials`, threat-intelligence-and-enrichment→`feed`), and (c) emits `value: true` gated on the capability condition `value: "on"` And vice-versa. Meaning, if we have in serializer a fetch flag emitted, need to check its on the correct sub-capability as per the mapping. |  |
| CO172 | `IsFetchFlagGatedOnOwnSubCapability` | Both | The fetch-flag `computed_fields` block's `capability_id` must be THIS handler's subscribed sub-capability (`<capability-id>_<integration>`), not merely any capability that exists elsewhere in `capabilities.yaml`. |  |
| CO173 | `NoFetchFlagForAutomationRemediation` | Both | The `automation-and-remediation` sub-capability must NOT emit any fetch flag, since it is not a collection capability. Negative rule. |  |

## CODEOWNERS

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO174 | IsConnectorInCodeowners | Both | Every new connector must have a `/connectors/<connector-name>/**` entry in the repo-root CODEOWNERS file, and that entry must list at least one owner (user handle). (§3.11) |  |

## Breaking-Change Guards

These are diff-based guards that run in git mode (`demisto-sdk validate -g`), comparing the connector against its previously committed version. They fail when a change would break already-deployed customer instances or the FE/BE contract.

| Code | Validator Name | Applies To | Description | Status |
| :---- | :---- | :---- | :---- | :---- |
| CO175 | NoRemovedConnectorParams | Both | **Breaking Change Check:** Ensures no existing parameters were deleted from the YAML. |  |
| CO176 | NoChangeConnectorIDs | Both | **Breaking Change Check:** Ensure no change to existing connector fields handler\_id, capability\_id, sub\_capability\_id, profile\_id, connector\_id. |  |
| CO177 | NoRemovedCapabilities | Both | **Breaking Change Check:** A capability or sub-capability present in the prior version must not be removed; existing enabled instances would lose functionality. | Done |
| CO178 | NoParamTypeChanged | Both | **Breaking Change Check:** An existing field's `type` must not change (e.g., shortText→encrypted, single→checkbox\_group); it breaks stored values and FE rendering. |  |
| CO179 | NoParamRequiredTightened | Both | **Breaking Change Check:** An existing optional field must not become `required: true`; existing instances lacking a value would fail on save. |  |
| CO180 | NoRemovedProfile | Both | **Breaking Change Check:** A connection profile (`profiles[].id`) present in the prior version must not be removed; instances bound to it would break. |  |
| CO181 | NoRemovedAuthOption | Both | **Breaking Change Check:** A handler `auth_options[].id` or method present in the prior version must not be removed; authenticated instances would break. |  |
| CO182 | NoChangedViewGroupId | Grouped only | **Breaking Change Check:** A `view_groups[].id` must not change or be removed; grouped-connector field bindings would break. Short-circuits (pass) for non-grouped connectors. |  |
| CO183 | NoGroupedFlagFlipped | Both | **Breaking Change Check:** `settings.grouped` must not change (true↔false); it fundamentally alters the connector shape and registry. |  |
| CO184 | NoRemovedHandler | Both | **Breaking Change Check:** A handler folder present in the prior version must not be deleted; its integration's instances would break. |  |
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

