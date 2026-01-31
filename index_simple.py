#!/usr/bin/env python3
"""
Simplified WSGI entry point for debugging.
Use this to test if basic Python/Flask is working.
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Change to the application directory
os.chdir(current_dir)

# Try to create a minimal Flask app first
try:
    from flask import Flask
    test_app = Flask(__name__)
    
    @test_app.route('/')
    def hello():
        return """
        <h1>Python Flask is Working!</h1>
        <p>If you see this, Python and Flask are installed correctly.</p>
        <h2>Next Steps:</h2>
        <p>Now we need to test if the full app loads...</p>
        <p><a href="/test-full">Test Full App</a></p>
        """
    
    @test_app.route('/test-full')
    def test_full():
        try:
            from app import app as full_app
            return """
            <h1>Full App Loaded Successfully!</h1>
            <p>The full Flask application imported without errors.</p>
            <p><a href="/">Go to main app</a></p>
            """
        except Exception as e:
            return f"""
            <h1>Error Loading Full App</h1>
            <p>Error: {str(e)}</p>
            <p>Type: {type(e).__name__}</p>
            <pre>{str(e)}</pre>
            """
    
    application = test_app
    
except Exception as e:
    # Even Flask isn't working
    def error_wsgi(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/html')]
        start_response(status, headers)
        return [f"""
        <h1>Critical Error</h1>
        <p>Flask is not installed or there's a Python error.</p>
        <p>Error: {str(e)}</p>
        <p>Type: {type(e).__name__}</p>
        <pre>{str(e)}</pre>
        <p>Python version: {sys.version}</p>
        <p>Current directory: {current_dir}</p>
        """.encode()]
    
    application = error_wsgi

