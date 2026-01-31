#!/usr/bin/env python3
"""
GoDaddy WSGI entry point for Flask application.
This file is required for GoDaddy Python hosting.
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Change to the application directory
os.chdir(current_dir)

try:
    # Import the Flask app
    from app import app
    
    # For GoDaddy, we need to expose the application
    application = app
    
except Exception as e:
    # Create a simple error handler app if import fails
    from flask import Flask
    error_app = Flask(__name__)
    
    @error_app.route('/')
    def error():
        return f"""
        <h1>Application Error</h1>
        <p>Error loading Flask application:</p>
        <pre>{str(e)}</pre>
        <p>Please check:</p>
        <ul>
            <li>Python dependencies are installed (pip install -r requirements.txt)</li>
            <li>All required files are present</li>
            <li>File permissions are correct</li>
        </ul>
        <p>Current directory: {current_dir}</p>
        <p>Python path: {sys.path}</p>
        """
    
    application = error_app
