# iOS Shortcut Setup Guide

This guide walks through the iPhone and iPad setup in plain language. It is written for someone who does not work with APIs, tokens, or developer tools.

By the end of this guide, you will have a shortcut that:

- appears in the iPhone Share Sheet
- lets you save links from Safari and other apps
- asks you to sign in the first time you use it
- remembers your sign-in so you do not need to keep pasting a token

If you only want the big-picture install steps first, start with [`IOS_SHORTCUT_INSTALLATION.md`](./IOS_SHORTCUT_INSTALLATION.md) and then come back here for the detailed build steps.

## What You Are Building

You are creating an iOS Shortcut named `Save to ContentStash`.

When you share a web page to this shortcut, it will:

1. receive the shared URL
2. check whether you have already signed in before
3. if needed, ask for your email and password
4. send the link to ContentStash
5. show a success message

The important improvement is that the shortcut signs in using your normal ContentStash credentials. You no longer need to:

- open browser dev tools
- look for a JWT token
- paste `Bearer ...` manually
- separately copy a backend API URL

## Before You Start

Please make sure all of these are true before you begin:

- you have an iPhone or iPad with the Shortcuts app installed
- you already have a ContentStash account
- your ContentStash app is reachable from the phone
- you know the main web address for your ContentStash app

Examples of a ContentStash app address:

- `https://stash.example.com`
- `http://192.168.1.42:3000`

You can also open this page in your browser:

- `https://your-stash-app.com/shortcuts/ios`

That helper page shows the exact base URL your shortcut should use.

## A Quick Note About The URL

The shortcut should use your main ContentStash app address, not a separate backend API address.

For example:

- use `https://stash.example.com`
- do not use `https://stash.example.com/api/v1`
- do not use a separate Render backend URL

The shortcut will call these paths automatically:

- `/api/shortcut/login`
- `/api/shortcut/items`

## What To Expect In Shortcuts

The Shortcuts app works like a stack of little blocks called actions. You will add them one by one.

If you are brand new to Shortcuts, do not worry about understanding every action name ahead of time. Just follow the steps in order.

## Part 1: Create A New Shortcut

1. Open the `Shortcuts` app on your iPhone or iPad.
2. Tap the `+` button to create a new shortcut.
3. Tap the shortcut name at the top.
4. Rename it to `Save to ContentStash`.
5. Tap `Done` if iOS asks you to confirm the name.

At this point you will have a blank shortcut.

## Part 2: Turn It Into A Share Sheet Shortcut

This is what makes the shortcut appear when you tap the Share button in Safari or another app.

1. In the shortcut editor, tap the information button.
   On some versions of iOS this is an `i` icon or a settings button near the top.
2. Turn on `Show in Share Sheet`.
3. Under the types it accepts, choose:
   - `URLs`
   - `Safari Web Pages`
4. If `Text` is available and useful for your workflow, you can enable it too.
5. Tap `Done` to return to the editor.

## Part 3: Add The Basic Input Actions

These first actions grab the link you share from another app and store it in a variable named `URL`.

### Step 1: Add The URL Input

1. Tap `Add Action`.
2. Search for `Get Variable` or `Shortcut Input`.
   The exact label can vary slightly depending on iOS version.
3. Choose the action that uses the incoming shared item.
4. Make sure the action is using `Shortcut Input`.

If your shortcut already shows that it accepts share sheet input, this step may already be partially handled by iOS. That is okay.

### Step 2: Save That Input As `URL`

1. Tap `Add Action`.
2. Search for `Set Variable`.
3. Add the `Set Variable` action.
4. Set the variable name to `URL`.
5. Make sure the value being stored is the incoming shared item from the previous step.

Why this matters:

- later actions can use `URL` without you needing to rebuild the input each time

## Part 4: Store Your App Address Inside The Shortcut

This gives the shortcut one place where your ContentStash app address lives.

### Step 3: Add A Text Action

1. Tap `Add Action`.
2. Search for `Text`.
3. Add the `Text` action.
4. In the text field, type your ContentStash app address exactly.

Examples:

- `https://stash.example.com`
- `http://192.168.1.42:3000`

Do not add anything after the domain and port. For example:

- correct: `https://stash.example.com`
- incorrect: `https://stash.example.com/api/v1`

### Step 4: Save That Text As `BaseURL`

1. Tap `Add Action`.
2. Search for `Set Variable`.
3. Add it below the `Text` action.
4. Name the variable `BaseURL`.
5. Make sure it is saving the text from the previous step.

Why this matters:

- every network request in the shortcut will build from `BaseURL`
- if your app address ever changes, you only have to update it in one place

## Part 5: Check Whether The User Has Already Signed In

