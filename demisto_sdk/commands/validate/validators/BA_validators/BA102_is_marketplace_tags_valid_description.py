
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.BA_validators.BA102_is_marketplace_tags_valid import (
    MarketplaceTagsValidator,
)

ContentTypes = Integration

class MarketplaceTagsValidatorDescription(MarketplaceTagsValidator[ContentTypes]):
    related_file_type = [RelatedFileType.DESCRIPTION_File]
    def get_relevant_file_content(self, content_item: ContentTypes):
        return content_item.description_file.file_content
