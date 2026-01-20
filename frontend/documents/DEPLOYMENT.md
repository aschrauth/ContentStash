# Deployment Configuration

## Frontend Deployment

### Environment Variables

The frontend requires the following environment variable to be set:

#### `NEXT_PUBLIC_API_URL`

The base URL for the backend API, including the `/api/v1` prefix.

**Local Development:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Production (Vercel/Netlify/etc):**
```
NEXT_PUBLIC_API_URL=https://contentstash-backend.onrender.com/api/v1
```

### Deployment Platforms

#### Vercel

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add `NEXT_PUBLIC_API_URL` with value: `https://contentstash-backend.onrender.com/api/v1`
4. Redeploy the application

#### Netlify

1. Go to Site settings → Build & deploy → Environment
2. Add environment variable:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://contentstash-backend.onrender.com/api/v1`
3. Trigger a new deploy

#### Other Platforms

Ensure the `NEXT_PUBLIC_API_URL` environment variable is set to include the full API base URL with the `/api/v1` prefix.

### Important Notes

- The `/api/v1` prefix is **required** - without it, API calls will return 404 errors
- The environment variable must start with `NEXT_PUBLIC_` to be accessible in the browser
- After changing environment variables, you must redeploy the application for changes to take effect

---

## Backend Deployment (Render.com)

### Prerequisites

The backend uses Playwright for web content extraction, which requires:
1. Chromium browser binaries
2. System dependencies for running Chromium in headless mode
3. Proper build configuration

### Automatic Deployment with render.yaml

The repository includes a [`render.yaml`](../../render.yaml) file at the project root that automatically configures the entire deployment, including system dependencies. This is the **recommended approach** as it eliminates the need for manual dashboard configuration.

#### What render.yaml Provides

The configuration file automatically handles:
- **Service definition** - Web service configuration for the backend
- **System dependencies** - All required Chromium libraries (aptPackages)
- **Build command** - Executes [`backend/render-build.sh`](../../backend/render-build.sh)
- **Start command** - Launches the FastAPI application
- **Environment variables** - Placeholders for required secrets
- **Playwright browser persistence** - Ensures browser binaries persist from build to runtime

#### Deployment Steps

1. **Connect your repository** to Render.com
2. **Render will automatically detect** the `render.yaml` file
3. **Set environment variables** in the Render dashboard:
   - `DATABASE_URL` - PostgreSQL connection string
   - `SECRET_KEY` - JWT secret key
   - `GEMINI_API_KEY` - Google Gemini API key
   - `YOUTUBE_API_KEY` - (Optional) YouTube Data API v3 key
4. **Deploy** - Render will use the configuration from `render.yaml`

#### System Dependencies (Automatically Installed)

The `render.yaml` file includes all required Chromium dependencies in the `nativeEnvironments` section:

```yaml
nativeEnvironments:
  - libnss3
  - libatk1.0-0
  - libatk-bridge2.0-0
  - libcups2
  - libdrm2
  - libxkbcommon0
  - libxcomposite1
  - libxdamage1
  - libxfixes3
  - libxrandr2
  - libgbm1
  - libasound2
```

**No manual dashboard configuration required!** These packages are installed automatically during deployment.

#### Build and Start Commands

The `render.yaml` file specifies:

**Build Command:**
```bash
./backend/render-build.sh
```

**Start Command:**
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

These are configured automatically - you don't need to set them in the dashboard.

### Manual Configuration (Alternative)

If you prefer not to use `render.yaml`, you can configure manually in the Render dashboard:

#### 1. Build Command

Set **Build Command** to:
```bash
./backend/render-build.sh
```

#### 2. Start Command

Set **Start Command** to:
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### 3. System Dependencies

