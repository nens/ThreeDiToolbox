#!/bin/bash
set -e
set -u

VERSION=$(grep "^version" metadata.txt| cut -d= -f2)

ARTIFACT=threedi_results_analysis.${VERSION}.zip
PROJECT=ThreeDiToolbox

# Rename generated ThreeDiToolbox.zip to include version number.
cp threedi_results_analysis.zip ${ARTIFACT}

curl -X POST \
     --retry 3 \
     -H "Content-Type: multipart/form-data" \
     -F key=${THREEDITOOLBOX_ARTIFACTS_KEY} \
     -F artifact=@${ARTIFACT} \
     -F branch=${GITHUB_REF} \
     https://artifacts.lizard.net/upload/${PROJECT}/
