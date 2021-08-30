In order to release a new version of `demisto-sdk` to the public follow these steps:

### Validation before release:
1) Make sure the **CHANGELOG.md** file is in order and is updated with all the changes in the current release.
2) Create a [new release branch](https://github.com/demisto/demisto-sdk/releases/new) on the sdk repo, named according to the release version, formatted as `X.X.X`, e.g. `1.0.0`
3) Make sure that sdk-nightly and sdk-master builds are both green.
   a) If there were *no new commits* to the sdk after the nightly tests finished, you're good.
   b) If there were **new commits** to the sdk after the nightly tests finished, manually trigger the sdk nightly build again (this will test sdk master on content branch) \
   Enter the content repo, make sure you're on **master** there, and run `./Utils/trigger_nightly_sdk_build.sh -ct <circle_token> -bt <release_branch_name>`,\
   wait until the nightly sdk completes (around 2-3h, mostly for validation)\
     _circle_token is a private key tied to your github user, generate one on your circle user settings page, under `Personal API Tokens`._ 
5) If there was any change in the content creation steps (**create content artifacts** or **unify** commands) - check that the new content is valid.
To do so:\
  a) Compare the content_new.zip from nightly-sdk build and nightly-content build and see if there is any major difference between them.\
  b) If needed, trigger the nightly **Content** build from the Content repository by running:\
  `./Utils/trigger_content_nightly_build.sh <circle_token> <branch_name>` and make sure to wait until the build is finished.
6) In Demisto's content-private repository create a new branch and go to the build configuration file [**config.yml**](https://github.com/demisto/content-private/blob/master/.github/workflows/config.yml) and update the SDK installation command by replacing the line: `pip3 install demisto-sdk` with this line: `pip3 install git+https://github.com/demisto/demisto-sdk.git@release-branch-name.`
7) Open a PR for that content-private branch, and verify the build triggered is green. Note that **this PR is for SDK version check only, and it shouldn't be merged**, after build is finished successfully - you should discard this change and close the PR.
8) Create a new content branch and update the version of the SDK in Demisto's Content repository by updating the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file. Use the release branch first - replace the `demisto-sdk==version` line with this line: `git+https://github.com/demisto/demisto-sdk.git@release-branch-name.`
9) Open a PR for that content branch, and verify that the build triggered is green. Note that in order to trigger the build, opening the PR is required.

### Release process:
1) In demisto-sdk repository's main page click on **releases**.
2) Click on **Draft a new release**.
3) Update the **Tag version** and **Release title** - the form should be `vX.X.X` .
4) In the **Describe the release** text box enter the CHANGELOG contents for this release.
5) If nightly passes ok, press **Publish release** - your release is now public.
6) Update the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file again, this time with the release tag.
7) Run the regular build again or force merge your PR to the Content repository.
8) Announce regarding the SDK release in the content-team slack channel.
9) Update **CHANGELOG.md** file - change the `# Changelog` header to the release version in the format `# X.X.X` e.g. `# 1.0.0`, and create a new `# Changelog` header at the top of the file.

Your release was completed successfully!
