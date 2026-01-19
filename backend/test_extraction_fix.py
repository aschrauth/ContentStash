"""
Test script to verify the extraction fix for removing JSON formatting tags and extra content.
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content

async def test_extraction():
    """Test extraction with the problematic URL"""
    url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"
    
    print(f"Testing extraction for: {url}\n")
    print("=" * 80)
    
    content = await extract_content(url)
    
    if content:
        print(f"Extracted {len(content)} characters\n")
        print("First 1000 characters:")
        print("-" * 80)
        print(content[:1000])
        print("-" * 80)
        print("\nLast 1000 characters:")
        print("-" * 80)
        print(content[-1000:])
        print("-" * 80)
        
        # Check for problematic patterns
        issues = []
        if '[ { "type": "highlight"' in content:
            issues.append("❌ JSON formatting tags found")
        else:
            print("✅ No JSON formatting tags found")
            
        if '"shape": "marker"' in content:
            issues.append("❌ JSON metadata found")
        else:
            print("✅ No JSON metadata found")
            
        # Check for common navigation/footer elements
        footer_indicators = ['Related articles', 'Share this', 'Subscribe', 'Newsletter']
        for indicator in footer_indicators:
            if indicator.lower() in content.lower():
                issues.append(f"⚠️  Possible extra content: '{indicator}' found")
        
        if not issues:
            print("\n✅ Extraction looks clean!")
        else:
            print("\n⚠️  Issues found:")
            for issue in issues:
                print(f"  {issue}")
    else:
        print("❌ Extraction failed - no content returned")

if __name__ == "__main__":
    asyncio.run(test_extraction())