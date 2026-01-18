"""
Test script to verify the citation fix works correctly.
"""
import asyncio
import re
from app.models.chat import Citation

# Simulate the fixed _parse_answer_with_citations function
async def test_parse_answer_with_citations():
    """Test the citation parsing logic."""
    
    # Mock data
    # Test with comma-separated format (what Gemini actually generates)
    response_text = "Based on the evidence, Python is great [2, 3]. It's also versatile [2, 3]. Many developers use it [2, 3]. It has great libraries [2, 3]."
    
    chunks = [
        {"item_id": "item1", "text": "Python is a high-level programming language..."},
        {"item_id": "item2", "text": "Python has extensive library support..."},
        {"item_id": "item2", "text": "Python is used in web development..."},
        {"item_id": "item3", "text": "Python is popular for data science..."},
    ]
    
    source_mapping = {
        1: "Introduction to Python",
        2: "Python Libraries Guide", 
        3: "Python in Data Science"
    }
    
    # Extract answer
    answer = response_text.strip()
    
    # Build a mapping of item_id to chunk for quick lookup
    item_to_chunk = {}
    for chunk in chunks:
        item_id = chunk.get('item_id')
        if item_id and item_id not in item_to_chunk:
            item_to_chunk[item_id] = chunk
    
    # Build mapping: item_id -> source number (mimicking _build_evidence_from_chunks logic)
    item_to_number = {}
    seen_items = {}
    current_number = 1
    
    for chunk in chunks:
        item_id = chunk.get('item_id')
        if item_id and item_id not in seen_items:
            seen_items[item_id] = current_number
            item_to_number[item_id] = current_number
            current_number += 1
    
    print("Item to number mapping:", item_to_number)
    
    # Find all numbered citations in the answer
    # Handles both [1] and [1, 2, 3] formats
    citation_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
    matches = re.findall(citation_pattern, answer)
    
    # Extract individual numbers from matches (handles comma-separated lists)
    cited_numbers = set()
    for match in matches:
        # Split by comma and extract each number
        numbers = re.findall(r'\d+', match)
        cited_numbers.update(numbers)
    
    print(f"Cited numbers found: {cited_numbers}")
    
    # Generate citations for cited sources
    citations = []
    seen_source_numbers = set()
    
    for num_str in sorted(cited_numbers, key=int):
        source_num = int(num_str)
        
        # Skip if we've already created a citation for this source number
        if source_num in seen_source_numbers:
            continue
        
        # Get the title for this source number
        title = source_mapping.get(source_num)
        if not title:
            print(f"Warning: No title found for source {source_num}")
            continue
        
        # Find the corresponding chunk/item for this source number
        matching_item_id = None
        for item_id, num in item_to_number.items():
            if num == source_num:
                matching_item_id = item_id
                break
        
        if not matching_item_id:
            print(f"Warning: No matching item_id for source {source_num}")
            continue
        
        seen_source_numbers.add(source_num)
        chunk = item_to_chunk.get(matching_item_id)
        
        # Create excerpt from chunk text
        excerpt = "No preview available"
        if chunk:
            text = chunk.get('text', '')
            excerpt = text[:200]
            if len(text) > 200:
                excerpt += "..."
        
        citation = Citation(
            id=str(matching_item_id),
            title=f"{source_num}. {title}",
            excerpt=excerpt
        )
        citations.append(citation)
        print(f"Created citation: {citation.title}")
    
    print(f"\nTotal citations created: {len(citations)}")
    print(f"Expected: 2 citations (for sources 2 and 3)")
    
    return answer, citations

# Run the test
if __name__ == "__main__":
    asyncio.run(test_parse_answer_with_citations())