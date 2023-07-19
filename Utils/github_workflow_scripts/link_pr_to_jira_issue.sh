#!/bin/bash

reviewers=$(curl -s "https://raw.githubusercontent.com/demisto/content/master/.github/content_roles.json")
contribution_tl=$(echo $reviewers | jq -r '.CONTRIBUTION_TL')

echo "Adding contribution TL $contribution_tl as assignee and reviewer"
# gh pr edit "$PR_LINK" --add-assignee "$contribution_tl"
# gh pr edit "$PR_LINK" --add-reviewer "$contribution_tl"

changed_files=$(git diff --name-only "$BASE_REF" "$HEAD_REF" )
security_items=("*Playbooks*" "*IncidentTypes*" "*IncidentFields*" "*IndicatorTypes*" "*IndicatorFields*" "*Layouts*" "*Classifiers*")

function is_security_needed() {
    for file in $changed_files; do
        echo $file
        for name in "${security_items[@]}"; do
            echo $name
            [[ "$file" == "$name" ]] && return 
        done
    done
    false
}

if is_security_needed; then
    security_rev=$(echo $reviewers | jq -r '.CONTRIBUTION_SECURITY_REVIEWER')
    echo "Security needed"
    echo "Adding security reviewer $security_rev as assignee and reviewer"
    # gh pr edit "$PR_LINK" --add-assignee $security_rev
    # gh pr edit "$PR_LINK" --add-reviewer $security_rev
fi