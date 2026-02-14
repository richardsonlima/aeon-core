#!/bin/bash
# ============================================================================
# Æon Framework - PyPI Publishing Automation Script
# Publishes aeon-core to PyPI with validation and safety checks
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Æon Framework v0.3.0 - PyPI Publishing Script            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# ============================================================================
# Step 1: Validation
# ============================================================================
echo -e "\n${YELLOW}[1/6] Validating environment...${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  ✓ Python version: $PYTHON_VERSION"

# Check required tools
for tool in python3 pip git; do
    if ! command -v $tool &> /dev/null; then
        echo -e "${RED}  ✗ $tool not found. Please install it.${NC}"
        exit 1
    fi
done
echo "  ✓ Required tools available"

# Check we're in the right directory
if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo -e "${RED}  ✗ pyproject.toml not found. Are you in the project root?${NC}"
    exit 1
fi
echo "  ✓ Project structure validated"

# ============================================================================
# Step 2: Check PyPI credentials
# ============================================================================
echo -e "\n${YELLOW}[2/6] Checking PyPI credentials...${NC}"

if [ -z "$TWINE_USERNAME" ] && [ -z "$TWINE_PASSWORD" ]; then
    if [ ! -f "$HOME/.pypirc" ]; then
        echo -e "${RED}  ✗ No PyPI credentials found.${NC}"
        echo "  Setup options:"
        echo "    1. Create ~/.pypirc with your credentials"
        echo "    2. Export TWINE_USERNAME and TWINE_PASSWORD"
        echo "    3. Use: export TWINE_PASSWORD='pypi-AgE...'"
        exit 1
    fi
    echo "  ✓ Using ~/.pypirc credentials"
else
    echo "  ✓ Using TWINE_USERNAME and TWINE_PASSWORD env vars"
fi

# ============================================================================
# Step 3: Install build tools
# ============================================================================
echo -e "\n${YELLOW}[3/6] Installing build tools...${NC}"

if ! python3 -m pip show build &> /dev/null; then
    echo "  Installing build..."
    python3 -m pip install --quiet build
fi
echo "  ✓ build installed"

if ! python3 -m pip show twine &> /dev/null; then
    echo "  Installing twine..."
    python3 -m pip install --quiet twine
fi
echo "  ✓ twine installed"

# ============================================================================
# Step 4: Clean and build
# ============================================================================
echo -e "\n${YELLOW}[4/6] Building package...${NC}"

# Clean previous builds
if [ -d "$DIST_DIR" ]; then
    echo "  Cleaning dist/ directory..."
    rm -rf "$DIST_DIR"
fi
if [ -d "$BUILD_DIR" ]; then
    echo "  Cleaning build/ directory..."
    rm -rf "$BUILD_DIR"
fi

# Build
cd "$PROJECT_DIR"
echo "  Running: python3 -m build"
python3 -m build > /dev/null 2>&1

# Check build artifacts
if [ ! -f "$DIST_DIR/aeon_core-0.3.0.tar.gz" ]; then
    echo -e "${RED}  ✗ Source distribution not found${NC}"
    exit 1
fi
echo "  ✓ Source distribution: $(basename $DIST_DIR/aeon_core-0.3.0.tar.gz)"

if [ ! -f "$DIST_DIR/aeon_core-0.3.0-py3-none-any.whl" ]; then
    echo -e "${RED}  ✗ Wheel not found${NC}"
    exit 1
fi
echo "  ✓ Wheel: $(basename $DIST_DIR/aeon_core-0.3.0-py3-none-any.whl)"

# ============================================================================
# Step 5: Validate with twine
# ============================================================================
echo -e "\n${YELLOW}[5/6] Validating package with twine...${NC}"

if ! twine check "$DIST_DIR"/* > /dev/null 2>&1; then
    echo -e "${RED}  ✗ Package validation failed${NC}"
    twine check "$DIST_DIR"/*
    exit 1
fi
echo "  ✓ Package structure valid"
echo "  ✓ Metadata valid"
echo "  ✓ Long description renders correctly"

# ============================================================================
# Step 6: Publish to PyPI
# ============================================================================
echo -e "\n${YELLOW}[6/6] Publishing to PyPI...${NC}"

echo "  Repository: https://upload.pypi.org/legacy/"
echo "  Package: aeon-core 0.3.0"
echo ""
read -p "  Are you sure you want to publish? (yes/no): " -r CONFIRM

if [[ $CONFIRM != "yes" ]]; then
    echo -e "${YELLOW}  Cancelled.${NC}"
    exit 0
fi

echo ""
echo "  Publishing... (this may take a moment)"

if twine upload "$DIST_DIR"/* \
    ${TWINE_USERNAME:+--username "$TWINE_USERNAME"} \
    ${TWINE_PASSWORD:+--password "$TWINE_PASSWORD"} \
    --non-interactive \
    --skip-existing; then
    echo -e "${GREEN}  ✓ Published successfully!${NC}"
else
    echo -e "${RED}  ✗ Publication failed${NC}"
    exit 1
fi

# ============================================================================
# Success
# ============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Package published successfully!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Install with:"
echo -e "    ${BLUE}pip install aeon-core${NC}"
echo ""
echo "  View on PyPI:"
echo -e "    ${BLUE}https://pypi.org/project/aeon-core/${NC}"
echo ""
