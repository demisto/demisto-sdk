#!/bin/bash

# Get repositories path list from argument
repositories=("$@")

# Verify the repositories argument was provided
if [ ${#repositories[@]} -eq 0 ]; then
  echo "Please provide at least one repository to be updated, for example:
$0 <repository1> <repository2> ..."
  exit 1
fi

valid_repositories=()
invalid_repositories=()

# Go over the repositories and divide them between valid and invalid
for repository in "${repositories[@]}"
do
  # Verify the repository is actually a directory
  if [ ! -d "$repository" ]; then
    echo "$repository is not a valid directory"
    invalid_repositories+=("$repository")
  else
    valid_repositories+=("$repository")
  fi
done

# Make sure there are valid repositories
if [ ${#valid_repositories[@]} -eq 0 ]; then
  echo "Error, No valid repositories were found"
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
