#!/bin/bash

roles=$(curl -s "https://raw.githubusercontent.com/demisto/content/master/.github/content_roles.json")
contribution_tl=$(echo "$roles" | jq -r '.CONTRIBUTION_TL')

gh pr edit "$PR_LINK" --add-assignee "$contribution_tl"
gh pr edit "$PR_LINK" --add-label "Contribution"

# adds the contribution_tl as reviewer to the PR
# should be a temporary fix until GH API supports "gh pr edit "$PR_LINK" --add-reviewer $contribution_tl", link: https://github.com/cli/cli/issues/4844
curl -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos$OWNER/$REPO/pulls/$PR_NUMBER/requested_reviewers" \
    -d "{\"reviewers\": [\"$contribution_tl\"]}" \
    -o /dev/null