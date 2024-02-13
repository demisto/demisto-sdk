## split
Run the xsoar lint on the given paths.

**Arguments**:
The python files to run on.

**Examples**
1. `demisto-sdk xsoar-lint Packs/Some_Pack/Integrations/Some_Integration/Some_Integration.py`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

2. `demisto-sdk xsoar-lint Packs/Some_Pack/Integrations/Some_Integration/Some_Integration.py Packs/Some_Pack2/Integrations/Some_Integration2/Some_Integration2.py`
This will split the yml file to a directory with the script components (code, description, pipfile etc.)