The shortcut needs a simple way to remember that you already logged in before.

It will do that by storing a small file named `ContentStashAuth.json`.

### Step 5: Try To Read The Saved Auth File

1. Tap `Add Action`.
2. Search for `Get File`.
3. Add the `Get File` action.
4. Set the path to:

`Shortcuts/ContentStashAuth.json`

If iOS asks how to handle a missing file, choose the option that lets the shortcut continue instead of stopping completely. The wording varies by iOS version, but the idea is:

- if the file exists, use it
- if it does not exist yet, move on to the sign-in steps

## Part 6: Add The First-Run Sign-In Flow

This is the part that replaces the old manual token-copy process.

The first time the shortcut runs, it will:

- ask for your email
- ask for your password
- send those to ContentStash
- save the login response for later use

### Step 6A: Ask For Email

1. Tap `Add Action`.
2. Search for `Ask for Input`.
3. Add it below the auth file step.
4. Set the prompt to:

`Email`

5. If iOS offers an input type, choose `Email Address`.

### Step 6B: Ask For Password

1. Tap `Add Action`.
2. Search for `Ask for Input`.
3. Add another one.
4. Set the prompt to:

`Password`

5. If iOS offers a secure text option, turn it on.

### Step 6C: Send The Login Request

1. Tap `Add Action`.
2. Search for `Get Contents of URL`.
3. Add it below the password step.
4. Tap the URL field and build this:

`[BaseURL]/api/shortcut/login`

This means:

- use the `BaseURL` variable first
- then add `/api/shortcut/login`

5. Set `Method` to `POST`.
6. Add one header:
   - key: `Content-Type`
   - value: `application/json`
7. Set the request body type to `JSON`.
8. Add two JSON fields:
   - `email`
   - `password`
9. For the `email` value, insert the answer from the email prompt.
10. For the `password` value, insert the answer from the password prompt.

The body should effectively mean:

```json
{
  "email": "the email the user typed",
  "password": "the password the user typed"
}
```

### Step 6D: Turn The Response Into A Dictionary

1. Tap `Add Action`.
2. Search for `Get Dictionary from Input`.
3. Add it right after the login request.
4. Add `Set Variable`.
5. Name the variable:

`LoginResponse`

This makes it easier for Shortcuts to read values out of the login response.

### Step 6E: Confirm Login Worked

This step checks whether the login response contains a usable token.

The login endpoint returns a dictionary. On success, that dictionary has a `token` field. On failure, it has a `detail` field with a readable error message.

Success response shape:

```json
{
  "token": "eyJ...",
  "user": {
    "email": "you@example.com"
  }
}
```

Failure response shape:

```json
{
  "ok": false,
  "code": "INVALID_CREDENTIALS",
  "detail": "That email or password was not accepted. Please try signing in again."
}
```

#### Step 6E-1: Get The Token From The Login Response

1. Add `Get Dictionary Value`.
2. Set the key to:

`token`

3. Make sure the dictionary source is the `LoginResponse` variable from Step 6D.
4. Add `Set Variable`.
5. Name the variable:

`LoginToken`

#### Step 6E-2: Add The If Check

1. Add an `If` action below the `LoginToken` variable.
2. Set the condition to check whether `LoginToken` has any value.

Depending on your iOS version, this may look like one of these:

- `If LoginToken has any value`
- `If LoginToken is not empty`
- `If LoginToken is not [blank]`

The goal is simple:

- if `LoginToken` exists, login worked
- if `LoginToken` is blank, login failed

#### Step 6E-3: In The Failure Branch, Get The Error Message

Inside the branch where `LoginToken` is blank:

1. Add `Get Dictionary Value`.
2. Set the key to:

`detail`

3. Make sure the dictionary source is still `LoginResponse`.
4. Add `Set Variable`.
5. Name the variable:

`LoginError`

Yes, `detail` comes from the same dictionary as `token`. A successful login response has `token`; a failed login response has `detail`.

#### Step 6E-4: Show The Error To The User

Still inside the failure branch:

1. Add `Show Notification` or `Show Alert`.
2. Set the title to:

`ContentStash Sign-In Failed`

3. Set the body or message to the `LoginError` variable.

If Shortcuts will not let you use the variable in the notification body, use plain text instead:

`Sign-in failed. Please check your email and password, then try again.`

#### Step 6E-5: Ask For Email And Password Again

Still inside the failure branch, repeat the sign-in actions from Step 6A through Step 6E:

