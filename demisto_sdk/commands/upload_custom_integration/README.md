## upload-custom-integration

### Overview

Upload a custom integration to Cortex Platform with safety enforcement.

Validates that the integration's ``commonfields.id`` and ``name`` fields
end with the ``_copy`` marker before uploading, preventing ID conflicts
with official system pack integrations.


RISK: If a custom integration is uploaded with an ID that matches a system
integration's ID, subsequent installations of the system pack containing that
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

- **--input-path**: Path to the integration YAML file or its parent directory. The file's 'commonfields.id' and 'name' must end with '_copy'.

- **--force-id**: Bypass the '_copy' marker validation. WARNING: Uploading without '_copy' risks conflicting with official system pack IDs and may cause pack installation failures.
  - Default: `False`
