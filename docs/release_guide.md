In order to release a new version of `demisto-sdk` to the public follow these steps:

1) Make sure the **CAHNGELOG.md** file is in order and is updated with all the changes in the current release.
2) In core.py file change the version number listed at the top of the file.
3) In demisto-sdk repository's main page click on **releases**.
4) Click on **Draft a new release**.
5) Update the **Tag version** and **Release title** - the form should be vX.X.X .
6) In the **Describe the release** text box enter the CHANGELOG contents for this release.
7) Press **Publish release** - congratulations! your release is now public.
8) Finally, if you want to update the version of the SDK in Demisto's Content repository you need to update the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file.
