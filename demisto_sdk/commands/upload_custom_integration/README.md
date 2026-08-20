## upload-custom-integration

### Overview

Upload a custom integration to Cortex Platform with '_copy' marker safety enforcement.

Validates that the integration's 'commonfields.id' and 'name' fields end
with the '_copy' marker before uploading, preventing ID conflicts with
official marketplace integrations.


RISK: If a custom integration is uploaded with an ID that matches a marketplace
integration's ID, subsequent installations of the marketplace containing that
integration will fail with a system error.


ENVIRONMENT VARIABLES:
  DEMISTO_BASE_URL   Cortex Platform instance URL (required)
  DEMISTO_API_KEY    Valid API key for the instance (required)
  XSIAM_AUTH_ID      Auth ID for Cortex Platform (required)


EXAMPLES:
  demisto-sdk upload-custom-integration -i Integrations/MyIntegration_copy/MyIntegration_copy.yml
  demisto-sdk upload-custom-integration -i Integrations/MyIntegration_copy/
  demisto-sdk upload-custom-integration -i Integrations/MyIntegration/MyIntegration.yml --force-id
### Options

- **--input-path**: Path to the integration YAML file or its parent directory. The file's 'commonfields.id' and 'name' must end with '_copy'. NOTE: It is also strongly recommended to append '_copy' to the integration's display name ('display' field) to avoid confusion with existing marketplace integrations in the UI.

- **--force-id**: Bypass the '_copy' marker validation. WARNING: Uploading without '_copy' risks conflicting with official marketplace IDs and may cause pack installation failures. Before using this flag, verify ALL of the following: (1) Your chosen ID is completely unique and does NOT match the original integration ID. (2) Your chosen ID does NOT match any other integration ID already present in the repository. (3) Your chosen ID does NOT match any integration ID published on the Marketplace.
  - Default: `False`
