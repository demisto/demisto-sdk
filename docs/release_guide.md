In order to release a new version of `demisto-sdk` to the public follow these steps:

1) Make sure that sdk-nightly and sdk-master builds are both green.
2) Make sure the **CHANGELOG.md** file is in order and is updated with all the changes in the current release.
3) In demisto-sdk, create a new release branch, named after the release version in the format `X.X.X`, e.g. `1.0.0`
4) Important! If there were more commits to the sdk after the nightly tests finished, you will need to perform the tests manually before the release:\
  a. Trigger the nightly-sdk build from the Content repository by running:\
     `./Utils/trigger_nightly_sdk_build.sh <branch_name> <circle_token>`.\
  b. Trigger a build that imitates the content master build from the SDK repository by running:\
     `./demisto_sdk/utils/trigger_against_content_master.sh <release_branch_name> <circle_token>`.\
  Make sure both builds are green before releasing.
5) Update the version of the SDK in Demisto's Content repository by updating the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file. Use the release branch first - replace the `demisto-sdk==version` line with this line: `git+https://github.com/demisto/demisto-sdk.git@release-branch-name.`
6) If there was any change in the content creation steps (**create content artifacts** or **unify** commands) - we need to check that the new content is valid.
To do so, you can do the following:\
  a. Compare the content_new.zip from nightly-sdk build and nightly-content build and see if there is any major difference between them.\
  b. If needed, trigger the nightly Content build from the Content repository by running:\
  `./Utils/trigger_content_nightly_build.sh <branch_name> <circle_token>` and make sure to wait until the build is finished.\
7) In demisto-sdk repository's main page click on **releases**.
8) Click on **Draft a new release**.
9) Update the **Tag version** and **Release title** - the form should be `vX.X.X` .
10) In the **Describe the release** text box enter the CHANGELOG contents for this release.
11) If nightly passes ok, press **Publish release** - your release is now public.
12) Update the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file again, this time with the release tag.
13) Run the regular build again or force merge your PR to the Content repository.
14) Announce regarding the SDK release in the content-team slack channel.

Your release was completed successfully!
