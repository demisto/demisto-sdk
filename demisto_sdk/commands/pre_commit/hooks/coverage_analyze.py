from demisto_sdk.commands.common.constants import PreCommitModes
from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class CoverageAnalyzeHook(Hook):
    def prepare_hook(self, **kwargs):
        """
        Prepares the Coverahe-Analyze hook.
        In case of nightly mode run coverage-analyze with the flag --allowed-coverage-degradation-percentage 100.
        Else, run coverage-analyze with the flag --previous-coverage-report-url.
        """
        if self.mode == PreCommitModes.NIGHTLY:
            self.base_hook["args"].append("--allowed-coverage-degradation-percentage")
            self.base_hook["args"].append("100")
        else:
            self.base_hook["args"].append("--previous-coverage-report-url")
            self.base_hook["args"].append(
                "https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json"
            )

        self.hooks.append(self.base_hook)
