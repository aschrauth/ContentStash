"""
Test script to verify the embedding model fix works correctly.
This tests that the Gemini service can generate embeddings with the current model.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.gemini import gemini_service


async def test_embedding_generation():
    """Test that embedding generation works with the new model"""
    
    print("Testing Gemini embedding generation with models/gemini-embedding-001...")
    print("-" * 60)
    
    # Check if service is available
    if not gemini_service.is_available():
        print("❌ Gemini service is not configured (API key missing)")
        return False
    
    print("✓ Gemini service is configured")
    
    # Test single embedding
    test_text = "This is a test query for vector search"
    print(f"\nTest text: '{test_text}'")
    
    try:
        embedding = gemini_service.embed_content(test_text)
        
        if not embedding:
            print("❌ No embedding returned")
            return False
        
        print(f"✓ Embedding generated successfully")
        print(f"  - Dimension: {len(embedding)}")
        print(f"  - First 5 values: {embedding[:5]}")
        
        # Verify dimension is 3072 (expected for models/gemini-embedding-001)
        if len(embedding) != 3072:
            print(f"⚠️  Warning: Expected 3072 dimensions, got {len(embedding)}")
        else:
            print("✓ Embedding dimension is correct (3072)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating embedding: {str(e)}")
        return False


async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("EMBEDDING MODEL FIX VERIFICATION")
    print("=" * 60 + "\n")
    
    success = await test_embedding_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        print("\nThe embedding model fix is working correctly!")
        print("You can now use AI search functionality.")
    else:
        print("❌ TESTS FAILED")
        print("\nPlease check:")
        print("1. GEMINI_API_KEY is set in your .env file")
        print("2. The API key is valid and has quota available")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
