
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Integration


class FetchIntegrationsParamCounterValidator(BaseValidator[ContentTypes]):
    error_code = "GE100"
    description = "a"
    rationale = "a"
    error_message = "The following are the params count for {} integrations {}"
    related_field = "fetch"
    is_auto_fixable = False

    
    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        fetch_integrations_mapper = defaultdict(int)
        feed_integrations_mapper = defaultdict(int)
        collector_integrations_mapper = defaultdict(int)
        fetch_assets_integrations_mapper = defaultdict(int)
        fetch_secrets_integrations_mapper = defaultdict(int)
        for content_item in content_items:
            ct = content_item
            if content_item.is_fetch:
                fetch_integrations_mapper["fetch_integrations_counter"] += 1
                for param in content_item.params:
                    fetch_integrations_mapper[param.name] += 1
            if content_item.is_feed:
                feed_integrations_mapper["feed_integrations_counter"] += 1
                for param in content_item.params:
                    feed_integrations_mapper[param.name] += 1
            if content_item.is_fetch_events:
                collector_integrations_mapper["event_collector_integrations_counter"] += 1
                for param in content_item.params:
                    collector_integrations_mapper[param.name] += 1
            if content_item.is_fetch_assets:
                fetch_assets_integrations_mapper["fetch_assets_integrations_counter"] += 1
                for param in content_item.params:
                    fetch_assets_integrations_mapper[param.name] += 1
            for param in content_item.params:
                if param.name == "isFetchCredentials":
                    fetch_secrets_integrations_mapper["fetch_secrets_integrations_counter"] += 1
                    for nested_param in content_item.params:
                        fetch_secrets_integrations_mapper[nested_param.name] += 1
                    break
                
        sorted_fetch_integrations_mapper = dict(sorted(fetch_integrations_mapper.items(), key=lambda item: item[1], reverse=True))
        sorted_feed_integrations_mapper = dict(sorted(feed_integrations_mapper.items(), key=lambda item: item[1], reverse=True))
        sorted_fetch_events_integrations_mapper = dict(sorted(collector_integrations_mapper.items(), key=lambda item: item[1], reverse=True))
        sorted_fetch_assets_integrations_mapper = dict(sorted(fetch_assets_integrations_mapper.items(), key=lambda item: item[1], reverse=True))
        sorted_fetch_secrets_integrations_mapper = dict(sorted(fetch_secrets_integrations_mapper.items(), key=lambda item: item[1], reverse=True))
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format("fetch integrations", sorted_fetch_integrations_mapper),
                content_object=ct,
            ),
            ValidationResult(
                validator=self,
                message=self.error_message.format("feed integrations", sorted_feed_integrations_mapper),
                content_object=ct,
            ),
            ValidationResult(
                validator=self,
                message=self.error_message.format("fetch events", sorted_fetch_events_integrations_mapper),
                content_object=ct,
            ),
            ValidationResult(
                validator=self,
                message=self.error_message.format("fetch-assets integrations", sorted_fetch_assets_integrations_mapper),
                content_object=ct,
            ),
            ValidationResult(
                validator=self,
                message=self.error_message.format("fetch-secrets integrations", sorted_fetch_secrets_integrations_mapper),
                content_object=ct,
            ),
        ]
        

    
