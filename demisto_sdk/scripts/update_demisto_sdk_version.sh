#!/bin/bash

# Get repositories path list from argument
repositories=("$@")

# Validate repositories path list
if [ ${#repositories[@]} -eq 0 ]; then
  echo "Usage: $0 <repository1> <repository2> ..."
  exit 1
fi

valid_repositories=()
invalid_repositories=()

for repository in "${repositories[@]}"
do
  # Validate path
  if [ ! -d "$repository" ]; then
    invalid_repositories+=("$repository")
  else
    valid_repositories+=("$repository")
  fi
done

# Validate repositories path list
if [ ${#valid_repositories[@]} -eq 0 ]; then
  echo "No valid repositories are found"
  exit 1
fi

# Loop through valid repositories
for valid_repository in "${valid_repositories[@]}"
do
  # Move to repository path
  pushd "$valid_repository" || exit

  # Do git commands...
  current_content_branch=$(git branch --show-current)
  git stash
  git checkout master
  git pull
  poetry install
  git stash pop
  git checkout "$current_content_branch"
done

# Move back to original path
popd || exit

# Check if invalid_repositories is not empty and print its items
if [ ${#invalid_repositories[@]} -gt 0 ]; then
  echo "The following invalid repositories are found:"
  for invalid_repo in "${invalid_repositories[@]}"
  do
    echo "  - $invalid_repo"
  done
fi
