# Backend Development Plan

## 1️⃣ Executive Summary

**What Will Be Built:**
- FastAPI backend (Python 3.13, async) for Stash content management application
- MongoDB Atlas database with Motor driver and Pydantic v2 models
- JWT-based authentication system
- RESTful API endpoints for content saving, tagging, search, and AI chat features
- Real metadata fetching and content extraction (replacing frontend simulation)
- Background processing for content analysis and AI suggestions

**Key Constraints:**
- Python 3.13 runtime with FastAPI
- MongoDB Atlas only (no local instance)
- No Docker deployment
- Manual testing after every task via frontend UI
- Single-branch Git workflow (`main` only)
- API base path: `/api/v1/*`
- Per-task testing before sprint completion

**Sprint Structure:**
- S0: Environment Setup & Frontend Connection
- S1: Basic Auth (Signup/Login/Logout)
- S2: Content Management (Save/View/Edit/Delete Items)
- S3: Tagging System with Autocomplete
- S4: Search & Filtering
- S5: AI Features (Metadata, Extraction, Suggestions)
- S6: Chat-Based Search (RAG Implementation)

---

## 2️⃣ In-Scope & Success Criteria

**In-Scope Features:**
- User registration and JWT authentication
- Save content (URL or pasted text) with metadata
- CRUD operations for saved items
- Hashtag tagging with autocomplete
- Full-text search across titles, descriptions, notes, tags, archived content
- Tag filtering with AND logic
- AI-powered tag and topic suggestions
- Content extraction from URLs
- Chat-based search with citations (RAG)
- User preferences (view mode, sort order)
- Hard delete after user confirmation

**Success Criteria:**
- All frontend features functional end-to-end
- All task-level manual tests pass via UI
- Each sprint's code pushed to `main` after verification
- Backend connects to MongoDB Atlas successfully
- JWT authentication secures protected routes
- Search returns results in under 1 second
- AI features provide relevant suggestions
- Chat provides answers with proper citations

---

## 3️⃣ API Design

**Base Path:** `/api/v1`

**Error Envelope:** `{ "error": "message", "detail": "optional details" }`

### Health Check
- **GET /healthz**
- Purpose: Verify backend and database connectivity
- Response: `{ "status": "ok", "database": "connected", "timestamp": "ISO8601" }`

### Authentication Endpoints
- **POST /api/v1/auth/signup**
- Purpose: Register new user
- Request: `{ "email": "string", "password": "string", "name": "string" }`
- Response: `{ "user": { "id": "string", "email": "string", "name": "string" }, "token": "jwt_string" }`
- Validation: Email unique, password min 8 chars, name min 2 chars

- **POST /api/v1/auth/login**
- Purpose: Authenticate user
- Request: `{ "email": "string", "password": "string" }`
- Response: `{ "user": { "id": "string", "email": "string", "name": "string" }, "token": "jwt_string" }`

- **POST /api/v1/auth/logout**
- Purpose: Invalidate session (client-side token removal)
- Response: `{ "message": "Logged out successfully" }`

- **GET /api/v1/auth/me**
- Purpose: Get current user profile
- Headers: `Authorization: Bearer <token>`
- Response: `{ "id": "string", "email": "string", "name": "string", "preferences": { "viewMode": "grid|list" } }`

- **PATCH /api/v1/auth/me**
- Purpose: Update user profile
- Request: `{ "name": "string", "email": "string", "preferences": { "viewMode": "grid|list" } }`
- Response: Updated user object

### Items Endpoints
- **POST /api/v1/items**
- Purpose: Create new saved item
- Request: `{ "url": "string?", "title": "string", "description": "string?", "tags": ["string"], "notesMarkdown": "string?", "archivedText": "string?" }`
- Response: `{ "id": "string", "processingStatus": "pending", ... }`

- **GET /api/v1/items**
- Purpose: List user's saved items
- Query params: `?tags=tag1,tag2&search=query&sort=newest`
- Response: `{ "items": [...], "total": number }`

- **GET /api/v1/items/:id**
- Purpose: Get single item details
- Response: Full item object

- **PATCH /api/v1/items/:id**
- Purpose: Update item
- Request: Partial item object
- Response: Updated item

- **DELETE /api/v1/items/:id**
- Purpose: Permanently delete item
- Response: `{ "message": "Item deleted" }`

- **POST /api/v1/items/:id/reprocess**
- Purpose: Retry content extraction
- Response: `{ "message": "Reprocessing started" }`

