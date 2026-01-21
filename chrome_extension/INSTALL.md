# Chrome Extension Installation Guide

## ✅ Build Complete!

The extension has been successfully built and is ready to install.

## Installation Steps

### 1. Open Chrome Extensions Page
- Open Google Chrome
- Navigate to `chrome://extensions/`
- Or click the three dots menu → More Tools → Extensions

### 2. Enable Developer Mode
- Look for the "Developer mode" toggle in the top right corner
- Turn it **ON**

### 3. Load the Extension
- Click the **"Load unpacked"** button (appears after enabling Developer mode)
- Navigate to: `/Users/anthonyschrauth/Documents/Dev/ContentStash/chrome_extension/dist`
- Click **"Select"** or **"Open"**

### 4. Verify Installation
You should see the ContentStash extension appear in your extensions list with:
- Name: **ContentStash**
- Version: **1.0.0**
- Status: **Enabled**

### 5. Pin the Extension (Optional but Recommended)
- Click the puzzle piece icon in Chrome's toolbar
- Find "ContentStash" in the list
- Click the pin icon to keep it visible in your toolbar

## First Time Setup

### 1. Click the Extension Icon
- You'll see the ContentStash popup

### 2. Login
- **Server URL**: `http://localhost:8000` (or your production URL)
- **Email**: Your ContentStash account email
- **Password**: Your ContentStash account password
- Click **Login**

### 3. Test It Out!
1. Navigate to any webpage (try a YouTube video!)
2. Click the ContentStash extension icon
3. Choose extraction type:
   - **Fast (Server)**: Quick extraction
   - **Complete (Server)**: Full extraction
   - **Local (Browser)**: Use your browser (bypasses blocks!)
4. Click **"Save Page"**
5. Check your ContentStash library!

## Testing Local Extraction

### Test with YouTube (Blocked in Production)
1. Go to any YouTube video
2. Click ContentStash extension
3. Select **"Local (Browser)"** extraction type
4. Click "Save Page"
5. The extension will extract the content using your browser
6. Check your library - it should appear!

### Test Background Processing
1. Save a YouTube video with **"Fast"** extraction (will fail on server)
2. Server will mark it as `pending_local_extraction`
3. Extension automatically polls every 15 minutes
4. Or click **"Process Now"** button to process immediately
5. Extension opens the URL in background, extracts, and uploads
6. Content appears in your library!

## Troubleshooting

### Extension doesn't appear
- Make sure you selected the `dist` folder, not the root `chrome_extension` folder
- Try refreshing the extensions page
- Check Chrome console for errors

### Login fails
- Verify your server is running at the URL you entered
- Check your email/password are correct
- Open browser DevTools (F12) and check Console for errors

### Content extraction fails
- Check the extension's service worker console:
  - Go to `chrome://extensions/`
  - Find ContentStash
  - Click "service worker" link
  - Check console for errors

### Background polling not working
- Check if polling is enabled in settings (future feature)
- Manually click "Process Now" to test
- Check service worker console for errors

## Development Mode

If you're developing the extension:

```bash
# Watch mode (auto-rebuild on changes)
cd chrome_extension
npm run dev

# After changes, click the refresh icon on the extension card in chrome://extensions/
```

## Updating the Extension

After making code changes:

```bash
cd chrome_extension
npm run build
```

Then in Chrome:
1. Go to `chrome://extensions/`
2. Find ContentStash
3. Click the refresh icon (circular arrow)

## Uninstalling

1. Go to `chrome://extensions/`
2. Find ContentStash
3. Click **"Remove"**
4. Confirm removal

## Next Steps

- Set up iOS Shortcut (see `documents/IOS_SHORTCUT_GUIDE.md`)
- Configure polling interval (future feature)
- Add custom server URL for production

## Support

If you encounter issues:
1. Check the service worker console
2. Check browser DevTools console
3. Review the logs in your ContentStash server
4. Check `chrome_extension/README.md` for more details

---

**Congratulations!** 🎉 Your ContentStash extension is ready to use!