#!/bin/bash
# We upload a fresh zip to https://docs.3di.live/threeditoolbox-dev/
# for development purposes only.
set -e
#set -u

BRANCH=${GITHUB_HEAD_REF:-refactor}

ARTIFACT=threedi_results_analysis-${BRANCH}.zip
PROJECT=threeditoolbox-dev

# Rename generated ThreeDiToolbox.zip to include branch name.
cp threedi_results_analysis.zip ${ARTIFACT}

curl -X POST \
     --retry 3 \
     -H "Content-Type: multipart/form-data" \
     -F key=${THREEDITOOLBOX_DEV_ARTIFACTS_KEY} \
     -F artifact=@${ARTIFACT} \
     -F branch=${BRANCH} \
     https://artifacts.lizard.net/upload/${PROJECT}/
