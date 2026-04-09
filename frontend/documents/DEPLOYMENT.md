# ContentStash Deployment Guide

This guide is written for a first-time deployment.

We are deploying:

- Frontend: **Vercel Hobby**
- Backend: **Render free web service**
- Database: **MongoDB Atlas M0**

The goal is to get the app live on platform URLs first:

- Frontend: `https://<your-project>.vercel.app`
- Backend: `https://<your-backend>.onrender.com`

If some screen labels differ slightly in the UI, that is normal. The services change small bits of wording over time, but the overall flow should still match this guide.

---

## Before You Start

Set aside:

- Best case: 2 hours
- Typical first-time setup: 3 to 4 hours
- If we hit debugging issues: 4 to 5 hours

Have these ready before you start:

- Your GitHub repo already pushed to `main`
- Your Gemini API key
- Access to your MongoDB Atlas account
- Access to your Render account
- Access to your Vercel account

Keep a text note open while you work. You will want to temporarily save these values as you create them:

- Atlas connection string
- Atlas database username
- Atlas database password
- Render backend URL
- Vercel frontend URL
- JWT secret

---

## What Happens Automatically After Setup

Once this is fully connected:

- Every push to `main` on GitHub will automatically redeploy the frontend on Vercel
- Every push to `main` on GitHub will automatically redeploy the backend on Render
- MongoDB Atlas does not deploy from GitHub; it just stays live as the database

---

## Part 1: Prepare MongoDB Atlas

If you are already using MongoDB Atlas, you may be able to reuse your current project and cluster.

### 1. Open Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Sign in
3. Open the project you want to use for ContentStash

### 2. Make sure you have an M0 cluster

1. In the left sidebar, click **Database**
2. Look for your cluster
3. If you do not have one yet:
   - click **Create**
   - choose the **M0 Free** option
   - pick a provider/region
   - wait for the cluster to finish creating

### 3. Create or confirm a database user

1. In the left sidebar, click **Security**
2. Click **Database Access**
3. Click **Add New Database User**
4. Choose **Password** authentication
5. Enter:
   - username: something simple like `contentstash-app`
   - password: use a strong password and save it in your notes
6. For privileges, keep the default read/write access unless you know you want something stricter
7. Click **Add User**

Save this now:

- Atlas database username
- Atlas database password

### 4. Allow incoming connections

1. In the left sidebar, click **Security**
2. Click **Network Access**
3. Click **Add IP Address**
4. Choose **Allow Access from Anywhere**
5. Confirm the value is `0.0.0.0/0`
6. Add a short comment if you want
7. Click **Confirm**

This is the simplest way to get Render connected for the first deployment.

### 5. Copy your connection string

1. Go back to **Database**
2. Find your cluster
3. Click **Connect**
4. Choose **Drivers**
5. Copy the connection string that starts with:

```bash
mongodb+srv://...
```

It will look something like:

