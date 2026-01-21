# Refined Project Idea: Quick Capture & Local Fallback System

**App Description**: A seamless "Quick Capture" system for ContentStash that simplifies saving content from any device while robustly handling server-side blocks. It includes a Desktop Chrome Extension and iOS Shortcut for instant URL capture, with the Chrome Extension acting as a "Local Extraction Agent" to process blocked content (YouTube, Paywalls) using your local browser's access.

**Target Users**: Single-user personal knowledge base (You).

**Core Features**:
1.  **Desktop Chrome Extension**:
    *   **Quick Capture**: Save current page instantly without manual copy-pasting.
    *   **Local Extraction Agent**: Automatically identifies items that failed server-side extraction (due to blocks/paywalls) and re-processes them locally using your browser's cookies/IP.
2.  **iOS Share Sheet Shortcut**: A simple "Save to ContentStash" shortcut that captures URLs from any app and sends them to your server for initial processing.
3.  **Intelligent Fallback Workflow**:
    *   **Primary**: Server attempts extraction first.
    *   **Fallback**: If server is blocked (e.g., YouTube bot detection), the item is flagged for the Desktop Extension to process in the background.

**Technical Requirements**:
*   **Frontend**: Chrome Extension (Manifest V3) using React/TypeScript.
*   **Mobile**: iOS Shortcut file (.shortcut) configured for your API.
*   **Backend**: Update extraction logic to handle "Partial/Pending" states and accept updates from the local extension.