# Demisto-SDK Release Guide

Throughout the guide, `X.Y.Z` will mark the upcoming version.

## Pre-release validations

1) Branch out from the latest SDK PR used for a nightly test, name the branch `X.Y.Z`.
2) Make sure the **CHANGELOG.md** file is in order. Add a subtitle `## X.Y.Z` under the `## Unreleased`, leaving the unreleased list empty.
3) Run `poetry update` (in the SDK folder).
5) Run `poetry version X.Y.Z`.
6) Make sure that all the following passed:
  - [content nightly](https://code.pan.run/xsoar/content/-/pipeline_schedules)
  - [SDK nightly](https://code.pan.run/xsoar/content/-/pipeline_schedules)
  - [SDK master](https://github.com/demisto/demisto-sdk) (last post-merge build passed)
  - [content-gold](https://code.pan.run/xsoar/content-internal-dist/-/pipeline_schedules)
  - [content-private](https://github.com/demisto/content-private/actions).

  If any failed, consult with the SDK owner, and see [triggering nightlies manually](#triggering-nightlies-manually)

### Release process

1) Click [Here](https://github.com/demisto/demisto-sdk/releases/new)
2) Set **Tag** and **Release title** to be `vX.Y.Z`.
3) Select the SDK release branch as the **Target**.
4) In the **Describe the release** text box, paste the `CHANGELOG` contents for this release.
5) Click **Publish release**. Your release will go through a deploy build (follow it on the [CI website](https://app.circleci.com/pipelines/github/demisto/demisto-sdk).
6) If the build is successful, and `vX.Y.Z` shows in [PyPi](https://pypi.org/project/demisto-sdk/), your release is public! 🎉
7) Under the **Content** repo, run `poetry add demisto-sdk==X.Y.Z && poetry update`.
  **NOTE**: it may take up to an hour for the Gitlab's PyPi mirror to sync with PyPi ang have X.Y.Z available, so the build _may_ fail. Should this happen, wait ~1h and retry.
9) Wait for the build to finish, and merge it.
10) Announce regarding the SDK release [here](https://panw-global.slack.com/archives/G011E63JXPB):
  a) Mention the release version,
  b) Paste the `CHANGELOG` contents for this release
  c) Add a link to demisto-sdk in pypi
  d) Remind everyone to pull master (on both content & SDK) and `poetry update` content.


## Triggering nightlies manually
The following should _only_ be done when new PRs were mergerd between the nightly trigger and the release start. This is seldom required.

1) Under the content repo, change the `demisto-sdk` dependency under [pyproject.toml]([url](https://github.com/demisto/content/blob/master/pyproject.toml)) to `demisto_sdk = {git = "https://github.com/demisto/demisto-sdk.git", rev =<commit hash here>}`
2) Push your branch to remote, and run `./Utils/gitlab_triggers/trigger_content_nightly_build.sh -ct <gitlab_token> -b <new_content_branch_name>`.
  **Note:** if you're on `content/master`, a notification will be sent to the slack [channel](https://panw-global.slack.com/archives/G011E63JXPB). The destination channel can be set via argument.  Wait until the nightly sdk completes (2-3h)
3) Open a PR for that content branch, and verify that the build triggered is green.
4) Update [content-internal](https://code.pan.run/xsoar/content-internal-dist/-/blob/master/.gitlab/.gitlab-ci.yml): replace the `pip3 install git+https://github.com/demisto/demisto-sdk.git@master#egg=demisto-sdk` line with: `pip3 install git+https://github.com/demisto/demisto-sdk.git@<release-branch-name>#egg=demisto-sdk`, and push to remote.
5) Run `./.gitlab/trigger_content_gold_nightly_build.sh -ct <gitlab_token> -b <internal_dist_branch_name>`.
  **Note:** if you're on `content-internal-dist/master`, a notification will be sent to the content-team slack channel. The destination channel can be set via argument.
6) Discard both PRs (content & internal)
7) In Demisto's content-private [**config.yml**](https://github.com/demisto/content-private/blob/master/.github/workflows/config.yml), replace `pip3 install demisto-sdk` with `pip3 install git+https://github.com/demisto/demisto-sdk.git@<sdk-release-branch-name>.`
8) Open a PR for that content-private branch, and verify the build triggered finishes. Once successful, discard this change and close the PR.
