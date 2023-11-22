"""
import all validation for the validators directory,
so 'BaseValidator.__subclasses__()' will recognize them when called from filter_validators.
"""
import importlib
import sys
from pathlib import Path

package_path = Path(__path__[0])
sys.path.append(str(package_path))

for folder in package_path.rglob("*.py"):
    if not folder.name.startswith("__"):
        module_name = (
            folder.relative_to(package_path)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )

        # Import module
        module = importlib.import_module(module_name)
