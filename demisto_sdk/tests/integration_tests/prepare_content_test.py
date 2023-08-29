from click.testing import CliRunner

from demisto_sdk.__main__ import main
from TestSuite.test_tools import ChangeCWD

PREPARE_CONTENT_CMD = "prepare-content"


class TestPrepareContent:
    def test_prepare_content_inputs(self, repo):
        """
        Given
        - The prepare-content command

        When
        - Passing both the -i and -a parameters.
        - Not passing neither -i nor -a parameters.
        - Providing mulitple inputs with -i and an output path of a file.

        Then
        - Ensure an error message is raised.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("dummy-integration")
        integration.create_default_integration()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)

            # Verify that passing both -a and -i raises an exception.
            result = runner.invoke(
                main,
                [PREPARE_CONTENT_CMD, "-i", f"{integration.path}", "-a"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of the '-a' or '-i' parameters must be provided."
            )

            # Verify that not passing either of -a and -i raises an exception.
            result = runner.invoke(
                main,
                [PREPARE_CONTENT_CMD, "-o", "output-path"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of the '-a' or '-i' parameters must be provided."
            )

            # Verify that specifying an output path of a file and passing multiple inputs raises an exception
            result = runner.invoke(
                main,
                [
                    PREPARE_CONTENT_CMD,
                    "-i",
                    f"{integration.path},{integration.path}",
                    "-o",
                    "output-path.yml",
                ],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "When passing multiple inputs, the output path should be a directory "
                "and not a file."
            )
