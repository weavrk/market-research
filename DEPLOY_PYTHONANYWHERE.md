# Deploy to PythonAnywhere - Step by Step

PythonAnywhere is the EASIEST way to host Python/Flask apps. No SSH, no terminal, no manual setup needed!

## Step 1: Sign Up (Free)
1. Go to https://www.pythonanywhere.com
2. Click "Beginner" (free account)
3. Sign up with email

## Step 2: Upload Files
1. In PythonAnywhere dashboard, click **Files**
2. Create folder: `market-research`
3. Upload these files (drag & drop or click Upload):
   - `app.py`
   - `index.py`
   - `requirements.txt`
   - `templates/` folder (all HTML files)
   - `static/` folder
   - `data/` folder

## Step 3: Install Dependencies
1. Click **Tasks** tab
2. Click **Bash** (opens a console)
3. Run:
   ```bash
   cd market-research
   pip3.10 install --user -r requirements.txt
   ```

## Step 4: Configure Web App
1. Click **Web** tab
2. Click **Add a new web app**
3. Choose **Flask**
4. Python version: **3.10**
5. Flask project path: `/home/yourusername/market-research`
6. Flask app file: `index.py`
7. Variable name: `application`

## Step 5: Set Up Static Files
1. In Web tab, scroll to **Static files**
2. Add:
   - URL: `/static/`
   - Directory: `/home/yourusername/market-research/static`

## Step 6: Update APPLICATION_ROOT
Since PythonAnywhere uses a subdomain, update `app.py`:
- Change `APPLICATION_ROOT = '/hrefs/market-research'` 
- To: `APPLICATION_ROOT = ''` (empty string)

Or keep it if you want the paths to match.

## Step 7: Reload Web App
Click the green **Reload** button in Web tab.

## Done!
Your app will be at: `yourusername.pythonanywhere.com`

**That's it! No SSH, no terminal commands, everything through the web interface.**

