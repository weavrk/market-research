#!/usr/bin/env python3
"""
Check for .htaccess files in parent directories that might be causing issues.
"""

import os
from ftplib import FTP
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass

FTP_HOST = os.getenv('FTP_HOST', 'ftp.weavrk.com')
FTP_USER = os.getenv('FTP_USER', 'weavrk')
FTP_PASS = os.getenv('FTP_PASS', 'Oneplus1=2')

print("="*60)
print("Checking for .htaccess files in parent directories...")
print("="*60)

try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    print("✓ Connected\n")
    
    # Check various parent directories
    paths_to_check = [
        '/public_html/hrefs/',
        '/public_html/',
        '/home/weavrk/public_html/hrefs/',
        '/home/weavrk/public_html/',
    ]
    
    for path in paths_to_check:
        try:
            ftp.cwd(path)
            try:
                ftp.size('.htaccess')
                print(f"⚠ FOUND .htaccess in: {path}")
            except:
                print(f"✓ No .htaccess in: {path}")
        except Exception as e:
            print(f"✗ Cannot access: {path} ({str(e)[:50]})")
    
    ftp.quit()
    print("\n" + "="*60)
    print("If .htaccess found in parent directories, you may need to")
    print("delete or modify them, or contact GoDaddy support.")
    print("="*60)
    
except Exception as e:
    print(f"Error: {e}")

