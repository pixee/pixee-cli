#!/bin/sh
set -v

export

cd $BITBUCKET_CLONE_DIR
#CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
FILESTR=$(python /pixee/bitbucket/changed_files.py)

echo "Running pixee fix for: $CHANGED_FILES --- $FILESTR $BITBUCKET_CLONE_DIR"
#pixee fix -v --apply-fixes --path-include $FILESTR $BITBUCKET_CLONE_DIR

echo "Fixing files: $FILESTR"
pixee fix $PIXEE_OPTS -v --path-include "$FILESTR" --apply-fixes .

#python /pixee/bitbucket/main.py ./results.codetf.json

FILE_PATH="./results.codetf.json"

# Check if the file exists
if [ -f "$FILE_PATH" ]; then
    # If the file exists, run the Python script
    python /pixee/bitbucket/main.py "$FILE_PATH"
else
    # If the file does not exist, output an error message
    echo "Error: File '$FILE_PATH' not found."
fi
