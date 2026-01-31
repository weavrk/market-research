#!/bin/bash
# Script to install Python dependencies on GoDaddy server
# Run this via SSH or cPanel Terminal

echo "Installing Python dependencies for Market Research app..."
echo "=================================================="

# Navigate to application directory
cd /hrefs/market-research || cd ~/public_html/hrefs/market-research

# Check Python version
echo "Python version:"
python3 --version

# Install dependencies using pip3 with --user flag (required for shared hosting)
echo ""
echo "Installing dependencies..."
pip3 install --user -r requirements.txt

echo ""
echo "Installation complete!"
echo ""
echo "To verify, run: python3 -c 'import flask; print(flask.__version__)'"

