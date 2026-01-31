# GoDaddy Subdomain Setup - Step by Step

## Step 1: Create the Subdomain in GoDaddy

1. **Go to cPanel**
2. **Find "Subdomains"** (usually under "Domains" section)
3. **Create subdomain:**
   - Subdomain: `market-research` (or whatever you want)
   - Document Root: `/public_html/market-research` (or let it auto-create)
4. **Click "Create"**

This creates: `market-research.weavrk.com`

---

## Step 2: Upload Files to Subdomain Directory

Files should go to: `/public_html/market-research/`

(Not `/public_html/hrefs/market-research/` - that's the old path)

---

## Step 3: Set Up Python App for Subdomain

1. **Go to "Python App" or "Setup Python App"** in cPanel
2. **Click "Create Application"**
3. **Configure:**
   - **Python version:** 3.10 or 3.11 (latest available)
   - **Application root:** `/home/weavrk/public_html/market-research`
   - **Application URL:** 
     - Domain: `market-research.weavrk.com`
     - Path: `/` (just a slash, empty)
   - **Application startup file:** `index.py`
   - **Application Entry point:** `application`
4. **Click "Create"**

---

## Step 4: Update APPLICATION_ROOT in app.py

Since it's now a subdomain (not a subdirectory), we need to change:

**In `app.py`, change:**
```python
app.config['APPLICATION_ROOT'] = '/hrefs/market-research'
```

**To:**
```python
app.config['APPLICATION_ROOT'] = ''
```

(Empty string because it's the root of the subdomain)

---

## Step 5: Install Dependencies

In Python App setup:
1. Find your application
2. Click "Run Pip Install" or use Terminal
3. Enter: `requirements.txt`
4. Click "Run Pip Install"
5. Wait for it to complete

---

## Step 6: Set File Permissions

In File Manager:
- `index.py` → **755** (executable)
- `app.py` → **644**
- Folders → **755**

---

## Step 7: Restart and Test

1. In Python App setup, click **"RESTART"**
2. Wait 30 seconds
3. Visit: `https://market-research.weavrk.com`

---

## Important Notes:

- **No .htaccess needed** - Python App handles routing
- **Subdomain = root path** - So APPLICATION_ROOT should be empty
- **Make sure Python is 3.x** - Not 2.7

---

**That's it! The subdomain setup is actually simpler than the subdirectory path.**

