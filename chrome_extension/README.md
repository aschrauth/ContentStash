# ContentStash Chrome Extension

Quick capture and local extraction agent for ContentStash.

## Features

- **Quick Capture**: Save current page with one click
- **Extraction Types**:
  - Fast (Server): Quick server-side extraction
  - Complete (Server): Full server-side extraction with Playwright
  - Local (Browser): High-quality browser-based extraction matching server-side standards
- **Local Extraction Agent**: Automatically processes items blocked by server
- **Background Polling**: Configurable polling for pending items

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
cd chrome_extension
npm install

# Development build (with hot reload)
npm run dev

# Production build
npm run build
```

### Loading in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome_extension/dist` folder

## Usage

### First Time Setup

1. Click the ContentStash extension icon
2. Enter your server URL (default: `http://localhost:8000`)
3. Login with your email and password

### Saving Pages

1. Navigate to any page you want to save
2. Click the extension icon
3. Choose extraction type:
   - **Fast**: Quick extraction (good for most sites)
   - **Complete**: Full extraction (for JavaScript-heavy sites)
   - **Local**: Use your browser to extract (for blocked sites/paywalls)
4. Click "Save Page"

### Local Extraction

The extension automatically processes items that failed server-side extraction:

- **Automatic**: Polls every 15 minutes (configurable in settings)
- **Manual**: Click "Process Now" button in popup

### Improved Extraction Quality

We have significantly improved local extraction to match the quality of our server-side tools. It now features:

- **Clean Markdown**: Converts HTML to clean, formatted Markdown directly in the browser.
- **Noise Removal**: Aggressively strips ads, navigation, sidebars, and comments.
- **Smart Parsing**: Uses Mozilla's Readability library to identify main content.
- **Safety**: Sanitizes output to remove JSON blocks and scripts.

For full technical details on these improvements, see [Local Extraction Improvements](../documents/LOCAL_EXTRACTION_IMPROVEMENTS.md).

## Architecture

- **Popup** (`src/popup/`): React UI for user interaction
- **Background Worker** (`src/background/`): Service worker for polling and processing
- **Content Script** (`src/content/`): Injected into pages for content extraction
- **API Client** (`src/lib/api.ts`): Communication with ContentStash server
- **Storage** (`src/lib/storage.ts`): Chrome storage wrapper

## Configuration

Settings are stored in Chrome's local storage:

- `serverUrl`: ContentStash server URL
- `token`: JWT authentication token
- `pollingEnabled`: Enable/disable background polling
- `pollingIntervalMinutes`: Polling frequency (default: 15)

## Troubleshooting

### Extension not loading
- Ensure you've run `npm run build`
- Check Chrome DevTools console for errors
- Verify manifest.json is valid

### Authentication fails
- Verify server URL is correct
- Check server is running and accessible
- Ensure CORS is configured on server

### Content extraction fails
- Try different extraction types
- Check browser console for errors
- Verify content script is injected

## Building for Production

```bash
npm run build
```

The built extension will be in `dist/` folder. You can:
1. Load it unpacked in Chrome for testing
2. Zip the `dist/` folder for distribution
3. Submit to Chrome Web Store (requires developer account)

## License

Same as ContentStash main project