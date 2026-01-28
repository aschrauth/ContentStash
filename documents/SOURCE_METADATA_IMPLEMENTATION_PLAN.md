# Source Metadata Implementation Plan

This document outlines the plan to add a "source" field to saved items in ContentStash. This field will store the origin of the content (e.g., "nytimes.com", "YouTube | Channel Name", or "Pasted Content").

## 1. Backend Implementation

### 1.1. Data Model Updates
**File:** `backend/app/models/saved_item.py`

*   **Changes:**
    *   Add `source: Optional[str] = Field(None, max_length=100)` to `SavedItemBase`.
    *   Update `SavedItemUpdate` to include `source: Optional[str] = Field(None, max_length=100)`.

### 1.2. Service Updates

#### Extraction Service
**File:** `backend/app/services/extraction.py`

*   **Changes:**
    *   Update `extract_content_with_metadata` to return a `source` field in its dictionary.
    *   Logic for web pages:
        *   Parse the domain from the URL.
        *   If subdomain is "www", use `domain.com`.
        *   Otherwise, use `subdomain.domain.com`.
    *   Logic for YouTube (inside `extract_content_with_metadata` or helper):
        *   If it's a YouTube URL, format source as `"YouTube | {Channel Name}"`.

#### YouTube Service
**File:** `backend/app/services/youtube.py`

*   **Changes:**
    *   Ensure `get_video_metadata_from_api` and `get_video_metadata_from_ytdlp` return `channel_name` reliably (they already do).
    *   No major structural changes needed here, just ensuring the consumer (extraction service) uses the channel name to format the source string.

### 1.3. API Router Updates
**File:** `backend/app/routers/items.py`

*   **Changes:**
    *   **`create_item`:**
        *   If `url` is provided:
            *   Extract initial source from URL (domain) immediately for the API response, before background processing.
            *   Pass this initial source to the `SavedItem` constructor.
        *   If `url` is NOT provided (Pasted Content):
            *   Accept `source` from `item_data` if provided (user input).
            *   Default to `"Pasted Content"` if not provided.
    *   **`update_item`:**
        *   Allow updating the `source` field via `SavedItemUpdate`.
    *   **Background Processing (implicit):**
        *   Ensure `process_item_background` (in `backend/app/services/background.py` - need to verify if this needs changes or if it just uses `extract_content_with_metadata` result) updates the item with the refined source (e.g., getting the YouTube channel name after API call).

### 1.4. Data Migration
**File:** `backend/migrate_source_field.py` (New File)

*   **Purpose:** Populate `source` for existing items.
*   **Logic:**
    *   Iterate through all items in `saved_items` collection.
    *   If `source` is missing:
        *   If `url` exists:
            *   If YouTube URL: Try to extract channel name from existing metadata/description or default to "YouTube".
            *   If Web URL: Extract domain (e.g., "nytimes.com").
        *   If `url` is missing: Set to "Pasted Content".
    *   Update the document.

## 2. Frontend Implementation

### 2.1. Store Interface
**File:** `frontend/lib/store.ts`

*   **Changes:**
    *   Add `source?: string;` to the `SavedItem` interface.

### 2.2. Save Modal
**File:** `frontend/components/SaveModal.tsx`

*   **Changes:**
    *   **"Paste Content" Tab:**
        *   Add an input field for "Source" (optional).
        *   Placeholder: "e.g., Book Excerpt, Meeting Notes".
    *   **Logic:**
        *   When submitting pasted content, include the `source` value (or "Pasted Content" if empty) in the API call.
        *   For URLs, the backend handles extraction, so no manual input needed usually, but we could display the extracted domain in the preview if desired.

### 2.3. Item Card (List/Grid View)
**File:** `frontend/components/ItemCard.tsx`

*   **Changes:**
    *   Display the `item.source` field.
    *   **Design:**
        *   Place it near the date or extraction status.
        *   Style it subtly (e.g., small text, slate-400).
        *   Example: `nytimes.com • Jan 28, 2026`

### 2.4. Item Detail View
**File:** `frontend/app/items/[id]/page.tsx`

*   **Changes:**
    *   **Display:** Show the `source` prominently in the header area (e.g., above the title or next to the date).
    *   **Editing:**
        *   When "Edit" mode is active, provide an input field to modify the `source`.
    *   **Functionality:**
        *   Include `source` in the `handleSaveMetadata` function.

## 3. Implementation Order

1.  **Backend Models & Migration:** Add the field and migrate existing data.
2.  **Backend Services:** Implement logic to extract source from URLs/YouTube.
3.  **Backend API:** Ensure endpoints handle read/write of the new field.
4.  **Frontend Store:** Update types.
5.  **Frontend UI:** Update Display (Card/Detail) and Creation (Modal).

## 4. Edge Cases & Considerations

*   **YouTube Shorts/Live:** Ensure URL parsing handles all YouTube variants.
*   **Subdomains:**
    *   `www.example.com` -> `example.com`
    *   `blog.example.com` -> `blog.example.com`
    *   `platform.substack.com` -> `platform.substack.com`
*   **Empty Source:** Migration script should ensure no item is left with null source.
*   **User Overrides:** If a user manually edits the source, subsequent background re-processing should NOT overwrite their manual change (unless explicitly requested). *Self-correction: The current background processing usually updates metadata. We might need a flag `source_manually_edited` or just accept that "Reprocess" resets metadata.* -> *Decision: Keep it simple. Reprocessing re-extracts everything.*