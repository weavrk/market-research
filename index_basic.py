#!/usr/bin/env python3
"""
Ultra-basic WSGI test - no Flask, just raw WSGI.
This will tell us if Python itself is working.
"""

import sys
import os

def application(environ, start_response):
    """Basic WSGI application - no dependencies."""
    status = '200 OK'
    headers = [('Content-type', 'text/html; charset=utf-8')]
    start_response(status, headers)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Python WSGI Test</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .success {{ color: green; font-size: 24px; }}
            .info {{ background: #f0f0f0; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1 class="success">✓ Python WSGI is Working!</h1>
        <p>If you see this, Python and WSGI are configured correctly.</p>
        
        <div class="info">
            <h2>System Information:</h2>
            <p><strong>Python Version:</strong> {sys.version}</p>
            <p><strong>Python Executable:</strong> {sys.executable}</p>
            <p><strong>Current Directory:</strong> {os.getcwd()}</p>
            <p><strong>Python Path:</strong></p>
            <ul>
    """
    
    for path in sys.path[:5]:  # Show first 5 paths
        html += f"<li>{path}</li>"
    
    html += """
            </ul>
        </div>
        
        <div class="info">
            <h2>Testing Imports:</h2>
            <ul>
    """
    
    # Test basic imports
    imports_to_test = [
        ('os', 'os'),
        ('sys', 'sys'),
        ('json', 'json'),
    ]
    
    for name, module in imports_to_test:
        try:
            __import__(module)
            html += f"<li style='color: green;'>✓ {name} - OK</li>"
        except Exception as e:
            html += f"<li style='color: red;'>✗ {name} - {str(e)}</li>"
    
    # Test Flask
    try:
        import flask
        html += f"<li style='color: green;'>✓ Flask - {flask.__version__}</li>"
    except ImportError:
        html += "<li style='color: red;'>✗ Flask - NOT INSTALLED</li>"
    except Exception as e:
        html += f"<li style='color: red;'>✗ Flask - {str(e)}</li>"
    
    html += """
            </ul>
        </div>
        
        <div class="info">
            <h2>Next Steps:</h2>
            <p>If Flask is installed, try changing the startup file to <code>index_simple.py</code></p>
            <p>If Flask is NOT installed, you need to run: <code>pip3 install --user flask</code></p>
        </div>
    </body>
    </html>
    """
    
    return [html.encode('utf-8')]

