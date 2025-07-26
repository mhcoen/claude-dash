#!/bin/bash
# Test runner script for Claude Dash

echo "🧪 Running Claude Dash Test Suite"
echo "================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate 2>/dev/null

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -e . -q
pip install pytest pytest-cov pytest-mock -q

# Run tests with different configurations
echo ""
echo -e "${GREEN}Running unit tests...${NC}"
pytest tests/unit -v --tb=short

echo ""
echo -e "${GREEN}Running integration tests...${NC}"
pytest tests/integration -v --tb=short -m "not slow"

echo ""
echo -e "${GREEN}Running all tests with coverage...${NC}"
pytest --cov=claude_dash --cov-report=term-missing --cov-report=html

# Check code quality
echo ""
echo -e "${GREEN}Running code quality checks...${NC}"

# Check if ruff is installed
if command -v ruff &> /dev/null; then
    echo "Running ruff..."
    ruff check claude_dash tests
else
    echo -e "${YELLOW}Ruff not installed, skipping linting${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}Test suite complete!${NC}"
echo "Coverage report available at: htmlcov/index.html"

# Deactivate virtual environment
deactivate 2>/dev/null || true