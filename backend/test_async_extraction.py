"""
Test script to verify async Playwright extraction works correctly.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content

async def test_extraction():
    """Test extraction with the problematic URL."""
    url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"
    
    print(f"Testing extraction from: {url}")
    print("-" * 80)
    
    try:
        content = await extract_content(url)
        
        if content:
            print(f"✅ SUCCESS! Extracted {len(content)} characters")
            print("\nFirst 500 characters of content:")
            print("-" * 80)
            print(content[:500])
            print("-" * 80)
            return True
        else:
            print("❌ FAILED: No content extracted")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_extraction())
    sys.exit(0 if success else 1)