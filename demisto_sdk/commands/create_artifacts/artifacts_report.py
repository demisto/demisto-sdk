from typing import List, Tuple, Optional

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.logger import Colors


class FileReport:
    def __init__(self, src: Path, dst: Path, reason: Optional[str] = None):
        self.src = src
        self.dst = dst
        self.reason = reason


class ArtifactsReport:
    def __init__(self, header: str):
        self.header = header
        self.content_test: List[FileReport] = list()
        self.content_packs: List[FileReport] = list()
        self.content_new: List[FileReport] = list()


def generate_report(artifact_report: ArtifactsReport) -> str:
    report = ""
    report += Colors.Fg.cyan + artifact_report.header + Colors.reset

    report += Colors.underline + "content_new" + Colors.reset
    report += generate_files_report(artifact_report.content_new)

    report += Colors.underline + "content_packs" + Colors.reset
    report += generate_files_report(artifact_report.content_packs)

    report += Colors.underline + "content_test" + Colors.reset
    report += generate_files_report(artifact_report.content_test)

    return report


def generate_files_report(files: List[FileReport]):
    files_bullet_add, files_bullet_ignore = generate_files_bullets(files)

    return f'Collected files:\n{files_bullet_add}Ignored files:\n{files_bullet_ignore}'


def generate_files_bullets(files: List[FileReport]) -> Tuple[str, str]:
    files_bullet_add = ""
    files_bullet_ignore = ""

    for file in files:
        if file.reason:
            files_bullet_add += f'\t- {file} - {file.reason}\n'
        else:
            files_bullet_add += f'\t- {file}\n'

    return files_bullet_add, files_bullet_ignore