### Tags Endpoints
- **GET /api/v1/tags**
- Purpose: Get all user's tags with counts
- Response: `{ "tags": [{ "name": "string", "count": number }] }`

- **GET /api/v1/tags/autocomplete?q=query**
- Purpose: Autocomplete suggestions
- Response: `{ "suggestions": ["tag1", ...] }` (max 10)

### Chat Endpoints
- **POST /api/v1/chat/threads**
- Purpose: Create new chat thread
- Request: `{ "message": "string" }`
- Response: `{ "threadId": "string", "message": {...} }`

- **POST /api/v1/chat/threads/:threadId/messages**
- Purpose: Send message in thread
- Request: `{ "message": "string" }`
- Response: `{ "userMessage": {...}, "assistantMessage": { "content": "string", "citations": [...] } }`

- **GET /api/v1/chat/threads**
- Purpose: List user's threads
- Response: `{ "threads": [...] }`

- **GET /api/v1/chat/threads/:threadId**
- Purpose: Get thread with messages
- Response: `{ "id": "string", "messages": [...] }`

---

## 4️⃣ Data Model (MongoDB Atlas)

### users Collection
- `_id`: ObjectId
- `email`: string (unique, indexed)
- `name`: string
- `password_hash`: string (Argon2)
- `preferences`: object `{ "view_mode": "grid|list", "sort_order": "newest|oldest|title" }`
- `created_at`: datetime
- `updated_at`: datetime

Example:
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "email": "alex@example.com",
  "name": "Alex Smith",
  "password_hash": "$argon2id$v=19$m=65536...",
  "preferences": { "view_mode": "list", "sort_order": "newest" },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### saved_items Collection
- `_id`: ObjectId
- `owner_id`: ObjectId (ref users, indexed)
- `url`: string (optional)
- `title`: string (required, max 500 chars)
- `description`: string (optional, max 2000 chars)
- `image_url`: string (optional)
- `favicon_url`: string (optional)
- `notes_markdown`: string (optional, max 50000 chars)
- `tags`: array of strings (max 20)
- `suggested_tags`: array of strings (optional)
- `suggested_topic`: string (optional)
- `archived_text`: string (optional)
- `processing_status`: string enum ("pending", "processed", "failed")
- `processing_error`: string (optional)
- `created_at`: datetime (indexed)
- `updated_at`: datetime

### chat_threads Collection
- `_id`: ObjectId
- `owner_id`: ObjectId (ref users, indexed)
- `title`: string (auto-generated from first message)
- `created_at`: datetime
- `updated_at`: datetime

### chat_messages Collection
- `_id`: ObjectId
- `thread_id`: ObjectId (ref chat_threads, indexed)
- `role`: string enum ("user", "assistant")
- `content`: string
- `citations`: array of objects `[{ "item_id": ObjectId, "excerpt": string, "title": string }]` (optional)
- `created_at`: datetime

---

## 5️⃣ Frontend Audit & Feature Map

### Landing Page (`/`)
- Route: Public landing page
- Purpose: Marketing and signup
- Backend: None
- Auth: Not required

### Login Page (`/login`)
- Route: `/login`
- Purpose: User authentication
- Backend: [`POST /api/v1/auth/login`](backend/app/routers/auth.py:login)
- Auth: Not required

### Register Page (`/register`)
- Route: `/register`
- Purpose: User registration
- Backend: [`POST /api/v1/auth/signup`](backend/app/routers/auth.py:signup)
- Auth: Not required

### Library Page (`/library`)
- Route: `/library`
- Purpose: Display all saved items with filtering
- Backend: [`GET /api/v1/items`](backend/app/routers/items.py:list_items), [`GET /api/v1/tags`](backend/app/routers/tags.py:get_tags)
- Auth: Required (JWT)

### Item Detail Page (`/items/[id]`)
- Route: `/items/:id`
- Purpose: View and edit single item
- Backend: [`GET /api/v1/items/:id`](backend/app/routers/items.py:get_item), [`PATCH /api/v1/items/:id`](backend/app/routers/items.py:update_item), [`DELETE /api/v1/items/:id`](backend/app/routers/items.py:delete_item)
- Auth: Required (JWT)

### Save Modal (Component)
- Component: Overlay modal
- Purpose: Save new content
- Backend: [`POST /api/v1/items`](backend/app/routers/items.py:create_item)
- Auth: Required (JWT)

