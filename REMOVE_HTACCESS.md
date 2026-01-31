# Remove .htaccess File

Since GoDaddy's Python App uses Passenger/WSGI, the .htaccess file might be causing conflicts.

## Option 1: Delete via File Manager
1. Go to cPanel → File Manager
2. Navigate to `/public_html/hrefs/market-research/`
3. Find `.htaccess` file
4. Right-click → Delete

## Option 2: Delete via FTP
Use your FTP client to delete the `.htaccess` file from the server.

## After Deleting:
1. Wait 30 seconds
2. Try accessing: https://weavrk.com/hrefs/market-research/
3. The Python App should handle routing automatically

