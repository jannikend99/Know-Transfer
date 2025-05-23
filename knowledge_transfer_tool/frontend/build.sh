#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define directories
FRONTEND_DIR=$(pwd) # Assumes script is run from frontend directory
BACKEND_STATIC_DIR_ROOT="../backend/static" # This is backend/static/
CRA_BUILD_OUTPUT_SUBSTATIC="static" # The 'static' folder INSIDE backend/static where CRA assets go
BUILD_DIR="build"

echo "Starting React build process..."

# 1. Navigate to the frontend directory (redundant if already there, but good practice)
# cd "${FRONTEND_DIR}"

# 2. Install dependencies (optional, could be done once manually)
# echo "Installing frontend dependencies..."
# npm install

# 3. Run the build script
echo "Building React app... (npm run build)"
CI=false npm run build

# 4. Prepare the backend static directory root
echo "Preparing backend static directory root: ${BACKEND_STATIC_DIR_ROOT}"
rm -rf "${BACKEND_STATIC_DIR_ROOT:?}"/* # Safety: :? ensures var is set
mkdir -p "${BACKEND_STATIC_DIR_ROOT}"

# 5. Copy CRA build output to backend/static/
echo "Copying CRA build files from ${BUILD_DIR} to ${BACKEND_STATIC_DIR_ROOT}..."
cp -r "${BUILD_DIR}"/* "${BACKEND_STATIC_DIR_ROOT}/"

# 6. Copy custom CSS files (global.css, components.css, layout.css)
# These need to go into the directory that will be served under /static/styles by FastAPI
# which is backend/static/static/styles/
TARGET_CUSTOM_CSS_DIR="${BACKEND_STATIC_DIR_ROOT}/${CRA_BUILD_OUTPUT_SUBSTATIC}/styles"
echo "Ensuring custom CSS target directory exists: ${TARGET_CUSTOM_CSS_DIR}"
mkdir -p "${TARGET_CUSTOM_CSS_DIR}"

if [ -f "src/styles/global.css" ]; then
    echo "Copying global.css to ${TARGET_CUSTOM_CSS_DIR}/global.css ..."
    cp "src/styles/global.css" "${TARGET_CUSTOM_CSS_DIR}/global.css"
else
    echo "Warning: src/styles/global.css not found, skipping copy."
fi

if [ -f "src/styles/components.css" ]; then
    echo "Copying components.css to ${TARGET_CUSTOM_CSS_DIR}/components.css ..."
    cp "src/styles/components.css" "${TARGET_CUSTOM_CSS_DIR}/components.css"
fi
if [ -f "src/styles/layout.css" ]; then
    echo "Copying layout.css to ${TARGET_CUSTOM_CSS_DIR}/layout.css ..."
    cp "src/styles/layout.css" "${TARGET_CUSTOM_CSS_DIR}/layout.css"
fi

echo "Frontend build and copy completed successfully!"

# Reminder: Make this script executable with `chmod +x build.sh` 