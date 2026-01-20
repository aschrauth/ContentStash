# PRODUCT REQUIREMENTS DOCUMENT (UPDATED)

**Product Name:** Stash  
**Version:** 1.1 (Frontend Complete)  
**Owner:** Anthony  
**Platform:** Web Application (Responsive, Desktop & Mobile Browser)  
**Status:** Frontend Built / Backend Pending

---

## EXECUTIVE SUMMARY

**Product Vision:**  
Stash is a personal knowledge base that helps people save, organize, and rediscover content from the web and their own AI conversations. It transforms scattered links, transcripts, and threads into a searchable, chat-first "second brain" with automatic categorization and citation-backed answers.

**Core Purpose:**  
Solves the problem of saved content becoming unfindable and losing context. People bookmark valuable articles, videos, podcasts, and ChatGPT threads but cannot reliably retrieve them later or remember why they mattered.

**Target Users:**  
Primary: Knowledge workers (product managers, researchers, strategists) who consume 10-15 pieces of content weekly and need to build a searchable library with personal context.

**Key Features (Implemented in Frontend):**
- **Content Saving:** Save URLs with auto-fetched metadata or paste rich text content.
- **AI-Powered Metadata:** Auto-generation of titles, descriptions, and tags for pasted content and URLs.
- **Smart Organization:** Hashtag tagging with autocomplete and AI-suggested tags/topics.
- **Rich Text Notes:** WYSIWYG editor (TipTap) for personal notes that saves as Markdown.
- **Library Management:** Toggleable Grid/List views with tag filtering, sorting, and search.
- **Chat-Based Search:** "Ask Stash" overlay for RAG-based Q&A with citations.
- **User Authentication:** Registration, login, and profile management (simulated).

---

## 1. USERS & PERSONAS

**Primary Persona: Alex the Knowledge Worker**
- **Context:** Product manager reading 10-15 articles weekly.
- **Goals:** Build a searchable library. Add personal context. Quickly retrieve content.
- **Pain Points:** Bookmarks lack context. Saved items disappear. Hard to connect ideas.

---

## 2. FUNCTIONAL REQUIREMENTS

### 2.1 Core Features

**FR-001: User Authentication**
- **Status:** Implemented (Simulated)
- **Description:** Register, Login, Logout, Profile management.
- **Data:** Users stored in `localStorage` with hashed passwords.
- **UI:** Glassmorphism login/register pages.

**FR-002: Save Content (URL & Paste)**
- **Status:** Implemented
- **Description:** 
    - **URL Tab:** Paste URL -> Auto-fetch metadata (Title, Description, Image, Favicon) -> Show AI Suggestions.
    - **Paste Tab:** Paste rich text -> "Generate Metadata" button triggers AI analysis for Title/Description/Tags.
- **UI:** Modal with tabs, loading states, and preview card.

**FR-003: Library View**
- **Status:** Implemented
- **Description:** 
    - **Grid View:** Card-based layout with large preview images.
    - **List View (Default):** Compact horizontal layout with left-aligned fixed-width image and right-aligned text.
    - **Persistence:** User preference (Grid vs. List) saved to profile/store.
    - **Filtering:** Search bar (title/desc/tags) and clickable tag pills.

**FR-004: Item Detail View**
- **Status:** Implemented
- **Description:** 
    - **Header:** Editable Title/Description, Date, Status badges.
    - **Preview Image:** Fixed width (250px), left-aligned, text wrapping around it.
    - **Personal Notes:** Rich Text Editor (TipTap) supporting Bold, Italic, Lists, Headings, Quotes, Code. Saves as Markdown.
    - **Archived Content:** Read-only view of extracted content, rendered as Rich Text (Markdown).
    - **Sidebar:** Actions (Reprocess, Delete), Tags (add/remove), AI Suggestions (click to add), Topic.

**FR-005: AI Suggestions**
- **Status:** Implemented (Simulated)
- **Description:** 
    - **On Save:** Suggestions appear immediately after metadata fetch.
    - **On Detail:** Suggestions panel allows one-click addition of tags.
    - **Logic:** Simulated heuristics based on content keywords.

