# Frontend Deployment Configuration

## Environment Variables

The frontend requires the following environment variable to be set:

### `NEXT_PUBLIC_API_URL`

The base URL for the backend API, including the `/api/v1` prefix.

**Local Development:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Production (Vercel/Netlify/etc):**
```
NEXT_PUBLIC_API_URL=https://contentstash-backend.onrender.com/api/v1
```

## Deployment Platforms

### Vercel

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add `NEXT_PUBLIC_API_URL` with value: `https://contentstash-backend.onrender.com/api/v1`
4. Redeploy the application

### Netlify

1. Go to Site settings → Build & deploy → Environment
2. Add environment variable:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://contentstash-backend.onrender.com/api/v1`
3. Trigger a new deploy

### Other Platforms

Ensure the `NEXT_PUBLIC_API_URL` environment variable is set to include the full API base URL with the `/api/v1` prefix.

## Important Notes

- The `/api/v1` prefix is **required** - without it, API calls will return 404 errors
- The environment variable must start with `NEXT_PUBLIC_` to be accessible in the browser
- After changing environment variables, you must redeploy the application for changes to take effect