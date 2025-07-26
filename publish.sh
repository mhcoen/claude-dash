#!/bin/bash
# Script to publish Claude Dash to PyPI

echo "Building Claude Dash for PyPI..."

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build

echo "Build complete. Files created:"
ls -la dist/

echo ""
echo "To upload to TestPyPI (for testing):"
echo "  python -m twine upload --repository testpypi dist/*"
echo ""
echo "To upload to PyPI (for production):"
echo "  python -m twine upload dist/*"
echo ""
echo "After publishing, users can install with:"
echo "  uvx claude-dash"
echo "  # or"
echo "  pip install claude-dash"