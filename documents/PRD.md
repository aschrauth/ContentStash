# PRODUCT REQUIREMENTS DOCUMENT

**Product Name:** Stash  
**Version:** 1.0 MVP  
**Owner:** Anthony  
**Platform:** Web Application (Responsive, Desktop & Mobile Browser)  
**Target Delivery:** 48-72 hour build sprint

---

## EXECUTIVE SUMMARY

**Product Vision:**  
Stash is a personal knowledge base that helps people save, organize, and rediscover content from the web and their own AI conversations. It transforms scattered links, transcripts, and threads into a searchable, chat-first "second brain" with automatic categorization and citation-backed answers.

**Core Purpose:**  
Solves the problem of saved content becoming unfindable and losing context. People bookmark valuable articles, videos, podcasts, and ChatGPT threads but cannot reliably retrieve them later or remember why they mattered. Traditional bookmarking is link-first and context-light; search is mostly keyword-based.

**Target Users:**  
Primary: Knowledge workers (product managers, researchers, strategists) who consume 10-15 pieces of content weekly and need to build a searchable library with personal context.

**Key MVP Features:**
- **Content Saving** (User-Generated) - Save URLs or pasted content with auto-fetched metadata
- **Smart Organization** (User-Generated) - Hashtag tagging with autocomplete, AI-suggested tags and topics
- **Personal Notes** (User-Generated) - Markdown-formatted annotations on saved items
- **Library Management** (User-Generated) - Grid/list view with tag filtering, sorting, and search
- **Chat-Based Search** (System/AI) - Ask questions and get answers with citations and excerpts
- **User Authentication** (System/Configuration) - Secure registration, login, profile management

**Platform:** Web application (responsive design, works on all devices via browser)

**Complexity Assessment:** Moderate
- **State Management:** Frontend state with localStorage persistence + simulated backend
- **External Integrations:** Simulated AI/RAG features (Gemini-like responses), URL metadata extraction
- **Business Logic:** Moderate - content chunking simulation, tag autocomplete, search ranking, chat context

**MVP Success Criteria:**
- Users can save content (URL or paste) and see it appear immediately with processing status
- Auto-suggested tags and topics appear after "processing" completes
- Users can accept/edit suggestions and add manual tags with autocomplete
- Keyword search returns results instantly across titles, descriptions, notes, and archived text
- Chat interface provides answers with citations and excerpts from saved library
- Tag filtering and sorting work smoothly with visual feedback
- Responsive design functions on mobile, tablet, and desktop

---

## 1. USERS & PERSONAS

**Primary Persona: Alex the Knowledge Worker**
- **Context:** Product manager reading 10-15 articles weekly about product strategy, UX, and industry trends. Currently saves links across browser bookmarks, notes apps, Slack, and ChatGPT threads with no unified system.
- **Goals:** Build a searchable library of insights and examples. Add personal context and takeaways to each item. Quickly retrieve relevant content when working on specific projects. Connect related ideas across multiple sources.
- **Pain Points:** Bookmarks lack context and are hard to search. Saved items disappear into a "black hole." Cannot remember why something was important weeks later. Switching between note-taking apps and bookmarks is cumbersome. Keyword search fails when exact phrases aren't remembered.

**Secondary Persona: Riley the Researcher**
- **Context:** Collects long-form sources and wants to ask synthesis questions like "What did I save about pricing experiments in B2B?"
- **Goals:** Ask questions and get structured answers backed by sources. Capture and reuse excerpts and citations in documents and presentations.
- **Pain Points:** Manual scanning is slow. Hard to connect related ideas across multiple sources. Search results don't explain why something is relevant.

---

## 2. FUNCTIONAL REQUIREMENTS

### 2.1 Core MVP Features (Priority 0)

