# Local Extraction Immediate Queue Processing Plan (Chrome Extension)

## Goal
Process local-extraction queue items within seconds of being queued, while keeping CPU, memory, and network overhead very low on Chrome clients.

## Current Bottleneck
The extension primarily discovers queued local items via fixed-interval polling (default 15 minutes). This is efficient, but it can delay processing for newly queued items.

## Proposed Approach: Event-Hinted + Adaptive Polling (Lightweight)

### 1) Add a tiny "queue hint" endpoint on the backend
Create a very lightweight endpoint that returns only queue metadata for the current user (no item payload):

- `GET /api/v1/items/pending-local/hint`
- Response shape:
  - `pending_count: number`
  - `queue_version: string` (monotonic timestamp/version hash that changes whenever a user's local queue changes)
  - `recommended_poll_seconds: number` (server guidance; e.g. 5 when queue > 0, 900 when empty)

Implementation notes:
- Keep this endpoint DB-cheap: use count + latest `updated_at` among matching queue docs.
- Return small JSON (< 200 bytes typical).
- Optional: add `ETag` / `If-None-Match` support so unchanged responses become HTTP 304.

Why this is lightweight:
- Most checks avoid fetching full queued items.
- Tiny payload and optional 304 significantly reduce bandwidth.

### 2) Replace fixed polling with adaptive alarm cadence
In service worker:

- Keep one alarm (`pollPendingItems`) but adapt the next fire time using the hint response:
  - If `pending_count > 0`: poll aggressively for a short period (e.g. every 5-10s) until queue drains.
  - If empty: fall back to low-frequency checks (e.g. 60s for a brief warm window after activity, then 15m steady-state).
- Add jitter (±10%) to avoid synchronized clients.
- Enforce **single in-flight request per extension instance** (if one poll/process cycle is running, skip starting another).

Why this is lightweight:
- High-frequency checks happen only when there is actual work.
- Idle users remain at low frequency.

### 3) Immediate trigger on known queue-creation actions
When the extension itself performs actions likely to create queue work, run `processPendingItems()` immediately (no wait for next alarm):

- After login success
- After extraction type/settings changes that enable polling
- On popup "Save" success when extraction type is local (or when a URL save could cascade to local)

Why this is lightweight:
- Zero background churn; only action-driven.

### 4) Fast claim + process loop to avoid duplicate work
Before processing each item, claim it atomically server-side to prevent duplicate extraction from multiple extension instances:

- New endpoint: `POST /api/v1/items/{id}/claim-local`
- Transition only if status is `pending` or `pending_local_extraction` -> `processing` with short claim TTL metadata.

If claim fails, skip item.

Why this matters:
- Prevents redundant tab launches and extraction work.
- Reduces CPU and network waste in multi-device scenarios.

### 5) Keep heavy extraction path unchanged
Do not add always-on background tabs or persistent connections.
Only change *how quickly* queue checks happen and when full item payload is fetched.

### 6) Simplify extension settings UI
Remove manual polling controls from the popup/settings UI:

- Remove "Enable automatic polling for pending items" toggle
- Remove "Polling interval (minutes)" input
- Keep polling internal and adaptive (not user-tunable)

Why this is lightweight and safer:
- Avoids users setting overly aggressive intervals that increase load
- Keeps behavior predictable and aligned with server guidance

### 7) Failure + backoff strategy
If hint endpoint or item fetch fails:

- Exponential backoff on next alarm (15s -> 30s -> 60s -> 5m max)
- Reset backoff on success
- Never spin loops in-memory; always reschedule via `chrome.alarms`

This keeps the worker sleep-friendly and resilient.

## Optional Near-Real-Time Enhancement (Phase 2)
If needed later, add server-sent queue signals (SSE/WebPush). Keep this optional because it increases complexity and can keep processes alive longer.

## Rollout Plan

### Phase 1 (low risk, immediate value)
1. Add `/pending-local/hint` backend endpoint.
2. Add adaptive cadence logic to service worker alarm scheduling.
3. Enforce single in-flight request guard in service worker poll/process paths.
4. Trigger immediate `processPendingItems()` on known extension actions.
5. Remove polling interval/toggle controls from extension settings UI.
6. Add telemetry logs around hint latency and queue-to-processing lag.

### Phase 2 (consistency and scale)
1. Add atomic claim endpoint.
2. Update extension to claim before extraction.
3. Add stale-claim recovery (TTL expiry).

### Phase 3 (optional ultra-low latency)
1. Evaluate SSE/WebPush only if Phase 1/2 latency is insufficient.

## Expected Outcomes
- Typical queue start latency drops from up to 15 minutes to ~5-30 seconds.
- Idle resource usage remains close to current behavior.
- Active resource usage scales with real queue work, not constant polling.

## Acceptance Criteria
- P95 time from queue insertion to first extraction attempt < 30s (with extension authenticated/open profile).
- No measurable increase in idle CPU usage.
- < 1 duplicate extraction attempt per 1,000 queued items across multi-device users.
- Poll/network volume lower than naive 5-second full-item polling.
- Extension settings no longer expose manual polling interval controls.
