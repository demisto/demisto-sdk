#!/bin/bash

welcome_message=$(cat Utils/github_workflow_scripts/contribution_comment.md | awk "{gsub(/<contribution_tl>/,\"$contribution_tl\")}1")
roles=$(curl -s "https://raw.githubusercontent.com/demisto/content/master/.github/content_roles.json")
contribution_tl=$(echo "$roles" | jq -r '.CONTRIBUTION_TL')

echo "Adding contributions TL $contribution_tl as assignee and reviewer"
gh pr comment "$PR_LINK" --body "$welcome_message"
gh pr edit "$PR_LINK" --add-assignee "$contribution_tl"
gh pr edit "$PR_LINK" --add-label "Contribution"

# should be a temporary fix until GH API supports "gh pr edit "$PR_LINK" --add-reviewer $contribution_tl", link: https://github.com/cli/cli/issues/4844
curl -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos$OWNER/$REPO/pulls/$PR_NUMBER/requested_reviewers" \
    -d "{\"reviewers\": [\"$contribution_tl\"]}" \
    -o /dev/null

# security_items="Playbooks|IncidentTypes|IncidentFields|IndicatorTypes|IndicatorFields|Layouts|Classifiers"

# if git diff --name-only $HEAD..$BASE | grep -E "$security_items"; then  # use: ${{ github.event.pull_request.diff_url }}
#     security_reviewer=$(echo "$roles" | jq -r '.CONTRIBUTION_SECURITY_REVIEWER')
#     echo "Security needed"
#     echo "Adding security reviewer $security_reviewer as assignee and reviewer"
#     gh pr edit "$PR_LINK" --add-reviewer $security_reviewer
# fi