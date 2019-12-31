## Contributing to Demisto SDK

To add functionality to the SDK you would need to perform the following steps:

### Create a new class
You will need to create a new directory under the root which will contain the files relevant to your contribution.
Then, in a dedicated method, you will create an instance of your class in the SDK core class (in `core.py`) with the relevant arguments, and then invoke methods
according to the user's request. The user should be able to invoke it by importing the `core` class or by using the CLI.

### Add a new sub parser
The SDK works in the CLI (command line) and uses `argparse` to parse user arguments.
Your class should contain the following static method:
```
@staticmethod
def add_sub_parser(subparsers):
    parser = subparsers.add_parser('parser_name',
                                   help='parser_help')
    parser.add_argument("-a", "--argA", help="Argument help", required=True/False)
    parser.add_argument("-b", "--argB", help="Argument help", required=True/False)
    ...
```
You should call this method in the `initialize_parsers` method in the core SDK class and handle your new command
(its name will be the parser name you created in `add_sub_parser`) in the `parse_args` method.

### Add tests
All tests are run from the `tests` folder. They also run in the CircleCI build.
Also make sure your methods work from the CLI by running `python demisto_sdk <your_method>` in your local environment.

### How to run build using an unreleased demisto-sdk version
Push your branch and create a PR in demisto-sdk repository.
In your IDE go to content repository on a local branch.
Search for the file: **dev-requirements-py3.txt**.
There swap the line `demisto-sdk==X.X.X` with: `git+https://github.com/demisto/demisto-sdk.git@{your_sdk_branch_name}`
Go to the file **config.yml** there you can find all the build steps - you can change whichever steps you want to check using demisto-sdk.
Make any other changes you want in the content repository and push - this will make CircleCI run using your localized branch of demisto-sdk and on the changes made on content repository.

### General guidelines
* The code is in python 3, we support python 3.7 and up.
* For common tools and constants we have the `common` directory. Before you add a constant or a tool, check if it already exists there.
* We use flake8 for lint. Before you commit you can run `flake8 demisto_sdk` to check your code.

### Good Luck!
