#!/bin/bash
#
# Git hooks installer for dazzlesum static versioning
# Installs pre-commit hook that automatically updates version strings
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Dazzlesum Git Hooks Installer${NC}"
echo "=================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error:${NC} Not in a git repository. Please run from the root of the dazzlesum repository."
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "hooks" ]; then
    echo -e "${RED}Error:${NC} hooks/ directory not found. Please run from the dazzlesum project root."
    exit 1
fi

# Check if source hook exists
if [ ! -f "hooks/pre-commit" ]; then
    echo -e "${RED}Error:${NC} hooks/pre-commit template not found."
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Check if pre-commit hook already exists
if [ -f ".git/hooks/pre-commit" ]; then
    echo -e "${YELLOW}Warning:${NC} Existing pre-commit hook found."
    echo "Current hook:"
    echo "----------------------------------------"
    head -5 .git/hooks/pre-commit
    echo "----------------------------------------"
    echo
    read -p "Replace existing hook? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    
    # Backup existing hook
    cp .git/hooks/pre-commit .git/hooks/pre-commit.backup
    echo -e "${GREEN}Backed up existing hook to:${NC} .git/hooks/pre-commit.backup"
fi

# Install the hook
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo -e "${GREEN}Successfully installed dazzlesum versioning hook!${NC}"
echo
echo "The hook will now automatically update version strings when you commit."
echo
echo -e "${BLUE}Version Format:${NC} MAJOR.MINOR.PATCH_(Build#)-YYYYMMDD-CommitHash"
echo -e "${BLUE}Example:${NC} 1.3.0_35-20250629-4e4fd00a"
echo
echo -e "${BLUE}Features:${NC}"
echo "• Automatically extracts base version from dazzlesum.py"
echo "• Uses previous commit hash to avoid chicken-and-egg problem"
echo "• Handles edge cases (initial commit, shallow repos)"
echo "• Provides clear success/error feedback"
echo "• Creates backup before any changes"
echo
echo -e "${GREEN}Installation complete!${NC} Try making a commit to see it in action."