1. Add `Ask for Input` with the prompt `Email`.
2. Add `Ask for Input` with the prompt `Password`.
3. Add `Get Contents of URL` for `[BaseURL]/api/shortcut/login`.
4. Add `Get Dictionary from Input`.
5. Set that dictionary as `LoginResponse`.
6. Get `token` from `LoginResponse`.
7. If `token` is still blank, show the `detail` message again and stop the shortcut.

Stopping after the second failed attempt avoids trapping the user in an endless loop.

#### Step 6E-6: In The Success Branch, Continue

Inside the branch where `LoginToken` has a value, do nothing extra. Let the shortcut continue to Step 6F.

This matters because failed sign-in attempts return readable JSON instead of stopping the shortcut.

### Step 6F: Save The Login Response

1. Tap `Add Action`.
2. Search for `Save File`.
3. Add it below the dictionary action.
4. Save the file as:

`Shortcuts/ContentStashAuth.json`

5. Allow overwrite if prompted.

Why this matters:

- the shortcut can reuse the saved token later
- the user does not need to sign in every time

## Part 7: Read The Token Back Out

Once the auth file exists, the shortcut needs to extract the token field from it.

### Step 7A: Read The File As A Dictionary

1. Add `Get Dictionary from Input` after the auth file step or after the saved-file branch, depending on how your shortcut is organized.
2. Make sure it is reading from `ContentStashAuth.json`.

### Step 7B: Get The `token` Value

1. Tap `Add Action`.
2. Search for `Get Dictionary Value`.
3. Add it.
4. Set the key to:

`token`

5. Make sure the source is the auth dictionary.

### Step 7C: Save The Token As A Variable

1. Tap `Add Action`.
2. Search for `Set Variable`.
3. Name the variable:

`Token`

Now your later save requests can use `Token`.

## Part 8: Let The User Choose An Extraction Type

This menu is what the user sees every time they save a link.

1. Tap `Add Action`.
2. Search for `Choose from Menu`.
3. Set the prompt to:

`Extraction Type`

4. Add these menu items:
   - `Fast (Server)`
   - `Complete (Server)`
   - `Local (Browser)`

You will now create one save request inside each menu branch.

## Part 9: Add The Save Request For Each Menu Option

Each branch will look almost the same. Only the `extraction_type` value changes.

### Step 9A: Fast (Server)

Inside the `Fast (Server)` branch:

1. Add `Get Contents of URL`.
2. Set the URL to:

`[BaseURL]/api/shortcut/items`

3. Set `Method` to `POST`.
4. Add two headers:
   - `Content-Type` = `application/json`
   - `Authorization` = `Bearer [Token]`
5. Set the body type to `JSON`.
6. Add these JSON fields:
   - `url`
   - `extraction_type`
7. Set:
   - `url` = the `URL` variable
   - `extraction_type` = `fast`

### Step 9B: Complete (Server)

Inside the `Complete (Server)` branch:

1. Add `Get Contents of URL`.
2. Use the same URL:

`[BaseURL]/api/shortcut/items`

3. Use the same headers:
   - `Content-Type` = `application/json`
   - `Authorization` = `Bearer [Token]`
4. Use the same JSON body fields:
   - `url`
   - `extraction_type`
5. Set:
   - `url` = the `URL` variable
   - `extraction_type` = `complete`

### Step 9C: Local (Browser)

Inside the `Local (Browser)` branch:

1. Add `Get Contents of URL`.
2. Use the same URL:

`[BaseURL]/api/shortcut/items`

3. Use the same headers:
   - `Content-Type` = `application/json`
   - `Authorization` = `Bearer [Token]`
4. Use the same JSON body fields:
   - `url`
   - `extraction_type`
5. Set:
   - `url` = the `URL` variable
   - `extraction_type` = `local`

## Part 10: Handle Expired Sign-In Before Showing Success

The save endpoint is designed for Shortcuts. If the saved token is expired or no longer valid, it returns a normal JSON response that Shortcuts can read instead of stopping the workflow on a network error.

After each save request:

1. Add `Get Dictionary from Input`.
2. Add `Set Variable`.
3. Name the variable:

`SaveResponse`

4. Add `Get Dictionary Value`.
5. Set the key to:

`auth_required`

6. Make sure the dictionary source is `SaveResponse`.
7. Add `Set Variable`.
8. Name the variable:

`AuthRequired`

9. Add an `If` action.
10. Set the condition to check whether `AuthRequired` is true.

### Step 10A: If `AuthRequired` Is True, Delete The Saved Auth File

Inside the true branch of the `If` action:

1. Add `Get File`.
2. Set the path to:

`Shortcuts/ContentStashAuth.json`

3. If iOS shows an option like `Error If Not Found`, turn it off.
4. Add `Delete File`.
5. Make sure it deletes the file returned by the `Get File` action.
6. If iOS shows an option like `Delete Immediately` or asks whether to confirm deletion, choose the option that does not interrupt the shortcut every time.

