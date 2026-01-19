# Citation Fix Summary

## Problem
The citation system was completely broken - NO sources were showing up in the SOURCES section, even though the response text contained citation references like `[2, 3]`.

## Root Cause
The issue was in the `_parse_answer_with_citations` function in [`backend/app/services/rag.py`](backend/app/services/rag.py:431). There were two problems:

1. **Regex Pattern Mismatch**: The regex pattern `r'\[(\d+)\]'` only matched single-number citations like `[2]` or `[3]`, but Gemini was generating comma-separated citations like `[2, 3]`. This caused the regex to find zero matches, resulting in an empty citations list.

2. **Async Mapping Issue**: The previous fix attempted to build `item_to_number` mapping by calling `await _get_item_metadata(chunk)` in a regular loop, which wouldn't work properly. The new fix replicates the same logic used in `_build_evidence_from_chunks` to build the mapping synchronously.

## Solution
Updated the citation parsing logic to:

1. **Handle Multiple Citation Formats**: New regex pattern `r'\[(\d+(?:,\s*\d+)*)\]'` matches both:
   - Single citations: `[1]`, `[2]`, `[3]`
   - Comma-separated citations: `[1, 2]`, `[2, 3]`, `[1, 2, 3]`

2. **Extract Individual Numbers**: After matching, extract all individual numbers from comma-separated lists:
   ```python
   cited_numbers = set()
   for match in matches:
       numbers = re.findall(r'\d+', match)
       cited_numbers.update(numbers)
   ```

3. **Fixed Mapping Logic**: Replicate the exact same item-to-number mapping logic from `_build_evidence_from_chunks` to ensure consistency:
   ```python
   item_to_number = {}
   seen_items = {}
   current_number = 1
   
   for chunk in chunks:
       item_id = chunk.get('item_id')
       if item_id and item_id not in seen_items:
           seen_items[item_id] = current_number
           item_to_number[item_id] = current_number
           current_number += 1
   ```

## Testing
Created [`backend/test_citation_fix.py`](backend/test_citation_fix.py) to verify the fix works correctly:
- Tests citation parsing with comma-separated format `[2, 3]`
- Confirms that all unique source numbers are extracted
- Verifies that correct citations are created

Test output:
```
Item to number mapping: {'item1': 1, 'item2': 2, 'item3': 3}
Cited numbers found: {'2', '3'}
Created citation: 2. Python Libraries Guide
Created citation: 3. Python in Data Science

Total citations created: 2
Expected: 2 citations (for sources 2 and 3)
```

## Result
✅ Citations now properly appear in the SOURCES section
✅ All unique sources referenced in the response are displayed
✅ Works with both single `[1]` and comma-separated `[1, 2, 3]` citation formats
✅ Committed and pushed to testing branch

## Files Changed
- [`backend/app/services/rag.py`](backend/app/services/rag.py:431) - Fixed citation parsing logic
- [`backend/test_citation_fix.py`](backend/test_citation_fix.py) - Added test script