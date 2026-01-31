#!/usr/bin/env python3
"""
Script to check and report file permissions via FTP.
This helps diagnose 403 errors.
"""

import os
from ftplib import FTP
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except Exception:
    pass

# FTP Configuration
FTP_HOST = os.getenv('FTP_HOST', 'ftp.weavrk.com')
FTP_USER = os.getenv('FTP_USER', 'weavrk')
FTP_PASS = os.getenv('FTP_PASS', 'Oneplus1=2')
FTP_REMOTE_PATH = os.getenv('FTP_REMOTE_PATH', '/public_html/hrefs/market-research/')

print("="*60)
print("Checking File Permissions on GoDaddy Server...")
print("="*60)

try:
    # Connect to FTP
    print(f"Connecting to {FTP_HOST}...")
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    print("✓ Connected successfully")
    
    # Change to remote directory
    ftp.cwd(FTP_REMOTE_PATH)
    print(f"✓ Changed to {FTP_REMOTE_PATH}\n")
    
    # List files and check permissions
    files_to_check = ['index.py', 'app.py', 'index_simple.py']
    
    print("File Status:")
    print("-" * 60)
    
    for filename in files_to_check:
        try:
            # Try to get file info (FTP doesn't directly show permissions, but we can check if file exists)
            ftp.size(filename)
            print(f"✓ {filename:20} - EXISTS")
        except:
            print(f"✗ {filename:20} - NOT FOUND")
    
    # Check directories
    print("\nDirectory Status:")
    print("-" * 60)
    
    dirs_to_check = ['templates', 'static', 'data']
    for dirname in dirs_to_check:
        try:
            ftp.cwd(dirname)
            ftp.cwd('..')  # Go back
            print(f"✓ {dirname:20} - EXISTS")
        except:
            print(f"✗ {dirname:20} - NOT FOUND")
    
    ftp.quit()
    print("\n" + "="*60)
    print("Note: FTP doesn't show permissions directly.")
    print("Check permissions in cPanel File Manager:")
    print("- index.py should be 755 (executable)")
    print("- app.py should be 644")
    print("- Folders should be 755")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ Error: {e}")

