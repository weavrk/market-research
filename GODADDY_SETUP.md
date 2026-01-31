# GoDaddy Python/Flask Setup Guide

## 403 Forbidden Error - Troubleshooting

If you're getting a 403 Forbidden error, follow these steps:

### Step 1: Enable Python on GoDaddy

1. Log into your **GoDaddy cPanel**
2. Navigate to **Software** → **Setup Python App**
3. Click **Create Application**
4. Configure:
   - **Python Version**: Select Python 3.x (latest available)
   - **Application Root**: `/hrefs/market-research`
   - **Application URL**: `/hrefs/market-research`
   - **Application Startup File**: `index.py`
   - **Application Entry Point**: `application`
5. Click **Create**

### Step 2: Install Python Dependencies

In cPanel, go to **Software** → **Setup Python App**:
1. Find your application
2. Click **Open Terminal** or use SSH
3. Run:
   ```bash
   cd /hrefs/market-research
   pip3 install -r requirements.txt --user
   ```

### Step 3: Set File Permissions

Using FTP or File Manager:
1. Set `index.py` to **755** (executable)
2. Set `app.py` to **644**
3. Set directories `data/` and `uploads/` to **755**
4. Ensure `.htaccess` is **644**

### Step 4: Alternative .htaccess (if needed)

If the current `.htaccess` doesn't work, try this alternative:

```apache
# Alternative GoDaddy Python Configuration
Options +ExecCGI
AddHandler cgi-script .py

# Enable Python
<FilesMatch "\.py$">
    SetHandler fcgid-script
</FilesMatch>

# Rewrite rules
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.py/$1 [QSA,L]
```

### Step 5: Verify Python is Working

Create a test file `test.py`:
```python
#!/usr/bin/env python3
print("Content-Type: text/html\n")
print("<h1>Python is working!</h1>")
```

Upload it and visit: `https://weavrk.com/hrefs/market-research/test.py`

If this works, Python is configured correctly.

### Step 6: Check Error Logs

In cPanel:
1. Go to **Metrics** → **Errors**
2. Check for Python-related errors
3. Common issues:
   - Missing modules (install via pip)
   - Permission errors (fix file permissions)
   - Path errors (check APPLICATION_ROOT)

## Alternative: Using Passenger (if available)

If GoDaddy supports Passenger/Phusion:

1. Create `passenger_wsgi.py`:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from app import app
application = app
```

2. Update `.htaccess`:
```apache
PassengerEnabled On
PassengerAppRoot /hrefs/market-research
PassengerBaseURI /hrefs/market-research
PassengerPython /usr/bin/python3
```

## Still Getting 403?

### Check These:

1. **Directory Index**: Ensure `index.py` is listed as an index file
   - In `.htaccess`, add: `DirectoryIndex index.py index.html`

2. **Python Path**: Verify Python path in cPanel matches your installation

3. **File Ownership**: Files should be owned by your cPanel user

4. **Contact GoDaddy Support**: 
   - Ask them to enable Python for your account
   - Request assistance with Flask/WSGI configuration
   - Provide them with your application structure

## Quick Test Commands

SSH into your server and test:

```bash
# Check Python version
python3 --version

# Check if Flask is installed
python3 -c "import flask; print(flask.__version__)"

# Test the app directly
cd /hrefs/market-research
python3 index.py
```

## File Structure on Server

Your files should be at:
```
/public_html/hrefs/market-research/
├── index.py          (755 - executable)
├── app.py            (644)
├── .htaccess         (644)
├── requirements.txt  (644)
├── templates/        (755)
├── static/           (755)
├── data/             (755 - writable)
└── uploads/          (755 - writable)
```

## Need Help?

If you're still having issues:
1. Check GoDaddy's Python documentation
2. Contact GoDaddy support with your error logs
3. Verify your hosting plan supports Python (some shared plans don't)

