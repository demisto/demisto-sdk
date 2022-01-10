In order to release a new version of `demisto-sdk` to the public follow these steps:

### Validation before release:
1) Make sure the **CHANGELOG.md** file is in order and is updated with all the changes in the current release.
2) Create a new release branch on the sdk repo, formatted as `X.X.X`, e.g. `1.0.0`.
3) Make sure that both `sdk-nightly` and `sdk-master` builds passed.
   * If **new SDK commits** were pushed after the nightly tests have started, manually trigger the sdk nightly build again as written in step 4. This will test sdk master on content branch.
   * If **no new SDK commits** were done after the nightly tests, skip step 4.
4) Enter the content repo, and run `./Utils/trigger_nightly_sdk_build.sh -ct <GitLab_token> -bt <release_branch_name>`.
  **Note:** if you're on `content/master`, a notification will be sent to the content-team slack channel. The destination channel can be set via argument.
  Wait until the nightly sdk completes (around 2-3h, mostly for validation)
5) In Demisto's content-private repository create a new branch and go to the build configuration file [**config.yml**](https://github.com/demisto/content-private/blob/master/.github/workflows/config.yml) and update the SDK installation command by replacing the line: `pip3 install demisto-sdk` with this line: `pip3 install git+https://github.com/demisto/demisto-sdk.git@release-branch-name.` Open a PR for that content branch, and this will trigger a build. Do not merge this PR yet! wait for step 5 in the second section.
7) Create a new content branch and update the version of the SDK in Demisto's Content repository by updating the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file. Use the release branch first - replace `demisto-sdk==version` with `git+https://github.com/demisto/demisto-sdk.git@release-branch-name`. Open a PR for that content branch, and this will trigger a build. Once it's green, you can discard the PR & delete the branch.

### Release process:
1) Click [Here](https://github.com/demisto/demisto-sdk/releases/new) (alternatively: visit the [SDK github page](https://github.com/demisto/demisto-sdk), click on **releases**, and then **Draft a new release**)
2) Update the **Tag version** and **Release title** to `vX.X.X`.
3) In the **Describe the release** text box paste the `CHANGELOG` contents for this release.
4) Make sure the relevant nightly SDK build passed (step 3 on the previous section), then click **Publish release**. Your release will go through a deploy build (follow it on the [CI website](https://app.circleci.com/pipelines/github/demisto/demisto-sdk). If the build is successful, your release will be public 🎉.
5) Go back to the branch you made on step 5 of the previous section, and update [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) again, this time with the newly-released version (rather than the branch name), e.g `demisto-sdk==x.x.x` - this time we **will** merge the change.
6) Wait for the build to finish, or (disengouraged) force merge your PR to the Content repository.
7) Announce regarding the SDK release in the content-team slack channel.
8) Update **CHANGELOG.md** file - change the `# Changelog` header to the release version in the format `# X.X.X` e.g. `# 1.0.0`, and create a new `# Changelog` header at the top of the file.

Your release was completed successfully!
