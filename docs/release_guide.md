In order to release a new version of `demisto-sdk` to the public follow these steps:

### Validation before release:
1) Make sure the **CHANGELOG.md** file is in order and is updated with all the changes in the current release.
2) Create a new release branch on the sdk repo, formatted as `X.X.X`, e.g. `1.0.0`.
3) Make sure that both `sdk-nightly` and `sdk-master` builds passed.
   * If **new SDK commits** were pushed after the nightly tests had started, manually trigger the sdk nightly build again as written in step 4. This will test sdk master on content branch.
   * If **no new SDK commits** were done after the nightly tests, skip step 4.
4) Enter the content repo, open a new branch and update the version of the SDK in Demisto's Content repository by updating the demisto-sdk version in the [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) file. Use the release branch first - replace the `demisto-sdk==version` line with this line: `git+https://github.com/demisto/demisto-sdk.git@release-branch-name.`
5) Push your branch to remote, and run `./Utils/gitlab_triggers/trigger_content_nightly_build.sh -ct <GitLab_token> -b <new_content_branch_name>`.
  **Note:** if you're on `content/master`, a notification will be sent to the content-team slack channel. The destination channel can be set via argument.
  Wait until the nightly sdk completes (around 2-3h, mostly for validation)
6) Open a PR for that content branch, and verify that the build triggered is green. Note that in order to trigger the build, opening the PR is required.
7) Enter the content-internal-dist repo, open a new branch and update the demisto-sdk version in the [**.gitlab-ci.yml**](https://code.pan.run/xsoar/content-internal-dist/-/blob/master/.gitlab/.gitlab-ci.yml) file. Use the release branch - replace the `pip3 install git+https://github.com/demisto/demisto-sdk.git@master` line with this line: `pip3 install git+https://github.com/demisto/demisto-sdk.git@release-branch-name.`
8) Push your branch to remote, and run `./.gitlab/trigger_content_gold_nightly_build.sh -ct <GitLab_token> -b <new_internal_dist_branch_name>`.
  **Note:** if you're on `content-internal-dist/master`, a notification will be sent to the content-team slack channel. The destination channel can be set via argument.
  Wait until the nightly sdk completes.
  **Note:** you should discard this change and delete the branch after the build is finished successfully.
9) In Demisto's content-private repository create a new branch and go to the build configuration file [**config.yml**](https://github.com/demisto/content-private/blob/master/.github/workflows/config.yml) and update the SDK installation command by replacing `pip3 install demisto-sdk` with `pip3 install git+https://github.com/demisto/demisto-sdk.git@<sdk-release-branch-name>.`
10) Open a PR for that content-private branch, and verify the build triggered is green. Note that **this PR is for SDK version check only, and it shouldn't be merged**, once the build is successful, discard this change and close the PR.

**Note:** Steps 5, 6, 8, 10 can be performed at the same time (no need to wait for one to finish before starting the other).

### Release process:
1) Click [Here](https://github.com/demisto/demisto-sdk/releases/new) (alternatively: visit the [SDK github page](https://github.com/demisto/demisto-sdk), click on **releases**, and then **Draft a new release**)
2) Update the **Tag version** and **Release title** to `vX.X.X`.
3) In the **Describe the release** text box paste the `CHANGELOG` contents for this release.
4) Make sure the relevant nightly SDK build passed (step 3 on the previous section), then click **Publish release**. Your release will go through a deploy build (follow it on the [CI website](https://app.circleci.com/pipelines/github/demisto/demisto-sdk). If the build is successful, your release will be public 🎉.
5) Update [**dev-requirements-py3.txt**](https://github.com/demisto/content/blob/master/dev-requirements-py3.txt) again, this time with the newly-released version (rather than the branch), e.g demisto-sdk==x.x.x.
6) Wait for the build to finish, or force merge your PR to the Content repository.
7) Update **CHANGELOG.md** file - change the `# Changelog` header to the release version in the format `# X.X.X` e.g. `# 1.0.0`, and create a new `# Changelog` header at the top of the file.
8) Announce regarding the SDK release in the **dmst-content-team** slack channel - mention the release version, paste the `CHANGELOG` contents for this release, and add a link to demisto-sdk in pypi.

Your release was completed successfully!

**Note:** Don't forget to discard any unnecessary PR or branch you opened during the release process.
