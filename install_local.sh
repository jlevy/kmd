#!/bin/bash

# Build and install kmd and dependencies locally.

set -euo pipefail

trap 'echo "Error: $0 failed with exit code $?. See errors above."' ERR

APP_NAME=kmd

if [ ! -f "pyproject.toml" ]; then
  echo "This script must be run from the project directory that contains pyproject.toml."
  exit 1
fi

PYTHON_SITE_PACKAGES=$(python -c 'import site; print(site.USER_SITE)')

echo
echo "We will build and install $APP_NAME and its dependencies using pip"
echo "to the current Python environment:"
echo
echo "$PYTHON_SITE_PACKAGES"
echo
echo "Running this script with options: $0 $@"
echo "You can run with --force-reinstall to force pip to do reinstallation."
echo
read -p "Do you want to continue (y/n)? " choice

case "$choice" in 
  y|Y ) echo "Building and installing...";;
  n|N ) echo "Installation aborted."; exit 1;;
  * ) echo "Invalid choice. Installation aborted."; exit 1;;
esac

echo

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
pip install --user "$WHEEL_FILE" $@

set +x

echo
echo "Checking everything worked (may take a minute to compile bytecode)..."
echo "Running from: $(which kmd)"

# Use a full command to import/bytecompile more code now.
# Self check also handles some caching like tldr.
if kmd self_check; then
  echo
  echo 'Success!'
  echo
  echo 'Check above for warnings about needed tools or .env file API key setup.'
  echo 'Then run `kmd` to get started.'
  echo
else
  echo
  echo 'Something went wrong. :('
  echo
  echo 'Look above for error messages and see `installation` docs for help.'
  echo
  exit 1
fi