**FR-006: Chat-Based Search (Ask Stash)**
- **Status:** Implemented (Simulated)
- **Description:** Persistent overlay. User asks question -> System simulates RAG -> Returns answer with citations.
- **UI:** Chat interface with history, typing indicators, and citation links that open item details.

**FR-007: Deletion Workflow**
- **Status:** Implemented
- **Description:** "Delete" button triggers a custom in-app confirmation modal (matching design system) instead of browser alert.
- **Logic:** Soft delete (archivedAt set) or hard delete from store.

---

## 3. USER INTERFACE & DESIGN SYSTEM

**Design Style:** "Apple-Inspired" / "Glassmorphism"
- **Theme:** Dark mode default (`bg-slate-950`).
- **Materials:** `bg-white/5` with `backdrop-blur` for cards and panels.
- **Typography:** Sans-serif (Geist), clean hierarchy.
- **Accents:** Violet/Cyan gradients for primary actions and highlights.
- **Animations:** Framer Motion for modals, transitions, and hover effects.

**Key Components:**
- **RichTextEditor:** TipTap-based, supports Markdown conversion, custom toolbar.
- **ConfirmationModal:** Reusable glassmorphic modal for destructive actions.
- **ItemCard:** Responsive, supports `viewMode` prop for Grid/List layouts.

---

## 4. DATA MODEL (Frontend Store)

**User**
```typescript
{
  id: string;
  email: string;
  name: string;
  passwordHash: string;
  preferences: {
    viewMode: 'grid' | 'list'; // Persisted preference
  };
}
```

**SavedItem**
```typescript
{
  id: string;
  ownerId: string;
  url?: string;
  title: string;
  description?: string;
  imageUrl?: string;
  notesMarkdown?: string; // Stores HTML/Markdown from TipTap
  tags: string[];
  suggestedTags?: string[];
  suggestedTopic?: string;
  archivedText?: string; // Main content body
  processingStatus: 'pending' | 'processed' | 'failed';
  createdAt: string;
  updatedAt: string;
}
```

---

## 5. FUTURE BACKEND REQUIREMENTS (For Testing)

To replace the current `localStorage` simulation, the backend must provide:

1.  **API Endpoints:**
    - `POST /auth/register`, `POST /auth/login`
    - `GET /items`, `POST /items`, `GET /items/:id`, `PUT /items/:id`, `DELETE /items/:id`
    - `POST /items/metadata` (URL scraping)
    - `POST /items/analyze` (AI analysis for pasted text)
    - `POST /chat` (RAG endpoint)

2.  **AI Services:**
    - **Scraper:** Puppeteer/Playwright to fetch OG tags and main content from URLs.
    - **LLM Integration:** OpenAI/Anthropic for:
        - Generating tags/topics from content.
        - Generating Title/Description from pasted text.
        - RAG Chat responses (Embeddings + Retrieval + Generation).

3.  **Database:**
    - Users table (with preferences JSON).
    - Items table (with vector embeddings for search).
    - Tags table (many-to-many).

---

## 6. ACCEPTANCE CRITERIA (For QA)

1.  **View Preference:**
    - [ ] User toggles to "List View".
    - [ ] User navigates away and back.
    - [ ] Library should still be in "List View".
    - [ ] New users should see "List View" by default.

2.  **Save Flow:**
    - [ ] Paste URL -> Metadata loads -> AI Suggestions appear -> Click suggestion adds tag.
    - [ ] Paste Text -> Click "Generate Metadata" -> Title/Desc/Tags populate.

3.  **Detail View:**
    - [ ] Image is left-aligned, fixed width, text wraps around.
    - [ ] Notes editor shows rich text (bold, headings) but saves content.
    - [ ] Archived content renders as rich text (not raw markdown).

4.  **Deletion:**
    - [ ] Click Delete -> Custom Modal appears -> Confirm -> Item removed.

---

**Document Date:** 2024-05-22  
**Status:** Ready for Backend Integration

