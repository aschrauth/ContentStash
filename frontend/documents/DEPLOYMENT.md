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

**Optional:**
- `YOUTUBE_API_KEY` - YouTube Data API v3 key (for video metadata)
- `ENVIRONMENT` - Set to `production`


### Troubleshooting Playwright Issues

#### Error: "Executable doesn't exist"

**Cause:** Playwright browser binaries were not installed during build.

**Solution:**
1. Verify the build script is being executed
2. Check build logs for `playwright install chromium` output
3. Ensure the build command is set to `./backend/render-build.sh`

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