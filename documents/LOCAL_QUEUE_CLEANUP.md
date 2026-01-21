# Local Extraction Queue Cleanup

## Problem Summary

The local extraction queue showed 45 pending items. Investigation revealed that 44 of these items (98%) were stuck with content already extracted but still marked as pending, while only 1 item legitimately needed local extraction.

## Root Cause

Items were being successfully extracted via the browser extension and had their `archived_text` populated, but their `processing_status` was not being updated from `"pending_local_extraction"` to `"processed"`. This caused them to remain in the queue indefinitely.

## Investigation Results

### Total Items Analyzed: 45

**Stuck Items (with content):** 44 items
- These items had `archived_text` populated (ranging from 123 to 23,084 characters)
- Status was incorrectly set to `"pending_local_extraction"`
- Some even had chunks created, confirming successful processing
- Examples:
  - 21 duplicates of "The SCARF Model by David Rock" article
  - 13 duplicates of YouTube video about car chargers
  - 5 duplicates of "How Zapier rolled out AI" article

**Legitimate Items (without content):** 1 item
- ID: `69704561107cdc5e094be409`
- URL: Curious Beginner's Guide to AI Evaluations
- Correctly waiting for local extraction via browser extension

## Solution Implemented

Created two scripts to manage the local extraction queue:

### 1. Investigation Script: `backend/investigate_local_queue.py`

**Purpose:** Analyze items in the local extraction queue

**Usage:**
```bash
cd backend
source venv/bin/activate
python3 investigate_local_queue.py
```

**Output:**
- Total count of items in queue
- Categorization into stuck vs. legitimate items
- Detailed information for each item (ID, URL, title, status, content length)
- Recommendations for cleanup
- List of item IDs for reference

### 2. Cleanup Script: `backend/clear_local_queue.py`

**Purpose:** Clear stuck items and manage extraction types

**Commands:**

#### Clear All Stuck Items
```bash
# Dry run (preview changes)
python3 backend/clear_local_queue.py --clear-stuck

# Execute (actually clear items)
python3 backend/clear_local_queue.py --clear-stuck --execute
```

#### Change Extraction Type for Specific Item
```bash
python3 backend/clear_local_queue.py --change-type <item_id> <new_type>

# Example: Change to fast extraction
python3 backend/clear_local_queue.py --change-type 69704561107cdc5e094be409 fast
```

Valid extraction types: `fast`, `complete`, `local`

#### Clear Specific Items by ID
```bash
# Dry run
python3 backend/clear_local_queue.py --clear-ids <id1> <id2> <id3>

# Execute
python3 backend/clear_local_queue.py --clear-ids <id1> <id2> --execute
```

## Cleanup Execution

**Date:** January 21, 2026

**Action Taken:**
```bash
python3 backend/clear_local_queue.py --clear-stuck --execute
```

**Result:**
- ✅ Updated 44 items from `"pending_local_extraction"` to `"processed"`
- ✅ Queue reduced from 45 items to 1 legitimate item
- ✅ All stuck items now properly marked as processed

**Verification:**
```bash
python3 investigate_local_queue.py
```

Confirmed only 1 legitimate item remains in queue.

## Recommendations

### Prevent Future Issues

1. **Fix Browser Extension:** Update the browser extension to properly set `processing_status` to `"processed"` after successful extraction

2. **Add Status Validation:** Implement server-side validation to automatically update status when `archived_text` is populated

3. **Monitor Queue:** Periodically run the investigation script to catch stuck items early:
   ```bash
   python3 backend/investigate_local_queue.py
   ```

4. **Deduplicate Items:** Consider implementing duplicate detection to prevent multiple saves of the same URL

### When to Use These Scripts

**Use Investigation Script When:**
- Local queue count seems unusually high
- Items appear stuck in pending status
- Debugging extraction issues
- Regular maintenance checks

**Use Cleanup Script When:**
- Investigation reveals stuck items
- Need to change extraction type for items
- Clearing specific problematic items
- Bulk status updates needed

## Technical Details

### Database Queries

**Find Stuck Items:**
```javascript
{
  "extraction_type": "local",
  "processing_status": {"$in": ["pending", "pending_local_extraction"]},
  "archived_text": {"$exists": true, "$ne": "", "$ne": null}
}
```

**Update to Processed:**
```javascript
{
  "$set": {
    "processing_status": "processed",
    "updated_at": new Date()
  }
}
```

### Item Categories

1. **Stuck Items:** Have content but wrong status
   - Action: Update to `"processed"`
   - Safe to clear automatically

2. **Legitimate Items:** No content, waiting for extraction
   - Action: Keep in queue OR change extraction type
   - Requires user decision

## Files Created

- [`backend/investigate_local_queue.py`](../backend/investigate_local_queue.py) - Investigation script
- [`backend/clear_local_queue.py`](../backend/clear_local_queue.py) - Cleanup script
- [`documents/LOCAL_QUEUE_CLEANUP.md`](LOCAL_QUEUE_CLEANUP.md) - This documentation

## Summary

The local extraction queue issue was successfully resolved by:
1. Identifying 44 stuck items with content but incorrect status
2. Creating diagnostic and cleanup scripts
3. Safely clearing the stuck items
4. Reducing queue from 45 to 1 legitimate item

The scripts are now available for future maintenance and troubleshooting.