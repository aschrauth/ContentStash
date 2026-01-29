"""
Test script to verify enhanced content cleaning for IndieWire articles.
Tests that author bios, sharing widgets, and "Read More" sections are properly removed.
"""
import asyncio
from app.services.extraction import extract_content

async def test_indiewire_extraction():
    url = 'https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/'
    
    print("=" * 80)
    print("Testing IndieWire Content Extraction with Enhanced Cleaning")
    print("=" * 80)
    print(f"\nURL: {url}\n")
    
    # Extract content using complete mode (Playwright)
    content, method = await extract_content(url, extraction_type="complete")
    
    if content:
        print(f"✓ Extraction successful using method: {method}")
        print(f"✓ Content length: {len(content)} characters")
        print("\n" + "=" * 80)
        print("CHECKING FOR UNWANTED CONTENT:")
        print("=" * 80)
        
        # Check for problematic patterns that should be removed
        unwanted_patterns = {
            'Author Bio': [
                'has joined',
                'courtesy of',
                'more stories by',
                'brian welk',
                'senior business reporter'
            ],
            'Sharing Widget': [
                'share on facebook',
                'post to tumblr',
                'share to flipboard',
                'submit to reddit',
                'pin it',
                'share on whatsapp',
                'print this page',
                'show more sharing options',
                'share on linkedin'
            ],
            'Read More Section': [
                'read more',
                'a24',
                'pillion',
                'daily headlines'
            ],
            'Newsletter Signup': [
                'daily headlines covering',
                'sign up',
                'newsletter'
            ]
        }
        
        issues_found = []
        for category, patterns in unwanted_patterns.items():
            found_patterns = []
            for pattern in patterns:
                if pattern.lower() in content.lower():
                    found_patterns.append(pattern)
            
            if found_patterns:
                issues_found.append((category, found_patterns))
                print(f"\n✗ {category} - Found unwanted content:")
                for pattern in found_patterns:
                    print(f"  - '{pattern}'")
            else:
                print(f"\n✓ {category} - Clean (no unwanted content)")
        
        print("\n" + "=" * 80)
        if issues_found:
            print("❌ CLEANING INCOMPLETE - Issues found:")
            for category, patterns in issues_found:
                print(f"  {category}: {', '.join(patterns)}")
        else:
            print("✅ ALL UNWANTED CONTENT SUCCESSFULLY REMOVED")
        print("=" * 80)
        
        # Show a preview of the cleaned content
        print("\n" + "=" * 80)
        print("CONTENT PREVIEW (first 1000 characters):")
        print("=" * 80)
        print(content[:1000])
        print("...")
        print("=" * 80)
        
    else:
        print("✗ Extraction failed")
        print(f"Method attempted: {method}")

if __name__ == "__main__":
    asyncio.run(test_indiewire_extraction())