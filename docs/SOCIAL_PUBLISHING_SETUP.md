# Social Publishing Setup Guide

Connect LinkedIn, X (Twitter), and Threads to enable direct publishing from Postmagiq.

---

## Prerequisites

1. **Deploy your app** with HTTPS (required for OAuth callbacks)
2. **One contact email** (e.g., `support@postmagiq.com` or your personal email)
3. **App logo** - 100x100px image for each platform

Your app URLs:
- Privacy Policy: `https://yourdomain.com/privacy`
- Terms of Service: `https://yourdomain.com/terms`

---

## LinkedIn Setup

### 1. Create LinkedIn Page (if needed)

LinkedIn requires a company page to create an app.

1. Go to https://www.linkedin.com/company/setup/new/
2. Fill in company name: "Postmagiq"
3. Click Create

### 2. Create LinkedIn App

1. Go to https://www.linkedin.com/developers/apps
2. Click "Create app"
3. Fill in:

| Field | Value |
|-------|-------|
| App name | Postmagiq |
| LinkedIn Page | Select your page |
| Privacy policy URL | `https://yourdomain.com/privacy` |
| App logo | Upload 100x100 image |

4. Check the agreement box and click "Create app"

### 3. Request Products

In your app settings, go to "Products" tab and request:

- **Sign In with LinkedIn using OpenID Connect** - For user authentication
- **Share on LinkedIn** - For posting content

These are usually auto-approved.

### 4. Configure OAuth

Go to "Auth" tab:

1. Add OAuth 2.0 redirect URL:
   ```
   https://yourdomain.com/api/v1/social/callback/linkedin
   ```

2. Copy your credentials:
   - Client ID
   - Client Secret (click to reveal)

### 5. Add to Environment

```bash
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/linkedin
```

---

## X (Twitter) Setup

### 1. Create X Developer Account

1. Go to https://developer.twitter.com/en/portal/petition/essential/basic-info
2. Sign in with your X account
3. Complete the developer application (describe your use case)

### 2. Create Project & App

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Click "Create Project"
3. Fill in:

| Field | Value |
|-------|-------|
| Project name | Postmagiq |
| Use case | Making a bot / Publishing content |
| Project description | AI-powered content publishing tool |

4. Create an App within the project:

| Field | Value |
|-------|-------|
| App name | Postmagiq |
| App environment | Production |

### 3. Configure OAuth 1.0a

Go to your app settings → "User authentication settings" → Edit:

1. **App permissions**: Read and write
2. **Type of App**: Web App, Automated App or Bot
3. **Callback URI**:
   ```
   https://yourdomain.com/api/v1/social/callback/x
   ```
4. **Website URL**: `https://yourdomain.com`
5. **Terms of service**: `https://yourdomain.com/terms`
6. **Privacy policy**: `https://yourdomain.com/privacy`

### 4. Get API Keys

Go to "Keys and tokens" tab:

1. **API Key and Secret** (Consumer Keys):
   - Generate or regenerate
   - Copy both values

### 5. Add to Environment

```bash
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/x
```

### Rate Limits (Free Tier)

- 1,500 posts per month
- 50 requests per 15 minutes

---

## Threads Setup

### 1. Create Meta Developer Account

1. Go to https://developers.facebook.com/
2. Click "Get Started" or "My Apps"
3. Sign in with your Facebook account
4. Complete developer registration

### 2. Create App

1. Click "Create App"
2. Select "Other" for use case
3. Select "Business" as app type
4. Fill in:

| Field | Value |
|-------|-------|
| App name | Postmagiq |
| App contact email | your email |

### 3. Add Threads Product

1. In your app dashboard, click "Add Product"
2. Find "Threads API" and click "Set Up"
3. Accept the terms

### 4. Configure OAuth

Go to Threads API → Settings:

1. Add redirect URI:
   ```
   https://yourdomain.com/api/v1/social/callback/threads
   ```

2. Add Deauthorize callback URL:
   ```
   https://yourdomain.com/api/v1/social/deauth/threads
   ```

### 5. Get Credentials

Go to Settings → Basic:

1. Copy **App ID**
2. Copy **App Secret** (click Show)

### 6. Add to Environment

```bash
THREADS_APP_ID=your_app_id
THREADS_APP_SECRET=your_app_secret
THREADS_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/threads
```

### 7. Submit for Review (Production)

For production use, you need to:

1. Complete Data Use Checkup
2. Provide Privacy Policy URL
3. Submit for App Review

During development, you can test with your own account.

---

## Environment Variables Summary

Add all of these to your `.env` file:

```bash
# Encryption key for storing tokens (generate with: openssl rand -hex 32)
SOCIAL_ENCRYPTION_KEY=your_encryption_key

# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/linkedin

# X (Twitter)
X_API_KEY=
X_API_SECRET=
X_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/x

# Threads
THREADS_APP_ID=
THREADS_APP_SECRET=
THREADS_REDIRECT_URI=https://yourdomain.com/api/v1/social/callback/threads
```

---

## Testing Locally

For local development, use localhost URLs:

```bash
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/social/callback/linkedin
X_REDIRECT_URI=http://localhost:8000/api/v1/social/callback/x
THREADS_REDIRECT_URI=http://localhost:8000/api/v1/social/callback/threads
```

**Note:** LinkedIn and Threads require HTTPS for production. For local testing:
- LinkedIn: Allows localhost without HTTPS
- X: Allows localhost without HTTPS
- Threads: May require HTTPS even for testing (use ngrok if needed)

---

## Troubleshooting

### "Invalid redirect URI"
- Make sure the redirect URI in your app settings exactly matches the one in your `.env`
- Check for trailing slashes

### "Token expired"
- LinkedIn tokens expire after 60 days
- X tokens don't expire (OAuth 1.0a)
- Threads tokens expire after 60 days
- Users will see "expired - reconnect" in Settings

### "Permission denied"
- Check that you've requested the correct products/scopes
- For LinkedIn: Make sure "Share on LinkedIn" product is approved
- For X: Make sure "Read and write" permissions are enabled

### "App not approved"
- LinkedIn: Products are usually auto-approved
- X: Basic access is auto-approved
- Threads: Requires app review for production (test mode works with your own account)
