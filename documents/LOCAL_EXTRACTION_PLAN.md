# Local Extraction & Quick Capture System - Implementation Plan

## Overview
This document outlines the technical plan for implementing a "Local Extraction" fallback system. This allows ContentStash to bypass server-side blocks (like YouTube or Paywalls) by leveraging a Desktop Chrome Extension as a "local agent" that extracts content using the user's browser session.

## Architecture

### 1. Data Flow & States
The system introduces a new state `pending_local_extraction` to the `SavedItem` lifecycle.

1.  **Capture**: User saves URL via **iOS Shortcut** or **Chrome Extension**.
2.  **Server Attempt**: Backend attempts extraction (`process_item_background`).
3.  **Block Detection**: If server detects a block (403 Forbidden, YouTube Bot Detection), it updates status to `pending_local_extraction` (instead of `failed`).
4.  **Local Poll**: Chrome Extension (Background Service Worker) polls `GET /items/pending-local` periodically.
5.  **Local Extraction**: Extension opens the URL in an offscreen/background tab, executes content extraction script.
6.  **Upload**: Extension uploads result via `PATCH /items/{id}/content`.
7.  **Finalize**: Server receives content, generates embeddings/AI tags, and sets status to `processed`.

## Phase 1: Backend Updates

### 1.1 Model Updates (`backend/app/models/saved_item.py`)
-   Update `processing_status` Enum to include `pending_local_extraction`.
-   Update `extraction_type` Enum/Pattern to include `local`.

### 1.2 API Endpoints (`backend/app/routers/items.py`)
-   **New Endpoint**: `GET /items/pending-local`
    -   Returns list of items owned by user with status `pending_local_extraction`.
-   **New Endpoint**: `PATCH /items/{item_id}/content`
    -   Accepts `{ "content": "...", "extraction_type": "local_extension" }`.
    -   Updates `archived_text`.
    -   Triggers post-processing (Embeddings, AI Tags) immediately.

### 1.3 Logic Updates (`backend/app/services/background.py` & `extraction.py`)
-   **Force Local**: If `extraction_type == "local"`, `process_item_background` skips server extraction and immediately sets status to `pending_local_extraction`.
-   **Auto Fallback**: Refine `extract_content` to identify "hard blocks" vs "soft errors".
    -   *YouTube*: If `yt-dlp` and API fail, return specific `ExtractionBlockError`.
    -   *Web*: If status code is 403/401, return `ExtractionBlockError`.
-   Update `process_item_background` to catch `ExtractionBlockError` and set status to `pending_local_extraction`.

## Phase 2: Chrome Extension (New Project)

### 2.1 Project Structure
-   **Tech Stack**: React + Vite (for Popup/Options), TypeScript.
-   **Manifest V3**.

### 2.2 Core Components
-   **Popup**:
    -   Login Screen (Email/Password -> JWT).
    -   **Quick Save Interface**:
        -   "Save Current Tab" button.
        -   **Extraction Type Dropdown**: "Fast (Server)", "Complete (Server)", "Local (Browser)".
            -   *Local* bypasses server and uses browser extraction immediately.
    -   **Manual Control**:
        -   "Process Pending Items" button (manual trigger for local extraction queue).
    -   Status indicator ("3 items pending extraction...").
-   **Settings Page**:
    -   **Polling Interval**: Input for minutes (default 15).
    -   **Enable Background Polling**: Toggle switch (default On).
-   **Background Service Worker**:
    -   Maintains JWT state.
    -   Polls server based on user settings.
    -   Orchestrates tab creation for extraction.
-   **Content Script**:
    -   **Generic**: Runs `readability` logic in browser context.
    -   **YouTube**: Targeted DOM selectors to expand description/transcript.

### 2.3 Local Extraction Logic (Background)
-   When `pending` items are found:
    1.  Create a tab (pinned, non-focused, or offscreen document).
    2.  Inject Content Script.
    3.  Wait for message with extracted content.
    4.  Send to Server.
    5.  Close Tab.

## Phase 3: iOS Shortcut
-   Simple shortcut using "Get Contents of URL" (POST request).
-   Prompts user for API Key (one-time setup) or hardcoded server URL.

## Security Considerations
-   **Authentication**: Extension must securely store JWT.
-   **CORS**: Update Backend CORS settings to allow requests from the Extension ID.