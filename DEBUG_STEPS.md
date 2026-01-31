# Debug Steps for 500 Error

## Step 1: Check Error Logs in cPanel

1. **Go to cPanel**
2. **Find "Metrics" section** (or "Errors" or "Error Log")
3. **Click "Errors"** or "Error Log"
4. **Look for the most recent error** (should be from just now)
5. **Copy the FULL error message** - this will tell us exactly what's wrong

The error will look something like:
- `ModuleNotFoundError: No module named 'pandas'`
- `ImportError: cannot import name 'app'`
- `FileNotFoundError: [Errno 2] No such file or directory`
- `PermissionError: [Errno 13] Permission denied`

**Share that error message with me!**

---

## Step 2: Try Simplified Test File

In the Python App setup page:

1. **Change "Application startup file"** from `index.py` to `index_simple.py`
2. **Click "SAVE"**
3. **Click "RESTART"**
4. **Wait 30 seconds**
5. **Visit:** `https://weavrk.com/hrefs/market-research/`

This will show you a diagnostic page that tells you:
- If Python/Flask is working
- What error is happening
- What's missing

---

## Step 3: Check Passenger Logs

The Passenger log file path is shown in your Python App setup. To view it:

1. **Go to File Manager** in cPanel
2. **Navigate to:** `/home/weavrk/` (or the path shown)
3. **Look for log files** (might be named `passenger.log` or similar)
4. **Open the most recent one**
5. **Copy the error messages**

---

## Step 4: Verify Python Version

Make sure in the Python App setup:
- **Python version** is **3.x** (NOT 2.7)
- If it's still 2.7, change it to 3.x and restart

---

## Step 5: Verify Dependencies Installed

In the Python App setup page, there should be a way to run commands. Try:

1. Look for **"Execute python script"** section
2. Or find **Terminal/Console** option
3. Run: `python3 -c "import flask; print('Flask OK')"`
4. Run: `python3 -c "import pandas; print('Pandas OK')"`

If these fail, the packages aren't installed correctly.

---

## Most Common Issues:

1. **Python 2.7 instead of 3.x** - Check the version dropdown
2. **Missing packages** - pip install might have failed
3. **Wrong Application Root path** - Should be full path like `/home/weavrk/public_html/hrefs/market-research`
4. **File permissions** - `index.py` should be executable (755)

---

**Start with Step 1 - check the error logs and share what you see!**