### Chat Overlay (Component)
- Component: Slide-in panel
- Purpose: AI-powered search
- Backend: [`POST /api/v1/chat/threads`](backend/app/routers/chat.py:create_thread), [`POST /api/v1/chat/threads/:id/messages`](backend/app/routers/chat.py:send_message)
- Auth: Required (JWT)

---

## 6️⃣ Configuration & ENV Vars

**Core Environment Variables:**
- `APP_ENV` — Environment (development, production)
- `PORT` — HTTP port (default: 8000)
- `MONGODB_URI` — MongoDB Atlas connection string (required)
- `JWT_SECRET` — Token signing key (required, min 32 chars)
- `JWT_EXPIRES_IN` — Seconds before JWT expiry (default: 604800 = 7 days)
- `CORS_ORIGINS` — Allowed frontend URL(s) (comma-separated)
- `GEMINI_API_KEY` — For AI features (required for S5-S6)

---

## 7️⃣ Background Work

### Content Processing (After Item Creation)
- Trigger: Item created with URL
- Purpose: Fetch metadata, extract content, generate suggestions
- Idempotency: Can be retried via reprocess endpoint
- UI Check: Frontend polls item status field

### AI Suggestions Generation
- Trigger: After content extraction completes
- Purpose: Generate 3-7 tag suggestions and topic label
- UI Check: Suggestions appear in item detail view

---

## 8️⃣ Integrations

### Gemini API (Required for S5-S6)
- Purpose: Generate AI suggestions, embeddings, and chat responses
- Endpoints: Content generation, embeddings
- Env Var: `GEMINI_API_KEY`
- Fallback: Keyword-based heuristics if API unavailable

### URL Metadata Fetching
- Purpose: Extract title, description, image from URLs
- Implementation: Use `requests` + `BeautifulSoup`
- Timeout: 10 seconds

### Content Extraction
- Purpose: Extract main article text from web pages
- Implementation: Use `beautifulsoup4` or `trafilatura`
- Timeout: 15 seconds

---

## 9️⃣ Testing Strategy (Manual via Frontend)

**Validation Approach:**
- Every task includes manual test via frontend UI
- Test after completing each task (not only after sprint)
- If test fails, fix immediately before proceeding
- After all sprint tasks pass, commit and push to `main`

**Test Format:**
- **Manual Test Step:** Exact UI action + expected result
- **User Test Prompt:** Copy-paste friendly testing instruction

---

## 🔟 Dynamic Sprint Plan & Backlog

---

## 🧱 S0 – Environment Setup & Frontend Connection

**Objectives:**
- Create FastAPI skeleton with `/api/v1` and `/healthz`
- Connect to MongoDB Atlas using `MONGODB_URI`
- `/healthz` performs DB ping and returns JSON status
- Enable CORS for frontend
- Replace dummy API URLs in frontend with real backend URLs
- Initialize Git only once at root, set default branch to `main`, and push to GitHub
- Create a single `.gitignore` file at root

**Definition of Done:**
- Backend runs locally and connects to MongoDB Atlas
- `/healthz` returns success
- Frontend renders live data
- Repo live on GitHub `main`

**Tasks:**

### Task 1: Initialize FastAPI Project
- Create project structure: `backend/`, `backend/app/`, `backend/app/main.py`
- Install dependencies: `fastapi`, `uvicorn[standard]`, `motor`, `pydantic`, `python-dotenv`, `argon2-cffi`, `pyjwt[crypto]`
- Create `requirements.txt`
- Create `.env.example` with all required variables
- Create `.gitignore` at root (ignore `__pycache__`, `.env`, `*.pyc`, `.venv`, `.pytest_cache`, `node_modules/`, `.next/`)
- **Manual Test Step:** Run `pip install -r requirements.txt` → all packages install successfully
- **User Test Prompt:** "Install dependencies and confirm no errors."

### Task 2: Create Basic FastAPI App
- Implement `main.py` with FastAPI app instance
- Add CORS middleware with configurable origins
- Create `/healthz` endpoint returning `{ "status": "ok" }`
- **Manual Test Step:** Run `uvicorn app.main:app --reload` → server starts on port 8000
- **User Test Prompt:** "Start the backend and visit http://localhost:8000/healthz — confirm JSON response."

### Task 3: Connect to MongoDB Atlas
- Create `app/database.py` with Motor client initialization
- Implement async DB connection with ping test
- Update `/healthz` to include DB status: `{ "status": "ok", "database": "connected" }`
- **Manual Test Step:** Set `MONGODB_URI` in `.env` → `/healthz` returns `"database": "connected"`
- **User Test Prompt:** "Add your MongoDB Atlas URI to .env and restart. Visit /healthz and confirm database connection."

