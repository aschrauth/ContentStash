"""
Test script to verify the Relatedness section extraction issue and fix.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content

async def test_scarf_extraction():
    """Test extraction of the SCARF model article."""
    url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"
    
    print(f"Testing extraction from: {url}\n")
    print("=" * 80)
    
    content = await extract_content(url)
    
    if not content:
        print("ERROR: No content extracted!")
        return
    
    print(f"Extracted {len(content)} characters\n")
    
    # Check for all 5 SCARF sections
    sections = {
        "Status": "Status" in content,
        "Certainty": "Certainty" in content,
        "Autonomy": "Autonomy" in content,
        "Relatedness": "Relatedness" in content,
        "Fairness": "Fairness" in content
    }
    
    print("SCARF Sections Found:")
    print("-" * 40)
    for section, found in sections.items():
        status = "✓ FOUND" if found else "✗ MISSING"
        print(f"{section:15} {status}")
    
    print("\n" + "=" * 80)
    
    if not sections["Relatedness"]:
        print("\n⚠️  ISSUE CONFIRMED: Relatedness section is missing!")
        
        # Show a snippet around where Relatedness should be
        if "Autonomy" in content:
            autonomy_pos = content.find("Autonomy")
            snippet_start = max(0, autonomy_pos - 200)
            snippet_end = min(len(content), autonomy_pos + 1000)
            print("\nContent around Autonomy section:")
            print("-" * 40)
            print(content[snippet_start:snippet_end])
    else:
        print("\n✓ All SCARF sections present!")
        
        # Show the Relatedness section
        relatedness_pos = content.find("Relatedness")
        snippet_start = max(0, relatedness_pos - 100)
        snippet_end = min(len(content), relatedness_pos + 500)
        print("\nRelatedness section preview:")
        print("-" * 40)
        print(content[snippet_start:snippet_end])

if __name__ == "__main__":
    asyncio.run(test_scarf_extraction())