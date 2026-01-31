# Fix 403 Forbidden - After .htaccess Deleted

Since .htaccess is deleted, the 403 is likely due to:

## 1. Check if Python App is Running

In the Python App setup page:
- Look for **"STOP APP"** and **"RESTART"** buttons
- If you see **"START"** button, click it
- The app should show as **"Running"** or **"Started"**

## 2. Check File Permissions

In cPanel File Manager, check these permissions:

**Required Permissions:**
- `index.py` → **755** (executable)
- `app.py` → **644**
- `templates/` folder → **755**
- `static/` folder → **755**
- `data/` folder → **755** (writable)

**To change permissions:**
1. Right-click the file/folder
2. Select "Change Permissions" or "File Permissions"
3. Set:
   - For files: 644
   - For folders: 755
   - For index.py: 755 (executable)
4. Click "Change Permissions"

## 3. Verify Python App Configuration

In Python App setup, double-check:
- **Application root:** `/home/weavrk/public_html/hrefs/market-research`
- **Application startup file:** `index.py`
- **Application Entry point:** `application`
- **Python version:** 3.x (NOT 2.7)

## 4. Try Simplified Test File

Temporarily change the startup file:
1. In Python App setup
2. Change "Application startup file" to: `index_simple.py`
3. Click "SAVE"
4. Click "RESTART"
5. Wait 30 seconds
6. Try the site

This will help us see if it's a permissions issue or an import error.

## 5. Check Error Logs Again

Check the error log in cPanel:
- Go to **Metrics → Errors**
- Look for new errors
- The error message will tell us what's wrong

---

**Start with #1 and #2 - those are most likely the issue!**