### Task 4: Update Frontend API URLs
- Replace all frontend dummy API calls with real backend URLs
- Update `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **Manual Test Step:** Open frontend → Network tab shows successful call to `http://localhost:8000/healthz`
- **User Test Prompt:** "Start both frontend and backend. Open browser DevTools Network tab and confirm /healthz request succeeds."

### Task 5: Initialize Git and Push to GitHub
- Run `git init` at project root (once only)
- Commit initial code: `git add . && git commit -m "Initial backend setup"`
- Set default branch: `git branch -M main`
- Create GitHub repo and push: `git remote add origin <url> && git push -u origin main`
- **Manual Test Step:** Visit GitHub repo → code visible on `main` branch
- **User Test Prompt:** "Create a GitHub repo, push your code, and confirm it appears online."

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S1 – Basic Auth (Signup / Login / Logout)

**Objectives:**
- Implement JWT-based signup, login, and logout
- Protect one backend route + one frontend page

**Endpoints:**
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

**Tasks:**

### Task 1: Create User Model
- Create `app/models/user.py` with Pydantic User model
- Fields: `id`, `email`, `name`, `password_hash`, `preferences`, `created_at`, `updated_at`
- **Manual Test Step:** Import model in Python shell → no errors
- **User Test Prompt:** "Run `python -c 'from app.models.user import User'` and confirm no import errors."

### Task 2: Implement Password Hashing
- Create `app/utils/auth.py` with Argon2 hash and verify functions
- **Manual Test Step:** Hash a password and verify it matches
- **User Test Prompt:** "Run a test script to hash 'password123' and verify it — confirm success."

### Task 3: Implement Signup Endpoint
- Create `app/routers/auth.py`
- Implement `POST /api/v1/auth/signup`
- Validate email uniqueness, password length (min 8), name length (min 2)
- Hash password with Argon2
- Store user in MongoDB `users` collection
- Return user object (without password) and JWT token
- **Manual Test Step:** Use frontend register page → account created, redirected to library
- **User Test Prompt:** "Open /register, create an account, and confirm you're redirected to /library."

### Task 4: Implement Login Endpoint
- Implement `POST /api/v1/auth/login`
- Validate credentials (email + password)
- Generate JWT token with user ID and expiry
- Return user object and token
- **Manual Test Step:** Use frontend login page → successful login, redirected to library
- **User Test Prompt:** "Open /login, enter credentials, and confirm you're redirected to /library."

### Task 5: Implement JWT Middleware
- Create `app/middleware/auth.py` with JWT verification
- Protect `GET /api/v1/auth/me` endpoint
- Return current user profile from token
- **Manual Test Step:** Login via frontend → visit library page → user data loads
- **User Test Prompt:** "Log in and confirm your name appears in the navbar."

### Task 6: Implement Logout
- Create `POST /api/v1/auth/logout` (returns success message)
- Frontend clears token from storage
- **Manual Test Step:** Click logout → redirected to login, protected pages blocked
- **User Test Prompt:** "Log out and try visiting /library — confirm you're redirected to /login."

**Definition of Done:**
- Auth flow works end-to-end in frontend

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S2 – Content Management (CRUD for Saved Items)

**Objectives:**
- Implement CRUD operations for saved items
- Support URL and pasted content
- Hard delete after user confirmation

**Tasks:**

### Task 1: Create SavedItem Model
- Create `app/models/saved_item.py` with Pydantic SavedItem model
- Fields match frontend store structure
- **Manual Test Step:** Import model → no errors
- **User Test Prompt:** "Run `python -c 'from app.models.saved_item import SavedItem'` and confirm no errors."

### Task 2: Implement Create Item Endpoint
- Implement `POST /api/v1/items`
- Validate title required, either URL or content required
- Set `processing_status` to "pending"
- Store in MongoDB `saved_items` collection
- **Manual Test Step:** Click "Save" in frontend, paste URL, save → item appears in library with "pending" status
- **User Test Prompt:** "Open Save modal, paste a URL, save, and confirm item appears in library."

### Task 3: Implement List Items Endpoint
- Implement `GET /api/v1/items`
- Filter by `owner_id` (from JWT)
- Return all items owned by the user
- Support query params: `?tags=tag1,tag2&search=query&sort=newest`
- **Manual Test Step:** Open library page → saved items display
- **User Test Prompt:** "Open /library and confirm your saved items appear."

