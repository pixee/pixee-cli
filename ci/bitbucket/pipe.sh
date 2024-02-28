#!/bin/sh
set -e

export

cd $BITBUCKET_CLONE_DIR
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
FILESTR=$(echo "$CHANGED_FILES" | sed "s/^/**/" | tr "\n" ",")

echo "Running pixee fix for: $CHANGED_FILES --- $FILESTR $BITBUCKET_CLONE_DIR"
echo "pixee fix -v $FILESTR $BITBUCKET_CLONE_DIR"
pixee fix -v --apply-fixes --path-include $FILESTR .

python /pixee/bitbucket/main.py ./results.codetf.json
