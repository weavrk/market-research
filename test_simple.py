#!/usr/bin/env python3
"""
Simple test script to verify Python is working on GoDaddy.
Upload this and visit: https://weavrk.com/hrefs/market-research/test_simple.py
"""

print("Content-Type: text/html\n")
print("""
<!DOCTYPE html>
<html>
<head>
    <title>Python Test</title>
</head>
<body>
    <h1>Python is Working!</h1>
    <p>If you see this, Python is configured correctly on GoDaddy.</p>
    <h2>System Information:</h2>
    <ul>
""")

import sys
import os

print(f"<li>Python Version: {sys.version}</li>")
print(f"<li>Current Directory: {os.getcwd()}</li>")
print(f"<li>Python Path: {sys.path[:3]}</li>")

# Test imports
print("<h2>Testing Imports:</h2>")
print("<ul>")

try:
    import flask
    print(f"<li style='color: green;'>✓ Flask: {flask.__version__}</li>")
except Exception as e:
    print(f"<li style='color: red;'>✗ Flask: {str(e)}</li>")

try:
    import pandas
    print(f"<li style='color: green;'>✓ Pandas: {pandas.__version__}</li>")
except Exception as e:
    print(f"<li style='color: red;'>✗ Pandas: {str(e)}</li>")

try:
    import googlemaps
    print(f"<li style='color: green;'>✓ Google Maps API</li>")
except Exception as e:
    print(f"<li style='color: red;'>✗ Google Maps API: {str(e)}</li>")

print("</ul>")

# Check files
print("<h2>Checking Files:</h2>")
print("<ul>")

files_to_check = ['app.py', 'index.py', 'requirements.txt']
for file in files_to_check:
    if os.path.exists(file):
        print(f"<li style='color: green;'>✓ {file} exists</li>")
    else:
        print(f"<li style='color: red;'>✗ {file} missing</li>")

print("</ul>")
print("</body></html>")

