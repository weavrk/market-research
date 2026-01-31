# How to Check Error Logs in GoDaddy

## Step 1: Find Error Logs

1. In GoDaddy cPanel, look for **"Metrics"** or **"Errors"** section
2. Click on **"Errors"** or **"Error Log"**
3. Look for recent errors related to your Python app

## Step 2: What to Look For

Common errors you might see:
- `ModuleNotFoundError` - Missing Python package
- `ImportError` - Can't import a module
- `FileNotFoundError` - Missing file
- `PermissionError` - File permission issue
- `SyntaxError` - Python syntax error

## Step 3: Copy the Error

Copy the full error message and share it - that will tell us exactly what's wrong!

---

## Alternative: Check Passenger Logs

In the Python App setup page, you should see:
- **Passenger log file:** `/home/weavrk/`

You can view this log file in cPanel File Manager to see what's failing.

