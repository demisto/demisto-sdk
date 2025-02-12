from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.common.constants import MarketplaceVersions 
MULTIPLE_ZIPPED_PACKS_FILE_STEM = "uploadable_packs"
MULTIPLE_ZIPPED_PACKS_FILE_NAME = f"{MULTIPLE_ZIPPED_PACKS_FILE_STEM}.zip"

CONTENT_TYPES_EXCLUDED_FROM_UPLOAD = {
    ContentType.TEST_PLAYBOOK,
    ContentType.TEST_SCRIPT,
}

CONTENT_TYPES_EXCLUDED_FROM_PLATFORM = {
    ContentType.INCIDENT_FIELD,
    ContentType.INCIDENT_TYPE,
    ContentType.CLASSIFIER,
    ContentType.MAPPER,
    ContentType.DASHBOARD,
    ContentType.WIDGET,
    ContentType.REPORT,
}
CONTENT_TYPES_EXCLUDED_FROM_UPLOAD_FOR_MARKETPLACE = {
    MarketplaceVersions.PLATFORM: CONTENT_TYPES_EXCLUDED_FROM_PLATFORM.union(CONTENT_TYPES_EXCLUDED_FROM_UPLOAD)
}