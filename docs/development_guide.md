## Contributing to Demisto SDK

To add functionality to the SDK you would need to perform the following steps:

### Create a new class
You will need to create a new directory under the `commands` folder which will contain the files relevant to your contribution.
Then, in a dedicated method, you will create an instance of your class in the SDK core class (in `__main__.py`) with the relevant arguments,
then invoke the command according to the user request.
For example, The `init` command, has a `init` folder within common, where the `Initiator` class resides
When this command is called, an instance of `Iniator` is created and the command is invoked.

### Add tests
All tests are run from the `tests` folder within the correlating command folder. They also run in the CircleCI build.
Also make sure your methods work from the CLI by running `python demisto_sdk <your_method>` in your local environment.

### How to run your unreleased demisto-sdk branch locally
There are 2 options:
1. Run `pip install -e .` in the terminal of your demisto-sdk repository. This will automatically sync your venev until deactivating it.
2. Run `tox -e py37` in the terminal of your demisto-sdk repository. This will update the changes you have made in your branch until now.

Now, Switch to your content repo and run commands from your unreleased demisto-sdk branch.

### How to run build using an unreleased demisto-sdk version
Push your branch and create a PR in demisto-sdk repository.
In your IDE go to content repository on a local branch.
Search for the file: **dev-requirements-py3.txt**.
There swap the line `demisto-sdk==X.X.X` with: `git+https://github.com/demisto/demisto-sdk.git@{your_sdk_branch_name}`. For example see [here](https://github.com/demisto/content/blob/ad06ef4d1bdd398ce4b70f0fd2e5eab7a772c11c/dev-requirements-py3.txt#L2).
Go to the file **config.yml** there you can find all the build steps - you can change whichever steps you want to check using demisto-sdk.
Make any other changes you want in the content repository and push - this will make CircleCI run using your localized branch of demisto-sdk and on the changes made on content repository.

### General guidelines
* The code is in python 3, we support python 3.7 and up.
* For common tools and constants we have the `common` directory. Before you add a constant or a tool, check if it already exists there.
* We use flake8 for lint. Before you commit you can run `flake8 demisto_sdk` to check your code.
* Whenever adding a functionality to the `validate` command, consider to add the possibility to the `format` command accordingly.
* Try to ask the user for the minimal amount of arguments possible. e.g: Do not ask for the file type, infer it using the `find_type` command from `tools.py`.
* Follow the arguments convention. e.g: `-i --input`, `-o --output`, `--insecure`.
* When adding a functionality, update the `.md` file of the command accordingly.

### Good Luck!
