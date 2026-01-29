# iOS Shortcut Setup Guide

This guide explains how to create an iOS Shortcut to quickly save URLs to ContentStash from your iPhone or iPad.

## Overview

The iOS Shortcut allows you to:
- Save URLs from any app using the Share Sheet
- Send URLs directly to your ContentStash server
- Choose extraction type (Fast, Complete, or Local)
- Automatically fetch metadata (title, description, thumbnail) from URLs

## Prerequisites

- iOS 13 or later
- ContentStash server running and accessible from your device
- Your ContentStash account credentials

## Setup Instructions

### Step 1: Get Your API Token

1. Log into ContentStash web app
2. Open browser DevTools (F12)
3. Go to Application > Local Storage
4. Find and copy your `token` value (JWT)

### Step 2: Create the Shortcut

1. Open the **Shortcuts** app on your iPhone/iPad
2. Tap the **+** button to create a new shortcut
3. Add the following actions:

#### Action 1: Receive Input
- Type: **URLs**
- Source: **Share Sheet**

#### Action 2: Set Variable
- Variable Name: **URL**
- Value: **Shortcut Input**

#### Action 3: Choose from Menu
- Prompt: **"Extraction Type"**
- Options:
  - Fast (Server)
  - Complete (Server)
  - Local (Browser)

#### Action 4-6: For each menu option, add "Get Contents of URL"

**For "Fast (Server)" option:**
```
Get contents of: https://your-server.com/api/items
Method: POST
Headers:
  Content-Type: application/json
  Authorization: Bearer YOUR_JWT_TOKEN_HERE
Request Body: JSON
{
  "url": "[URL Variable]",
  "extraction_type": "fast"
}
```

**For "Complete (Server)" option:**
```
Get contents of: https://your-server.com/api/items
Method: POST
Headers:
  Content-Type: application/json
  Authorization: Bearer YOUR_JWT_TOKEN_HERE
Request Body: JSON
{
  "url": "[URL Variable]",
  "extraction_type": "complete"
}
```

**For "Local (Browser)" option:**
```
Get contents of: https://your-server.com/api/items
Method: POST
Headers:
  Content-Type: application/json
  Authorization: Bearer YOUR_JWT_TOKEN_HERE
Request Body: JSON
{
  "url": "[URL Variable]",
  "extraction_type": "local"
}
```

#### Action 7: Show Notification
- Title: **"Saved to ContentStash"**
- Body: **"URL saved successfully"**

### Step 3: Configure the Shortcut

1. Name your shortcut: **"Save to ContentStash"**
2. Add an icon (optional)
3. Enable **"Show in Share Sheet"**
4. Set **"Share Sheet Types"** to: **URLs, Safari Web Pages, Text**

### Step 4: Replace Placeholders

In each "Get Contents of URL" action:
1. Replace `https://your-server.com` with your actual server URL
2. Replace `YOUR_JWT_TOKEN_HERE` with your actual JWT token

## Usage

### From Safari
1. Open a webpage you want to save
2. Tap the **Share** button
3. Scroll down and tap **"Save to ContentStash"**
4. Choose extraction type
5. Done! The title and metadata will be automatically fetched from the URL
6. You'll see a notification when saved

### From Other Apps
1. Find content with a shareable URL (articles, videos, etc.)
2. Tap **Share**
3. Select **"Save to ContentStash"**
4. Follow the prompts

## Advanced: Manual Title Entry (Optional)

If you prefer to manually enter titles instead of automatic extraction:

Add these actions after Action 2 (Set Variable for URL):
1. **Ask for Input**
   - Prompt: "Title for this item? (Leave empty for auto-fetch)"
   - Input Type: Text
   - Default Answer: Leave empty
2. **Set Variable**
   - Variable Name: Title
   - Value: Provided Input

Then in each "Get Contents of URL" action, add the title field to the JSON:
```json
{
  "url": "[URL Variable]",
  "title": "[Title Variable]",
  "extraction_type": "fast"
}
```

**Note**: If you provide an empty title, the server will automatically fetch it from the URL's metadata.

## Troubleshooting

### "Could not connect to server"
- Verify your server URL is correct
- Ensure your server is accessible from your device
- Check if you're on the same network (for localhost)

### "Authentication failed"
- Your JWT token may have expired
- Get a new token from the web app
- Update the token in all three "Get Contents of URL" actions

### "Shortcut doesn't appear in Share Sheet"
- Ensure "Show in Share Sheet" is enabled
- Check "Share Sheet Types" includes URLs
- Restart the Shortcuts app

## Security Notes

⚠️ **Important**: Your JWT token is stored in plain text in the shortcut. Anyone with access to your device can see it.

**Best Practices**:
- Use a strong device passcode
- Don't share your shortcut file with others
- Regenerate your token periodically
- Consider using a dedicated API key (future feature)

## Limitations

- **No Local Extraction on iOS**: The "Local" extraction type will still be processed by the server or your Desktop Chrome Extension
- **Token Expiration**: JWT tokens expire after a certain time (default: 30 days)
- **No Offline Support**: Requires internet connection

## Future Enhancements

Planned improvements:
- Native iOS app with proper authentication
- Offline queue for URLs
- Background sync
- Safari extension for iOS (requires App Store distribution)

## Example Shortcut File

A pre-configured shortcut template is available at:
`documents/ContentStash-Save.shortcut`

To use it:
1. Download the file to your iPhone
2. Open it in the Shortcuts app
3. Update the server URL and token
4. Save and enable

---

**Need Help?** Check the main documentation or open an issue on GitHub.