### Task 4: Implement Get Single Item Endpoint
- Implement `GET /api/v1/items/:id`
- Verify ownership
- Return full item details
- **Manual Test Step:** Click an item card → detail page loads with all data
- **User Test Prompt:** "Click a saved item and confirm the detail page loads."

### Task 5: Implement Update Item Endpoint
- Implement `PATCH /api/v1/items/:id`
- Allow updating: `title`, `description`, `notes_markdown`, `tags`
- Verify ownership
- **Manual Test Step:** Edit item title in detail page → changes save automatically
- **User Test Prompt:** "Edit an item's title and confirm changes persist after refresh."

### Task 6: Implement Delete Item Endpoint
- Implement `DELETE /api/v1/items/:id`
- Hard delete: remove document from `saved_items` and related chunks from `item_chunks`
- **Manual Test Step:** Click delete button → confirmation modal → item removed from library
- **User Test Prompt:** "Delete an item and confirm it disappears from the library."

**Definition of Done:**
- Users can save, view, edit, and delete items via frontend

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S3 – Tagging System with Autocomplete

**Objectives:**
- Implement tag management
- Support adding/removing tags from items
- Provide autocomplete suggestions

**Tasks:**

### Task 1: Implement Get All Tags Endpoint
- Implement `GET /api/v1/tags`
- Aggregate all unique tags from user's items
- Return tags with usage counts
- **Manual Test Step:** Open library → tag filter pills display
- **User Test Prompt:** "Open /library and confirm tag filter buttons appear if you have tagged items."

### Task 2: Implement Tag Autocomplete Endpoint
- Implement `GET /api/v1/tags/autocomplete?q=query`
- Search user's existing tags matching query
- Return max 10 suggestions sorted by frequency
- **Manual Test Step:** Type "#" in tag input → suggestions appear
- **User Test Prompt:** "In item detail, start typing a tag and confirm autocomplete suggestions appear."

### Task 3: Update Item Endpoint to Support Tags
- Ensure `PATCH /api/v1/items/:id` accepts `tags` array
- Validate max 20 tags per item
- **Manual Test Step:** Add tag to item → tag appears in item card
- **User Test Prompt:** "Add a tag to an item and confirm it appears on the item card."

### Task 4: Implement Tag Filtering
- Update `GET /api/v1/items?tags=tag1,tag2`
- Filter items with AND logic
- **Manual Test Step:** Click tag filter pill → library filters to matching items
- **User Test Prompt:** "Click a tag filter and confirm only items with that tag appear."

**Definition of Done:**
- Tags can be added and removed
- Autocomplete works
- Tag filtering works

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S4 – Search & Filtering

**Objectives:**
- Implement full-text search across items
- Return results ranked by relevance

**Tasks:**

### Task 1: Implement Search Endpoint
- Implement `GET /api/v1/search?q=query`
- Validate query min 2 chars
- Search across: `title`, `description`, `notes_markdown`, `tags`, `archived_text`
- Return max 100 results
- **Manual Test Step:** Type in search bar → matching items appear
- **User Test Prompt:** "Type a keyword in the search bar and confirm matching items appear."

### Task 2: Implement Search Ranking
- Rank results by relevance: title > tags > notes > content
- **Manual Test Step:** Search for term in title → that item appears first
- **User Test Prompt:** "Search for a word in an item's title and confirm it appears at the top."

### Task 3: Optimize Search Performance
- Add text index to MongoDB `saved_items` collection
- Ensure search returns in under 1 second
- **Manual Test Step:** Search with 50+ items → results appear instantly
- **User Test Prompt:** "Perform a search and confirm results load quickly."

**Definition of Done:**
- Search works across all fields
- Results ranked by relevance
- Search performs well

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S5 – AI Features (Metadata, Extraction, Suggestions)

**Objectives:**
- Implement URL metadata fetching
- Implement content extraction from URLs
- Generate AI tag and topic suggestions
- Support reprocessing failed extractions

**Tasks:**

### Task 1: Implement Metadata Fetching
- Create `app/services/metadata.py`
- Use `requests` + `BeautifulSoup` to fetch title, description, image, favicon
- Timeout: 10 seconds
- **Manual Test Step:** Paste URL in Save modal → metadata appears within 3 seconds
- **User Test Prompt:** "Paste a URL in the Save modal and confirm metadata loads automatically."

