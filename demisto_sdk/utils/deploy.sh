#!/bin/bash

# exit on errors
set -e

function deploy_to_pypi () {
    pip install twine
    python setup.py sdist
    TWINE_USERNAME=__token__ twine upload dist/*
}

if [[ "${CIRCLE_BRANCH}" == "master" ]]; then
    echo "Deploying to Pypi test site."
    TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/ TWINE_PASSWORD="${PYPI_TEST_TOKEN}" deploy_to_pypi
elif [[ $(echo "${CIRCLE_TAG}" | grep -E "^v[0-9]+\.[0-9]+\.[0-9]+$") ]]; then
    echo "Deploying to Pypi production site"
    TWINE_PASSWORD="${PYPI_TOKEN}" deploy_to_pypi
else
    echo "Skipping Pypi deploy as we are not building a tag or on master"
fi
