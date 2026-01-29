# iOS Shortcut Installation Guide

## Important Note About Unsigned Shortcuts

⚠️ **iOS does not allow direct import of unsigned `.shortcut` files via AirDrop or file sharing.** You have two options:

### Option 1: Manual Creation (Recommended)

Follow the detailed step-by-step guide in [`IOS_SHORTCUT_GUIDE.md`](./IOS_SHORTCUT_GUIDE.md) to manually create the shortcut on your device. This takes about 5-10 minutes but gives you full control.

### Option 2: Use the Template as Reference

The `ContentStash-Save.shortcut` file I created serves as a **reference template** showing the exact structure and configuration. You can:

1. Open `documents/ContentStash-Save.shortcut` in a text editor on your Mac
2. Use it as a guide while manually building the shortcut on your iOS device
3. Copy the exact values for URLs, headers, and JSON bodies

## Manual Creation Steps (Quick Version)

Here's a condensed version of the manual setup:

### Step 1: Create New Shortcut

1. Open **Shortcuts** app on your iPhone/iPad
2. Tap **+** to create a new shortcut
3. Tap the **ⓘ** icon and:
   - Name it: **"Save to ContentStash"**
   - Toggle on **"Show in Share Sheet"**
   - Under "Share Sheet Types", select: **URLs** and **Safari Web Pages**
   - Tap **Done**

### Step 2: Add Actions

Add these actions in order (tap **+** or search for each action):

1. **Get Variable** → Select **"Shortcut Input"**
2. **Set Variable** → Name it **"URL"**
3. **Choose from Menu** → Prompt: "Extraction Type"
   - Add 3 options: "Fast (Server)", "Complete (Server)", "Local (Browser)"

4. For **each menu option**, add **Get Contents of URL**:
   - **Method**: POST
   - **URL**: `http://YOUR_SERVER_IP:8000/api/v1/items`
   - **Headers**: Add two headers:
     - `Content-Type`: `application/json`
     - `Authorization`: `Bearer YOUR_JWT_TOKEN`
   - **Request Body**: JSON
   - **JSON**: Add two fields:
     - `url`: [Select Variable: URL]
     - `extraction_type`: `"fast"` (or `"complete"` or `"local"` for each option)

5. After the menu ends, add **Show Notification**:
   - Title: "Saved to ContentStash"
   - Body: "URL saved successfully"

### Step 3: Get Your JWT Token

1. Open your ContentStash web app in a browser on your computer
2. Press **F12** to open Developer Tools
3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Click **Local Storage** in the left sidebar
5. Find the `token` key and copy its value (starts with `eyJ...`)
6. You'll need this token for the Authorization header in Step 2

### Step 4: Get Your Server URL

Determine your server URL:
- **Local network**: `http://192.168.1.XXX:8000/api/v1/items` (replace XXX with your server's IP)
- **Production**: `https://your-domain.com/api/v1/items`
- **Localhost** (if running on same device): `http://localhost:8000/api/v1/items`

To find your local IP on Mac:
- System Settings → Network → Your connection → Details → TCP/IP → IPv4 Address

## Usage

### From Safari
1. Open any webpage
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **"Save to ContentStash"**
4. Choose your extraction type (Fast/Complete/Local)
5. You'll see a notification when saved!
6. The title and metadata will be automatically fetched from the URL

### From Other Apps
Works with any app that shares URLs (YouTube, Twitter, Reddit, etc.)

## Troubleshooting

### "Untrusted Shortcut" Warning
- Go to **Settings > Shortcuts**
- Enable **"Allow Untrusted Shortcuts"**
- You may need to run any shortcut once before this option appears

### "Could not connect to server"
- Verify your server URL is correct and accessible
- If using local network (192.168.x.x), ensure your phone is on the same WiFi
- Try accessing the URL in Safari first to test connectivity

### "Authentication failed" (401 error)
- Your JWT token may have expired
- Get a fresh token from the web app (see Step 4)
- Update all three "Get contents of URL" actions with the new token

### Shortcut doesn't appear in Share Sheet
- Make sure "Show in Share Sheet" is enabled
- Restart the Shortcuts app
- Try sharing from Safari first (it's most reliable)

## Security Note

⚠️ **Important**: Your JWT token is stored in plain text in the shortcut. Anyone with access to your device can view it.

**Best practices:**
- Use a strong device passcode
- Enable Face ID/Touch ID
- Don't share the shortcut file with others
- Regenerate your token periodically

## What This Shortcut Does

The shortcut:
1. Receives a URL from the Share Sheet
2. Lets you choose an extraction type (Fast/Complete/Local)
3. Sends a POST request to your ContentStash server with the URL and extraction type
4. The server automatically fetches the title, description, and thumbnail from the URL
5. Shows a notification when complete

## Optional: Manual Title Entry

If you prefer to manually enter titles instead of automatic extraction, you can add these actions after Step 2:

1. **Ask for Input** → Prompt: "Title (leave empty for auto-fetch)" → Type: Text
2. **Set Variable** → Name it **"Title"**

Then in each "Get Contents of URL" action, add a third field to the JSON:
- `title`: [Select Variable: Title]

**Note**: If you leave the title empty, the server will automatically fetch it from the URL's metadata.

## Need Help?

- Check the main guide: [`IOS_SHORTCUT_GUIDE.md`](./IOS_SHORTCUT_GUIDE.md)
- Review the API documentation
- Open an issue on GitHub