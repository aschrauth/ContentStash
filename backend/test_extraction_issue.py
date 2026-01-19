"""
Test script to investigate content extraction issue with specific URL.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.extraction import extract_content
import requests
from readability import Document
from markdownify import markdownify as md

# The problematic URL
test_url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"

print(f"Testing URL: {test_url}\n")
print("=" * 80)

# Step 1: Fetch the raw HTML
print("\n1. Fetching raw HTML...")
try:
    response = requests.get(test_url, timeout=10)
    response.raise_for_status()
    html_length = len(response.text)
    print(f"   ✓ Successfully fetched HTML ({html_length:,} characters)")
    
    # Save raw HTML for inspection
    with open('debug_raw_html.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"   ✓ Saved raw HTML to debug_raw_html.html")
except Exception as e:
    print(f"   ✗ Error fetching HTML: {e}")
    sys.exit(1)

# Step 2: Parse with readability
print("\n2. Parsing with readability-lxml...")
try:
    doc = Document(response.text)
    html_content = doc.summary()
    readability_length = len(html_content)
    print(f"   ✓ Readability extracted {readability_length:,} characters of HTML")
    
    # Save readability output
    with open('debug_readability_output.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"   ✓ Saved readability output to debug_readability_output.html")
    
    # Count paragraphs in readability output
    p_count = html_content.count('<p>')
    print(f"   ℹ Found {p_count} <p> tags in readability output")
    
except Exception as e:
    print(f"   ✗ Error with readability: {e}")
    sys.exit(1)

# Step 3: Convert to markdown
print("\n3. Converting to markdown...")
try:
    markdown_content = md(
        html_content,
        heading_style="ATX",
        strip=['script', 'style']
    )
    markdown_length = len(markdown_content)
    print(f"   ✓ Converted to markdown ({markdown_length:,} characters)")
    
    # Save markdown output
    with open('debug_markdown_output.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"   ✓ Saved markdown to debug_markdown_output.md")
    
    # Count paragraphs in markdown (rough estimate)
    paragraph_count = markdown_content.count('\n\n')
    print(f"   ℹ Estimated {paragraph_count} paragraphs in markdown")
    
except Exception as e:
    print(f"   ✗ Error converting to markdown: {e}")
    sys.exit(1)

# Step 4: Use the actual extraction function
print("\n4. Testing actual extract_content function...")
try:
    extracted = extract_content(test_url)
    if extracted:
        print(f"   ✓ Function extracted {len(extracted):,} characters")
        print(f"\n   First 500 characters:")
        print(f"   {'-' * 76}")
        print(f"   {extracted[:500]}")
        print(f"   {'-' * 76}")
        
        print(f"\n   Last 500 characters:")
        print(f"   {'-' * 76}")
        print(f"   {extracted[-500:]}")
        print(f"   {'-' * 76}")
    else:
        print(f"   ✗ Function returned None")
except Exception as e:
    print(f"   ✗ Error with extract_content: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test complete. Check the debug_*.html and debug_*.md files for details.")