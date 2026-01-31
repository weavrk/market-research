#!/usr/bin/env python3
"""
Script to delete .htaccess file from GoDaddy server via FTP.
"""

import os
from ftplib import FTP
from dotenv import load_dotenv

# Load environment variables (ignore errors if .env doesn't exist)
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
print("Deleting .htaccess file from GoDaddy server...")
print("="*60)

try:
    # Connect to FTP
    print(f"Connecting to {FTP_HOST}...")
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    print("✓ Connected successfully")
    
    # Change to remote directory
    try:
        ftp.cwd(FTP_REMOTE_PATH)
        print(f"✓ Changed to {FTP_REMOTE_PATH}")
    except Exception as e:
        print(f"✗ Error changing directory: {e}")
        ftp.quit()
        exit(1)
    
    # Delete .htaccess file
    try:
        ftp.delete('.htaccess')
        print("✓ Successfully deleted .htaccess file")
    except Exception as e:
        # File might not exist or already deleted
        if '550' in str(e) or 'not found' in str(e).lower():
            print("⚠ .htaccess file not found (might already be deleted)")
        else:
            print(f"✗ Error deleting .htaccess: {e}")
    
    # Close connection
    ftp.quit()
    print("\n✓ Done!")
    print("\nWait 30 seconds, then try: https://weavrk.com/hrefs/market-research/")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    exit(1)