### Task 2: Implement Content Extraction
- Create `app/services/extraction.py`
- Use `beautifulsoup4` or `trafilatura` to extract main content
- Timeout: 15 seconds
- Store in `archived_text` field
- **Manual Test Step:** Save URL → after 5-10 seconds, item status changes to "processed"
- **User Test Prompt:** "Save a URL and wait. Confirm the item status changes to 'processed' after a few seconds."

### Task 3: Implement Background Processing
- Use FastAPI `BackgroundTasks` to process after item creation
- Fetch metadata → extract content → generate suggestions
- Update item with results
- **Manual Test Step:** Save URL → processing happens in background → item updates automatically
- **User Test Prompt:** "Save a URL and refresh the page after 10 seconds. Confirm archived content appears."

### Task 4: Implement AI Tag Suggestions
- Create `app/services/ai.py`
- Use Gemini API to generate 3-7 tag suggestions
- Consider user's existing tags for consistency
- Store in `suggested_tags` field
- **Manual Test Step:** After processing, open item detail → suggested tags appear
- **User Test Prompt:** "Open a processed item and confirm AI-suggested tags appear in the sidebar."

### Task 5: Implement Topic Classification
- Use Gemini API to generate single topic label
- Store in `suggested_topic` field
- **Manual Test Step:** After processing, open item detail → topic label appears
- **User Test Prompt:** "Open a processed item and confirm a topic label appears."

### Task 6: Implement Reprocess Endpoint
- Implement `POST /api/v1/items/:id/reprocess`
- Re-run extraction and AI suggestions
- **Manual Test Step:** Click "Reprocess" button on failed item → status changes to "pending" → eventually "processed"
- **User Test Prompt:** "Click the Reprocess button on a failed item and confirm it processes successfully."

**Definition of Done:**
- Metadata fetching works
- Content extraction works
- AI suggestions appear
- Reprocessing works

**Post-sprint:**
- Commit and push to `main`

---

## 🧩 S6 – Chat-Based Search (RAG Implementation)

**Objectives:**
- Implement RAG-based chat interface
- Provide answers with citations and excerpts
- Support chat threads and message history

**Tasks:**

### Task 1: Create Chat Models
- Create `app/models/chat.py` with ChatThread and ChatMessage models
- **Manual Test Step:** Import models → no errors
- **User Test Prompt:** "Run `python -c 'from app.models.chat import ChatThread'` and confirm no errors."

### Task 2: Implement Create Thread Endpoint
- Implement `POST /api/v1/chat/threads`
- Create thread with first user message
- Store in MongoDB `chat_threads` and `chat_messages` collections
- **Manual Test Step:** Open chat overlay, type message → thread created
- **User Test Prompt:** "Open the chat overlay, send a message, and confirm it appears."

### Task 3: Implement RAG Search
- Create `app/services/rag.py`
- Search user's items by keyword matching
- Retrieve top 3-5 relevant items
- **Manual Test Step:** Send chat message → relevant items found
- **User Test Prompt:** "Ask a question in chat about content you've saved and confirm you get a response."

### Task 4: Implement AI Answer Generation
- Use Gemini API to generate answer from retrieved items
- Include context from archived text
- **Manual Test Step:** Send chat message → AI generates contextual answer
- **User Test Prompt:** "Ask a question in chat and confirm the answer is relevant to your saved content."

### Task 5: Implement Citations
- Extract excerpts from relevant items
- Return citations with item ID, title, and excerpt
- **Manual Test Step:** Chat response includes citation cards with links
- **User Test Prompt:** "After receiving a chat answer, confirm citation cards appear below with links to items."

### Task 6: Implement List Threads Endpoint
- Implement `GET /api/v1/chat/threads`
- Return user's chat threads sorted by most recent
- **Manual Test Step:** Create multiple chats → threads list shows all
- **User Test Prompt:** "Create multiple chat conversations and confirm they all appear in the thread list."

### Task 7: Implement Get Thread Endpoint
- Implement `GET /api/v1/chat/threads/:id`
- Return thread with all messages
- **Manual Test Step:** Open existing thread → message history loads
- **User Test Prompt:** "Open a previous chat thread and confirm the conversation history loads."

**Definition of Done:**
- Chat interface works end-to-end
- RAG provides relevant answers
- Citations link to items
- Thread history persists

**Post-sprint:**
- Commit and push to `main`

---

## ✅ COMPLETION

After generating and saving this Backend-dev-plan.md file, switch to orchestrator mode to execute the development plan.
