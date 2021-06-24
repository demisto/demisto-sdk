### XSOAR Linter

XSOAR linter runs as part of the demisto-sdk *lint* command and is implemented using pylint plugins.
XSOAR linter is divided into 4 support levels, while support level is build on top the previous one base->community->partner->xsoar.

#### How to add a new check?
1. Chose the lowest support level that the checker should check.
2. Add a new checker in the `<support>_level_checker.py` file.
    1. Add a new Error/ Warning message in the message list.
    2. Add a new checker function which includes the actual logic of the check.
    3. Add your checker function under the relevant visit/leave function so which will activate it on the node.
    * For more explanation regarding pylint plugins and how to add a new checker:  http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker
3. Add a new unit test for your checker inside the `test_pylint_plugin` folder under the relevant support level.
4. For error messages, add your new message number in the `test_build_xsoar_linter_py3_command` and `test_build_xsoar_linter_py2_command` of the `command_builder_test.py` file.
5. Add the check to the `xsoar_linter_integration_test.py` test suit.
