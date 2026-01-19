"""
Test the updated extraction service with Playwright support.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.extraction import extract_content

# The problematic URL
test_url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"

print(f"Testing URL: {test_url}\n")
print("=" * 80)
print("\nTesting extract_content with Playwright fallback...\n")

try:
    content = extract_content(test_url)
    
    if content:
        print(f"✓ Successfully extracted {len(content):,} characters")
        print(f"\nFirst 1000 characters:")
        print("-" * 80)
        print(content[:1000])
        print("-" * 80)
        
        print(f"\nLast 500 characters:")
        print("-" * 80)
        print(content[-500:])
        print("-" * 80)
        
        # Count sections/headings
        heading_count = content.count('###') + content.count('##') + content.count('#')
        print(f"\n✓ Found {heading_count} headings in the content")
        
        # Estimate paragraphs
        paragraph_count = content.count('\n\n')
        print(f"✓ Estimated {paragraph_count} paragraphs")
        
        # Check if we got the full SCARF model content
        scarf_elements = ['Status', 'Certainty', 'Autonomy', 'Relatedness', 'Fairness']
        found_elements = [elem for elem in scarf_elements if elem in content]
        print(f"\n✓ Found {len(found_elements)}/{len(scarf_elements)} SCARF elements: {', '.join(found_elements)}")
        
        if len(content) > 2000:
            print(f"\n✅ SUCCESS: Extracted full article content ({len(content):,} characters)")
        else:
            print(f"\n⚠️  WARNING: Content seems short ({len(content):,} characters)")
    else:
        print("✗ Extraction returned None")
        
except Exception as e:
    print(f"✗ Error during extraction: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)