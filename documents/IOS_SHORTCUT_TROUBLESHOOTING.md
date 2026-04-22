# iOS Shortcut Troubleshooting Guide

## Common Issues and Fixes

Based on the server logs, here are the issues you're encountering and how to fix them:

### Issue 1: Expired Sign-In Or 401 Unauthorized Error

**Symptom:** Server logs show:
```
INFO: 10.51.1.29:53468 - "POST /api/v1/items HTTP/1.1" 401 Unauthorized
```

**Cause:** Your shortcut sign-in token is either:
- Expired (tokens expire after 7 days by default)
- Incorrect (missing "Bearer " prefix or wrong token)
- From a different user/session

**Fix for the current shortcut flow:**
1. Delete `Shortcuts/ContentStashAuth.json`.
2. Run the shortcut again.
3. Sign in with your ContentStash email and password when prompted.

**Best fix inside the shortcut:**
After the save request, read the response as a dictionary and check `auth_required`. If it is true, delete `Shortcuts/ContentStashAuth.json`, ask the user to sign in again, and retry the save once.

The shortcut save proxy returns this kind of response when sign-in is needed:

```json
{
  "ok": false,
  "auth_required": true,
  "requires_login": true,
  "detail": "Your ContentStash sign-in expired. Please sign in again to continue saving."
}
```

### Issue 2: 422 Validation Error - Smart Quotes

**Symptom:** Server logs show:
```
Validation errors: [
  {'type': 'string_pattern_mismatch', 'loc': ('body', 'extraction_type'), 
   'msg': "String should match pattern '^(fast|complete|local)$'", 
   'input': '"fast"'}
]
```

**Cause:** iOS is converting straight quotes to smart/curly quotes (`"` instead of `"`)

**Fix:**
1. Edit your shortcut
2. Find the JSON body in each "Get Contents of URL" action
3. For the `extraction_type` field, make sure it's:
   - `fast` (not `"fast"` with quotes)
   - `complete` (not `"complete"`)
   - `local` (not `"local"`)
4. The value should be plain text without any quotes around it

**How to enter it correctly:**
- When adding the JSON field, iOS will ask for the value
- Type just: `fast` (no quotes)
- If you see curly quotes, delete and retype using the standard keyboard

### Issue 3: Missing Title Field

**Symptom:** Server logs show:
```
{'type': 'missing', 'loc': ('body', 'title'), 'msg': 'Field required'}
```

**Cause:** The title variable isn't being passed correctly to the JSON body

**Fix:**
1. Make sure you have these actions in order:
   - Ask for Input (prompt: "Title for this item?")
   - Set Variable (name: "Title")
2. In the JSON body of "Get Contents of URL":
   - Add a field named `title`
   - For the value, tap and select **Variable** → **Title**
   - Do NOT type "Title" as text - it must be the variable

## Correct JSON Body Configuration

For each "Get Contents of URL" action, your JSON should have exactly 3 fields:

### Field 1: url
- **Key**: `url` (text)
- **Value**: Variable → **URL**

### Field 2: title  
- **Key**: `title` (text)
- **Value**: Variable → **Title**

### Field 3: extraction_type
- **Key**: `extraction_type` (text)
- **Value**: `fast` (plain text, no quotes)
  - For the second menu option: `complete`
  - For the third menu option: `local`

## Testing Your Shortcut

### Step 1: Check the Response
1. After running the shortcut, tap and hold on the "Get Contents of URL" action
2. Select "Show Result"
3. You should see a JSON response with an `id` field

### Step 2: Check Server Logs
Look at your backend terminal for:
- ✅ **Good**: `POST /api/v1/items HTTP/1.1" 201 Created`
- ❌ **Bad**: `401 Unauthorized` or `422 Unprocessable Content`

### Step 3: Verify in Web App
1. Open ContentStash web app
2. Refresh the library page
3. Your item should appear

## Quick Checklist

Before running the shortcut, verify:

- [ ] JWT token is fresh (less than 7 days old)
- [ ] Authorization header has "Bearer " prefix with space
- [ ] Save response is checked for `auth_required`
- [ ] Server URL is correct and accessible from your phone
- [ ] Phone is on same network as server (if using local IP)
- [ ] JSON has all 3 fields: url, title, extraction_type
- [ ] extraction_type values are plain text without quotes
- [ ] url and title are variables (not plain text)

## Still Not Working?

### Enable Shortcut Debugging

Add a "Show Result" action after "Get Contents of URL" to see the server response:

1. Edit shortcut
2. After the first "Get Contents of URL" action
3. Add "Show Result" action
4. Run the shortcut
5. You'll see the server's response (error message or success)

### Check Network Connectivity

Test if your phone can reach the server:

1. Open Safari on your iPhone
2. Navigate to: `http://YOUR_SERVER_IP:8000/api/v1/items`
3. You should see an error about authentication (that's good - it means the server is reachable)
4. If you get "Cannot connect", check:
   - Server is running
   - Phone is on same WiFi network
   - Firewall isn't blocking port 8000

## Example of Correct Configuration

Here's what a working "Get Contents of URL" action looks like:

```
Get Contents of URL
  URL: http://10.51.1.54:8000/api/v1/items
  Method: POST
  Headers:
    Content-Type: application/json
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Request Body: JSON
  JSON:
    url: [Variable: URL]
    title: [Variable: Title]
    extraction_type: fast
```

Note: The `url` and `title` show as blue variable pills, not plain text!
