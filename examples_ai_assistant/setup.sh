#!/bin/bash

# Quick Setup for Æon Framework Examples
# Run this script to set up the examples environment

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Æon Framework - Examples Quick Setup                  ║"
echo "╚════════════════════════════════════════════════════════╝"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python version
echo -e "\n${YELLOW}[1/5] Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if [[ "$python_version" < "3.10" ]]; then
    echo "Error: Python 3.10+ required"
    exit 1
fi

# Step 2: Install dependencies
echo -e "\n${YELLOW}[2/5] Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Step 3: Setup environment file
echo -e "\n${YELLOW}[3/5] Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your credentials:"
    echo "  nano .env"
else
    echo ".env file already exists"
fi

# Step 4: Optional - Install Ollama
echo -e "\n${YELLOW}[4/5] Ollama setup (optional)${NC}"
if command -v ollama &> /dev/null; then
    echo "Ollama already installed"
    echo "Available models:"
    ollama list 2>/dev/null || echo "  (Start ollama serve first)"
else
    echo "Ollama not found. To install:"
    echo "  Mac/Linux: brew install ollama"
    echo "  Then: ollama serve (in another terminal)"
    echo "  Then: ollama pull mistral"
fi

# Step 5: Verify installation
echo -e "\n${YELLOW}[5/5] Verifying installation...${NC}"
python3 -c "import aeon; print('✓ Æon Framework installed')" 2>/dev/null || echo "⚠ Æon Framework not found (install with: pip install aeon-core)"

echo -e "\n${GREEN}✓ Setup complete!${NC}"
echo -e "\nNext steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run an example: python simple_chat_ollama.py"
echo "  3. Check README.md for more examples"