This deletion is important. If the shortcut keeps `ContentStashAuth.json`, the next run will reuse the same expired token and hit the same auth-required response again.

### Step 10B: Show The Expired Sign-In Message

Still inside the true branch:

1. Add `Get Dictionary Value`.
2. Set the key to:

`detail`

3. Make sure the dictionary source is `SaveResponse`.
4. Add `Set Variable`.
5. Name the variable:

`SaveError`

6. Add `Show Notification` or `Show Alert`.
7. Set the title to:

`ContentStash Sign-In Expired`

8. Set the body or message to the `SaveError` variable.

If Shortcuts will not let you use the variable in the notification body, use plain text instead:

`Your ContentStash sign-in expired. Please sign in again.`

### Step 10C: Sign In Again And Retry Once

Still inside the true branch:

1. Run the sign-in actions from Step 6A through Step 6F again.
2. Get the new `token` value from the new saved login response.
3. Set the `Token` variable to that new token.
4. Retry the same save request once with `Authorization` set to `Bearer [Token]`.
5. Do not retry more than once. If the second save still returns `auth_required`, show the error and stop the shortcut.

### Step 10D: If `AuthRequired` Is Not True, Continue

Inside the false branch of the `If` action, do nothing extra. Let the shortcut continue to the success message.

The save response may also include `requires_login`. It means the same thing as `auth_required`, so use whichever key is easier to select in your Shortcuts editor.

The JSON looks like this when sign-in is needed:

```json
{
  "ok": false,
  "auth_required": true,
  "requires_login": true,
  "detail": "Your ContentStash sign-in expired. Please sign in again to continue saving."
}
```

## Part 11: Show A Success Message

After the menu finishes, add a simple confirmation message.

1. Tap `Add Action`.
2. Search for `Show Notification`.
3. Set the title to:

`Saved to ContentStash`

4. Set the body to:

`URL saved successfully`

This gives the user quick feedback that the shortcut ran.

## Part 12: Test The Shortcut

Now test it from Safari.

1. Open Safari on your iPhone.
2. Visit any article or page you want to save.
3. Tap the Share button.
4. Choose `Save to ContentStash`.
5. If this is your first run:
   - enter your email
   - enter your password
6. Choose an extraction type.
7. Wait for the success notification.
8. Open ContentStash and confirm the item appears.

## What Happens On Later Runs

After the first successful login:

- the shortcut should reuse the saved auth file
- the user should not be asked for email and password every time
- the user only chooses an extraction type and saves the link

## What To Do If Sign-In Stops Working Later

Tokens can expire eventually. If that happens, the shortcut should receive a response where `auth_required` is true.

The easiest fix is:

1. delete the saved auth file `Shortcuts/ContentStashAuth.json`
2. run the shortcut again
3. sign in again when prompted

For the smoothest shortcut, keep the recovery branch from Part 10 in place. It should:

1. detect `auth_required`
2. clears the saved auth file
3. asks the user to sign in again
4. retries the save once

## Common Mistakes To Watch For

### Using The Wrong URL

Use the main ContentStash app URL only.

- correct: `https://stash.example.com`
- incorrect: `https://stash.example.com/api/v1`
- incorrect: a separate backend host that the user was never meant to see

### Forgetting `Bearer ` In The Authorization Header

The `Authorization` header must begin with:

`Bearer `

There needs to be a space after `Bearer`.

### Saving The Wrong Variable In The JSON Body

Double-check:

- `url` uses the `URL` variable
- `Authorization` uses the `Token` variable
- `BaseURL` is used when building the request URL

### The Shortcut Does Not Show In The Share Sheet

Go back to the shortcut settings and confirm:

- `Show in Share Sheet` is turned on
- `URLs` is allowed
- `Safari Web Pages` is allowed

## Security Notes

This shortcut approach is much better than hardcoding a bearer token inside the shortcut, but it still stores sign-in information on the device in a local file.

That means:

- the setup is easier for normal users
- the user does not need to manually manage tokens
- but this is still not as secure or polished as a native iOS app with Keychain-backed authentication

Best practices:

- use a device passcode
- do not share the auth file with other people
- remove the auth file before handing your device to someone else

## Final Result

Once this is set up, the normal user experience is:

1. share a page
2. tap `Save to ContentStash`
3. sign in only if needed
4. choose an extraction type
5. continue browsing

That is a much simpler and more realistic workflow for non-technical users.

---

If anything in this guide feels too abstract while you are building the shortcut, open the helper page in your app at `/shortcuts/ios` and use it alongside this document.
