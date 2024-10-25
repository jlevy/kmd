#!/bin/bash

# Build and install kmd and dependencies locally.

set -euo pipefail

APP_NAME=kmd

if [ ! -f "pyproject.toml" ]; then
  echo "This script must be run from the project directory that contains pyproject.toml."
  exit 1
fi

PYTHON_SITE_PACKAGES=$(python -c 'import site; print(site.USER_SITE)')

echo
echo "This will build and install $APP_NAME and its dependencies to the current Python environment:"
echo "$PYTHON_SITE_PACKAGES"
echo
read -p "Do you want to continue (y/n)? " choice

case "$choice" in 
  y|Y ) echo "Building and installing...";;
  n|N ) echo "Installation aborted."; exit 1;;
  * ) echo "Invalid choice. Installation aborted."; exit 1;;
esac

set -x

# Do build.
poetry self add "poetry-dynamic-versioning[plugin]"
poetry build

set +x

# Find the latest built wheel file.
WHEEL_FILE=$(find dist -name "*.whl" -print0 | xargs -0 ls -t | head -n 1)
if [ -z "$WHEEL_FILE" ]; then
  echo "Wheel file not found. Make sure the build was successful."
  exit 1
fi

# We install for the user.
set -x
pip install --user "$WHEEL_FILE" $*
