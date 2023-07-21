#!/bin/bash

gh pr comment "$PR_LINK" --body "$(cat Utils/github_workflow_scripts/contribution_comment.md)"

reviewers=$(curl -s "https://raw.githubusercontent.com/demisto/content/master/.github/content_roles.json")
contribution_tl=$(echo "$reviewers" | jq -r '.CONTRIBUTION_TL')

echo "Adding contributions TL $contribution_tl as assignee and reviewer"
gh pr edit "$PR_LINK" --add-assignee jlevypaloalto  # "$contribution_tl"
# gh pr edit "$PR_LINK" --add-reviewer jlevypaloalto  # "$contribution_tl"
gh pr edit "$PR_LINK" --add-label "Contribution"

# should be a temporary fix until GH API supports "gh pr edit "$PR_LINK" --add-reviewer", link: https://github.com/cli/cli/issues/4844
curl -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GITHUB_TOKEN"\
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$API_URL" \
    -d "{\"reviewers\": \"$contribution_tl\"}"

# security_items="Playbooks|IncidentTypes|IncidentFields|IndicatorTypes|IndicatorFields|Layouts|Classifiers"

# if git diff --name-only $HEAD..$BASE | grep -E "$security_items"; then
#     security_reviewer=$(echo "$reviewers" | jq -r '.CONTRIBUTION_SECURITY_REVIEWER')
#     echo "Security needed"
#     echo "Adding security reviewer $security_reviewer as assignee and reviewer"
#     gh pr edit "$PR_LINK" --add-assignee $security_reviewer
#     gh pr edit "$PR_LINK" --add-reviewer $security_reviewer
# fi