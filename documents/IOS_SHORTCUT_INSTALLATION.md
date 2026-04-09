# iOS Shortcut Installation Guide

This document is the simple overview. It explains what the shortcut is, what the user needs, and the order to follow during setup.

If you want the exact action-by-action Shortcuts instructions, read [`IOS_SHORTCUT_GUIDE.md`](./IOS_SHORTCUT_GUIDE.md).

## What This Shortcut Is For

The iOS shortcut gives iPhone and iPad users a simple way to send links into ContentStash from the Share Sheet.

That means a user can:

1. open an article, video, or page on their phone
2. tap the Share button
3. tap `Save to ContentStash`
4. choose how they want the content processed

## What Has Improved

The old setup was technical and easy to get wrong because users had to:

- find the backend URL manually
- open browser developer tools
- copy a token out of local storage
- paste that token into the shortcut with the `Bearer ` prefix

The new setup is much friendlier:

- the shortcut uses the normal ContentStash app URL
- the shortcut signs in with email and password
- the shortcut remembers that sign-in for later runs

In plain English, the goal is:

`install -> sign in once -> use normally`

## What The User Needs Before Starting

Before creating the shortcut, make sure the user has:

- an iPhone or iPad with the Shortcuts app
- a ContentStash account
- the ContentStash app URL
- a ContentStash deployment that is reachable from the phone

Examples of the app URL:

- `https://stash.example.com`
- `http://192.168.1.42:3000`

If the user is not sure which address to use, they should open:

- `/shortcuts/ios`

inside the ContentStash app. That page shows the correct base URL and the shortcut-specific endpoints.

## The Recommended Install Flow

For a non-technical user, the simplest order is:

1. open the helper page at `/shortcuts/ios`
2. confirm the main ContentStash app URL
3. create or install the shortcut
4. make sure the shortcut uses that app URL
5. run the shortcut once
6. sign in with email and password when prompted
7. start saving links from the Share Sheet

## What The Shortcut Will Save Internally

The shortcut keeps a small local file named:

`Shortcuts/ContentStashAuth.json`

This file stores the saved login response so the user does not need to sign in every time.

That is what makes the new flow feel smoother than the old manual token setup.

## The Two Main User Journeys

### First-Time Use

The first time the user runs the shortcut:

1. the shortcut asks for email
2. the shortcut asks for password
3. the shortcut sends those to the ContentStash login endpoint
4. the shortcut stores the returned auth information
5. the shortcut saves the shared URL

### Everyday Use

After that:

1. the user shares a URL
2. the shortcut reuses the saved auth file
3. the user chooses an extraction type
4. the save request is sent
5. the user sees a success notification

## What URL The Shortcut Should Use

This is one of the most important setup details.

The shortcut should use the main frontend app URL only.

Examples:

- correct: `https://stash.example.com`
- correct: `http://192.168.1.42:3000`
- incorrect: `https://stash.example.com/api/v1`
- incorrect: a separate backend host

The shortcut then builds the full requests automatically:

- login: `[BaseURL]/api/shortcut/login`
- save: `[BaseURL]/api/shortcut/items`

## Installation Options

There are two realistic ways to install this shortcut.

Important: option 2 is not a replacement for building the shortcut at least once. Someone has to create the shortcut first before there is anything to share.

### Option 1: Manual Creation In The Shortcuts App

This is the most reliable option today.

Use this when:

- you are setting up the shortcut for yourself
- you are testing locally
- you do not yet have a shared iCloud shortcut link ready

For this option, follow the full step-by-step build guide in [`IOS_SHORTCUT_GUIDE.md`](./IOS_SHORTCUT_GUIDE.md).

This manual build is also the step you use to create the first working version of the shortcut that can later be shared with other people.

### Option 2: Share A Prebuilt iCloud Shortcut Link

This is the best experience for end users once you are ready to distribute the shortcut more widely.

What "prebuilt iCloud shortcut link" means in plain language:

1. you manually create the shortcut first
2. you test it on your own device
3. once it is working, you open that shortcut in the Shortcuts app
4. you use the Shortcuts app share option to share the finished shortcut
5. Apple gives you an iCloud shortcut link that other people can open and install

So yes, option 2 depends on option 1 happening first. You cannot share a prebuilt shortcut link until someone has already built the shortcut and saved it in the Shortcuts app.

Use this when:

- you have a production deployment
- the app URL is stable
- you want the fewest manual steps for the user

The ideal experience becomes:

1. user opens the shortcut link
2. user installs it
3. user runs it
4. user signs in
5. user starts saving content

In other words:

- option 1 = create the shortcut
- option 2 = distribute the shortcut you already created

## Local Development Notes

If you are testing on your own local network, the phone must be able to reach the computer running the frontend app.

Example:

- frontend app on your computer: `http://192.168.1.42:3000`
- phone connected to the same Wi-Fi network

If the phone cannot open that address in Safari, the shortcut will not be able to use it either.

## Troubleshooting Summary

### The Shortcut Cannot Reach ContentStash

Check these first:

- is the app URL correct
- can the phone open that URL in Safari
- if self-hosting locally, are both devices on the same Wi-Fi

### The Shortcut Asks For Sign-In Again

This usually means the saved token expired or the saved auth file should be refreshed.

The easiest fix:

1. delete `Shortcuts/ContentStashAuth.json`
2. run the shortcut again
3. sign in again

### The Shortcut Does Not Appear In The Share Sheet

Check the shortcut settings and make sure:

- `Show in Share Sheet` is enabled
- `URLs` is allowed
- `Safari Web Pages` is allowed

## Security Notes

This setup is intentionally much easier for normal users, but it still has an important limitation:

- the shortcut stores sign-in information on the device in a local file

That is acceptable for a shortcut-based workflow, but it is still not as strong as a native iOS app using Apple’s secure credential storage.

## Best Recommendation

If you want the least confusing experience for a non-technical user:

1. host ContentStash on a stable production domain
2. create a shared iCloud shortcut with the app URL already filled in
3. send the user to `/shortcuts/ios` for reference
4. ask them to sign in the first time they run the shortcut

That is the most streamlined setup you can realistically get with Apple Shortcuts while staying inside the current web app architecture.

## Next Step

When you are ready to build the shortcut itself, follow the detailed recipe in [`IOS_SHORTCUT_GUIDE.md`](./IOS_SHORTCUT_GUIDE.md).
