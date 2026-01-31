# Google Cloud Billing API Setup Guide

To get **real-time actual costs** instead of estimates, you need to set up the Google Cloud Billing API.

## 🚀 Quick Setup (5 minutes)

### 1. Enable Billing API
```bash
# In Google Cloud Console
1. Go to: https://console.cloud.google.com/apis/library
2. Search for "Cloud Billing API"
3. Click "Enable"
```

### 2. Create Service Account
```bash
# In Google Cloud Console
1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "Create Service Account"
3. Name: "billing-monitor"
4. Role: "Billing Account Viewer"
5. Create and download JSON key
```

### 3. Update Your Code
Replace the mock data in `app.py` with real API calls:

```python
# Add to requirements.txt
google-cloud-billing==1.11.0

# Update get_google_cloud_billing_data() function
from google.cloud import billing_v1
import json

def get_google_cloud_billing_data():
    try:
        # Initialize billing client
        client = billing_v1.CloudBillingClient()
        
        # Get billing account (replace with your account ID)
        billing_account = "billingAccounts/YOUR_BILLING_ACCOUNT_ID"
        
        # Get current month's usage
        current_month = datetime.now().strftime("%Y-%m")
        
        # Make API calls to get real data
        # This is where you'd implement the actual billing API calls
        
        return real_billing_data
        
    except Exception as e:
        logger.error(f"Error getting billing data: {e}")
        return None
```

### 4. Set Environment Variables
```bash
# Add to your .env file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
BILLING_ACCOUNT_ID=your-billing-account-id
```

## 📊 What You'll Get

Once set up, you'll see **real-time data** in the navigation bar:

- **Monthly Total**: Actual spending this month
- **Daily Total**: Today's spending
- **API Usage**: Real request counts
- **Free Tier Remaining**: Actual remaining credits
- **Auto-refresh**: Updates every 5 minutes

## 🔧 Alternative: Manual Billing Check

If you don't want to set up the API, you can manually check:

1. **Google Cloud Console**: https://console.cloud.google.com/billing
2. **Billing Reports**: View detailed usage by API
3. **Quotas**: Monitor API usage limits

## 💡 Current Status

Right now, the system shows:
- ✅ **Cost structure** and pricing
- ✅ **Safety limits** and protection
- ✅ **Real-time API call tracking** (per search)
- ⚠️ **Mock billing data** (until you set up the API)

## 🎯 Next Steps

1. **Set up Google Cloud Billing API** (5 minutes)
2. **Replace mock data** with real API calls
3. **See actual costs** in real-time
4. **Set up billing alerts** for overages

Your web scraper is ready - just needs the billing API connection for real-time costs!
