#!/usr/bin/env python3
"""
Deployment script for Market Research application.
Handles deployment to GoDaddy FTP and GitHub.
"""

import os
import sys
import subprocess
from pathlib import Path
from ftplib import FTP
from dotenv import load_dotenv
import argparse

# Load environment variables (ignore errors if .env doesn't exist)
try:
    load_dotenv()
except Exception:
    pass  # Continue with defaults if .env can't be loaded

# FTP Configuration (from credentials.md)
FTP_HOST = os.getenv('FTP_HOST', 'ftp.weavrk.com')
FTP_USER = os.getenv('FTP_USER', 'weavrk')
FTP_PASS = os.getenv('FTP_PASS', 'Oneplus1=2')
FTP_REMOTE_PATH = os.getenv('FTP_REMOTE_PATH', '/public_html/hrefs/market-research/')

# GitHub Configuration
GITHUB_REPO = os.getenv('GITHUB_REPO', 'git@github.com:weavrk/market-research.git')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

# Files and directories to deploy
DEPLOY_FILES = [
    'app.py',
    'requirements.txt',
    'credentials.md',
    'BILLING_SETUP.md',
    'check_api_usage.py',
    'all_cities.txt',
]

DEPLOY_DIRS = [
    'templates',
    'static',
    'data',
]

# Files to exclude
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '.env',
    '.git',
    'uploads',
    '*.log',
    '.DS_Store',
    'x.archive',
]


def upload_file_ftp(ftp, local_path, remote_path):
    """Upload a single file via FTP."""
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  ✓ Uploaded: {remote_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error uploading {remote_path}: {e}")
        return False


def upload_dir_ftp(ftp, local_dir, remote_dir):
    """Upload a directory recursively via FTP."""
    local_path = Path(local_dir)
    remote_path = remote_dir.rstrip('/')
    
    # Create remote directory if it doesn't exist
    try:
        ftp.mkd(remote_path)
    except:
        pass  # Directory might already exist
    
    # Upload files
    for item in local_path.rglob('*'):
        if item.is_file():
            # Check if file should be excluded
            if any(pattern in str(item) for pattern in EXCLUDE_PATTERNS):
                continue
            
            # Calculate relative path from the local_dir (not parent)
            rel_path = item.relative_to(local_path)
            remote_file_path = f"{remote_path}/{rel_path.as_posix()}"
            
            # Create subdirectories if needed
            remote_file_dir = '/'.join(remote_file_path.split('/')[:-1])
            if remote_file_dir:
                # Create directory structure recursively
                dir_parts = remote_file_dir.split('/')
                current_path = ''
                for part in dir_parts:
                    if part:
                        current_path = f"{current_path}/{part}" if current_path else part
                        try:
                            ftp.mkd(current_path)
                        except:
                            pass  # Directory might already exist
            
            upload_file_ftp(ftp, item, remote_file_path)


def deploy_ftp(skip_build=False):
    """Deploy files to GoDaddy via FTP."""
    print("\n" + "="*60)
    print("Deploying to GoDaddy FTP...")
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
            return False
        
        # Upload individual files
        print("\nUploading files...")
        for file in DEPLOY_FILES:
            if os.path.exists(file):
                upload_file_ftp(ftp, file, file)
            else:
                print(f"  ⚠ Skipping (not found): {file}")
        
        # Upload directories
        print("\nUploading directories...")
        for dir_name in DEPLOY_DIRS:
            if os.path.exists(dir_name):
                print(f"  Uploading {dir_name}/...")
                upload_dir_ftp(ftp, dir_name, f"{FTP_REMOTE_PATH.rstrip('/')}/{dir_name}")
            else:
                print(f"  ⚠ Skipping (not found): {dir_name}/")
        
        # Close connection
        ftp.quit()
        print("\n✓ FTP deployment completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ FTP deployment failed: {e}")
        return False


def deploy_github(commit_message=None):
    """Deploy to GitHub by pushing to repository."""
    print("\n" + "="*60)
    print("Deploying to GitHub...")
    print("="*60)
    
    if not commit_message:
        commit_message = input("Enter commit message (or press Enter for default): ").strip()
        if not commit_message:
            commit_message = f"Deploy: {subprocess.check_output(['date'], text=True).strip()}"
    
    try:
        # Check if git is initialized
        if not os.path.exists('.git'):
            print("Initializing git repository...")
            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'remote', 'add', 'origin', GITHUB_REPO], check=True)
        
        # Check current remote
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                 capture_output=True, text=True, check=True)
            current_remote = result.stdout.strip()
            if current_remote != GITHUB_REPO:
                print(f"Updating remote URL from {current_remote} to {GITHUB_REPO}")
                subprocess.run(['git', 'remote', 'set-url', 'origin', GITHUB_REPO], check=True)
        except:
            subprocess.run(['git', 'remote', 'add', 'origin', GITHUB_REPO], check=True)
        
        # Add all files
        print("Staging files...")
        subprocess.run(['git', 'add', '-A'], check=True)
        
        # Commit
        print(f"Committing changes: {commit_message}")
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        # Push to GitHub
        print(f"Pushing to {GITHUB_REPO} ({GITHUB_BRANCH})...")
        subprocess.run(['git', 'push', '-u', 'origin', GITHUB_BRANCH], check=True)
        
        print("\n✓ GitHub deployment completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ GitHub deployment failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ GitHub deployment failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Deploy Market Research application')
    parser.add_argument('--ftp-only', action='store_true', help='Deploy only to FTP')
    parser.add_argument('--github-only', action='store_true', help='Deploy only to GitHub')
    parser.add_argument('--skip-build', action='store_true', help='Skip build step (not applicable for Python)')
    parser.add_argument('--commit-message', type=str, help='Git commit message')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Market Research - Deployment Script")
    print("="*60)
    
    success = True
    
    # Deploy to FTP
    if not args.github_only:
        if not deploy_ftp(args.skip_build):
            success = False
    
    # Deploy to GitHub
    if not args.ftp_only:
        if not deploy_github(args.commit_message):
            success = False
    
    print("\n" + "="*60)
    if success:
        print("✓ Deployment completed successfully!")
        print(f"  Live site: https://weavrk.com/hrefs/market-research/")
        print(f"  GitHub: {GITHUB_REPO}")
    else:
        print("✗ Deployment completed with errors. Please check the output above.")
        sys.exit(1)
    print("="*60)


if __name__ == '__main__':
    main()

