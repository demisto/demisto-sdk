In order to release a new version of `demisto-sdk` to the public follow these steps:

1) Make sure the **CHANGELOG.md** file is in order and is updated with all the changes in the current release.
2) In demisto-sdk repository's main page click on **releases**.
3) Click on **Draft a new release**.
4) Update the **Tag version** and **Release title** - the form should be vX.X.X .
5) In the **Describe the release** text box enter the CHANGELOG contents for this release.
6) Press **Publish release** - your release is now public.
7) Update the version of the SDK in Demisto's Content repository by updating the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file.
8) After completing the regular Content build, initiate a nightly Content build from the Content repository by running: `./Utils/trigger_content_nightly_build.sh <branch_name> <circle_token>`
9) Look at the circleci build:
  a) Check that the unit-tests containter is sucessfull.
  b) Check that the Test Playbooks have started running successfully.
  c) Download the artifacts and check that the amount of content items for the release is ok, open a few and see that they are      not corruptted. e.g: have `omap!!` string inside or any unexpected fields.
10) merge your PR to the Content repository and announce regarding the release in the content-team slack channel.

Your release was completed successsfully!