Navigate to "Environment" → "Native Environment" and add:
```
libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

#### 4. Environment Variables

Ensure all required environment variables are set in Render.com:

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `GEMINI_API_KEY` - Google Gemini API key
- `PLAYWRIGHT_BROWSERS_PATH` - Set to `/opt/render/project/src/backend/ms-playwright-browsers` (critical for browser persistence)

**Optional:**
- `YOUTUBE_API_KEY` - YouTube Data API v3 key (for video metadata)
- `ENVIRONMENT` - Set to `production`


### Playwright Browser Persistence on Render.com

#### Why Browser Persistence is Critical

Render.com uses **separate environments** for build and runtime:
- **Build environment**: Where dependencies are installed (including Playwright browsers)
- **Runtime environment**: Where your application runs

By default, Playwright installs browsers to `/opt/render/.cache/`, which is **not accessible at runtime**. This causes the error:
```
Executable doesn't exist at /opt/render/.cache/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell
```

#### The Solution: PLAYWRIGHT_BROWSERS_PATH

To fix this, we install browsers to an **absolute path** that persists from build to runtime:

1. **During build** ([`backend/render-build.sh`](../../backend/render-build.sh)):
   ```bash
   export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/backend/ms-playwright-browsers
   playwright install chromium
   ```

2. **At runtime** ([`render.yaml`](../../render.yaml)):
   ```yaml
   envVars:
     - key: PLAYWRIGHT_BROWSERS_PATH
       value: /opt/render/project/src/backend/ms-playwright-browsers
   ```

**Why Absolute Paths?**
- Render.com's working directory may differ between build and runtime
- Relative paths like `./ms-playwright-browsers` can resolve to different locations
- Using the absolute path `/opt/render/project/src/backend/ms-playwright-browsers` ensures consistency
- This path is based on Render's standard project structure where code is deployed to `/opt/render/project/src/`

This ensures Playwright looks for browsers in the same absolute location during both build and runtime.

### Troubleshooting Playwright Issues

#### Error: "Executable doesn't exist at /opt/render/.cache/..."

**Cause:** `PLAYWRIGHT_BROWSERS_PATH` is not set correctly, causing browsers to install to the default cache location.

**Solution:**
1. Verify `PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/backend/ms-playwright-browsers` is set in [`render.yaml`](../../render.yaml)
2. Verify the build script exports this variable (with the same absolute path) before installing browsers
3. Redeploy to apply the changes
4. Check build logs for "Chromium installed successfully to /opt/render/project/src/backend/ms-playwright-browsers"

#### Error: "Executable doesn't exist" (general)

**Cause:** Playwright browser binaries were not installed during build.

**Solution:**
1. Verify the build script is being executed
2. Check build logs for `playwright install chromium` output
3. Ensure the build command is set to `./backend/render-build.sh`
4. Verify `PLAYWRIGHT_BROWSERS_PATH` is set in both build script and runtime environment

#### Error: "Browser closed unexpectedly" or "Failed to launch browser"

**Cause:** Missing system dependencies for Chromium.

**Solution:**
1. Verify all system packages are installed (see System Dependencies Configuration above)
2. Check deployment logs for missing library errors
3. Add any missing libraries to the Native Environment configuration

#### Error: "TimeoutError" during content extraction

**Cause:** Network issues or slow-loading websites.

**Solution:**
- The extraction service has built-in timeout handling (30-90 seconds)
- Check logs for specific timeout errors
- Consider increasing timeout values in [`backend/app/services/extraction.py`](../../backend/app/services/extraction.py) if needed

#### Debugging Playwright in Production

The extraction service includes detailed logging. To view Playwright-specific logs:

1. Go to Render.com dashboard → Logs
2. Filter for messages containing "Playwright"
3. Look for error messages with stack traces

Common log messages:
- `"Attempting Playwright extraction for {url}"` - Playwright is being used
- `"Playwright successfully extracted {n} characters"` - Success
- `"Playwright error extracting content"` - Failure with error details

### Performance Considerations

**Memory Usage:**
- Playwright with Chromium requires ~200-300MB RAM per instance
- Ensure your Render.com plan has sufficient memory (recommended: 512MB minimum)

**Cold Starts:**
- First Playwright extraction after deployment may be slower (~5-10 seconds)
- Subsequent extractions are faster due to browser caching

**Extraction Strategy:**
- The service uses a two-tier approach:
  1. **Fast mode** (default): Tries lightweight extraction first, falls back to Playwright
  2. **Complete mode**: Uses Playwright directly for JavaScript-heavy sites
- This minimizes Playwright usage and improves performance

### Verification Steps

After deployment, verify Playwright is working:

1. **Test content extraction:**
   ```bash
   curl -X POST https://your-backend.onrender.com/api/v1/items \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "extraction_type": "complete"}'
   ```

2. **Check logs for Playwright messages:**
   - Look for "Playwright successfully extracted" messages
   - Verify no browser launch errors

3. **Test with JavaScript-heavy site:**
   - Try saving a Substack article or similar dynamic content
   - Verify content is extracted correctly

### Additional Resources

- [Playwright Documentation](https://playwright.dev/python/docs/intro)
- [Render.com Native Environment](https://render.com/docs/native-environments)
- [Backend Extraction Service](../../backend/app/services/extraction.py)