#!/bin/bash

# Build and install kmd and dependencies locally.

set -euo pipefail

APP_NAME=kmd

if [ ! -f "pyproject.toml" ]; then
  echo "This script must be run from the project directory that contains pyproject.toml."
  exit 1
fi

PYTHON_SITE_PACKAGES=$(python -c 'import site; print(site.USER_SITE)')

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
poetry build

set +x

# Find the built wheel file
WHEEL_FILE=$(find dist -name "*.whl" | head -n 1)
if [ -z "$WHEEL_FILE" ]; then
  echo "Wheel file not found. Make sure the build was successful."
  exit 1
fi

# Check if it's already installed.
if python -m pip show $APP_NAME > /dev/null 2>&1; then
  echo "$APP_NAME is already installed. Using --force-reinstall --no-deps to ensure it is reinstalled."
  set -x
  pip install --user --force-reinstall --no-deps "$WHEEL_FILE"
else
  set -x
  pip install --user "$WHEEL_FILE"
fi