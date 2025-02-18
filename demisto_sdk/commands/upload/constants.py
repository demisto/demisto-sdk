from demisto_sdk.commands.content_graph.common import ContentType

MULTIPLE_ZIPPED_PACKS_FILE_STEM = "uploadable_packs"
MULTIPLE_ZIPPED_PACKS_FILE_NAME = f"{MULTIPLE_ZIPPED_PACKS_FILE_STEM}.zip"

CONTENT_TYPES_EXCLUDED_FROM_UPLOAD = {
    ContentType.TEST_PLAYBOOK,
    ContentType.TEST_SCRIPT,
}
