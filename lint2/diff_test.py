import pytest
import io
from diff import get_diff, _parse_changed_files

@pytest.mark.parametrize(
    'mock_diff, expected_result',
    [
        (
            '--- a/demisto_sdk/commands/common/hook_validations/pack_unique_files.py\n+++ b/demisto_sdk/pack_unique_files.py\n@@ -328,0 +329 @@ class PackUniqueFilesValidator(BaseValidator):\n+        # hi\ndiff --git a/lint2/diff.py b/lint2/diff.py\nnew file mode 100644\nindex 00000000..1259988a\n--- /dev/null\n+++ b/lint2/diff.py\n@@ -0,0 +1,63 @@\n+import os\n+import',
            ['demisto_sdk/pack_unique_files.py', '329', 'lint2/diff.py', '1,63']
        )
    ]
)
def test_get_diff(mocker, mock_diff: str, expected_result: list):
    mocker.patch('os.popen', return_value=io.TextIOBase)
    mocker.patch('io.TextIOBase.read', return_value=mock_diff)
    mock_parse_changed_files = mocker.patch('diff._parse_changed_files', return_value=None)
    get_diff()
    mock_parse_changed_files.call_args[0][0] == expected_result