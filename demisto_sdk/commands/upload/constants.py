from demisto_sdk.commands.content_graph.common import ContentType

MULTIPLE_ZIPPED_PACKS_FILE_STEM = "uploadable_packs"
MULTIPLE_ZIPPED_PACKS_FILE_NAME = f"{MULTIPLE_ZIPPED_PACKS_FILE_STEM}.zip"

CONTENT_TYPES_EXCLUDED_FROM_UPLOAD = {
    ContentType.TEST_PLAYBOOK,
    ContentType.TEST_SCRIPT,
    ContentType.AGENTIX_ACTION_TEST,
}

# Content types that are not supported by the platform and should cause the upload to fail
# with a clear error message when found in a pack.
CONTENT_TYPES_NOT_SUPPORTED_IN_UPLOAD = {
    ContentType.JOB,
}
