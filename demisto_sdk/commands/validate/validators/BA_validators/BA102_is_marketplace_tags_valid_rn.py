from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.BA_validators.BA102_is_marketplace_tags_valid import (
    MarketplaceTagsValidator,
)

ContentTypes = Pack


class MarketplaceTagsValidatorRN(MarketplaceTagsValidator[ContentTypes]):
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def get_relevant_file_content(self, content_item: ContentTypes):
        if content_item.release_note.exist:
            return content_item.release_note.file_content
        return ""