**FR-001: User Authentication**
- **Description:** Secure user registration, login, session management, profile viewing and editing
- **Entity Type:** System/Configuration
- **Operations:** Register, Login, View profile, Edit profile (name/email), Reset password, Logout
- **Key Rules:** Passwords securely hashed. Sessions persist across browser sessions. Email must be unique and valid format. Minimum 8 characters for passwords.
- **Acceptance:** Users can register with email/password, log in, view/edit their profile, reset password, and log out securely

**FR-002: Save Content with Auto Metadata**
- **Description:** Save URLs or pasted content. For URLs, system fetches title, description, and preview image. For pasted content, user provides title and system generates short description.
- **Entity Type:** User-Generated Content
- **Operations:** Create, View, Edit (URL, title, description, image, content type, notes, tags), Delete (hard delete after confirmation), List/Search, Export
- **Key Rules:** URL must be valid format. Metadata fetch simulated with 1-3 second delay. User can override auto-fetched fields. Processing status: pending → processed/failed. Max 500 chars for title, 2000 for description. Deleted items are permanently removed after user confirmation.
- **Acceptance:** User pastes URL, sees metadata preview within 3 seconds, can save. User pastes text with title, can save. Item appears immediately in library with visible processing status.

**FR-003: Hashtag Tagging with Autocomplete**
- **Description:** Add tags by typing hashtags (#design, #research) with real-time autocomplete suggesting previously used tags
- **Entity Type:** User-Generated Content
- **Operations:** Create tags (via hashtag typing), View tags on items, Edit tags (add/remove), Remove tags from item, List all user tags
- **Key Rules:** Tags created on-the-fly when typing #. Autocomplete shows max 10 suggestions sorted by frequency. Case-insensitive. Max 20 tags per item. Tag names 2-50 characters.
- **Acceptance:** Users type #, see suggestions, select or create new tag, tags save with item, tags can be removed

**FR-004: AI-Suggested Tags and Topics**
- **Description:** After content processing, system proposes 3-7 tags and a single topic label based on content and user's existing tag vocabulary
- **Entity Type:** User-Generated Content (suggestions)
- **Operations:** View suggestions, Accept all suggestions, Accept individual tags, Reject suggestions, Edit accepted tags
- **Key Rules:** Suggestions appear after processing completes. Not automatically applied - user must accept. Prefer existing tags for consistency. "Apply all" button plus per-tag accept/reject. Accepted suggestions become normal tags.
- **Acceptance:** Suggested tags and topic appear on item detail after processing. User can apply all in one click or selectively accept. Accepted tags behave like manual tags for filtering and autocomplete.

**FR-005: Personal Notes with Markdown**
- **Description:** Write personal annotations on saved items using Markdown (bold, italic, lists)
- **Entity Type:** User-Generated Content
- **Operations:** Create notes, View rendered notes, Edit notes (preserve history), Clear notes content, Export notes
- **Key Rules:** Markdown rendered in view mode. Edit mode shows raw Markdown. Auto-save on blur. Support bold, italic, lists, headings, links. Max 50,000 characters.
- **Acceptance:** Users write notes in Markdown, see formatted preview, edit existing notes, notes persist and auto-save

**FR-006: Library View with Tag Filtering**
- **Description:** Grid/list view of saved items with tag filtering, sorting, and view mode toggle
- **Entity Type:** User-Generated Content
- **Operations:** View all items, Filter by single/multiple tags (AND logic), Sort (newest, oldest, title A-Z), Toggle grid/list view, Bulk select for delete
- **Key Rules:** Default sort newest first. Multiple tag filters use AND logic. Empty states show helpful prompts. Pagination at 50 items. Processing status visible on cards.
- **Acceptance:** Users filter by tags, change sort order, switch grid/list view, see processing status, bulk delete items

**FR-007: Keyword Search (Full-Text)**
- **Description:** Real-time search across titles, descriptions, notes, tags, and archived text
- **Entity Type:** System Data
- **Operations:** Search (real-time as user types), View results, Clear search, Export search results
- **Key Rules:** Minimum 2 characters. Case-insensitive. Results ranked by relevance (title > tags > notes > content). Max 100 results. Highlight matched terms.
- **Acceptance:** Users type query, see matching items instantly with highlighted terms. Clearing search returns to full library.

**FR-008: Item Detail View with Editing**
- **Description:** Full-page view showing metadata, notes, tags, suggested tags/topic, and archived content with inline editing
- **Entity Type:** User-Generated Content
- **Operations:** View full details, Edit title/description/URL/image, Edit notes, Add/remove tags, Accept/reject suggestions, Delete item, View archived content
- **Key Rules:** All editable fields auto-save. Original URL preserved. Show created/updated timestamps. Archived content read-only. Processing status visible. Reprocess button if failed.
- **Acceptance:** Users open item, edit fields inline, changes persist, can delete with confirmation, see suggestions and archived content

**FR-009: Content Extraction and Archival (Simulated)**
- **Description:** For URLs, simulate fetching page and extracting main readable content. For pasted content, use paste as archived text.
- **Entity Type:** System Data
- **Operations:** Extract (simulated), Store archived text, View archived text, Reprocess, Mark failed, Manual fallback paste
- **Key Rules:** Extraction simulated with 2-5 second delay. Best-effort simulation - some URLs marked as "failed" randomly (10% failure rate). Store enough content for search and citations. Show processing metadata: extracted length, chunk count, errors.
- **Acceptance:** For typical article URL, archived text visible in detail view after processing. Keyword search finds phrases in archived text. Processing errors visible with "Paste content manually" fallback.

**FR-010: Chat-Based Search with Citations (Simulated RAG)**
- **Description:** Persistent chat overlay where users ask questions and receive answers grounded in their saved library with citations and excerpts
- **Entity Type:** System/AI
- **Operations:** Ask question, View answer with citations, View excerpts, Open cited items, Follow-up questions (thread context), Clear chat, Start new thread
- **Key Rules:** Answers based only on user's library (simulated). Include direct answer + "Sources" section + 1-3 quoted excerpts. Links to open item detail. Maintain thread history for follow-ups. If confidence low, suggest alternative queries or tags.
- **Acceptance:** User asks "What did I save about onboarding checklists?", receives synthesized answer with citations and excerpts. Follow-up questions use thread context. Can open cited items directly.

---

## 3. USER WORKFLOWS

### 3.1 Primary Workflow: Save and Rediscover via Chat

**Trigger:** User finds valuable content and wants to save it with context  
**Outcome:** User saves content, sees it categorized, later retrieves it through chat with cited sources

**Steps:**
1. User clicks "Save" button in main navigation and enters URL or pastes content
2. System fetches metadata (simulated 1-3 sec delay) and shows preview with editable fields
3. User adds personal notes in Markdown and optional manual tags using # autocomplete
4. User clicks "Save" - item appears immediately in library with status "pending"
5. System simulates extraction (2-5 sec), generates archived text, updates status to "processed" or "failed", and generates suggested tags/topic
6. User later opens persistent "Ask Stash" chat overlay and asks question
7. System retrieves relevant chunks (simulated) and returns answer with sources and excerpts
8. User clicks cited item to open detail view, reviews archived content, adds/edits notes and tags

### 3.2 Key Supporting Workflows

**Register Account:** User navigates to /register → fills email/password → account created → redirected to library

**Login:** User enters credentials at /login → session created → redirected to library

**Edit Saved Item:** User opens item detail → clicks edit on any field → modifies → auto-saves on blur

**Delete Saved Item:** User selects item(s) → clicks delete → confirms → permanently deleted

**Filter by Tags:** User clicks tag pill in library → items filter to show only those with tag → can add multiple tags (AND logic)

**Keyword Search:** User types in search box → results update in real-time → matched terms highlighted → user opens item

**Accept Suggestions:** User opens item with suggestions → clicks "Apply all" or individual tag accepts → suggestions become normal tags

**Reprocess Extraction:** User sees "failed" status → clicks "Reprocess" → system reruns extraction simulation

---

## 4. BUSINESS RULES

### 4.1 Entity Lifecycle Rules

| Entity | Type | Who Creates | Who Edits | Who Deletes | Delete Action |
|--------|------|-------------|-----------|-------------|---------------|
| User | System/Config | Self (registration) | Self | Self | Hard delete + cascade all data |
| SavedItem | User-Generated | Owner | Owner (metadata, notes, tags) | Owner | Hard delete (permanent) |
| Tag | User-Generated | Owner (manual or accepted) | Owner (add/remove from items) | Owner (remove from item) | Removing from item doesn't delete globally |
| Note | User-Generated | Owner | Owner | Owner | Clear content, preserve history |
| ContentChunk | System Data | System (processing) | System only | System (with item) | Deleted with parent item |
| ChatThread | System Data | Owner (new chat) | System (messages) | Owner (optional) | Hard delete thread + messages |
| ChatMessage | System Data | System (user/assistant) | None | With thread | Deleted with parent thread |

### 4.2 Data Validation Rules

| Entity | Required Fields | Key Constraints |
|--------|-----------------|-----------------|
| User | email, password | Email unique and valid format, password min 8 chars |
| SavedItem | ownerId, title, (url OR pastedContent) | Title max 500 chars, description max 2000 chars, valid URL format if provided |
| Tag | name, ownerId | Name 2-50 chars, case-insensitive, max 20 tags per item |
| Note | ownerId, savedItemId | Max 50,000 chars, Markdown allowed |
| ContentChunk | savedItemId, chunkText | Max chunk size for performance, overlap for context |

### 4.3 Access & Process Rules

- Users can only view, edit, and delete their own data (all entities scoped by ownerId)
- Metadata fetching simulated with 1-3 second delay, 5% random failure rate
- Content extraction simulated with 2-5 second delay, 10% random failure rate
- Autocomplete shows max 10 tag suggestions, sorted by usage frequency
- Search requires minimum 2 characters, returns max 100 results ranked by relevance
- Deleted items are permanently deleted immediately after user confirmation
- Processing errors must be visible with recovery path (reprocess, manual paste)
- Chat responses limited to 500 words with 3-5 citations maximum

---

## 5. DATA REQUIREMENTS

### 5.1 Core Entities

**User**
- **Type:** System/Configuration | **Storage:** localStorage
- **Key Fields:** id, email, passwordHash, name, createdAt, updatedAt, preferences (viewMode: grid/list, sortOrder: newest/oldest/title)
- **Relationships:** has many SavedItems, has many Tags (via items), has many ChatThreads
- **Lifecycle:** Full CRUD with export and account deletion (cascade delete all user data)

**SavedItem**
- **Type:** User-Generated Content | **Storage:** localStorage with cache for recent items
- **Key Fields:** id, ownerId, contentType (article/video/podcast/chat/note/unknown), url (optional), title, description, imageUrl, faviconUrl, notesMarkdown, notesHistory, tags (array of accepted tag names), suggestedTags (array), suggestedTopic, suggestedSummary, archivedText, processingStatus (pending/processed/failed), processingError, createdAt, updatedAt
- **Relationships:** belongs to User, has many ContentChunks, has many Tags
- **Lifecycle:** Full CRUD + hard delete (permanent) + export

**Tag**
- **Type:** User-Generated Content | **Storage:** localStorage (derived from SavedItems or separate registry)
- **Key Fields:** ownerId, name, usageCount, firstUsedAt, lastUsedAt
- **Relationships:** belongs to User, used by many SavedItems
- **Lifecycle:** Create (via hashtag), view, remove from items (doesn't delete globally if used elsewhere)

**ContentChunk**
- **Type:** System Data | **Storage:** localStorage (simulated chunking)
- **Key Fields:** id, ownerId, savedItemId, chunkIndex, chunkText, tokenCount (simulated), embeddingId (simulated), createdAt
- **Relationships:** belongs to SavedItem
- **Lifecycle:** Created by system during processing, deleted with parent item

**ChatThread**
- **Type:** System Data | **Storage:** localStorage
- **Key Fields:** id, ownerId, title (optional, auto-generated from first question), createdAt, updatedAt
- **Relationships:** belongs to User, has many ChatMessages
- **Lifecycle:** Create (new chat), view, delete (optional for MVP)

**ChatMessage**
- **Type:** System Data | **Storage:** localStorage
- **Key Fields:** id, threadId, role (user/assistant), content, citations (array of {savedItemId, excerpt, relevanceScore}), createdAt
- **Relationships:** belongs to ChatThread
- **Lifecycle:** Create only, deleted with parent thread

### 5.2 Data Storage Strategy

- **Primary Storage:** Browser localStorage (5-10MB capacity)
- **Capacity:** Approximately 500-1000 saved items with notes and archived text
- **Persistence:** Data persists across sessions via localStorage
- **Cache Strategy:** Recently viewed items (last 50) cached for instant load
- **Audit Fields:** All entities include createdAt, updatedAt, createdBy (ownerId), updatedBy (ownerId)
- **Export Format:** JSON export of all user data (items, notes, tags, archived text)

---

## 6. INTEGRATION REQUIREMENTS

**URL Metadata Fetching (Simulated)**
- **Purpose:** Extract title, description, imageUrl, favicon from web URLs
- **Type:** Frontend simulation with realistic delays
- **Data Exchange:** Sends URL, receives metadata object
- **Trigger:** When user pastes URL in Save form
- **Error Handling:** 5% random failure rate, 10-second timeout, fallback to manual entry with "Could not fetch metadata" message

**Content Extraction (Simulated)**
- **Purpose:** Fetch HTML and extract main content text for archival
- **Type:** Frontend simulation with realistic processing delays
- **Data Exchange:** Sends URL, receives archivedText and processing metadata
- **Trigger:** After item creation or user clicks "Reprocess"
- **Error Handling:** 10% random failure rate, mark status "failed", store error message, allow manual paste fallback

**AI Tag/Topic Suggestions (Simulated)**
- **Purpose:** Generate suggested tags (3-7), topic label, and optional summary based on content
- **Type:** Frontend simulation using content analysis heuristics
- **Data Exchange:** Sends archivedText and user's existing tags, receives suggestions
- **Trigger:** After content extraction completes
- **Error Handling:** If content too short, skip suggestions with message "Content too brief for suggestions"

**RAG Chat Responses (Simulated)**
- **Purpose:** Generate answers to user questions with citations and excerpts from saved library
- **Type:** Frontend simulation using keyword matching and template responses
- **Data Exchange:** Sends question and user's library, receives answer with citations array
- **Trigger:** User submits question in Ask Stash chat
- **Error Handling:** If no relevant items found, respond with "I couldn't find enough support in your library. Try searching for [suggested tags] or saving more content on this topic."

---

## 7. VIEWS & NAVIGATION

### 7.1 Primary Views

**Login/Register** (`/login`, `/register`) - Auth forms with email/password, validation, error messages, "Forgot password" link

**Library** (`/` or `/library`) - Grid/list toggle, search bar (top), tag filter pills (below search), sort dropdown (newest/oldest/title A-Z), "Save" button (prominent), item cards showing title/image/tags/status/excerpt, pagination controls, empty state with "Save your first item" prompt

**Save Modal/Overlay** (`/save` or modal) - URL input with auto-fetch preview OR paste textarea, editable title/description/image fields, notes editor (Markdown), tag input with # autocomplete, content type selector, save/cancel buttons

**Item Detail** (`/items/:id`) - Hero image, title (editable inline), description (editable), source link with favicon, tags (editable with autocomplete), suggested tags/topic section (if pending acceptance), notes editor (Markdown with preview toggle), archived content tab (read-only, collapsible), processing status badge, reprocess button (if failed), timestamps (created/updated), delete button (with confirmation)

**Ask Stash Chat** (persistent overlay, collapsible) - Chat interface with message history, input box at bottom, responses include direct answer + "Sources" section with item cards + excerpts (quoted, 1-3 per answer), links to open cited items in detail view, "New chat" button, collapse/expand toggle, thread history (optional)

**Settings** (`/settings`) - Profile section (name, email, password change), view preferences (grid/list default, sort default), export all data (JSON download), delete account (with confirmation and warning)

### 7.2 Navigation Structure

**Main Nav (Top Bar):** Stash logo (→ Library) | Search bar (global) | Save button (prominent, primary color) | Ask Stash button (opens overlay) | User menu (Settings, Logout)

**Default Landing:** Library view after login

**Mobile:** Hamburger menu for main nav, bottom action bar with Save and Ask Stash buttons, responsive grid (1 column on mobile, 2-3 on tablet, 3-4 on desktop), collapsible filters

**Chat Overlay:** Slides in from right side (desktop) or bottom (mobile), semi-transparent backdrop, collapse to floating button when minimized, persists across page navigation

---

## 8. MVP SCOPE & CONSTRAINTS

### 8.1 MVP Success Definition

The MVP is successful when:
- ✅ Users can save content (URL or paste) and see it appear immediately with processing status
- ✅ Auto-suggested tags and topics appear after simulated processing (2-5 seconds)
- ✅ Users can accept/edit suggestions and add manual tags with autocomplete
- ✅ Keyword search returns results instantly (<1 second) across all fields including archived text
- ✅ Tag filtering and sorting work smoothly with visual feedback
- ✅ Chat interface provides relevant answers with citations and excerpts from saved library
- ✅ Responsive design functions properly on mobile, tablet, and desktop
- ✅ Data persists across sessions via localStorage
- ✅ All entity lifecycle operations (CRUD) work without errors

### 8.2 In Scope for MVP

Core features included:
- FR-001: User Authentication (register, login, profile, logout)
- FR-002: Save Content with Auto Metadata (URL or paste, metadata fetch simulation)
- FR-003: Hashtag Tagging with Autocomplete (create, view, edit, remove tags)
- FR-004: AI-Suggested Tags and Topics (view, accept, reject suggestions)
- FR-005: Personal Notes with Markdown (create, edit, view rendered, export)
- FR-006: Library View with Tag Filtering (grid/list, filter, sort, bulk actions)
- FR-007: Keyword Search (real-time, full-text, highlight matches)
- FR-008: Item Detail View with Editing (inline editing, all metadata, notes, tags)
- FR-009: Content Extraction and Archival (simulated extraction, archived text storage)
- FR-010: Chat-Based Search with Citations (simulated RAG, answers with sources and excerpts)

### 8.3 Technical Constraints

- **Data Storage:** Browser localStorage (5-10MB limit, approximately 500-1000 items)
- **Concurrent Users:** Single-user per browser (no multi-device sync)
- **Performance:** Page loads <2 seconds, search results <1 second, instant UI interactions
- **Browser Support:** Chrome, Firefox, Safari, Edge (last 2 versions)
- **Mobile:** Responsive design, iOS/Android browser support, touch-optimized
- **Offline:** Basic offline support via localStorage (no real-time sync)
- **Simulation Fidelity:** AI features simulated with realistic delays and heuristic-based responses

### 8.4 Known Limitations

**For MVP:**
- Browser localStorage limits total items per user (~500-1000 depending on content size)
- No multi-device sync - data stored locally per browser
- No data backup - user must manually export JSON
- Metadata and extraction simulated - not real web scraping
- AI suggestions and chat responses simulated - not real LLM integration
- No browser extension for one-click saving
- No collaboration or sharing features
- Extraction "fails" randomly (10%) to simulate real-world challenges
- Chat quality depends on keyword matching, not semantic understanding

**Future Enhancements (Post-MVP):**
- Real backend with database for multi-device sync
- Actual LLM integration for suggestions and RAG chat
- Real web scraping and content extraction
- Browser extension for one-click saving
- Bulk import from Pocket, Instapaper, browser bookmarks
- Shared collections and collaboration
- Advanced search operators (boolean, date ranges, saved searches)
- Mobile native apps

---

## 9. ASSUMPTIONS & DECISIONS

### 9.1 Platform Decisions

- **Type:** Web application (frontend-focused with localStorage persistence)
- **Storage:** localStorage for all data (users, items, tags, notes, chunks, chat threads)
- **Auth:** Local authentication with password hashing (bcrypt simulation), JWT-like session tokens
- **Simulation Strategy:** Realistic delays and failure rates to mimic real backend/AI behavior
- **Visual Density:** Medium density - show multiple items at once without overwhelming (3-4 columns on desktop, 2 on tablet, 1 on mobile)

### 9.2 Entity Lifecycle Decisions

**SavedItem:** Full CRUD + hard delete (permanent) + export
- **Reason:** User-generated content needs full control, and permanent deletion keeps storage usage predictable and implementation simpler.

**Tag:** Create via hashtag, remove from items (doesn't delete globally)
- **Reason:** Tags are vocabulary that should persist even if removed from individual items. Prevents accidental loss of tag history.

**Note:** Full CRUD with history preservation + export
- **Reason:** User-generated annotations are valuable context. History allows tracking thought evolution.

**ContentChunk:** System-managed, deleted with parent item
- **Reason:** Technical artifact for search/retrieval, not user-facing entity. No independent lifecycle needed.

**ChatThread/Message:** Create and view, optional delete
- **Reason:** Chat history provides context for follow-ups. Deletion optional for MVP to reduce complexity.

### 9.3 Key Assumptions

1. **Users prefer speed over perfection in MVP**
   - Reasoning: Simulated AI features with realistic delays provide faster validation than waiting for real integrations. Users can test UX and workflows immediately.

2. **Medium visual density balances information and usability**
   - Reasoning: Alex wants to see multiple items at once (grid view with 3-4 columns) but not be overwhelmed. Cards show key info (title, image, tags, excerpt) without clutter.

3. **Persistent chat overlay is more valuable than dedicated page**
   - Reasoning: Users want to ask questions while browsing their library. Overlay allows seamless context switching without losing place. Collapsible design prevents intrusion.

4. **localStorage is sufficient for MVP validation**
   - Reasoning: 500-1000 items is enough to validate core workflows. No backend reduces build complexity. Export feature provides data portability.

5. **Hashtag-based tagging is more natural than dropdown selection**
   - Reasoning: Typing # feels familiar (social media pattern). Autocomplete provides discovery of existing tags while allowing quick creation of new ones.

### 9.4 Clarification Q&A Summary

**Q:** Architecture approach - full-stack or frontend simulation?  
**A:** Frontend simulation with realistic mock data  
**Decision:** Build high-fidelity frontend that simulates AI/RAG and extraction features using localStorage and realistic delays. Enables rapid UX validation without backend complexity.

**Q:** Visual density preference for Alex persona?  
**A:** Medium level - see a lot without being overwhelmed  
**Decision:** Grid view with 3-4 columns on desktop, 2 on tablet, 1 on mobile. Cards show title, image, tags, excerpt. List view shows more metadata in rows. Filters and search always visible.

**Q:** Chat interface UX - sidebar or dedicated page?  
**A:** Persistent overlay, easily collapsed, always accessible but not intrusive  
**Decision:** Chat slides in from right (desktop) or bottom (mobile) as overlay. Collapse to floating button. Persists across navigation. Semi-transparent backdrop. Users can browse library while chatting.

---

**PRD Complete - Ready for Development**
