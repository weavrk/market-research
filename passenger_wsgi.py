#!/usr/bin/env python3
"""
Alternative WSGI entry point for Passenger/Phusion (if GoDaddy supports it).
Use this if the standard index.py doesn't work.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app

# Passenger expects 'application'
application = app

