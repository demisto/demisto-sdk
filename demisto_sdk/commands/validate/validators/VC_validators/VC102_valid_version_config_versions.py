from __future__ import annotations

from typing import Iterable, List

from packaging import version

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack
json = JSON_Handler()


# def natural_keys(text):
#     return [int(c) for c in re.split(r'(\d+)', text)]


def version_key(version):
    return tuple(map(int, version.split(".")))


class ValidVersionConfigVersions(BaseValidator[ContentTypes]):
    error_code = "VC102"
    description = (
        "Verify content versions are continuos according to platform versions."
    )
    rationale = "Prevent situations where platform version has an earlier content version than the previous platform version"
    error_message = "version config file does not adhere to platform content versions."
    related_field = "version_config"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.VERSION_CONFIG]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        file_content = {
            "8.9": {"to": "1.5.0"},
            "8.10": {"from": "1.5.1", "to": "2.0.0"},
            "9.0": {"from": "2.0.1"},
        }
        for content_item in content_items:
            if content_item.version_config:
                if not self.is_continuous_version(file_content):
                    return [
                        ValidationResult(
                            validator=self,
                            message=self.error_message,
                            content_object=content_item,
                        )
                    ]
        return []
        # for content_item in content_items
        # if content_item.version_config and content_item.version_config.file_content
        # ]

    def is_continuous_version(self, file_content) -> bool:
        platform_versions = []
        content_versions = []
        sorted_platform_version_data = dict(
            sorted(file_content.items(), key=lambda item: version_key(item[0]))
        )
        for platform_version, content_items in sorted_platform_version_data.items():
            platform_versions.append(version.parse(platform_version))
            content_versions.append(content_items)

        if not self.validated_platform_versions(platform_versions):
            return False

        if not self.validate_content_version(content_versions):
            return False

        return True

    def validate_content_version(self, versions) -> bool:
        for i in range(len(versions) - 1):
            if "to" and "from" in versions[i].keys():
                # if not self.validated_platform_versions([version.parse(versions[i].get('to')), version.parse(versions[i].get('from'))]):
                #     return False
                continue
            elif "to" in versions[i].keys():
                if not self.validated_platform_versions(
                    [
                        version.parse(versions[i].get("to")),
                        version.parse(versions[i + 1].get("from")),
                    ]
                ):
                    return False
            else:
                if not self.validated_platform_versions(
                    [
                        version.parse(versions[i - 1].get("to")),
                        version.parse(versions[i].get("from")),
                    ]
                ):
                    return False
        return True

    def validated_platform_versions(self, versions) -> bool:
        for i in range(len(versions) - 1):
            curr_version = versions[i]
            next_version = versions[i + 1]
            major_delta = next_version.major - curr_version.major
            minor_delta = next_version.minor - curr_version.minor
            micro_delta = next_version.micro - curr_version.micro
            if major_delta:
                if next_version.minor != 0 or next_version.micro != 0:
                    return False
                minor_delta = 0
                micro_delta = 0
            elif minor_delta:
                if next_version.micro != 0:
                    return False
                micro_delta = 0
            if major_delta > 1 or minor_delta > 1 or micro_delta > 1:
                return False
        return True