```bash
mongodb+srv://<username>:<password>@clustername.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

Replace:

- `<username>` with your Atlas database username
- `<password>` with your Atlas database password

Save the final full string in your notes. You will paste it into Render as:

```bash
MONGODB_URI
```

---

## Part 2: Create the Backend on Render

This backend is the FastAPI service. Render will run it for you.

### 1. Open Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Sign in

### 2. Start creating a new service

1. Click **New +**
2. Choose **Blueprint** if Render offers to deploy from `render.yaml`
3. If you do not see Blueprint as an option, choose **Web Service**
4. Connect your GitHub account if Render asks
5. Select the `ContentStash` GitHub repository

### 3. Use the repo settings from `render.yaml`

This repo already includes a Render config file at the root:

- [`render.yaml`](../../render.yaml)

If Render detects it:

1. Let Render use the Blueprint settings
2. Confirm the service name is something like `contentstash-backend`
3. Confirm the branch is `main`
4. Confirm the plan is `free`

If Render instead shows you a manual service form, use these values:

- **Name**: `contentstash-backend`
- **Runtime**: `Python`
- **Branch**: `main`
- **Root Directory**: `backend`
- **Build Command**: `./render-build.sh`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 4. Add backend environment variables

Find the section called something like:

- **Environment Variables**
- or **Add Environment Variable**
- or **Secret Files and Env Vars**

Add each of these one by one.

#### Required backend variables

```bash
MONGODB_URI=<paste your full Atlas connection string here>
JWT_SECRET=<paste a long random secret here>
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=<paste your Gemini API key here>
APP_ENV=production
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/backend/ms-playwright-browsers
```

#### Optional backend variable

```bash
YOUTUBE_API_KEY=<your YouTube API key, if you have one>
```

### 5. How to make a JWT secret

If you do not already have one, use any strong random string at least 32 characters long.

Example format:

```bash
JWT_SECRET=replace-this-with-a-very-long-random-secret-value
```

Save this in your notes too.

### 6. Start the deploy

1. Click **Create Web Service**
2. Or click **Deploy**
3. Wait while Render runs the build

The first deploy may take a while because it needs to install Python packages and Playwright Chromium.

### 7. Watch the logs

In Render:

1. Click into the service
2. Open the **Logs** tab
3. Watch for:
   - Python dependency install
   - Playwright Chromium install
   - startup logs

What you want to see:

- build completes successfully
- service starts successfully
- health check passes

### 8. Copy the backend URL

Once the service is live, Render will show a public URL.

It will look like:

```bash
https://contentstash-backend.onrender.com
```

Save it in your notes.

### 9. Test the backend directly

Open these in your browser:

1. Backend root:

```bash
https://<your-render-backend>.onrender.com/
```

2. Health check:

```bash
https://<your-render-backend>.onrender.com/healthz
```

What you want:

- the root URL shows basic API info
- `/healthz` returns JSON
- ideally `database` says `connected`

If the backend is sleeping, the first request may take a little while on the free tier.

---

## Part 3: Create the Frontend on Vercel

This is the Next.js app your users will open in the browser.

### 1. Open Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Sign in

### 2. Create a new project

1. Click **Add New...**
2. Click **Project**
3. Import your GitHub repository
4. If Vercel asks for GitHub access, approve it

### 3. Configure the project

When Vercel shows the project settings:

1. Confirm framework is detected as **Next.js**
2. Find **Root Directory**
3. Set **Root Directory** to:

```bash
frontend
```

### 4. Add the frontend environment variable

Find the area labeled:

- **Environment Variables**
- or **Build and Output Settings**

Add this:

**Name**

```bash
NEXT_PUBLIC_API_URL
```

**Value**

```bash
https://<your-render-backend>.onrender.com/api/v1
```

Important:

- it must include `/api/v1`
- use your actual backend URL from Render

### 5. Deploy

1. Click **Deploy**
2. Wait for Vercel to build and publish the frontend

### 6. Copy the frontend URL

It will look like:

```bash
https://<your-project>.vercel.app
```

Save it in your notes.

---

## Part 4: Finish CORS Setup on Render

Now that the frontend URL exists, we need to tell the backend to allow it.

### 1. Go back to Render

1. Open the backend service
2. Click **Environment**
3. Find the variable:

```bash
CORS_ORIGINS
```

### 2. Update the value

Change it from:

```bash
http://localhost:3000
```

To:

```bash
http://localhost:3000,https://<your-vercel-project>.vercel.app
```

Use your real Vercel URL.

### 3. Save and redeploy

1. Save the environment variable
2. If Render does not automatically redeploy, click **Manual Deploy**
3. Choose the latest commit on `main`

Wait for the backend to finish redeploying.

---

## Part 5: Smoke Test the Whole App

Open your Vercel URL and test in this order.

### 1. Open the app

Go to:

```bash
https://<your-project>.vercel.app
```

Make sure:

- the page loads
- login page works
- register page works

### 2. Create an account

1. Register a new test account
2. Log in
3. Refresh the page

Make sure:

- you stay logged in
- protected pages still load

### 3. Save pasted content

1. Paste some content into the app
2. Save it

Make sure:

- the item appears in your library

### 4. Save a URL

1. Save a normal article URL
2. Wait for processing

Make sure:

- preview works
- item eventually appears as processed

### 5. Test chat or search

If Atlas vector search is already configured:

1. Ask a question about saved content
2. Confirm you get an answer

If this part fails, the rest of the deployment can still be considered mostly successful. We can debug vector search after the core app is live.

---

## Part 6: Confirm Automatic Deployments

### Vercel

To confirm Vercel auto-deploy is on:

1. Open the Vercel project
2. Click **Settings**
3. Click **Git**
4. Confirm:
   - the connected branch is `main`
   - automatic deployments are enabled

### Render

To confirm Render auto-deploy is on:

1. Open the Render backend service
2. Click **Settings**
3. Look for the Git or deploy settings
4. Confirm:
   - the branch is `main`
   - auto-deploy is enabled

The repo’s `render.yaml` already sets:

```yaml
branch: main
autoDeployTrigger: commit
```

That means new commits pushed to `main` should trigger backend deploys automatically.

---

## Common Problems and What to Check

### Problem: backend says database disconnected

Check:

1. Atlas Network Access includes `0.0.0.0/0`
2. Atlas database username/password are correct
3. The password in the connection string is correct
4. You pasted the connection string into `MONGODB_URI`, not somewhere else

### Problem: frontend cannot talk to backend

Check:

1. `NEXT_PUBLIC_API_URL` in Vercel includes `/api/v1`
2. `CORS_ORIGINS` in Render includes the exact Vercel URL
3. You redeployed after changing env vars

### Problem: first request is very slow

This is expected on Render free services.

The backend sleeps after inactivity and wakes up on the next request.

### Problem: URL extraction fails

Go to Render:

1. Open the backend service
2. Click **Logs**
3. Look for:
   - Playwright errors
   - Chromium launch errors
   - timeouts

### Problem: login or signup fails

Check:

1. Render backend is healthy
2. MongoDB Atlas is connected
3. Browser devtools network tab shows whether it is a 401, 422, 500, or CORS error

---

## After This Is Working

Once the first deployment works, your normal workflow becomes simple:

1. make a change locally
2. commit it
3. push to `main`
4. Vercel redeploys the frontend automatically
5. Render redeploys the backend automatically

---

## Official Docs

- Vercel docs: [vercel.com/docs](https://vercel.com/docs)
- Render docs: [render.com/docs](https://render.com/docs)
- MongoDB Atlas docs: [mongodb.com/docs/atlas](https://www.mongodb.com/docs/atlas/)
