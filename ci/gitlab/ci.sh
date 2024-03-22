#!/usr/bin/env bash
set -e

if [[ -n "$CI_MERGE_REQUEST_IID" ]]; then
    FILES=$(git --no-pager diff --name-only $CI_MERGE_REQUEST_DIFF_BASE_SHA...HEAD)
    FILESTR=$(echo "$FILES" | sed "s/^/**/" | tr "\n" ",")
    pixee fix $PIXEE_OPTS --apply-fixes --path-include $FILESTR $CI_PROJECT_DIR
else
    pixee fix $PIXEE_OPTS --apply-fixes $CI_PROJECT_DIR
fi

python /pixee/gitlab/pipeline.py ./results.codetf.json
