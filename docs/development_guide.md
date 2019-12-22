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

### General guidelines
* The code is in python 3, we support python 3.7 and up.
* For common tools and constants we have the `common` directory. Before you add a constant or a tool, check if it already exists there.
* We use flake8 for lint. Before you commit you can run `flake8 demisto_sdk` to check your code.

### Good Luck!
