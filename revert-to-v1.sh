#!/bin/bash
# Revert to v1 checkpoint
# Usage: ./revert-to-v1.sh

set -e

echo "Reverting to v1 checkpoint..."

# Check if v1 tag exists
if ! git rev-parse v1 >/dev/null 2>&1; then
    echo "Error: v1 tag not found!"
    exit 1
fi

# Reset to v1 tag
git reset --hard v1

echo "Successfully reverted to v1 checkpoint!"
echo ""
echo "To go back to the latest version, run:"
echo "  git reset --hard HEAD"
