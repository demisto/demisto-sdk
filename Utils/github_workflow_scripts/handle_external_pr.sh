#!/bin/bash

reviewers=$(curl -s "https://raw.githubusercontent.com/demisto/content/master/.github/content_roles.json")
contribution_tl=$(echo "$reviewers" | jq -r '.CONTRIBUTION_TL')

echo "Adding contributions TL $contribution_tl as assignee and reviewer"
# gh pr edit "$PR_LINK" --add-assignee "$contribution_tl"
# gh pr edit "$PR_LINK" --add-reviewer "$contribution_tl"
gh pr edit "$PR_LINK" --add-label "Contribution"
gh pr comment "$PR_LINK" --body "$(cat Utils/github_workflow_scripts/contribution_comment.md)"

security_items="Playbooks|IncidentTypes|IncidentFields|IndicatorTypes|IndicatorFields|Layouts|Classifiers"

if git diff --name-only $HEAD..$BASE | grep -E "$security_items"; then
    security_reviewer=$(echo "$reviewers" | jq -r '.CONTRIBUTION_SECURITY_REVIEWER')
    echo "Security needed"
    echo "Adding security reviewer $security_reviewer as assignee and reviewer"
    # gh pr edit "$PR_LINK" --add-assignee $security_reviewer
    # gh pr edit "$PR_LINK" --add-reviewer $security_reviewer
fi