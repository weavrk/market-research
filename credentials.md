# Market Research - Deployment Credentials

## FTP (GoDaddy)

**Connection Details:**
- **Host:** `ftp.weavrk.com`
- **Username:** `weavrk`
- **Password:** `Oneplus1=2`
- **Remote Path:** `/public_html/hrefs/market-research/`

**Usage:**
These credentials are stored in `.env` file for the deploy script.

```bash
FTP_HOST=ftp.weavrk.com
FTP_USER=weavrk
FTP_PASS=Oneplus1=2
FTP_REMOTE_PATH=/public_html/hrefs/market-research/
```

---

## GitHub

**Repository:** https://github.com/weavrk/market-research.git

**SSH URL:** git@github.com:weavrk/market-research.git

**Credentials:**
- **Username:** `weavrk`
- **Password:** `Oneplus1#2`

**Note:** GitHub requires SSH keys or Personal Access Tokens for authentication. Password authentication is deprecated. The repository uses SSH authentication with git@github.com:weavrk/market-research.git

---

## Live Site URL

**Production:** https://weavrk.com/hrefs/market-research/

**GitHub Repository:** https://github.com/weavrk/market-research

---

## Deployment Commands

**Build & Deploy to GoDaddy:**
```bash
npm run build
npm run deploy
```

**Deploy without rebuilding:**
```bash
npm run deploy -- --skip-build
```

**Push to GitHub:**
```bash
git add -A
git commit -m "Your commit message"
git push origin main
```

---

## Mobile Access

For testing on mobile devices (same WiFi network):

1. Find your computer's IP: `ipconfig getifaddr en0`
2. Access locally: `http://[YOUR-IP]:8002/`
3. Access production: https://weavrk.com/hrefs/market-research/

