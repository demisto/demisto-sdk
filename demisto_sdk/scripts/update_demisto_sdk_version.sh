#!/bin/bash

# Get CD path list from argument
repositories=("$@")

# Validate CD path list
if [ ${#repositories[@]} -eq 0 ]; then
  echo "Usage: $0 <repository1> <repository2> ..."
  exit 1
fi

# Save current path
current_path="$PWD"

# Loop through paths
for repository in "${repositories[@]}"
do
  # Validate path
  if [ ! -d "$repository" ]; then
    echo "Error: $repository is not a valid directory."
    exit 1
  fi

  # CD to path
  cd "$repository" || exit

  # Do git commands...
  current_content_branch=$(git branch --show-current)
  git stash
  git checkout master
  git pull
  poetry install
  git stash pop
  git checkout "$current_content_branch"
done

# CD back to original path
cd "$current_path" || exit
