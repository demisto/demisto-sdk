from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.BA_validators.BA102_is_marketplace_tags_valid import (
    MarketplaceTagsValidator,
)

ContentTypes = Pack


class MarketplaceTagsValidatorReadme(MarketplaceTagsValidator[ContentTypes]):
    related_file_type = [RelatedFileType.README]
    def get_relevant_file_content(self, content_item: ContentTypes):
        return content_item.readme.file_content or ''
